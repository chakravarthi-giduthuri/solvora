import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.problem import FilterPreset

router = APIRouter()


@router.get("/", response_model=None)
async def list_presets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(FilterPreset).where(FilterPreset.user_id == current_user.id)
        .order_by(FilterPreset.created_at.desc())
    )
    presets = result.scalars().all()
    return JSONResponse(content=[
        {"id": p.id, "name": p.name, "filters": p.filters, "createdAt": p.created_at.isoformat()}
        for p in presets
    ])


@router.post("/", response_model=None)
async def create_preset(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    name = str(body.get("name", "")).strip()[:64]
    filters = body.get("filters")
    if not name or not filters:
        raise HTTPException(status_code=400, detail="name and filters are required")
    preset = FilterPreset(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=name,
        filters=json.dumps(filters),
    )
    db.add(preset)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Preset with this name already exists")
    return JSONResponse(
        content={"id": preset.id, "name": preset.name, "filters": preset.filters},
        status_code=201,
    )


@router.delete("/{preset_id}", response_model=None)
async def delete_preset(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(FilterPreset).where(FilterPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    if preset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your preset")
    await db.delete(preset)
    await db.commit()
    return JSONResponse(content={"ok": True})
