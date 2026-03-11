"""Shared pytest fixtures for Solvora backend tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# In-process SQLite engine (no external DB required)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create an async SQLite engine shared across the test session."""
    _engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Import Base after engine creation to avoid triggering app startup
    from app.models.base import Base  # noqa: PLC0415

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


@pytest_asyncio.fixture()
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional AsyncSession that rolls back after each test."""
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test application
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Return the FastAPI application configured for testing."""
    import os

    os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
    os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
    os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")

    from app.main import app as fastapi_app  # noqa: PLC0415

    return fastapi_app


@pytest_asyncio.fixture()
async def client(app, db) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient wired to the test app with the test DB session."""
    from app.core.database import get_db  # noqa: PLC0415

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def sample_category(db: AsyncSession):
    """Insert and return a sample Category row."""
    from app.models.category import Category  # noqa: PLC0415

    category = Category(name="Technology")
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@pytest_asyncio.fixture()
async def sample_problem(db: AsyncSession, sample_category):
    """Insert and return a sample Problem row."""
    from app.models.problem import Problem  # noqa: PLC0415

    problem = Problem(
        title="How do I fix my Python async code?",
        body="I keep getting runtime errors with asyncio. Need help.",
        platform="reddit",
        source_id="abc123",
        source_hash="deadbeefdeadbeefdeadbeefdeadbeef",
        url="https://www.reddit.com/r/learnpython/comments/abc123/",
        author="test_user",
        upvotes=42,
        comment_count=7,
        sentiment="frustrated",
        category_id=sample_category.id,
        source_created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )
    db.add(problem)
    await db.flush()
    await db.refresh(problem)
    return problem


@pytest_asyncio.fixture()
async def sample_user(db: AsyncSession):
    """Insert and return a sample User row with a hashed password."""
    from app.models.user import User  # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415

    user = User(
        email="test@example.com",
        hashed_password=hash_password("correct-password"),
        full_name="Test User",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Event loop (pytest-asyncio session scope)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
