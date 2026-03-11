"""Multi-AI solution generation orchestrator.

Workflow per provider
---------------------
1. Check Redis cache: key = f"solution:{problem_id}:{provider}"
   → Cache hit: return cached text immediately (TTL 24 hours).
2. Check circuit breaker: if provider tripped → skip with logged warning.
3. Call provider adapter (Gemini / OpenAI / Claude).
4. On success: store in Redis (TTL 24 h) AND persist to solutions DB table.
5. On failure: increment error counter in Redis.
   → If error count >= 3 within 5 minutes, trip the circuit breaker
     (disable provider for 5 minutes).

Circuit breaker Redis keys
--------------------------
    cb:{provider}:open        → "1"  TTL=5min  (provider disabled)
    cb:{provider}:errors      → int  TTL=5min  (rolling error counter)

Solution cache key
------------------
    solution:{problem_id}:{provider}  TTL=86400s
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis
import structlog
from sqlalchemy import text

from app.ai.claude_adapter import ClaudeAdapter
from app.ai.gemini_adapter import GeminiAdapter
from app.ai.openai_adapter import OpenAIAdapter
from app.core.config import settings
from app.core.database import SessionLocal

logger = structlog.get_logger(__name__)

_CACHE_TTL = 86_400          # 24 hours in seconds
_CIRCUIT_OPEN_TTL = 300      # 5 minutes in seconds
_CIRCUIT_ERROR_TTL = 300     # rolling error window: 5 minutes
_CIRCUIT_THRESHOLD = 3       # errors to trip the breaker

_PROVIDER_MODELS = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "claude": "claude-haiku-4-5-20251001",
}


class SolutionOrchestrator:
    """Orchestrates solution generation across Gemini, OpenAI, and Claude."""

    def __init__(self) -> None:
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._adapters: dict[str, Any] = {
            "gemini": GeminiAdapter(),
            "openai": OpenAIAdapter(),
            "claude": ClaudeAdapter(),
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_for_problem(
        self,
        problem_id: str,
        providers: list[str] | None = None,
    ) -> dict[str, str | None]:
        """Generate solutions from each requested provider.

        Parameters
        ----------
        problem_id : str — UUID of the problem row
        providers  : list of provider names; defaults to all three

        Returns
        -------
        dict mapping provider → solution text (or None on failure/skip)
        """
        if providers is None:
            providers = ["gemini", "openai", "claude"]

        problem = self._load_problem(problem_id)
        if problem is None:
            logger.error("SolutionOrchestrator: problem not found", problem_id=problem_id)
            return {p: None for p in providers}

        results: dict[str, str | None] = {}

        for provider in providers:
            if provider not in self._adapters:
                logger.warning("Unknown provider skipped", provider=provider)
                results[provider] = None
                continue

            results[provider] = self._get_or_generate(problem_id, provider, problem)

        return results

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------

    def _is_circuit_open(self, provider: str) -> bool:
        """Return True if the provider's circuit breaker is open (tripped)."""
        key = f"cb:{provider}:open"
        return self._redis.exists(key) == 1

    def _trip_circuit(self, provider: str) -> None:
        """Open the circuit breaker for `provider` for 5 minutes."""
        open_key = f"cb:{provider}:open"
        self._redis.set(open_key, "1", ex=_CIRCUIT_OPEN_TTL)
        logger.warning(
            "SolutionOrchestrator: circuit breaker tripped",
            provider=provider,
            ttl_seconds=_CIRCUIT_OPEN_TTL,
        )

    def _record_error(self, provider: str) -> None:
        """Increment the rolling error counter; trip breaker at threshold."""
        error_key = f"cb:{provider}:errors"
        pipe = self._redis.pipeline()
        pipe.incr(error_key)
        pipe.expire(error_key, _CIRCUIT_ERROR_TTL)
        count, _ = pipe.execute()

        if int(count) >= _CIRCUIT_THRESHOLD:
            self._trip_circuit(provider)

    def _reset_error_count(self, provider: str) -> None:
        """Reset the error counter after a successful generation."""
        error_key = f"cb:{provider}:errors"
        self._redis.delete(error_key)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_key(self, problem_id: str, provider: str) -> str:
        return f"solution:{problem_id}:{provider}"

    def _get_cached(self, problem_id: str, provider: str) -> str | None:
        return self._redis.get(self._cache_key(problem_id, provider))

    def _set_cached(self, problem_id: str, provider: str, text: str) -> None:
        self._redis.set(
            self._cache_key(problem_id, provider),
            text,
            ex=_CACHE_TTL,
        )

    # ------------------------------------------------------------------
    # Core generation logic
    # ------------------------------------------------------------------

    def _get_or_generate(
        self,
        problem_id: str,
        provider: str,
        problem: dict[str, Any],
    ) -> str | None:
        """Check cache → circuit breaker → generate → persist → return."""

        # 1. Cache hit
        cached = self._get_cached(problem_id, provider)
        if cached:
            logger.info(
                "SolutionOrchestrator: cache hit",
                problem_id=problem_id,
                provider=provider,
            )
            return cached

        # 2. Circuit breaker
        if self._is_circuit_open(provider):
            logger.warning(
                "SolutionOrchestrator: circuit open, skipping provider",
                provider=provider,
                problem_id=problem_id,
            )
            return None

        # 3. Generate
        adapter = self._adapters[provider]
        try:
            solution_text = adapter.generate_solution(problem)
        except Exception as exc:
            logger.error(
                "SolutionOrchestrator: adapter raised exception",
                provider=provider,
                problem_id=problem_id,
                error=str(exc),
            )
            self._record_error(provider)
            return None

        if solution_text is None:
            logger.warning(
                "SolutionOrchestrator: adapter returned None",
                provider=provider,
                problem_id=problem_id,
            )
            self._record_error(provider)
            return None

        # 4a. Cache
        self._set_cached(problem_id, provider, solution_text)

        # 4b. Persist to DB
        self._persist_solution(problem_id, provider, solution_text)

        # Reset error count on success
        self._reset_error_count(provider)

        logger.info(
            "SolutionOrchestrator: solution generated",
            provider=provider,
            problem_id=problem_id,
            chars=len(solution_text),
        )
        return solution_text

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _load_problem(self, problem_id: str) -> dict[str, Any] | None:
        """Load problem fields needed to build the generation prompt."""
        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT
                        p.id,
                        p.title,
                        p.body,
                        p.platform,
                        p.sentiment,
                        p.confidence_score,
                        p.category
                    FROM problems p
                    WHERE p.id = :id
                    """
                ),
                {"id": problem_id},
            ).fetchone()

        if row is None:
            return None

        return {
            "id": str(row.id),
            "title": row.title or "",
            "body": row.body or "",
            "platform": row.platform or "unknown",
            "sentiment": row.sentiment or "neutral",
            "confidence": float(row.confidence_score or 0.0),
            "category": row.category or "Other",
        }

    def _persist_solution(
        self,
        problem_id: str,
        provider: str,
        solution_text: str,
    ) -> None:
        """Upsert the solution into the solutions table."""
        import uuid as _uuid
        model_name = _PROVIDER_MODELS.get(provider, provider)

        try:
            with SessionLocal() as db:
                # Try to update existing solution first
                result = db.execute(
                    text(
                        """
                        UPDATE solutions
                        SET solution_text = :solution_text,
                            model_name    = :model_name,
                            generated_at  = now(),
                            is_active     = true
                        WHERE problem_id = :problem_id
                          AND provider   = :provider
                        """
                    ),
                    {
                        "problem_id": problem_id,
                        "provider": provider,
                        "model_name": model_name,
                        "solution_text": solution_text,
                    },
                )
                # No existing row — insert fresh
                if result.rowcount == 0:
                    db.execute(
                        text(
                            """
                            INSERT INTO solutions (
                                id, problem_id, provider, model_name,
                                solution_text, rating, is_active, generated_at
                            )
                            VALUES (
                                :id, :problem_id, :provider, :model_name,
                                :solution_text, 0, true, now()
                            )
                            """
                        ),
                        {
                            "id": str(_uuid.uuid4()),
                            "problem_id": problem_id,
                            "provider": provider,
                            "model_name": model_name,
                            "solution_text": solution_text,
                        },
                    )
                db.commit()
        except Exception as exc:
            logger.error(
                "SolutionOrchestrator: failed to persist solution",
                provider=provider,
                problem_id=problem_id,
                error=str(exc),
            )
