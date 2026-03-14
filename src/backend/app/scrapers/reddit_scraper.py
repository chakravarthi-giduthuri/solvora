"""Reddit scraper — connects via PRAW OAuth2.

Targets:
    Subreddits : r/Advice, r/AskReddit, r/TrueOffMyChest, r/Problems, r/Help
    Keywords   : 'how do I fix', 'need help with', 'frustrated by',
                 'problem with', 'anyone know how'

Extracts per post:
    title, body, author, upvotes, comment_count, subreddit,
    timestamp, url, source_id

Also scrapes the top 5 comments per post.

Deduplication is handled in _save_posts via ON CONFLICT DO NOTHING on
source_hash (SHA-256 of platform+source_id).

Rate limiting:
    PRAW's built-in rate limiter is respected automatically.
    An additional 1-second sleep is inserted between subreddit fetches.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Any

import praw
import structlog
from sqlalchemy.orm import Session

from app.scrapers.base_scraper import BaseScraper

logger = structlog.get_logger(__name__)

TARGET_SUBREDDITS: list[str] = [
    "Advice",
    "AskReddit",
    "TrueOffMyChest",
    "Problems",
    "Help",
]

PROBLEM_KEYWORDS: list[str] = [
    "how do I fix",
    "need help with",
    "frustrated by",
    "problem with",
    "anyone know how",
]


class RedditScraper(BaseScraper):
    """Scrapes Reddit for problem-oriented posts using PRAW."""

    def __init__(self, settings: Any) -> None:
        """Initialise PRAW with OAuth2 credentials from settings.

        Parameters
        ----------
        settings : app.core.config.Settings — Pydantic settings object.
            Required attributes:
                REDDIT_CLIENT_ID
                REDDIT_CLIENT_SECRET
                REDDIT_USER_AGENT
        """
        self._reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
        # PRAW read-only mode (no username/password required for scraping)
        self._reddit.read_only = True
        self._settings = settings

    # ------------------------------------------------------------------
    # Public scraping methods
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict[str, Any]]:
        """Convenience method that runs both subreddit and keyword scrapes."""
        posts: list[dict[str, Any]] = []
        posts.extend(self.scrape_subreddits())
        posts.extend(self.scrape_keywords())
        return posts

    def scrape_subreddits(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch the `limit` newest posts from each target subreddit.

        Parameters
        ----------
        limit : int — posts per subreddit (default 100, PRAW max 1000)

        Returns
        -------
        list[dict] — normalised post dicts
        """
        all_posts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for subreddit_name in TARGET_SUBREDDITS:
            try:
                subreddit = self._reddit.subreddit(subreddit_name)
                logger.info("Scraping subreddit", subreddit=subreddit_name, limit=limit)

                for submission in subreddit.new(limit=limit):
                    post = self._extract_post(submission)
                    if post["source_id"] not in seen_ids:
                        seen_ids.add(post["source_id"])
                        all_posts.append(post)

            except praw.exceptions.PRAWException as exc:
                logger.error(
                    "PRAW error scraping subreddit",
                    subreddit=subreddit_name,
                    error=str(exc),
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error scraping subreddit",
                    subreddit=subreddit_name,
                    error=str(exc),
                )

            # Courtesy sleep between subreddits (PRAW handles per-request limiting)
            time.sleep(1)

        logger.info(
            "Subreddit scrape complete",
            subreddits=len(TARGET_SUBREDDITS),
            posts=len(all_posts),
        )
        return all_posts

    def scrape_keywords(self, limit: int = 50) -> list[dict[str, Any]]:
        """Search Reddit-wide for each problem keyword.

        Parameters
        ----------
        limit : int — posts per keyword search (default 50)

        Returns
        -------
        list[dict] — normalised post dicts (deduplicated within this call)
        """
        all_posts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for keyword in PROBLEM_KEYWORDS:
            try:
                logger.info("Searching Reddit by keyword", keyword=keyword, limit=limit)
                results = self._reddit.subreddit("all").search(
                    query=keyword,
                    sort="new",
                    time_filter="week",
                    limit=limit,
                )

                for submission in results:
                    post = self._extract_post(submission)
                    if post["source_id"] not in seen_ids:
                        seen_ids.add(post["source_id"])
                        all_posts.append(post)

            except praw.exceptions.PRAWException as exc:
                logger.error(
                    "PRAW error during keyword search",
                    keyword=keyword,
                    error=str(exc),
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error during keyword search",
                    keyword=keyword,
                    error=str(exc),
                )

            time.sleep(1)

        logger.info(
            "Keyword scrape complete",
            keywords=len(PROBLEM_KEYWORDS),
            posts=len(all_posts),
        )
        return all_posts

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_post(self, submission: praw.models.Submission) -> dict[str, Any]:
        """Convert a PRAW Submission object into a normalised post dict.

        Parameters
        ----------
        submission : praw.models.Submission

        Returns
        -------
        dict with keys matching BaseScraper._save_posts expectations
        """
        created_utc = datetime.fromtimestamp(
            submission.created_utc, tz=timezone.utc
        ).isoformat()

        post: dict[str, Any] = {
            "source_id": submission.id,
            "title": submission.title or "",
            "body": submission.selftext or "",
            "author": str(submission.author) if submission.author else "[deleted]",
            "upvotes": submission.score,
            "comment_count": submission.num_comments,
            "subreddit": submission.subreddit.display_name,
            "source_created_at": created_utc,
            "url": f"https://www.reddit.com{submission.permalink}",
            "platform": "reddit",
            "top_comments": self._extract_comments(submission, n=5),
        }
        return post

    def _extract_comments(
        self,
        submission: praw.models.Submission,
        n: int = 5,
    ) -> list[str]:
        """Return the body text of the top `n` comments on a submission.

        PRAW lazy-loads comments; this replaces MoreComments objects with
        actual comment data.  Errors are swallowed to avoid crashing the
        parent extraction.

        Parameters
        ----------
        submission : praw.models.Submission
        n          : int — maximum number of comments to return

        Returns
        -------
        list[str] — comment body strings (may be shorter than n)
        """
        comments: list[str] = []
        try:
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:n]:
                if hasattr(comment, "body") and comment.body not in ("[deleted]", "[removed]"):
                    comments.append(comment.body)
        except Exception as exc:
            logger.warning(
                "Could not extract comments",
                submission_id=submission.id,
                error=str(exc),
            )
        return comments


# ---------------------------------------------------------------------------
# Module-level runner
# ---------------------------------------------------------------------------

def run_reddit_scrape(db_session: Session, settings: Any) -> dict[str, int]:
    """Scrape Reddit, deduplicate, and persist posts to the database.

    Parameters
    ----------
    db_session : SQLAlchemy Session
    settings   : app.core.config.Settings

    Returns
    -------
    dict with keys 'fetched', 'inserted', 'skipped'
    """
    scraper = RedditScraper(settings)
    posts = scraper.scrape()

    fetched = len(posts)
    inserted, skipped = BaseScraper._save_posts(db_session, posts, platform="reddit")

    if inserted > 0:
        try:
            import redis as sync_redis
            r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
            r.incr("sse:new_problem_count", inserted)
        except Exception as exc:
            logger.warning("Reddit scrape: SSE counter update failed", error=str(exc))

    logger.info(
        "Reddit scrape finished",
        fetched=fetched,
        inserted=inserted,
        skipped=skipped,
    )
    return {"fetched": fetched, "inserted": inserted, "skipped": skipped}
