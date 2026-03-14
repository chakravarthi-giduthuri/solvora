"""Celery tasks for content curation.

Tasks
-----
select_potd_task     — Runs daily at 00:05 UTC. Picks the best unselected
                       problem and marks it as Problem of the Day.

auto_tag_problems_task — Runs every 30 min. Extracts keyword tags from
                         problem titles for untagged problems.
"""

from __future__ import annotations

import json
import re
import structlog
from datetime import date, datetime, timezone
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.database import SessionLocal

logger = structlog.get_logger(__name__)

# Common stop-words to exclude from auto-tags
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "do", "i",
    "my", "me", "how", "why", "what", "when", "where", "who", "can",
    "not", "be", "are", "was", "were", "have", "has", "had", "will",
    "would", "could", "should", "get", "got", "just", "any", "all",
})


def _extract_keywords(title: str) -> list[str]:
    """Extract meaningful keywords from a problem title."""
    words = re.findall(r"[a-z0-9]+", title.lower())
    tags = [w for w in words if len(w) >= 3 and w not in _STOP_WORDS]
    # Return up to 5 unique tags, longest-first for relevance
    seen: list[str] = []
    for t in sorted(set(tags), key=len, reverse=True):
        if t not in seen:
            seen.append(t)
        if len(seen) >= 5:
            break
    return seen


@celery_app.task(
    name="content.select_potd",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=120,
    time_limit=180,
)
def select_potd_task(self) -> dict:
    """Select today's Problem of the Day.

    Picks the highest-upvoted active problem that has not yet been assigned
    a potd_date, then sets potd_date = today and invalidates the Redis cache.
    """
    today = date.today().isoformat()
    with SessionLocal() as db:
        # Check if a POTD is already set for today
        existing = db.execute(
            text("SELECT id FROM problems WHERE potd_date = :today LIMIT 1"),
            {"today": today},
        ).fetchone()
        if existing:
            logger.info("select_potd_task: already set for today", date=today)
            return {"status": "already_set", "date": today}

        # Pick the best unselected problem
        row = db.execute(
            text(
                """
                SELECT id FROM problems
                WHERE is_active = true
                  AND potd_date IS NULL
                  AND is_problem = true
                ORDER BY upvotes DESC, comment_count DESC
                LIMIT 1
                """
            )
        ).fetchone()

        if not row:
            logger.info("select_potd_task: no eligible problem found")
            return {"status": "no_eligible_problem"}

        db.execute(
            text("UPDATE problems SET potd_date = :today WHERE id = :id"),
            {"today": today, "id": row.id},
        )
        db.commit()

    # Invalidate POTD Redis cache
    try:
        import redis as sync_redis
        from app.core.config import settings
        r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
        r.delete(f"potd:{today}")
    except Exception as exc:
        logger.warning("select_potd_task: cache invalidation failed", error=str(exc))

    logger.info("select_potd_task: complete", problem_id=row.id, date=today)
    return {"status": "ok", "problem_id": row.id, "date": today}


@celery_app.task(
    name="content.auto_tag_problems",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def auto_tag_problems_task(self) -> dict:
    """Auto-tag problems that have no tags_auto value yet.

    Extracts keyword tags from the problem title and writes them as a
    JSON list to the tags_auto column.
    """
    processed = 0
    updated = 0

    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT id, title FROM problems
                WHERE tags_auto IS NULL
                  AND is_active = true
                ORDER BY scraped_at DESC
                LIMIT 200
                """
            )
        ).fetchall()

        if not rows:
            logger.info("auto_tag_problems_task: no untagged problems")
            return {"processed": 0, "updated": 0}

        for row in rows:
            processed += 1
            tags = _extract_keywords(row.title or "")
            db.execute(
                text("UPDATE problems SET tags_auto = :tags WHERE id = :id"),
                {"tags": json.dumps(tags), "id": row.id},
            )
            updated += 1

        db.commit()

    logger.info("auto_tag_problems_task: complete", processed=processed, updated=updated)
    return {"processed": processed, "updated": updated}
