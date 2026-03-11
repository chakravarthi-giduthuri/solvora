from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

# asyncpg does not accept sslmode= as a query param — strip it and pass ssl=True via connect_args
def _make_async_url(url: str):
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    ssl_required = params.pop("sslmode", ["disable"])[0] in ("require", "verify-ca", "verify-full")
    new_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=new_query))
    return clean_url, ssl_required

_async_url, _ssl_required = _make_async_url(settings.DATABASE_URL)
_connect_args = {"ssl": True} if _ssl_required else {}

# Async engine — used by FastAPI request handlers
engine = create_async_engine(_async_url, echo=False, pool_pre_ping=True, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine — used by Celery workers (scrapers, NLP tasks, AI tasks)
# Derives a sync URL from the async one: asyncpg → psycopg2
_sync_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
).replace(
    "postgresql://", "postgresql+psycopg2://"
)
_sync_engine = create_engine(_sync_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
