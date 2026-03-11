from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis_client import cache_get, cache_set

router = APIRouter()


@router.get("/summary", response_model=None)
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    cache_key = "analytics:summary"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    from app.services.analytics_service import get_analytics_summary_data
    data = await get_analytics_summary_data(db)
    await cache_set(cache_key, data, ttl=3600)
    return JSONResponse(content=data)


@router.get("/dashboard", response_model=None)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Full analytics dashboard data including click tracking, category distribution, solution rates."""
    cache_key = "analytics:dashboard"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    from app.services.analytics_service import get_dashboard_data
    data = await get_dashboard_data(db)
    await cache_set(cache_key, data, ttl=300)
    return JSONResponse(content=data)
