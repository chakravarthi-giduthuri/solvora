"""Tests for the Leaderboard API endpoint.

GET /api/v1/leaderboard accepts:
  - type:   problems | solutions | categories  (regex-validated)
  - period: 24h | 7d | 30d                     (regex-validated)

No authentication is required.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_leaderboard_envelope(data: dict, expected_type: str, expected_period: str) -> None:
    """Assert that the response contains the expected leaderboard envelope."""
    assert "items" in data
    assert "type" in data
    assert "period" in data
    assert "generated_at" in data
    assert isinstance(data["items"], list)
    assert data["type"] == expected_type
    assert data["period"] == expected_period


# ---------------------------------------------------------------------------
# Default behaviour (no query params)
# ---------------------------------------------------------------------------


async def test_leaderboard_default_returns_list(client: AsyncClient) -> None:
    """GET /api/v1/leaderboard with no params returns 200 and a valid envelope.

    Default type is 'problems', default period is '7d'.  No auth is needed.
    """
    response = await client.get("/api/v1/leaderboard")

    assert response.status_code == 200
    data = response.json()
    _assert_leaderboard_envelope(data, expected_type="problems", expected_period="7d")


# ---------------------------------------------------------------------------
# type parameter variations
# ---------------------------------------------------------------------------


async def test_leaderboard_by_problems_type(client: AsyncClient) -> None:
    """GET /api/v1/leaderboard?type=problems returns a problems leaderboard."""
    response = await client.get("/api/v1/leaderboard", params={"type": "problems"})

    assert response.status_code == 200
    _assert_leaderboard_envelope(response.json(), expected_type="problems", expected_period="7d")


async def test_leaderboard_by_solutions_type(client: AsyncClient) -> None:
    """GET /api/v1/leaderboard?type=solutions returns a solutions leaderboard."""
    response = await client.get("/api/v1/leaderboard", params={"type": "solutions"})

    assert response.status_code == 200
    _assert_leaderboard_envelope(response.json(), expected_type="solutions", expected_period="7d")


# ---------------------------------------------------------------------------
# period parameter variations
# ---------------------------------------------------------------------------


async def test_leaderboard_24h_period(client: AsyncClient) -> None:
    """GET /api/v1/leaderboard?period=24h returns a 24-hour window leaderboard."""
    response = await client.get("/api/v1/leaderboard", params={"period": "24h"})

    assert response.status_code == 200
    _assert_leaderboard_envelope(response.json(), expected_type="problems", expected_period="24h")


async def test_leaderboard_7d_period(client: AsyncClient) -> None:
    """GET /api/v1/leaderboard?period=7d returns a 7-day window leaderboard."""
    response = await client.get("/api/v1/leaderboard", params={"period": "7d"})

    assert response.status_code == 200
    _assert_leaderboard_envelope(response.json(), expected_type="problems", expected_period="7d")


async def test_leaderboard_30d_period(client: AsyncClient) -> None:
    """GET /api/v1/leaderboard?period=30d returns a 30-day window leaderboard."""
    response = await client.get("/api/v1/leaderboard", params={"period": "30d"})

    assert response.status_code == 200
    _assert_leaderboard_envelope(response.json(), expected_type="problems", expected_period="30d")
