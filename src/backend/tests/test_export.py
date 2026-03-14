"""Tests for the problem export endpoint.

Endpoint:
  GET /api/v1/problems/{problem_id}/export?format=markdown|pdf

- Valid format values: markdown, pdf
- Invalid format → 422 (FastAPI regex validation)
- Unknown problem_id → 404
- PDF requires weasyprint; if missing, returns 501

The test creates a problem via POST /api/v1/submit so the data lives in the
test DB. No external services are called.
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper — create an authenticated user and submit a problem
# ---------------------------------------------------------------------------


async def _signup_and_submit(
    client: AsyncClient, suffix: str
) -> tuple[str, str]:
    """Sign up a user, submit a problem, return (problem_id, access_token)."""
    email = f"exporter_{suffix}@example.com"
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPass123!", "name": f"Exporter {suffix}"},
    )
    assert signup_resp.status_code == 201, signup_resp.text
    token = signup_resp.json()["access_token"]

    submit_resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "A problem for export endpoint integration testing",
            "body": "This description is long enough to satisfy the body minimum length validation.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_resp.status_code == 201, submit_resp.text
    problem_id = submit_resp.json()["id"]
    return problem_id, token


# ---------------------------------------------------------------------------
# Markdown export — happy path
# ---------------------------------------------------------------------------


async def test_export_markdown_returns_200(client: AsyncClient) -> None:
    """GET /problems/{id}/export?format=markdown returns 200."""
    problem_id, _ = await _signup_and_submit(client, "md1")
    resp = await client.get(f"/api/v1/problems/{problem_id}/export?format=markdown")
    assert resp.status_code == 200


async def test_export_markdown_content_type(client: AsyncClient) -> None:
    """Markdown export has text/markdown content-type."""
    problem_id, _ = await _signup_and_submit(client, "md2")
    resp = await client.get(f"/api/v1/problems/{problem_id}/export?format=markdown")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers.get("content-type", "")


async def test_export_markdown_contains_title(client: AsyncClient) -> None:
    """The exported markdown document includes the problem title."""
    problem_id, _ = await _signup_and_submit(client, "md3")
    resp = await client.get(f"/api/v1/problems/{problem_id}/export?format=markdown")
    assert resp.status_code == 200
    assert "A problem for export endpoint integration testing" in resp.text


async def test_export_markdown_has_content_disposition(client: AsyncClient) -> None:
    """Markdown export includes a Content-Disposition attachment header."""
    problem_id, _ = await _signup_and_submit(client, "md4")
    resp = await client.get(f"/api/v1/problems/{problem_id}/export?format=markdown")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")


async def test_export_markdown_default_format(client: AsyncClient) -> None:
    """Omitting format defaults to markdown and returns 200."""
    problem_id, _ = await _signup_and_submit(client, "md5")
    resp = await client.get(f"/api/v1/problems/{problem_id}/export")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


async def test_export_invalid_format_returns_422(client: AsyncClient) -> None:
    """An unsupported format value returns 422."""
    resp = await client.get("/api/v1/problems/some-id/export?format=docx")
    assert resp.status_code == 422


async def test_export_invalid_format_html_returns_422(client: AsyncClient) -> None:
    """format=html is not in the allowed regex, returns 422."""
    resp = await client.get("/api/v1/problems/some-id/export?format=html")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


async def test_export_nonexistent_problem_returns_404(client: AsyncClient) -> None:
    """Exporting a problem that does not exist returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/problems/{fake_id}/export?format=markdown")
    assert resp.status_code == 404


async def test_export_inactive_problem_returns_404(client: AsyncClient) -> None:
    """The export endpoint checks is_active=True; an unknown id returns 404."""
    resp = await client.get(
        "/api/v1/problems/nonexistent-problem-id-xyz/export?format=markdown"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth — export does NOT require authentication (public endpoint)
# ---------------------------------------------------------------------------


async def test_export_does_not_require_auth(client: AsyncClient) -> None:
    """Markdown export can be accessed without authentication."""
    problem_id, _ = await _signup_and_submit(client, "noauth1")
    # Request without Authorization header
    resp = await client.get(f"/api/v1/problems/{problem_id}/export?format=markdown")
    assert resp.status_code == 200
