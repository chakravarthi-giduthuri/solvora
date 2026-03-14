"""Tests for the admin panel endpoints.

Endpoints:
  GET  /api/v1/admin/scrapers/status  — admin only
  GET  /api/v1/admin/users            — admin only
  GET  /api/v1/admin/reports          — admin only

Access control:
  - No token → 401
  - Regular user token → 403
  - Admin user token → 200

The _make_admin helper writes directly to the DB to elevate a user,
which avoids circular dependency on the admin endpoint itself.
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.problem import User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _signup(client: AsyncClient, email: str) -> tuple[str, str]:
    """Sign up a user and return (user_id, access_token)."""
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPass123!", "name": "Admin Test"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["user"]["id"], data["access_token"]


async def _make_admin(db: AsyncSession, email: str) -> None:
    """Directly set is_admin=True in the test DB for the given user."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.is_admin = True
        await db.flush()


# ---------------------------------------------------------------------------
# GET /admin/scrapers/status
# ---------------------------------------------------------------------------


async def test_scrapers_status_requires_auth(client: AsyncClient) -> None:
    """GET /admin/scrapers/status without token returns 401."""
    resp = await client.get("/api/v1/admin/scrapers/status")
    assert resp.status_code == 401


async def test_scrapers_status_requires_admin_role(client: AsyncClient) -> None:
    """Regular user (not admin) gets 403 on GET /admin/scrapers/status."""
    _, token = await _signup(client, "regular_user_admin1@example.com")
    resp = await client.get(
        "/api/v1/admin/scrapers/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_scrapers_status_as_admin(client: AsyncClient, db: AsyncSession) -> None:
    """Admin user gets 200 and a dict with expected platform keys."""
    email = "admin_scrapers1@example.com"
    _, token = await _signup(client, email)
    await _make_admin(db, email)

    resp = await client.get(
        "/api/v1/admin/scrapers/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reddit" in data
    assert "hn" in data


async def test_scrapers_status_reddit_has_status_field(client: AsyncClient, db: AsyncSession) -> None:
    """Each platform entry in scrapers/status contains a 'status' field."""
    email = "admin_scrapers2@example.com"
    _, token = await _signup(client, email)
    await _make_admin(db, email)

    resp = await client.get(
        "/api/v1/admin/scrapers/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "status" in resp.json()["reddit"]


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------


async def test_users_list_requires_auth(client: AsyncClient) -> None:
    """GET /admin/users without token returns 401."""
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


async def test_users_list_requires_admin_role(client: AsyncClient) -> None:
    """Regular user gets 403 on GET /admin/users."""
    _, token = await _signup(client, "regular_user_admin2@example.com")
    resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_users_list_as_admin_returns_list(client: AsyncClient, db: AsyncSession) -> None:
    """Admin user gets 200 and a list of users."""
    email = "admin_userlist1@example.com"
    _, token = await _signup(client, email)
    await _make_admin(db, email)

    resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_users_list_items_have_required_fields(client: AsyncClient, db: AsyncSession) -> None:
    """Each user item has id, email, name, is_active, is_admin, created_at."""
    email = "admin_userlist2@example.com"
    _, token = await _signup(client, email)
    await _make_admin(db, email)

    resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    first = users[0]
    for field in ("id", "email", "name", "is_active", "is_admin", "created_at"):
        assert field in first, f"Missing field: {field}"


async def test_users_list_search_filters_by_email(client: AsyncClient, db: AsyncSession) -> None:
    """The search param narrows the user list by email."""
    email = "admin_search1@example.com"
    _, token = await _signup(client, email)
    await _make_admin(db, email)

    # Search for the admin's own email fragment
    resp = await client.get(
        "/api/v1/admin/users?search=admin_search1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert email in emails


# ---------------------------------------------------------------------------
# GET /admin/reports
# ---------------------------------------------------------------------------


async def test_reports_list_requires_auth(client: AsyncClient) -> None:
    """GET /admin/reports without token returns 401."""
    resp = await client.get("/api/v1/admin/reports")
    assert resp.status_code == 401


async def test_reports_list_requires_admin_role(client: AsyncClient) -> None:
    """Regular user gets 403 on GET /admin/reports."""
    _, token = await _signup(client, "regular_user_admin3@example.com")
    resp = await client.get(
        "/api/v1/admin/reports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_reports_list_as_admin_returns_list(client: AsyncClient, db: AsyncSession) -> None:
    """Admin user gets 200 and a list (possibly empty) of reports."""
    email = "admin_reports1@example.com"
    _, token = await _signup(client, email)
    await _make_admin(db, email)

    resp = await client.get(
        "/api/v1/admin/reports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
