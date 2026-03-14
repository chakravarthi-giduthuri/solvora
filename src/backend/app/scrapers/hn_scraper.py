"""Hacker News scraper using the Algolia Search API.

No authentication required.

Endpoint : https://hn.algolia.com/api/v1/search
Tags     : ask_hn, show_hn
Keywords : same problem-indicating keywords as Reddit

Extracted fields per hit:
    title         — story_text or title field
    body          — story_text (may be empty for link posts)
    author        — author field
    upvotes       — points
    comment_count — num_comments
    created_at    — ISO-8601 timestamp
    url           — url or story_url fallback
    source_id     — objectID

Deduplication is handled in _save_posts via ON CONFLICT DO NOTHING on
source_hash (SHA-256 of 'hackernews' + source_id).
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from sqlalchemy.orm import Session

from app.scrapers.base_scraper import BaseScraper

logger = structlog.get_logger(__name__)

ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1/search"

PROBLEM_KEYWORDS: list[str] = [
    "how do I fix",
    "need help with",
    "frustrated by",
    "problem with",
    "anyone know how",
]


class HNScraper(BaseScraper):
    """Scrapes Hacker News Ask HN / Show HN posts via Algolia."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "Solvora/1.0 (hacker-news scraper)"},
        )

    # ------------------------------------------------------------------
    # Public scraping method
    # ------------------------------------------------------------------

    def scrape(self, limit_per_keyword: int = 50) -> list[dict[str, Any]]:
        """Search Ask HN / Show HN for each problem keyword.

        Parameters
        ----------
        limit_per_keyword : int — maximum hits to fetch per keyword (default 50)

        Returns
        -------
        list[dict] — normalised post dicts (deduplicated within this call)
        """
        all_posts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for keyword in PROBLEM_KEYWORDS:
            try:
                posts = self._fetch_keyword(keyword, limit_per_keyword)
                for post in posts:
                    if post["source_id"] not in seen_ids:
                        seen_ids.add(post["source_id"])
                        all_posts.append(post)
                logger.info(
                    "HN keyword scraped",
                    keyword=keyword,
                    new_posts=len(posts),
                )
            except Exception as exc:
                logger.error(
                    "HN keyword scrape failed",
                    keyword=keyword,
                    error=str(exc),
                )

            # Polite delay between API calls
            time.sleep(0.5)

        logger.info(
            "HN scrape complete",
            total_posts=len(all_posts),
        )
        return all_posts

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_keyword(
        self,
        keyword: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch Algolia search results for a single keyword.

        Parameters
        ----------
        keyword : str — search query string
        limit   : int — hitsPerPage cap

        Returns
        -------
        list[dict] — normalised post dicts
        """
        params: dict[str, Any] = {
            "query": keyword,
            "tags": "(ask_hn,show_hn)",  # OR logic: posts tagged ask_hn OR show_hn
            "hitsPerPage": min(limit, 50),
        }

        response = self._client.get(ALGOLIA_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        posts: list[dict[str, Any]] = []
        for hit in data.get("hits", []):
            extracted = self._extract_hit(hit)
            if extracted:
                posts.append(extracted)

        return posts

    @staticmethod
    def _extract_hit(hit: dict[str, Any]) -> dict[str, Any] | None:
        """Convert an Algolia hit dict into a normalised post dict.

        Returns None if the hit is missing a required field (objectID).
        """
        object_id = hit.get("objectID")
        if not object_id:
            return None

        # story_text is the self-text body for Ask HN posts
        body = hit.get("story_text") or ""
        # Title fallback: story_text first sentence vs title field
        title = hit.get("title") or (body[:120] if body else "")

        # URL: prefer url field, fall back to story_url, fall back to HN link
        url = (
            hit.get("url")
            or hit.get("story_url")
            or f"https://news.ycombinator.com/item?id={object_id}"
        )

        created_at = hit.get("created_at") or None

        return {
            "source_id": str(object_id),
            "title": title,
            "body": body,
            "author": hit.get("author") or None,
            "upvotes": int(hit.get("points") or 0),
            "comment_count": int(hit.get("num_comments") or 0),
            "subreddit": None,  # HN has no subreddit equivalent
            "source_created_at": created_at,
            "url": url,
            "platform": "hackernews",
            "top_comments": [],  # HN comments require separate API calls
        }

    def __del__(self) -> None:
        """Close the underlying HTTP client on garbage collection."""
        try:
            self._client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level runner
# ---------------------------------------------------------------------------

def run_hn_scrape(db_session: Session, settings: Any) -> dict[str, int]:
    """Scrape Hacker News, deduplicate, and persist posts to the database.

    Parameters
    ----------
    db_session : SQLAlchemy Session
    settings   : app.core.config.Settings (not used by HN scraper directly
                 but kept for API consistency with run_reddit_scrape)

    Returns
    -------
    dict with keys 'fetched', 'inserted', 'skipped'
    """
    scraper = HNScraper()
    posts = scraper.scrape()

    fetched = len(posts)
    inserted, skipped = BaseScraper._save_posts(
        db_session, posts, platform="hackernews"
    )

    if inserted > 0:
        try:
            import redis as sync_redis
            r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
            r.incr("sse:new_problem_count", inserted)
        except Exception as exc:
            logger.warning("HN scrape: SSE counter update failed", error=str(exc))

    logger.info(
        "HN scrape finished",
        fetched=fetched,
        inserted=inserted,
        skipped=skipped,
    )
    return {"fetched": fetched, "inserted": inserted, "skipped": skipped}
