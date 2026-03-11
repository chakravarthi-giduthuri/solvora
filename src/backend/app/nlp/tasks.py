"""Celery tasks for the NLP classification pipeline.

Tasks
-----
classify_new_posts_task   — Classifies posts that have not yet been
                            classified (is_problem=false, category=null,
                            confidence_score=null).

run_reddit_scrape_task    — Celery wrapper around run_reddit_scrape.

run_hn_scrape_task        — Celery wrapper around run_hn_scrape.
"""

from __future__ import annotations

import structlog
from celery import shared_task
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.nlp.classifier import NLPClassifier
from app.scrapers.hn_scraper import run_hn_scrape
from app.scrapers.reddit_scraper import run_reddit_scrape

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# NLP Classification Task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="nlp.classify_new_posts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=600,
    time_limit=660,
)
def classify_new_posts_task(self) -> dict:
    """Fetch unclassified problems and classify them with Gemini 1.5 Flash.

    A post is considered unclassified when:
        - is_problem is False (default)
        - category_id IS NULL
        - confidence IS NULL

    After classification:
        - is_problem, confidence, category_id, sentiment, summary are updated.
        - review_required is set to True if confidence < 0.65.
    """
    classifier = NLPClassifier()
    processed = 0
    updated = 0
    errors = 0

    with SessionLocal() as db:
        # Fetch up to 500 unclassified posts per task run
        rows = db.execute(
            text(
                """
                SELECT p.id, p.title, p.body
                FROM   problems p
                WHERE  p.is_problem = false
                  AND  p.category_id IS NULL
                  AND  p.confidence IS NULL
                  AND  p.is_active = true
                ORDER BY p.scraped_at DESC
                LIMIT  500
                """
            )
        ).fetchall()

        if not rows:
            logger.info("classify_new_posts_task: no unclassified posts found")
            return {"processed": 0, "updated": 0, "errors": 0}

        posts = [
            {"id": str(row.id), "title": row.title or "", "body": row.body or ""}
            for row in rows
        ]

        logger.info(
            "classify_new_posts_task: starting",
            count=len(posts),
        )

        batch_results = classifier.classify_batch(posts)

        for post_dict, result in batch_results:
            processed += 1
            if result is None:
                continue

            try:
                # Resolve category_id from category name
                category_id = _get_or_create_category_id(db, result.category)

                db.execute(
                    text(
                        """
                        UPDATE problems
                        SET
                            is_problem      = :is_problem,
                            confidence      = :confidence,
                            category_id     = :category_id,
                            sentiment       = :sentiment,
                            summary         = :summary,
                            review_required = :review_required
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": post_dict["id"],
                        "is_problem": result.is_problem,
                        "confidence": result.confidence,
                        "category_id": category_id,
                        "sentiment": result.sentiment.capitalize() if result.sentiment else None,
                        "summary": result.summary or None,
                        "review_required": result.review_required,
                    },
                )
                updated += 1

            except Exception as exc:
                errors += 1
                logger.error(
                    "Failed to update classified post",
                    post_id=post_dict["id"],
                    error=str(exc),
                )

        db.commit()

    logger.info(
        "classify_new_posts_task: complete",
        processed=processed,
        updated=updated,
        errors=errors,
    )
    return {"processed": processed, "updated": updated, "errors": errors}


def _get_or_create_category_id(db, category_name: str) -> int | None:
    """Return the category ID for the given name, creating it if absent."""
    if not category_name:
        return None

    row = db.execute(
        text("SELECT id FROM categories WHERE name = :name"),
        {"name": category_name},
    ).fetchone()

    if row:
        return row.id

    # Insert new category (slug = lower-case name, spaces → hyphens)
    slug = category_name.lower().replace(" ", "-")
    result = db.execute(
        text(
            """
            INSERT INTO categories (name, slug)
            VALUES (:name, :slug)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """
        ),
        {"name": category_name, "slug": slug},
    )
    db.commit()
    return result.fetchone().id


# ---------------------------------------------------------------------------
# Scraper Celery Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    name="scrapers.run_reddit_scrape",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=300,
    time_limit=360,
)
def run_reddit_scrape_task(self) -> dict:
    """Celery task: scrape Reddit and persist posts to the database."""
    try:
        with SessionLocal() as db:
            result = run_reddit_scrape(db_session=db, settings=settings)
        logger.info("run_reddit_scrape_task: complete", **result)
        return result
    except Exception as exc:
        logger.error("run_reddit_scrape_task: failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="scrapers.run_hn_scrape",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=180,
    time_limit=240,
)
def run_hn_scrape_task(self) -> dict:
    """Celery task: scrape Hacker News and persist posts to the database."""
    try:
        with SessionLocal() as db:
            result = run_hn_scrape(db_session=db, settings=settings)
        logger.info("run_hn_scrape_task: complete", **result)
        return result
    except Exception as exc:
        logger.error("run_hn_scrape_task: failed", error=str(exc))
        raise self.retry(exc=exc)
