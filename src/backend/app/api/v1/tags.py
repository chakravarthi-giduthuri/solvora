import hashlib
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.redis_client import cache_get, cache_set
from app.core.security import get_current_user
from app.models.problem import Tag, ProblemTag

router = APIRouter()


@router.get("/", response_model=None)
async def search_tags(q: str = Query(""), db: AsyncSession = Depends(get_db)):
    cache_key = f"tags:search:{hashlib.md5(q.lower().encode()).hexdigest()}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)
    stmt = select(Tag)
    if q:
        stmt = stmt.where(Tag.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Tag.use_count.desc()).limit(20)
    result = await db.execute(stmt)
    tags = result.scalars().all()
    data = [{"id": t.id, "name": t.name, "slug": t.slug, "use_count": t.use_count} for t in tags]
    await cache_set(cache_key, data, ttl=900)
    return JSONResponse(content=data)


@router.get("/problem/{problem_id}", response_model=None)
async def get_problem_tags(problem_id: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"problem_tags:{problem_id}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)
    result = await db.execute(
        select(Tag).join(ProblemTag, ProblemTag.tag_id == Tag.id)
        .where(ProblemTag.problem_id == problem_id)
        .order_by(Tag.use_count.desc())
    )
    tags = result.scalars().all()
    data = [{"id": t.id, "name": t.name, "slug": t.slug} for t in tags]
    await cache_set(cache_key, data, ttl=900)
    return JSONResponse(content=data)


@router.post("/problem/{problem_id}", response_model=None)
async def add_problem_tags(
    problem_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tag_names = body.get("tags", [])
    if not isinstance(tag_names, list) or len(tag_names) > 5:
        raise HTTPException(status_code=400, detail="Provide 1-5 tags")
    tag_names = [str(n).strip().lower()[:32] for n in tag_names if str(n).strip()]
    for name in tag_names:
        slug = name.replace(" ", "-")
        result = await db.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(id=str(uuid.uuid4()), name=name, slug=slug, use_count=0)
            db.add(tag)
            await db.flush()
        existing = await db.execute(
            select(ProblemTag).where(ProblemTag.problem_id == problem_id, ProblemTag.tag_id == tag.id)
        )
        if not existing.scalar_one_or_none():
            db.add(ProblemTag(problem_id=problem_id, tag_id=tag.id))
            tag.use_count += 1
    await db.commit()
    from app.core.redis_client import get_redis
    r = await get_redis()
    await r.delete(f"problem_tags:{problem_id}")
    result = await db.execute(
        select(Tag).join(ProblemTag, ProblemTag.tag_id == Tag.id)
        .where(ProblemTag.problem_id == problem_id)
    )
    tags = result.scalars().all()
    return JSONResponse(content=[{"id": t.id, "name": t.name, "slug": t.slug} for t in tags])
