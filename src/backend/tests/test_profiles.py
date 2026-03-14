"""Tests for the Profiles API endpoints.

Endpoints:
  GET /api/v1/profiles/me           — requires authentication
  PUT /api/v1/profiles/me           — requires authentication
  GET /api/v1/profiles/{username}   — public; looks up by username

Username rules (profiles.py): ^[a-zA-Z0-9_-]{3,32}$
Duplicate username → 409.
Unknown username   → 404.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _signup_and_token(client: AsyncClient, suffix: str) -> str:
    """Create a new user via the signup endpoint and return a Bearer access token.

    UserCreate schema uses 'name' (not 'full_name').
    The signup response is a Token with 'access_token' at the top level.
    """
    email = f"profiles_user_{suffix}@example.com"
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "TestPassword123!",
            "name": f"Profiles User {suffix}",
        },
    )
    assert resp.status_code == 201, f"Signup failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# GET /api/v1/profiles/me
# ---------------------------------------------------------------------------


async def test_get_my_profile_requires_auth(client: AsyncClient) -> None:
    """GET /api/v1/profiles/me without a token returns HTTP 401."""
    response = await client.get("/api/v1/profiles/me")

    assert response.status_code == 401


async def test_get_my_profile_success(client: AsyncClient) -> None:
    """GET /api/v1/profiles/me with a valid token returns the user's profile."""
    token = await _signup_and_token(client, "getme")

    response = await client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "stats" in data
    assert "submitted_count" in data["stats"]
    assert "bookmark_count" in data["stats"]
    assert "vote_count" in data["stats"]
    assert isinstance(data.get("recent_submissions"), list)


# ---------------------------------------------------------------------------
# PUT /api/v1/profiles/me
# ---------------------------------------------------------------------------


async def test_update_my_profile_requires_auth(client: AsyncClient) -> None:
    """PUT /api/v1/profiles/me without a token returns HTTP 401."""
    response = await client.put(
        "/api/v1/profiles/me",
        json={"bio": "Updated bio"},
    )

    assert response.status_code == 401


async def test_update_my_profile_success(client: AsyncClient) -> None:
    """PUT /api/v1/profiles/me with a valid token updates the bio field."""
    token = await _signup_and_token(client, "updateme")
    new_bio = "This is my updated profile bio."

    response = await client.put(
        "/api/v1/profiles/me",
        json={"bio": new_bio},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["bio"] == new_bio


# ---------------------------------------------------------------------------
# GET /api/v1/profiles/{username}
# ---------------------------------------------------------------------------


async def test_get_profile_by_username_success(client: AsyncClient) -> None:
    """GET /api/v1/profiles/{username} returns the public profile after username is set."""
    token = await _signup_and_token(client, "byusername")
    username = "testuser_byusername"

    put_resp = await client.put(
        "/api/v1/profiles/me",
        json={"username": username},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert put_resp.status_code == 200, f"Failed to set username: {put_resp.text}"

    response = await client.get(f"/api/v1/profiles/{username}")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert "id" in data
    assert "stats" in data


async def test_get_profile_by_username_not_found(client: AsyncClient) -> None:
    """GET /api/v1/profiles/{username} for an unknown username returns HTTP 404."""
    response = await client.get("/api/v1/profiles/definitely_nonexistent_user_xyz999")

    assert response.status_code == 404
    assert "detail" in response.json()
