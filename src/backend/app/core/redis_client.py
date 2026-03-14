import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

_redis: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        url = settings.REDIS_URL
        # Upstash requires TLS — treat redis:// pointing to upstash as rediss://
        if "upstash.io" in url and url.startswith("redis://"):
            url = url.replace("redis://", "rediss://", 1)
        ssl_opts = {"ssl_cert_reqs": None} if url.startswith("rediss://") else {}
        _redis = aioredis.from_url(url, encoding="utf-8", decode_responses=True, **ssl_opts)
    return _redis

async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val

async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))

async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)
