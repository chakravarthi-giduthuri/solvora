"""Tests for analytics endpoints.

Endpoints:
  GET /api/v1/analytics/summary
  GET /api/v1/analytics/custom?date_from=...&date_to=...
  GET /api/v1/analytics/export?date_from=...&date_to=...  (auth required)

Validation in /custom:
  - Non-ISO date → 400
  - date_from >= date_to → 400
  - Range > 365 days → 400
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_token(client: AsyncClient, suffix: str) -> str:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"analytics_{suffix}@example.com",
            "password": "TestPass123!",
            "name": f"Analytics User {suffix}",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="analytics/summary uses PostgreSQL-specific SQL (date_trunc) not supported by SQLite")
async def test_analytics_summary_returns_200(client: AsyncClient) -> None:
    """GET /analytics/summary returns 200."""
    resp = await client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200


@pytest.mark.xfail(reason="analytics/summary uses PostgreSQL-specific SQL (date_trunc) not supported by SQLite")
async def test_analytics_summary_returns_dict(client: AsyncClient) -> None:
    """GET /analytics/summary body is a JSON object."""
    resp = await client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


# ---------------------------------------------------------------------------
# GET /analytics/custom — happy paths
# ---------------------------------------------------------------------------


async def test_custom_analytics_valid_range(client: AsyncClient) -> None:
    """Custom date range with valid ISO dates returns 200."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-01-01&date_to=2025-06-30"
    )
    assert resp.status_code == 200


async def test_custom_analytics_contains_required_keys(client: AsyncClient) -> None:
    """Custom analytics response contains total_problems and by_platform."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-01-01&date_to=2025-12-31"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_problems" in data
    assert "by_platform" in data


async def test_custom_analytics_contains_by_category(client: AsyncClient) -> None:
    """Custom analytics response includes by_category."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-01-01&date_to=2025-12-31"
    )
    assert resp.status_code == 200
    assert "by_category" in resp.json()


async def test_custom_analytics_echoes_date_range(client: AsyncClient) -> None:
    """Response echoes back the requested date_from and date_to."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-03-01&date_to=2025-09-01"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_from"] == "2025-03-01"
    assert data["date_to"] == "2025-09-01"


async def test_custom_analytics_total_problems_is_int(client: AsyncClient) -> None:
    """total_problems is an integer."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-01-01&date_to=2025-12-31"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["total_problems"], int)


# ---------------------------------------------------------------------------
# GET /analytics/custom — validation failures
# ---------------------------------------------------------------------------


async def test_custom_analytics_invalid_date_format(client: AsyncClient) -> None:
    """Non-ISO date_from returns 400."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=not-a-date&date_to=2025-12-31"
    )
    assert resp.status_code == 400


async def test_custom_analytics_invalid_date_to_format(client: AsyncClient) -> None:
    """Non-ISO date_to returns 400."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-01-01&date_to=tomorrow"
    )
    assert resp.status_code == 400


async def test_custom_analytics_date_from_after_date_to(client: AsyncClient) -> None:
    """date_from after date_to returns 400."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-12-31&date_to=2025-01-01"
    )
    assert resp.status_code == 400


async def test_custom_analytics_date_from_equal_date_to(client: AsyncClient) -> None:
    """date_from equal to date_to returns 400 (must be strictly before)."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2025-06-01&date_to=2025-06-01"
    )
    assert resp.status_code == 400


async def test_custom_analytics_range_over_365_days(client: AsyncClient) -> None:
    """Date range exceeding 365 days returns 400."""
    resp = await client.get(
        "/api/v1/analytics/custom?date_from=2024-01-01&date_to=2025-12-31"
    )
    assert resp.status_code == 400


async def test_custom_analytics_missing_date_from(client: AsyncClient) -> None:
    """Omitting date_from returns 422 (required query param)."""
    resp = await client.get("/api/v1/analytics/custom?date_to=2025-12-31")
    assert resp.status_code == 422


async def test_custom_analytics_missing_date_to(client: AsyncClient) -> None:
    """Omitting date_to returns 422 (required query param)."""
    resp = await client.get("/api/v1/analytics/custom?date_from=2025-01-01")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /analytics/export — auth guard
# ---------------------------------------------------------------------------


async def test_export_analytics_requires_auth(client: AsyncClient) -> None:
    """CSV export without auth returns 401."""
    resp = await client.get(
        "/api/v1/analytics/export?date_from=2025-01-01&date_to=2025-12-31"
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /analytics/export — authenticated
# ---------------------------------------------------------------------------


async def test_export_analytics_csv_authenticated(client: AsyncClient) -> None:
    """Authenticated CSV export returns 200 with text/csv content-type."""
    token = await _get_token(client, "export1")
    resp = await client.get(
        "/api/v1/analytics/export?date_from=2025-01-01&date_to=2025-12-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


async def test_export_analytics_csv_has_header_row(client: AsyncClient) -> None:
    """The exported CSV contains the expected header row."""
    token = await _get_token(client, "export2")
    resp = await client.get(
        "/api/v1/analytics/export?date_from=2025-01-01&date_to=2025-12-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    first_line = resp.text.splitlines()[0] if resp.text else ""
    assert "date" in first_line
    assert "platform" in first_line
    assert "problem_count" in first_line


async def test_export_analytics_has_content_disposition(client: AsyncClient) -> None:
    """Export response includes a Content-Disposition header for file download."""
    token = await _get_token(client, "export3")
    resp = await client.get(
        "/api/v1/analytics/export?date_from=2025-01-01&date_to=2025-03-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
