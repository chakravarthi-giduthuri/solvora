from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.core.redis_client import cache_get, cache_set

router = APIRouter()

PERIOD_HOURS = {"24h": 24, "7d": 168, "30d": 720}


@router.get("")
async def get_leaderboard(
    type: str = Query("problems", regex="^(problems|solutions|categories)$"),
    period: str = Query("7d", regex="^(24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"leaderboard:{type}:{period}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    hours = PERIOD_HOURS[period]
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    if type == "problems":
        from app.models.problem import Problem
        result = await db.execute(
            select(Problem.id, Problem.title, Problem.category, Problem.upvotes, Problem.comment_count)
            .where(Problem.is_active == True, Problem.created_at >= since)
            .order_by((Problem.upvotes + Problem.comment_count).desc())
            .limit(20)
        )
        items = [
            {"rank": i + 1, "id": row.id, "title": row.title, "category": row.category,
             "score": row.upvotes + row.comment_count}
            for i, row in enumerate(result.all())
        ]
    elif type == "solutions":
        from app.models.problem import Solution
        result = await db.execute(
            select(Solution.id, Solution.problem_id, Solution.provider, Solution.rating)
            .where(Solution.is_active == True)
            .order_by(Solution.rating.desc())
            .limit(20)
        )
        items = [
            {"rank": i + 1, "id": row.id, "problem_id": row.problem_id,
             "provider": row.provider, "score": row.rating}
            for i, row in enumerate(result.all())
        ]
    else:  # categories
        from app.models.problem import Problem
        result = await db.execute(
            select(Problem.category, func.count(Problem.id).label("count"))
            .where(Problem.is_active == True, Problem.created_at >= since, Problem.category != None)
            .group_by(Problem.category)
            .order_by(func.count(Problem.id).desc())
            .limit(20)
        )
        items = [
            {"rank": i + 1, "category": row.category, "count": row.count}
            for i, row in enumerate(result.all())
        ]

    data = {
        "items": items,
        "type": type,
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await cache_set(cache_key, data, ttl=600)
    return JSONResponse(content=data)
