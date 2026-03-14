"""Tests for user-submitted problems endpoint.

The submit endpoint lives at POST /api/v1/submit (no trailing slash).
Auth uses the Token schema: response has access_token + user fields.
Signup payload uses 'name' (not 'full_name').
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIGNUP_COUNTER = 0


async def _signup(client: AsyncClient, suffix: str) -> str:
    """Create a fresh user and return the access_token."""
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"submitter_{suffix}@example.com",
            "password": "TestPass123!",
            "name": f"Submitter {suffix}",
        },
    )
    assert resp.status_code == 201, f"Signup failed: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------


async def test_submit_problem_requires_auth(client: AsyncClient) -> None:
    """POST /api/v1/submit without a token returns 401."""
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "My problem that needs solving today",
            "body": "I have been struggling with this issue for a very long time.",
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Successful submission
# ---------------------------------------------------------------------------


async def test_submit_problem_success(client: AsyncClient) -> None:
    """Authenticated user can submit a problem and gets 201 with id and source."""
    token = await _signup(client, "success1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "How do I configure async SQLAlchemy correctly",
            "body": "I keep running into session issues when using async SQLAlchemy with FastAPI.",
            "category": "programming",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["source"] == "user_submitted"
    assert data["title"] == "How do I configure async SQLAlchemy correctly"


async def test_submit_problem_returns_category(client: AsyncClient) -> None:
    """Submitted problem echoes back the provided category."""
    token = await _signup(client, "category1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "Category echo test for problem submission here",
            "body": "This body is definitely long enough to satisfy the minimum length requirement.",
            "category": "technology",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["category"] == "technology"


async def test_submit_problem_without_category(client: AsyncClient) -> None:
    """Category is optional; omitting it still returns 201."""
    token = await _signup(client, "nocat1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "A problem submitted without any category field here",
            "body": "This description is long enough to pass the minimum body length validation.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


async def test_submit_problem_title_too_short(client: AsyncClient) -> None:
    """Title shorter than 10 chars returns 422."""
    token = await _signup(client, "shortttl1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "Short",
            "body": "This body is long enough to pass validation easily.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_submit_problem_body_too_short(client: AsyncClient) -> None:
    """Body shorter than 20 chars returns 422."""
    token = await _signup(client, "shortbdy1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "A valid problem title here that is long enough",
            "body": "Too short",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_submit_problem_missing_title(client: AsyncClient) -> None:
    """Missing title field returns 422."""
    token = await _signup(client, "missing_title1")
    resp = await client.post(
        "/api/v1/submit",
        json={"body": "This body is definitely long enough to satisfy minimum requirements."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_submit_problem_missing_body(client: AsyncClient) -> None:
    """Missing body field returns 422."""
    token = await _signup(client, "missing_body1")
    resp = await client.post(
        "/api/v1/submit",
        json={"title": "A valid problem title that has enough characters"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_submit_problem_title_exactly_10_chars(client: AsyncClient) -> None:
    """Title of exactly 10 chars is accepted (boundary value)."""
    token = await _signup(client, "boundaryok1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "1234567890",  # exactly 10
            "body": "This body is long enough to pass the validation requirement.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


async def test_submit_problem_body_exactly_20_chars(client: AsyncClient) -> None:
    """Body of exactly 20 chars is accepted (boundary value)."""
    token = await _signup(client, "bodyboundary1")
    resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "A valid problem title for boundary testing here",
            "body": "12345678901234567890",  # exactly 20
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Problem appears in feed after submission
# ---------------------------------------------------------------------------


async def test_submitted_problem_appears_in_feed(client: AsyncClient) -> None:
    """After submitting, the problem appears in GET /api/v1/problems/."""
    token = await _signup(client, "feed_check1")
    submit_resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "This problem should appear in the feed for everyone",
            "body": "The description is long enough to pass the validation requirement easily.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_resp.status_code == 201
    problem_id = submit_resp.json()["id"]

    feed_resp = await client.get("/api/v1/problems/")
    assert feed_resp.status_code == 200
    data = feed_resp.json()
    assert "items" in data
    ids = [p["id"] for p in data["items"]]
    assert problem_id in ids


async def test_submitted_problem_has_user_platform(client: AsyncClient) -> None:
    """User-submitted problems have platform='user'."""
    token = await _signup(client, "platform_check1")
    submit_resp = await client.post(
        "/api/v1/submit",
        json={
            "title": "Platform verification for user submitted problem",
            "body": "This description is long enough to pass the minimum body length validation.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_resp.status_code == 201
    problem_id = submit_resp.json()["id"]

    detail_resp = await client.get(f"/api/v1/problems/{problem_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["platform"] == "user"
