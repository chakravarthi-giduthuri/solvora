"""Shared pytest fixtures for Solvora backend tests.

Strategy:
- Set all env vars at module level (before any app imports).
- Create a separate SQLite async engine for tests.
- Override the app's get_db dependency to use the test session.
- Mock the sync Celery/psycopg2 engine to avoid requiring a real PG server.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

# ── Set env vars before ANY app imports ───────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ["RATELIMIT_ENABLED"] = "0"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch as _patch
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Test SQLite engine (separate from app engine)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class _FakeRedis:
    """Minimal fake Redis that always returns None/0 — no external connection."""
    async def get(self, key): return None
    async def set(self, key, value, ex=None): return True
    async def setex(self, key, ttl, value): return True
    async def delete(self, *keys): return 0
    async def incr(self, key): return 1
    async def exists(self, key): return 0
    async def expire(self, key, ttl): return True
    async def ping(self): return True


async def _fake_get_redis():
    return _FakeRedis()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """SQLite async engine for the test session — no external DB needed."""
    # Patch the sync engine in database.py to avoid psycopg2/PG dependency
    import app.core.database as db_module  # noqa: PLC0415

    db_module._sync_engine = MagicMock()
    db_module.SessionLocal = MagicMock()

    _engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Patch Redis so tests don't need a running Redis server
    import app.core.redis_client as _rc  # noqa: PLC0415
    _rc.get_redis = _fake_get_redis

    from app.core.database import Base  # noqa: PLC0415
    import app.models.problem  # noqa: F401  — registers all models with Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


@pytest_asyncio.fixture()
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """AsyncSession for each test — lets route handlers commit normally."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI app + HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app(engine):
    """Return the FastAPI app with rate limiting disabled for tests."""
    from app.main import app as fastapi_app  # noqa: PLC0415
    from app.core.limiter import limiter  # noqa: PLC0415

    # Disable rate limiting in tests by patching the decorator to be a no-op
    limiter._disabled = True

    return fastapi_app


@pytest_asyncio.fixture()
async def client(app, db) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the test app, with get_db overridden."""
    from app.core.database import get_db  # noqa: PLC0415

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def sample_category(db: AsyncSession):
    """Insert and return a sample Category row."""
    from app.models.problem import Category  # noqa: PLC0415
    import uuid as _uuid

    cat = Category(
        id=str(_uuid.uuid4()),
        name="Technology",
        slug="technology",
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


@pytest_asyncio.fixture()
async def sample_problem(db: AsyncSession, sample_category):
    """Insert and return a sample Problem row."""
    from app.models.problem import Problem  # noqa: PLC0415
    import uuid as _uuid

    problem = Problem(
        id=str(_uuid.uuid4()),
        platform="reddit",
        title="How do I fix Python async issues?",
        body="I keep getting runtime errors with asyncio.",
        url=f"https://reddit.com/r/python/comments/{_uuid.uuid4().hex[:8]}/",
        source_id=_uuid.uuid4().hex,
        source="reddit",
        is_active=True,
        is_problem=True,
    )
    db.add(problem)
    await db.flush()
    await db.refresh(problem)
    return problem


@pytest_asyncio.fixture()
async def sample_user(client: AsyncClient):
    """Create a sample user via the signup API and return the user dict."""
    import uuid as _uuid
    unique = _uuid.uuid4().hex[:8]
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"sample_{unique}@example.com",
            "password": "Correct-Password1!",
            "name": "Sample User",
        },
    )
    assert resp.status_code == 201, f"sample_user fixture failed: {resp.text}"
    # Return an object with .email attribute for test compatibility
    data = resp.json()
    class _User:
        def __init__(self, d):
            self.email = d["user"]["email"]
            self.id = d["user"].get("id")
    return _User(data)


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
