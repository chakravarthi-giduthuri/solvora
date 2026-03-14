"""Celery application factory for Solvora.

The broker and result backend both point to the Upstash Redis instance
defined in settings.REDIS_URL.

Task modules are auto-discovered from the registered task packages:
    app.nlp.tasks
    app.ai.tasks

Beat schedule (cron triggers):
    Every 15 min  — HN scrape
    Every 30 min  — Reddit scrape
    Every 30 min  — Classify new posts
    Every 1 hour  — Batch generate solutions for viral posts
"""

from __future__ import annotations

import ssl
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Celery requires redis:// (not rediss://) when SSL is passed via broker_use_ssl dict
_celery_redis_url = settings.REDIS_URL.replace("rediss://", "redis://", 1)
_is_tls = settings.REDIS_URL.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _is_tls else None

celery_app = Celery(
    "solvora",
    broker=_celery_redis_url,
    backend="cache+memory://",
    include=[
        "app.scrapers.tasks",
        "app.nlp.tasks",
        "app.ai.tasks",
        "app.content.tasks",
        "app.notifications.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_use_ssl=_ssl_opts,
    redis_backend_use_ssl=_ssl_opts,
    # Celery beat periodic schedule
    beat_schedule={
        "hn-scrape-every-15min": {
            "task": "scrapers.run_hn_scrape",
            "schedule": crontab(minute="*/15"),
        },
        "reddit-scrape-every-30min": {
            "task": "scrapers.run_reddit_scrape",
            "schedule": crontab(minute="*/30"),
        },
        "classify-posts-every-30min": {
            "task": "nlp.classify_new_posts",
            "schedule": crontab(minute="*/30"),
        },
        "batch-generate-viral-hourly": {
            "task": "ai.batch_generate_for_viral_posts",
            "schedule": crontab(minute=0),
        },
        "select-potd-daily": {
            "task": "content.select_potd",
            "schedule": crontab(hour=0, minute=5),
        },
        "auto-tag-problems-every-30min": {
            "task": "content.auto_tag_problems",
            "schedule": crontab(minute="*/30"),
        },
        "send-digests-hourly": {
            "task": "notifications.send_weekly_digests",
            "schedule": crontab(minute=5),
        },
    },
)
