from __future__ import annotations

import asyncio
import hmac
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status
from app.core.config import settings
from app.core.database import SessionLocal

router = APIRouter(tags=["internal"])


def _verify(x_internal_api_key: str = Header(...)) -> None:
    if not hmac.compare_digest(x_internal_api_key, settings.INTERNAL_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _run_scraper(source: str) -> dict:
    from app.core.config import settings as s
    with SessionLocal() as db:
        if source == "reddit":
            from app.scrapers.reddit_scraper import run_reddit_scrape
            return run_reddit_scrape(db, s)
        elif source == "hn":
            from app.scrapers.hn_scraper import run_hn_scrape
            return run_hn_scrape(db, s)
    return {}


@router.post("/scrape/reddit", status_code=status.HTTP_202_ACCEPTED)
async def trigger_reddit_scrape(
    background_tasks: BackgroundTasks,
    x_internal_api_key: str = Header(...),
) -> dict:
    _verify(x_internal_api_key)
    background_tasks.add_task(
        asyncio.get_event_loop().run_in_executor, None, _run_scraper, "reddit"
    )
    return {"status": "started", "source": "reddit"}


@router.post("/scrape/hn", status_code=status.HTTP_202_ACCEPTED)
async def trigger_hn_scrape(
    background_tasks: BackgroundTasks,
    x_internal_api_key: str = Header(...),
) -> dict:
    _verify(x_internal_api_key)
    background_tasks.add_task(
        asyncio.get_event_loop().run_in_executor, None, _run_scraper, "hn"
    )
    return {"status": "started", "source": "hn"}


@router.post("/analytics/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_analytics(x_internal_api_key: str = Header(...)) -> dict:
    _verify(x_internal_api_key)
    from app.core.redis_client import cache_delete
    await cache_delete("analytics:summary")
    return {"status": "accepted"}
