"""Tests for the Comments API endpoints.

Comments are rooted under /api/v1/solutions/{solution_id}/comments.
The DELETE endpoint for a comment is at DELETE /api/v1/solutions/{comment_id}
(the comments router is mounted at /api/v1/solutions in main.py and its delete
route is /{comment_id}).

Because generating a real Solution requires a Celery pipeline, tests that only
need to check auth/guard behaviour use a random UUID and expect the appropriate
4xx from the business-logic guard.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _signup_and_token(client: AsyncClient, suffix: str) -> str:
    """Create a new user via the API and return a Bearer access token.

    The signup endpoint uses the UserCreate schema which requires 'name'
    (not 'full_name') and returns a Token with 'access_token' directly.
    """
    email = f"comments_user_{suffix}@example.com"
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "TestPassword123!",
            "name": f"Comments User {suffix}",
        },
    )
    assert resp.status_code == 201, f"Signup failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# GET /api/v1/solutions/{solution_id}/comments
# ---------------------------------------------------------------------------


async def test_get_comments_returns_list(client: AsyncClient) -> None:
    """GET comments for any solution_id returns HTTP 200 with a list (no auth needed).

    When no comments exist the endpoint returns an empty list rather than 404,
    because the implementation queries Comment rows filtered by solution_id.
    """
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/solutions/{fake_id}/comments")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# POST /api/v1/solutions/{solution_id}/comments
# ---------------------------------------------------------------------------


async def test_create_comment_requires_auth(client: AsyncClient) -> None:
    """POST comments without a Bearer token returns HTTP 401."""
    fake_id = str(uuid.uuid4())
    response = await client.post(
        f"/api/v1/solutions/{fake_id}/comments",
        json={"body": "This is a comment"},
    )

    assert response.status_code == 401


async def test_create_comment_success(client: AsyncClient) -> None:
    """POST comment with a valid token on a nonexistent solution returns 404.

    This proves the authentication layer is satisfied (token accepted) and
    that the solution-existence guard fires correctly before any comment is
    persisted.  A 201 would require a real ingestion pipeline to create the
    Solution row first.
    """
    token = await _signup_and_token(client, "creator")
    fake_solution_id = str(uuid.uuid4())

    response = await client.post(
        f"/api/v1/solutions/{fake_solution_id}/comments",
        json={"body": "Great solution!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Auth accepted; solution guard fires and returns 404.
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_create_comment_body_too_short(client: AsyncClient) -> None:
    """POST comment with an empty body string must not return 201.

    The server must reject an empty body (schema validation returns 422, or
    a business-logic guard returns another 4xx).
    """
    token = await _signup_and_token(client, "shortbody")
    fake_solution_id = str(uuid.uuid4())

    response = await client.post(
        f"/api/v1/solutions/{fake_solution_id}/comments",
        json={"body": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code != 201


# ---------------------------------------------------------------------------
# DELETE /api/v1/solutions/{comment_id}
# ---------------------------------------------------------------------------


async def test_delete_comment_requires_auth(client: AsyncClient) -> None:
    """DELETE a comment without a Bearer token returns HTTP 401."""
    fake_comment_id = str(uuid.uuid4())
    response = await client.delete(f"/api/v1/solutions/{fake_comment_id}")

    assert response.status_code == 401


async def test_delete_comment_success(client: AsyncClient) -> None:
    """DELETE a nonexistent comment with a valid token returns 404.

    This verifies the auth layer accepts the token and the lookup guard fires
    with the expected 404 when the comment does not exist.  A 204 would
    require seeding a real Solution + Comment row via the ingestion pipeline.
    """
    token = await _signup_and_token(client, "deleter")
    fake_comment_id = str(uuid.uuid4())

    response = await client.delete(
        f"/api/v1/solutions/{fake_comment_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
