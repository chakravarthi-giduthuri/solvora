"""Twitter/X scraper using Tweepy."""
from __future__ import annotations
from typing import List
from app.scrapers.base_scraper import BaseScraper


class TwitterScraper(BaseScraper):
    """Scrape problem-related tweets using Twitter API v2."""

    def __init__(self) -> None:
        from app.core.config import settings
        self.bearer_token = getattr(settings, 'TWITTER_BEARER_TOKEN', None)

    def scrape(self) -> List[dict]:
        if not self.bearer_token:
            return []
        try:
            import tweepy
            client = tweepy.Client(bearer_token=self.bearer_token, wait_on_rate_limit=False)
            queries = [
                "how do I fix -is:retweet lang:en",
                "problem with -is:retweet lang:en",
                "help needed coding -is:retweet lang:en",
            ]
            results = []
            for query in queries:
                try:
                    response = client.search_recent_tweets(
                        query=query,
                        max_results=10,
                        tweet_fields=["created_at", "author_id", "public_metrics", "text"],
                    )
                    if response.data:
                        for tweet in response.data:
                            metrics = tweet.public_metrics or {}
                            results.append({
                                "platform": "twitter",
                                "source_id": str(tweet.id),
                                "title": tweet.text[:512],
                                "body": tweet.text,
                                "url": f"https://twitter.com/i/web/status/{tweet.id}",
                                "author_handle": str(tweet.author_id),
                                "upvotes": metrics.get("like_count", 0),
                                "comment_count": metrics.get("reply_count", 0),
                            })
                except Exception:
                    continue
            return results
        except ImportError:
            return []


def run_twitter_scrape_task_sync():
    from app.scrapers.twitter_scraper import TwitterScraper
    from app.services.scraper_service import process_scraped_items
    import asyncio
    scraper = TwitterScraper()
    items = scraper.scrape()
    if items:
        asyncio.run(process_scraped_items(items))
