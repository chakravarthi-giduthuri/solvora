import ssl
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Celery requires redis:// (not rediss://) when using broker_use_ssl dict config
_celery_redis_url = settings.REDIS_URL.replace("rediss://", "redis://", 1)
_is_tls = settings.REDIS_URL.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _is_tls else None

celery_app = Celery(
    "solvora",
    broker=_celery_redis_url,
    backend="cache+memory://",
    include=["app.nlp.tasks", "app.ai.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl=_ssl_opts,
    redis_backend_use_ssl=_ssl_opts,
    beat_schedule={
        "scrape-reddit-every-30min": {
            "task": "app.nlp.tasks.run_reddit_scrape_task",
            "schedule": crontab(minute="*/30"),
        },
        "scrape-hn-every-15min": {
            "task": "app.nlp.tasks.run_hn_scrape_task",
            "schedule": crontab(minute="*/15"),
        },
        "classify-new-posts-every-10min": {
            "task": "app.nlp.tasks.classify_new_posts_task",
            "schedule": crontab(minute="*/10"),
        },
        "refresh-analytics-hourly": {
            "task": "app.ai.tasks.batch_generate_for_viral_posts",
            "schedule": crontab(minute=0),
        },
    },
)
