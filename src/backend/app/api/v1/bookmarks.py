from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.problem import Bookmark, User
from app.schemas.problem import ProblemResponse

router = APIRouter()


class BookmarkCreate(BaseModel):
    problem_id: str


@router.post("/")
async def add_bookmark(
    payload: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id,
            Bookmark.problem_id == payload.problem_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_bookmarked"}
    bookmark = Bookmark(user_id=current_user.id, problem_id=payload.problem_id)
    db.add(bookmark)
    await db.commit()
    return {"status": "bookmarked"}


@router.delete("/{problem_id}")
async def remove_bookmark(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id,
            Bookmark.problem_id == problem_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(bookmark)
    await db.commit()
    return {"status": "removed"}


@router.get("/", response_model=list[ProblemResponse])
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .options(selectinload(Bookmark.problem))
        .order_by(Bookmark.created_at.desc())
    )
    bookmarks = result.scalars().all()
    return [ProblemResponse.model_validate(b.problem) for b in bookmarks]
