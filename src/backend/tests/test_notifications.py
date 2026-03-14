"""Tests for the Notifications Preferences API endpoints.

Covers:
  GET /api/v1/notifications/prefs
  PUT /api/v1/notifications/prefs
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _signup_and_token(client: AsyncClient, suffix: str) -> str:
    """Create a new user via signup and return a Bearer access token.

    UserCreate schema requires 'name' (not 'full_name').
    Token is returned directly by the signup endpoint (status 201).
    """
    email = f"notif_user_{suffix}@example.com"
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "TestPassword123!",
            "name": f"Notif User {suffix}",
        },
    )
    assert resp.status_code == 201, f"Signup failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# GET /api/v1/notifications/prefs
# ---------------------------------------------------------------------------


async def test_get_notification_prefs_requires_auth(client: AsyncClient) -> None:
    """GET /api/v1/notifications/prefs without a token returns HTTP 401."""
    response = await client.get("/api/v1/notifications/prefs")

    assert response.status_code == 401


async def test_get_notification_prefs_success(client: AsyncClient) -> None:
    """GET /api/v1/notifications/prefs returns defaults for a new user."""
    token = await _signup_and_token(client, "getprefs")

    response = await client.get(
        "/api/v1/notifications/prefs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all expected fields are present.
    assert "user_id" in data
    assert "digest_enabled" in data
    assert "digest_day" in data
    assert "digest_hour_utc" in data
    assert "category_interests" in data
    assert "notify_on_comment" in data
    assert "notify_on_vote" in data

    # Verify default values match what the implementation documents.
    assert data["digest_enabled"] is False
    assert data["digest_day"] == 1
    assert data["digest_hour_utc"] == 8
    assert data["category_interests"] == []
    assert data["notify_on_comment"] is True
    assert data["notify_on_vote"] is False


# ---------------------------------------------------------------------------
# PUT /api/v1/notifications/prefs
# ---------------------------------------------------------------------------


async def test_update_notification_prefs_requires_auth(client: AsyncClient) -> None:
    """PUT /api/v1/notifications/prefs without a token returns HTTP 401."""
    response = await client.put(
        "/api/v1/notifications/prefs",
        json={
            "digest_enabled": True,
            "digest_day": 2,
            "digest_hour_utc": 9,
            "category_interests": [],
            "notify_on_comment": True,
            "notify_on_vote": True,
        },
    )

    assert response.status_code == 401


async def test_update_notification_prefs_success(client: AsyncClient) -> None:
    """PUT /api/v1/notifications/prefs updates and returns the new preferences."""
    token = await _signup_and_token(client, "updateprefs")
    payload = {
        "digest_enabled": True,
        "digest_day": 5,
        "digest_hour_utc": 14,
        "category_interests": ["technology", "science"],
        "notify_on_comment": False,
        "notify_on_vote": True,
    }

    response = await client.put(
        "/api/v1/notifications/prefs",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["digest_enabled"] is True
    assert data["digest_day"] == 5
    assert data["digest_hour_utc"] == 14
    assert data["category_interests"] == ["technology", "science"]
    assert data["notify_on_comment"] is False
    assert data["notify_on_vote"] is True
