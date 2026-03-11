from __future__ import annotations

import hmac
from fastapi import APIRouter, Header, HTTPException, status
from app.core.config import settings

router = APIRouter(tags=["internal"])


def _verify(x_internal_api_key: str = Header(...)) -> None:
    # Use constant-time comparison to prevent timing-based key enumeration
    if not hmac.compare_digest(x_internal_api_key, settings.INTERNAL_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("/scrape/reddit", status_code=status.HTTP_202_ACCEPTED)
async def trigger_reddit_scrape(x_internal_api_key: str = Header(...)) -> dict:
    _verify(x_internal_api_key)
    from app.nlp.tasks import run_reddit_scrape_task
    task = run_reddit_scrape_task.delay()
    return {"status": "accepted", "task_id": task.id}


@router.post("/scrape/hn", status_code=status.HTTP_202_ACCEPTED)
async def trigger_hn_scrape(x_internal_api_key: str = Header(...)) -> dict:
    _verify(x_internal_api_key)
    from app.nlp.tasks import run_hn_scrape_task
    task = run_hn_scrape_task.delay()
    return {"status": "accepted", "task_id": task.id}


@router.post("/analytics/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_analytics(x_internal_api_key: str = Header(...)) -> dict:
    _verify(x_internal_api_key)
    from app.core.redis_client import cache_delete
    await cache_delete("analytics:summary")
    return {"status": "accepted"}
