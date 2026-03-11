from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.redis_client import cache_get, cache_set
from app.models.problem import Category
from app.schemas.problem import CategoryResponse

router = APIRouter()

@router.get("/", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    cached = await cache_get("categories:all")
    if cached:
        return cached
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    data = [CategoryResponse.model_validate(c).model_dump() for c in categories]
    await cache_set("categories:all", data, ttl=86400)
    return data
