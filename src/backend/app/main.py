from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.core.limiter import limiter
from app.api.v1 import problems, solutions, analytics, categories, auth, votes, bookmarks, internal, tags, filter_presets, stream, comments, profiles, leaderboard, export, notifications, admin, submit_problems


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


async def _run_migrations(conn):
    """Create tables and safely add any missing columns."""
    from sqlalchemy import text
    await conn.run_sync(Base.metadata.create_all)
    # Add columns that may be missing from pre-existing tables
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR DEFAULT 'email'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR",
    ]
    for sql in migrations:
        try:
            await conn.execute(text(sql))
        except Exception:
            pass  # Column may already exist with different constraints


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await _run_migrations(conn)
    yield


def create_app() -> FastAPI:
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    is_production = settings.ENVIRONMENT == "production"

    app = FastAPI(
        title="Solvora API",
        version="1.0.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )

    app.include_router(problems.router, prefix="/api/v1/problems", tags=["problems"])
    app.include_router(solutions.router, prefix="/api/v1/solutions", tags=["solutions"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(votes.router, prefix="/api/v1/votes", tags=["votes"])
    app.include_router(bookmarks.router, prefix="/api/v1/bookmarks", tags=["bookmarks"])
    app.include_router(internal.router, prefix="/api/v1/internal", tags=["internal"])
    app.include_router(tags.router, prefix="/api/v1/tags", tags=["tags"])
    app.include_router(filter_presets.router, prefix="/api/v1/filter-presets", tags=["filter-presets"])
    app.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"])
    app.include_router(comments.router, prefix="/api/v1/solutions", tags=["comments"])
    app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["profiles"])
    app.include_router(leaderboard.router, prefix="/api/v1/leaderboard", tags=["leaderboard"])
    app.include_router(export.router, prefix="/api/v1/problems", tags=["export"])
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(submit_problems.router, prefix="/api/v1/submit", tags=["submit"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.1"}

    return app


app = create_app()
