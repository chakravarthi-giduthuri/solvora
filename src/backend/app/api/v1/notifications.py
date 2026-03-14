from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.problem import User, UserNotificationPrefs

router = APIRouter()


class NotificationPrefsUpdate(BaseModel):
    digest_enabled: bool = False
    digest_day: int = Field(1, ge=1, le=7)
    digest_hour_utc: int = Field(8, ge=0, le=23)
    category_interests: List[str] = []
    notify_on_comment: bool = True
    notify_on_vote: bool = False


class NotificationPrefsResponse(BaseModel):
    user_id: str
    digest_enabled: bool
    digest_day: int
    digest_hour_utc: int
    category_interests: List[str]
    notify_on_comment: bool
    notify_on_vote: bool

    class Config:
        from_attributes = True


@router.get("/prefs", response_model=NotificationPrefsResponse)
async def get_prefs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserNotificationPrefs).where(UserNotificationPrefs.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        return NotificationPrefsResponse(
            user_id=current_user.id,
            digest_enabled=False,
            digest_day=1,
            digest_hour_utc=8,
            category_interests=[],
            notify_on_comment=True,
            notify_on_vote=False,
        )
    import json
    return NotificationPrefsResponse(
        user_id=prefs.user_id,
        digest_enabled=prefs.digest_enabled,
        digest_day=prefs.digest_day,
        digest_hour_utc=prefs.digest_hour_utc,
        category_interests=json.loads(prefs.category_interests),
        notify_on_comment=prefs.notify_on_comment,
        notify_on_vote=prefs.notify_on_vote,
    )


@router.put("/prefs", response_model=NotificationPrefsResponse)
async def update_prefs(
    req: NotificationPrefsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import json
    result = await db.execute(
        select(UserNotificationPrefs).where(UserNotificationPrefs.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserNotificationPrefs(user_id=current_user.id)
        db.add(prefs)
    prefs.digest_enabled = req.digest_enabled
    prefs.digest_day = req.digest_day
    prefs.digest_hour_utc = req.digest_hour_utc
    prefs.category_interests = json.dumps(req.category_interests)
    prefs.notify_on_comment = req.notify_on_comment
    prefs.notify_on_vote = req.notify_on_vote
    await db.commit()
    await db.refresh(prefs)
    return NotificationPrefsResponse(
        user_id=prefs.user_id,
        digest_enabled=prefs.digest_enabled,
        digest_day=prefs.digest_day,
        digest_hour_utc=prefs.digest_hour_utc,
        category_interests=json.loads(prefs.category_interests),
        notify_on_comment=prefs.notify_on_comment,
        notify_on_vote=prefs.notify_on_vote,
    )
