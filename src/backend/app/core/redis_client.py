import json
import time
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

_redis: Optional[aioredis.Redis] = None

# ── In-memory cache layer ─────────────────────────────────────────────────────
# Sits in front of Redis to absorb repeated reads without consuming Redis commands.
# Each entry: (value, expires_at_unix)
_mem_cache: dict[str, tuple[Any, float]] = {}
_MEM_MAX = 500  # max entries before evicting oldest


def _mem_get(key: str) -> Optional[Any]:
    entry = _mem_cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.time() > expires_at:
        _mem_cache.pop(key, None)
        return None
    return value


def _mem_set(key: str, value: Any, ttl: int) -> None:
    if len(_mem_cache) >= _MEM_MAX:
        # Evict the oldest 10% of entries
        oldest = sorted(_mem_cache.items(), key=lambda x: x[1][1])
        for k, _ in oldest[: _MEM_MAX // 10]:
            _mem_cache.pop(k, None)
    _mem_cache[key] = (value, time.time() + ttl)


def _mem_delete(key: str) -> None:
    _mem_cache.pop(key, None)


# ── Redis connection ──────────────────────────────────────────────────────────

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


# ── Public cache API (memory-first, Redis as fallback/persistence) ────────────

async def cache_get(key: str) -> Optional[Any]:
    # 1. Try memory first — zero Redis commands on hit
    val = _mem_get(key)
    if val is not None:
        return val
    # 2. Try Redis
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw is None:
            return None
        parsed = json.loads(raw)
        # Warm memory cache (use a fixed 5-min warm TTL; actual expiry in Redis)
        _mem_set(key, parsed, 300)
        return parsed
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    _mem_set(key, value, ttl)
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass  # Memory cache still works if Redis is down


async def cache_delete(key: str) -> None:
    _mem_delete(key)
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception:
        pass
