import csv
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.core.redis_client import cache_get, cache_set
from app.core.security import get_current_user

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
    await cache_set(cache_key, data, ttl=900)
    return JSONResponse(content=data)


@router.get("/custom")
async def get_custom_analytics(
    date_from: str = Query(..., description="ISO8601 date, e.g. 2025-01-01"),
    date_to: str = Query(..., description="ISO8601 date, e.g. 2025-03-01"),
    db: AsyncSession = Depends(get_db),
):
    try:
        dt_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        dt_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO8601 (e.g. 2025-01-01)")

    if dt_from >= dt_to:
        raise HTTPException(status_code=400, detail="date_from must be before date_to")
    if (dt_to - dt_from).days > 365:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

    cache_key = f"analytics:custom:{date_from}:{date_to}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    from app.models.problem import Problem
    problems_q = await db.execute(
        select(Problem.category, Problem.platform, Problem.sentiment, func.count(Problem.id).label("cnt"))
        .where(and_(Problem.is_active == True, Problem.created_at >= dt_from, Problem.created_at <= dt_to))
        .group_by(Problem.category, Problem.platform, Problem.sentiment)
    )
    rows = problems_q.all()

    by_category = {}
    by_platform = {}
    by_sentiment = {}
    for row in rows:
        if row.category:
            by_category[row.category] = by_category.get(row.category, 0) + row.cnt
        if row.platform:
            by_platform[row.platform] = by_platform.get(row.platform, 0) + row.cnt
        if row.sentiment:
            by_sentiment[row.sentiment] = by_sentiment.get(row.sentiment, 0) + row.cnt

    total_q = await db.execute(
        select(func.count(Problem.id)).where(
            and_(Problem.is_active == True, Problem.created_at >= dt_from, Problem.created_at <= dt_to)
        )
    )
    total = total_q.scalar() or 0

    data = {
        "by_category": by_category,
        "by_platform": by_platform,
        "sentiment_distribution": by_sentiment,
        "total_problems": total,
        "date_from": date_from,
        "date_to": date_to,
    }
    await cache_set(cache_key, data, ttl=3600)
    return JSONResponse(content=data)


@router.get("/export")
async def export_analytics_csv(
    request: Request,
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        dt_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        dt_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    from app.models.problem import Problem
    result = await db.execute(
        select(
            func.date(Problem.created_at).label("date"),
            Problem.platform,
            Problem.category,
            Problem.sentiment,
            func.count(Problem.id).label("problem_count"),
        )
        .where(and_(Problem.is_active == True, Problem.created_at >= dt_from, Problem.created_at <= dt_to))
        .group_by(func.date(Problem.created_at), Problem.platform, Problem.category, Problem.sentiment)
        .order_by(func.date(Problem.created_at))
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "platform", "category", "sentiment", "problem_count"])
    for row in rows:
        writer.writerow([row.date, row.platform, row.category, row.sentiment, row.problem_count])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=solvora-analytics-{date_from}-{date_to}.csv"},
    )
