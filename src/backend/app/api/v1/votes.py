from typing import Literal
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.problem import Vote, Solution, User

router = APIRouter()


class VoteCreate(BaseModel):
    solution_id: str
    vote_type: Literal[1, -1]


@router.post("/")
async def submit_vote(
    payload: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify solution exists before writing
    sol = await db.execute(select(Solution).where(Solution.id == payload.solution_id))
    if not sol.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Solution not found")

    existing = await db.execute(
        select(Vote).where(
            Vote.user_id == current_user.id,
            Vote.solution_id == payload.solution_id,
        )
    )
    vote = existing.scalar_one_or_none()

    if vote:
        old_type = vote.vote_type
        vote.vote_type = payload.vote_type
        delta = payload.vote_type - old_type
    else:
        vote = Vote(
            user_id=current_user.id,
            solution_id=payload.solution_id,
            vote_type=payload.vote_type,
        )
        db.add(vote)
        delta = payload.vote_type

    await db.execute(
        update(Solution)
        .where(Solution.id == payload.solution_id)
        .values(rating=Solution.rating + delta)
    )
    await db.commit()
    return {"status": "ok"}


@router.delete("/{solution_id}")
async def remove_vote(
    solution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vote).where(Vote.user_id == current_user.id, Vote.solution_id == solution_id)
    )
    vote = result.scalar_one_or_none()
    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

    await db.execute(
        update(Solution)
        .where(Solution.id == solution_id)
        .values(rating=Solution.rating - vote.vote_type)
    )
    await db.delete(vote)
    await db.commit()
    return {"status": "ok"}
