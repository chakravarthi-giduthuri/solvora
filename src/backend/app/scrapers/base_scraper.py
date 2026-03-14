from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

# ─── Simple keyword-based sentiment inference ─────────────────────────────────

_URGENT_KEYWORDS = [
    "urgent", "emergency", "asap", "immediately", "critical", "help me",
    "please help", "broken", "crash", "error", "failing", "not working",
    "can't access", "cannot access", "data loss", "stuck",
]
_FRUSTRATED_KEYWORDS = [
    "frustrated", "annoying", "ridiculous", "awful", "terrible", "horrible",
    "why is", "why does", "sick of", "fed up", "hate this", "worst",
    "unacceptable", "waste of time", "disgrace", "disappointed",
]
_CURIOUS_KEYWORDS = [
    "how do i", "how does", "how can", "why does", "what is", "what are",
    "anyone know", "is it possible", "wondering", "curious", "wondering if",
    "explain", "understand", "learn", "best way", "anyone else",
]


def _infer_sentiment(title: str, body: str) -> str:
    text_lower = (f"{title} {body}").lower()
    for kw in _URGENT_KEYWORDS:
        if kw in text_lower:
            return "urgent"
    for kw in _FRUSTRATED_KEYWORDS:
        if kw in text_lower:
            return "frustrated"
    for kw in _CURIOUS_KEYWORDS:
        if kw in text_lower:
            return "curious"
    return "neutral"


_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Technology", ["software", "app", "code", "bug", "computer", "laptop", "phone", "internet", "wifi", "website", "server", "api", "github", "python", "javascript", "programming", "developer", "tech", "hardware", "device"]),
    ("Health", ["doctor", "hospital", "medicine", "health", "pain", "symptoms", "diagnosis", "anxiety", "depression", "mental health", "therapy", "medication", "illness", "disease", "sick"]),
    ("Finance", ["money", "bank", "loan", "debt", "credit", "payment", "salary", "tax", "budget", "invest", "financial", "mortgage", "rent", "insurance", "bills"]),
    ("Relationships", ["relationship", "partner", "boyfriend", "girlfriend", "husband", "wife", "friend", "family", "breakup", "divorce", "dating", "marriage", "parents", "siblings"]),
    ("Career", ["job", "work", "boss", "coworker", "office", "career", "resume", "interview", "fired", "promotion", "workplace", "employee", "employer", "salary", "remote work"]),
    ("Legal", ["law", "legal", "lawyer", "court", "sue", "contract", "rights", "police", "crime", "landlord", "tenant", "copyright", "dispute"]),
    ("Education", ["school", "college", "university", "exam", "degree", "professor", "teacher", "homework", "course", "study", "student", "class", "grade"]),
]


def _infer_category(title: str, body: str) -> str | None:
    text_lower = (f"{title} {body}").lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def _normalize_title(title: str) -> str:
    """Lowercase and strip for dedup comparison."""
    return title.lower().strip()


class BaseScraper(ABC):

    @abstractmethod
    def scrape(self) -> list[dict[str, Any]]:
        pass

    @staticmethod
    def _save_posts(
        db_session: Session,
        posts: list[dict[str, Any]],
        platform: str,
    ) -> tuple[int, int]:
        if not posts:
            return 0, 0

        # Load existing titles from DB to skip cross-post duplicates
        existing_titles: set[str] = set()
        rows = db_session.execute(
            text("SELECT lower(trim(title)) FROM problems WHERE is_active = true")
        ).fetchall()
        existing_titles = {r[0] for r in rows}

        inserted = 0
        skipped = 0

        # Also track titles seen within this batch
        batch_titles: set[str] = set()

        for post in posts:
            title = (post.get("title") or "")[:512]
            body = post.get("body") or ""

            norm = _normalize_title(title)

            # Skip if title already exists in DB or seen in this batch
            if norm in existing_titles or norm in batch_titles:
                skipped += 1
                continue

            sentiment = _infer_sentiment(title, body)
            category_val = _infer_category(title, body)

            stmt = text(
                """
                INSERT INTO problems (
                    id, platform, source_id, title, body, url,
                    author_handle, upvotes, comment_count, subreddit,
                    sentiment, category, is_problem, is_active, scraped_at, created_at, updated_at
                )
                VALUES (
                    :id, :platform, :source_id, :title, :body, :url,
                    :author_handle, :upvotes, :comment_count, :subreddit,
                    :sentiment, :category, false, true, NOW(), NOW(), NOW()
                )
                ON CONFLICT ON CONSTRAINT uq_source_platform DO NOTHING
                """
            )

            result = db_session.execute(stmt, {
                "id": str(uuid.uuid4()),
                "platform": platform,
                "source_id": str(post.get("source_id", ""))[:128],
                "title": title,
                "body": body or None,
                "url": (post.get("url") or "")[:1024],
                "author_handle": (post.get("author") or None),
                "upvotes": int(post.get("upvotes") or 0),
                "comment_count": int(post.get("comment_count") or 0),
                "subreddit": post.get("subreddit") or None,
                "sentiment": sentiment,
                "category": category_val,
            })

            if result.rowcount > 0:
                inserted += 1
                batch_titles.add(norm)
                existing_titles.add(norm)
            else:
                skipped += 1

        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
            logger.exception("DB commit failed", platform=platform)
            raise

        logger.info("Posts saved", platform=platform, inserted=inserted, skipped=skipped)

        # Flush the in-memory problems cache so the feed immediately reflects new posts
        if inserted > 0:
            try:
                from app.core.redis_client import _mem_cache
                keys_to_drop = [k for k in list(_mem_cache.keys()) if k.startswith("problems:")]
                for k in keys_to_drop:
                    _mem_cache.pop(k, None)
            except Exception:
                pass

        return inserted, skipped
