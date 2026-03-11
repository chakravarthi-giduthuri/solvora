"""Tests for the Authentication API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Sign-up
# ---------------------------------------------------------------------------

async def test_signup_creates_user(client: AsyncClient) -> None:
    """POST /auth/signup creates a new user and returns user data."""
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
        "full_name": "New User",
    }

    response = await client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code in (200, 201)
    data = response.json()
    assert data["email"] == payload["email"]
    assert "password" not in data
    assert "hashed_password" not in data


async def test_signup_duplicate_email_returns_409(client: AsyncClient) -> None:
    """Attempting to sign up with an existing email returns HTTP 409."""
    payload = {
        "email": "duplicate@example.com",
        "password": "AnotherPassword1!",
        "full_name": "First User",
    }
    await client.post("/api/v1/auth/signup", json=payload)

    response = await client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def test_login_returns_token(
    client: AsyncClient,
    sample_user,
) -> None:
    """POST /auth/login with valid credentials returns an access token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": sample_user.email, "password": "correct-password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


async def test_login_wrong_password_returns_401(
    client: AsyncClient,
    sample_user,
) -> None:
    """POST /auth/login with an incorrect password returns HTTP 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": sample_user.email, "password": "wrong-password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    """POST /auth/login with an email that does not exist returns HTTP 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "whatever"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# /me (authenticated profile endpoint)
# ---------------------------------------------------------------------------

async def test_me_requires_auth(client: AsyncClient) -> None:
    """GET /auth/me without a token returns HTTP 401."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_me_returns_user_when_authenticated(
    client: AsyncClient,
    sample_user,
) -> None:
    """GET /auth/me with a valid token returns the authenticated user's profile."""
    # Obtain a token first
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": sample_user.email, "password": "correct-password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Use the token to call /me
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    data = me_response.json()
    assert data["email"] == sample_user.email
    assert "hashed_password" not in data
