import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.limiter import limiter
from app.models.problem import User, Problem

router = APIRouter()


class ProblemSubmitRequest(BaseModel):
    title: str = Field(..., min_length=10, max_length=512)
    body: str = Field(..., min_length=20)
    category: Optional[str] = None
    tags: List[str] = []


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def submit_problem(
    request: Request,
    body: ProblemSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    problem = Problem(
        id=str(uuid.uuid4()),
        platform="user",
        title=body.title,
        body=body.body,
        url=f"https://solvora.io/problems/user-{str(uuid.uuid4())[:8]}",
        source_id=str(uuid.uuid4()),
        category=body.category,
        source="user_submitted",
        submitted_by_user_id=current_user.id,
        is_active=True,
        is_problem=True,
    )
    db.add(problem)
    await db.commit()
    await db.refresh(problem)

    # Notify SSE stream so other devices see the new problem immediately
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        await r.incr('sse:new_problem_count')
    except Exception:
        pass  # Don't fail if Redis is unavailable

    try:
        from app.ai.tasks import generate_solutions_task
        generate_solutions_task.delay(problem.id, ["gemini", "openai", "claude"])
    except Exception:
        pass  # Don't fail if task queue is unavailable

    return {
        "id": problem.id,
        "title": problem.title,
        "category": problem.category,
        "source": problem.source,
        "created_at": problem.created_at.isoformat(),
    }
