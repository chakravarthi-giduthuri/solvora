"""Celery tasks that wrap the scraper functions.

These tasks are registered under the names referenced in the beat schedule:
    scrapers.run_hn_scrape      — every 15 minutes
    scrapers.run_reddit_scrape  — every 30 minutes
"""

from __future__ import annotations

import structlog

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="scrapers.run_hn_scrape",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def run_hn_scrape_task(self) -> dict:
    """Scrape Hacker News and persist new problems to the database."""
    from app.scrapers.hn_scraper import run_hn_scrape  # noqa: PLC0415

    try:
        with SessionLocal() as db:
            result = run_hn_scrape(db, settings)
        logger.info("hn_scrape_task: complete", **result)
        return result
    except Exception as exc:
        logger.error("hn_scrape_task: failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="scrapers.run_reddit_scrape",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def run_reddit_scrape_task(self) -> dict:
    """Scrape Reddit and persist new problems to the database."""
    from app.scrapers.reddit_scraper import run_reddit_scrape  # noqa: PLC0415

    try:
        with SessionLocal() as db:
            result = run_reddit_scrape(db, settings)
        logger.info("reddit_scrape_task: complete", **result)
        return result
    except Exception as exc:
        logger.error("reddit_scrape_task: failed", error=str(exc))
        raise self.retry(exc=exc)
