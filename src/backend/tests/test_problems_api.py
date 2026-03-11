"""Tests for the Problems REST API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# List / pagination
# ---------------------------------------------------------------------------

async def test_list_problems_returns_paginated_response(
    client: AsyncClient,
    sample_problem,
) -> None:
    """GET /problems should return a paginated envelope with items and total."""
    response = await client.get("/api/v1/problems/")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert data["total"] >= 1


async def test_list_problems_pagination_params(client: AsyncClient) -> None:
    """skip and limit query params are forwarded correctly."""
    response = await client.get("/api/v1/problems/?skip=0&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

async def test_filter_by_platform(
    client: AsyncClient,
    sample_problem,
) -> None:
    """Filtering by platform=reddit should only return reddit problems."""
    response = await client.get("/api/v1/problems/?platform=reddit")

    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["platform"] == "reddit"


async def test_filter_by_platform_returns_empty_for_unknown(
    client: AsyncClient,
) -> None:
    """Filtering by an unused platform value returns an empty list."""
    response = await client.get("/api/v1/problems/?platform=unknown_platform")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


async def test_filter_by_category(
    client: AsyncClient,
    sample_problem,
    sample_category,
) -> None:
    """Filtering by category_id should restrict results to that category."""
    category_id = sample_category.id
    response = await client.get(f"/api/v1/problems/?category_id={category_id}")

    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["category_id"] == category_id


# ---------------------------------------------------------------------------
# Single problem retrieval
# ---------------------------------------------------------------------------

async def test_get_problem_by_id(
    client: AsyncClient,
    sample_problem,
) -> None:
    """GET /problems/{id} returns the correct problem."""
    problem_id = sample_problem.id
    response = await client.get(f"/api/v1/problems/{problem_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == problem_id
    assert data["title"] == sample_problem.title
    assert data["platform"] == "reddit"


async def test_get_nonexistent_problem_returns_404(
    client: AsyncClient,
) -> None:
    """GET /problems/{id} with an unknown ID returns HTTP 404."""
    response = await client.get("/api/v1/problems/999999")

    assert response.status_code == 404
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Trending
# ---------------------------------------------------------------------------

async def test_trending_returns_list(
    client: AsyncClient,
    sample_problem,
) -> None:
    """GET /problems/trending should return a list of problems."""
    response = await client.get("/api/v1/problems/trending")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
