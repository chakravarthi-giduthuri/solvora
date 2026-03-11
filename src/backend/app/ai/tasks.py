"""Celery tasks for the AI solution generation pipeline.

Tasks
-----
generate_solutions_task        — Generate solutions for a specific problem
                                 using the requested providers.

batch_generate_for_viral_posts — Find high-upvote problems without solutions
                                 and generate solutions for all of them.
"""

from __future__ import annotations

import structlog
from sqlalchemy import text

from app.ai.solution_orchestrator import SolutionOrchestrator
from app.core.celery_app import celery_app
from app.core.database import SessionLocal

logger = structlog.get_logger(__name__)

_VIRAL_UPVOTE_THRESHOLD = 100
_BATCH_SIZE = 50  # max problems to process per batch_generate run


# ---------------------------------------------------------------------------
# Per-problem solution task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="ai.generate_solutions",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
)
def generate_solutions_task(
    self,
    problem_id: str,
    providers: list[str] | None = None,
) -> dict:
    """Generate AI solutions for a single problem.

    Parameters
    ----------
    problem_id : str — UUID of the problem
    providers  : list of provider names, e.g. ['gemini', 'openai', 'claude'].
                 Defaults to all three if None.

    Returns
    -------
    dict mapping provider → 'ok' | 'failed' | 'skipped'
    """
    if providers is None:
        providers = ["gemini", "openai", "claude"]

    logger.info(
        "generate_solutions_task: starting",
        problem_id=problem_id,
        providers=providers,
    )

    try:
        orchestrator = SolutionOrchestrator()
        results = orchestrator.generate_for_problem(
            problem_id=problem_id,
            providers=providers,
        )

        # Build a clean status dict for the task result
        status = {
            provider: ("ok" if text is not None else "failed")
            for provider, text in results.items()
        }

        logger.info(
            "generate_solutions_task: complete",
            problem_id=problem_id,
            status=status,
        )
        return {"problem_id": problem_id, "results": status}

    except Exception as exc:
        logger.error(
            "generate_solutions_task: unhandled error",
            problem_id=problem_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Batch task for viral / high-signal posts
# ---------------------------------------------------------------------------

@celery_app.task(
    name="ai.batch_generate_for_viral_posts",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=660,
)
def batch_generate_for_viral_posts(self) -> dict:
    """Find problems with upvotes > 100 and no solutions, then generate.

    Processes up to _BATCH_SIZE problems per run.  Actual generation is
    dispatched as individual generate_solutions_task sub-tasks so that
    failures in one problem do not affect others.

    Returns
    -------
    dict with 'dispatched' count
    """
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT p.id::text AS id
                FROM   problems p
                WHERE  p.is_problem = true
                  AND  p.upvotes >= :threshold
                  AND  p.is_active = true
                  AND  NOT EXISTS (
                      SELECT 1
                      FROM   solutions s
                      WHERE  s.problem_id = p.id
                  )
                ORDER BY p.upvotes DESC
                LIMIT  :batch_size
                """
            ),
            {
                "threshold": _VIRAL_UPVOTE_THRESHOLD,
                "batch_size": _BATCH_SIZE,
            },
        ).fetchall()

    problem_ids = [row.id for row in rows]

    if not problem_ids:
        logger.info("batch_generate_for_viral_posts: no viral problems without solutions")
        return {"dispatched": 0}

    for problem_id in problem_ids:
        generate_solutions_task.delay(
            problem_id=problem_id,
            providers=["gemini", "openai", "claude"],
        )

    logger.info(
        "batch_generate_for_viral_posts: dispatched tasks",
        count=len(problem_ids),
    )
    return {"dispatched": len(problem_ids)}
