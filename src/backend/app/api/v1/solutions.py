from typing import List
from pydantic import BaseModel, field_validator
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.problem import Solution, Problem
from app.schemas.problem import SolutionResponse

router = APIRouter()

_ALLOWED_PROVIDERS = frozenset({"gemini", "openai", "claude"})


class SolutionGenerateRequest(BaseModel):
    problem_id: str
    providers: List[str] = ["gemini", "openai", "claude"]

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v: List[str]) -> List[str]:
        valid = [p for p in v if p in _ALLOWED_PROVIDERS]
        if not valid:
            raise ValueError("No valid providers specified. Allowed: gemini, openai, claude")
        return valid


@router.get("/{problem_id}", response_model=list[SolutionResponse])
async def get_solutions(problem_id: str, db: AsyncSession = Depends(get_db)):
    q = select(Solution).where(Solution.problem_id == problem_id, Solution.is_active == True)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_solutions(
    payload: SolutionGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    q = select(Problem).where(Problem.id == payload.problem_id)
    result = await db.execute(q)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Problem not found")

    from app.ai.tasks import generate_solutions_task
    task = generate_solutions_task.delay(payload.problem_id, payload.providers)
    return {"task_id": task.id, "status": "queued"}
