import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.core.redis_client import cache_get, cache_set, cache_delete
from app.models.problem import Comment, Solution, User

router = APIRouter()


class CommentCreate(BaseModel):
    body: str
    parent_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    solution_id: str
    user_id: str
    parent_id: Optional[str] = None
    body: str
    is_active: bool
    is_flagged: bool
    created_at: datetime
    author_name: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/{solution_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    solution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    cache_key = f"comments:{solution_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Comment).where(Comment.solution_id == solution_id, Comment.is_active == True)
        .order_by(Comment.created_at)
    )
    comments = result.scalars().all()
    data = []
    for c in comments:
        user_result = await db.execute(select(User).where(User.id == c.user_id))
        user = user_result.scalar_one_or_none()
        data.append({
            "id": c.id,
            "solution_id": c.solution_id,
            "user_id": c.user_id,
            "parent_id": c.parent_id,
            "body": c.body,
            "is_active": c.is_active,
            "is_flagged": c.is_flagged,
            "created_at": c.created_at.isoformat(),
            "author_name": user.name if user else None,
        })
    await cache_set(cache_key, data, ttl=60)
    return data


@router.post("/{solution_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    solution_id: str,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sol_result = await db.execute(select(Solution).where(Solution.id == solution_id))
    solution = sol_result.scalar_one_or_none()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    if body.parent_id:
        parent_result = await db.execute(
            select(Comment).where(Comment.id == body.parent_id, Comment.solution_id == solution_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=400, detail="parent_id does not belong to this solution")

    comment = Comment(
        id=str(uuid.uuid4()),
        solution_id=solution_id,
        user_id=current_user.id,
        parent_id=body.parent_id,
        body=body.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    await cache_delete(f"comments:{solution_id}")
    return {
        "id": comment.id,
        "solution_id": comment.solution_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "body": comment.body,
        "is_active": comment.is_active,
        "is_flagged": comment.is_flagged,
        "created_at": comment.created_at.isoformat(),
        "author_name": current_user.name,
    }


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Forbidden")
    comment.is_active = False
    await db.commit()
    await cache_delete(f"comments:{comment.solution_id}")


@router.post("/{comment_id}/flag")
async def flag_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_flagged = True
    await db.commit()
    return {"flagged": True}
