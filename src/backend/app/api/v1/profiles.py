import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.core.redis_client import cache_get, cache_set, cache_delete
from app.models.problem import User, Problem, Bookmark, Vote

router = APIRouter()

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')


class ProfileUpdateRequest(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    username: Optional[str] = None


class ProfileStats(BaseModel):
    submitted_count: int
    bookmark_count: int
    vote_count: int


class ProfileResponse(BaseModel):
    id: str
    username: Optional[str]
    name: str
    bio: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    stats: ProfileStats
    recent_submissions: List[dict] = []


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _build_profile(db, current_user)


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    req: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.username is not None:
        if not USERNAME_RE.match(req.username):
            raise HTTPException(status_code=400, detail="Username must be 3-32 alphanumeric chars, hyphens, underscores")
        existing = await db.execute(
            select(User).where(User.username == req.username, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")
        old_username = current_user.username
        current_user.username = req.username
        if old_username:
            await cache_delete(f"profile:{old_username}")
    if req.bio is not None:
        current_user.bio = req.bio
    if req.avatar_url is not None:
        current_user.avatar_url = req.avatar_url
    await db.commit()
    await db.refresh(current_user)
    if current_user.username:
        await cache_delete(f"profile:{current_user.username}")
    return await _build_profile(db, current_user)


@router.get("/{username}", response_model=ProfileResponse)
async def get_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    cache_key = f"profile:{username}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = await _build_profile(db, user)
    await cache_set(cache_key, data.model_dump(mode="json"), ttl=120)
    return data


async def _build_profile(db: AsyncSession, user: User) -> ProfileResponse:
    submitted = await db.execute(
        select(func.count()).select_from(Problem).where(
            Problem.submitted_by_user_id == user.id, Problem.is_active == True
        )
    )
    submitted_count = submitted.scalar() or 0

    bookmarks = await db.execute(
        select(func.count()).select_from(Bookmark).where(Bookmark.user_id == user.id)
    )
    bookmark_count = bookmarks.scalar() or 0

    votes = await db.execute(
        select(func.count()).select_from(Vote).where(Vote.user_id == user.id)
    )
    vote_count = votes.scalar() or 0

    recent = await db.execute(
        select(Problem).where(
            Problem.submitted_by_user_id == user.id, Problem.is_active == True
        ).order_by(Problem.created_at.desc()).limit(5)
    )
    recent_submissions = [
        {"id": p.id, "title": p.title, "category": p.category, "created_at": p.created_at.isoformat()}
        for p in recent.scalars().all()
    ]

    return ProfileResponse(
        id=user.id,
        username=getattr(user, 'username', None),
        name=user.name,
        bio=getattr(user, 'bio', None),
        avatar_url=getattr(user, 'avatar_url', None),
        created_at=user.created_at,
        stats=ProfileStats(
            submitted_count=submitted_count,
            bookmark_count=bookmark_count,
            vote_count=vote_count,
        ),
        recent_submissions=recent_submissions,
    )
