import math
import hashlib
import json
import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.redis_client import cache_get, cache_set
from app.core.security import get_current_user
from app.models.problem import Problem
from app.schemas.problem import ProblemResponse, PaginatedProblems, TrendingTopic

router = APIRouter()

_ALLOWED_PROVIDERS = frozenset({"gemini", "openai", "claude"})
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


@router.get("/", response_model=None)
async def list_problems(
    platform: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    has_solution: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    cache_key = "problems:" + hashlib.md5(json.dumps({
        "platform": platform, "category": category, "sentiment": sentiment,
        "date_from": date_from, "date_to": date_to, "has_solution": has_solution,
        "search": search, "sort_by": sort_by, "page": page, "per_page": per_page
    }, sort_keys=True).encode()).hexdigest()

    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    filters = [Problem.is_active == True]
    if platform:
        filters.append(Problem.platform == platform)
    if category:
        # Match by category name or slug
        filters.append(Problem.category == category)
    if sentiment:
        filters.append(Problem.sentiment == sentiment)
    if search:
        filters.append(or_(
            Problem.title.ilike(f"%{search}%"),
            Problem.body.ilike(f"%{search}%")
        ))

    count_q = select(func.count()).select_from(Problem).where(and_(*filters))
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * per_page
    q = (select(Problem).where(and_(*filters))
         .options(selectinload(Problem.solutions)))

    # Sorting
    if sort_by == "upvotes":
        q = q.order_by(Problem.upvotes.desc())
    elif sort_by == "comments":
        q = q.order_by(Problem.comment_count.desc())
    else:
        q = q.order_by(Problem.created_at.desc())

    q = q.offset(offset).limit(per_page)

    if has_solution is True:
        from sqlalchemy import exists
        from app.models.problem import Solution
        q = q.where(exists().where(Solution.problem_id == Problem.id))

    result = await db.execute(q)
    problems = result.scalars().all()

    total_pages = math.ceil(total / per_page) if total else 0
    items_data = [
        ProblemResponse.model_validate(p).model_dump(mode='json', by_alias=True)
        for p in problems
    ]
    data = {
        "items": items_data,
        "total": total,
        "page": page,
        "perPage": per_page,
        "totalPages": total_pages,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
    }

    await cache_set(cache_key, data, ttl=600)
    return JSONResponse(content=data)


@router.get("/trending", response_model=None)
async def get_trending(
    period: str = Query("24h", pattern="^(24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"trending:{period}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    from app.services.analytics_service import get_trending_topics
    topics = await get_trending_topics(db, None, period)
    await cache_set(cache_key, topics, ttl=600)
    return JSONResponse(content=topics)


@router.get("/autocomplete", response_model=None)
async def autocomplete_problems(
    q: str = Query("", min_length=0),
    db: AsyncSession = Depends(get_db),
):
    if len(q.strip()) < 2:
        return JSONResponse(content={"suggestions": []})
    cache_key = f"autocomplete:{hashlib.md5(q.lower().strip().encode()).hexdigest()}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)
    result = await db.execute(
        select(Problem.title).where(
            Problem.title.ilike(f"%{q}%"),
            Problem.is_active == True
        ).distinct().limit(10)
    )
    suggestions = [row[0] for row in result.fetchall()]
    data = {"suggestions": suggestions}
    await cache_set(cache_key, data, ttl=900)
    return JSONResponse(content=data)


@router.get("/potd", response_model=None)
async def get_potd(db: AsyncSession = Depends(get_db)):
    from datetime import date as date_type, timedelta, timezone as tz
    today = date_type.today().isoformat()
    cache_key = f"potd:{today}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)
    result = await db.execute(
        select(Problem).where(
            Problem.potd_date == date_type.today(),
            Problem.is_active == True
        ).options(selectinload(Problem.solutions)).limit(1)
    )
    problem = result.scalar_one_or_none()
    if not problem:
        # No POTD set for today — auto-select the highest-upvoted active problem
        # and mark it as today's POTD so it persists for the rest of the day.
        fallback = await db.execute(
            select(Problem).where(
                Problem.is_active == True,
                Problem.is_problem == True,
                Problem.potd_date == None,
            ).options(selectinload(Problem.solutions))
            .order_by(Problem.upvotes.desc(), Problem.comment_count.desc())
            .limit(1)
        )
        problem = fallback.scalar_one_or_none()
        if problem:
            problem.potd_date = date_type.today()
            await db.commit()
            await db.refresh(problem)
    if not problem:
        data = {"potd": None}
    else:
        data = {"potd": ProblemResponse.model_validate(problem).model_dump(mode='json', by_alias=True)}
    from datetime import datetime, timezone as tz2
    now = datetime.now(tz2.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=tz2.utc)
    from datetime import timedelta
    midnight += timedelta(days=1)
    ttl = int((midnight - now).total_seconds())
    await cache_set(cache_key, data, ttl=ttl)
    return JSONResponse(content=data)


@router.post("/{problem_id}/share", response_model=None)
@limiter.limit("10/minute")
async def track_share(request: Request, problem_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    problem.share_count = (problem.share_count or 0) + 1
    await db.commit()
    return JSONResponse(content={"share_count": problem.share_count})


@router.get("/{problem_id}", response_model=None)
async def get_problem(problem_id: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"problem:{problem_id}"
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    q = (select(Problem).where(Problem.id == problem_id)
         .options(selectinload(Problem.solutions)))
    result = await db.execute(q)
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    data = ProblemResponse.model_validate(problem).model_dump(mode='json', by_alias=True)
    await cache_set(cache_key, data, ttl=900)
    return JSONResponse(content=data)


@router.get("/{problem_id}/solutions", response_model=None)
async def get_problem_solutions(problem_id: str, db: AsyncSession = Depends(get_db)):
    """Get solutions for a specific problem (frontend-friendly URL)."""
    from app.models.problem import Solution
    from app.schemas.problem import SolutionResponse

    q = select(Solution).where(
        Solution.problem_id == problem_id,
        Solution.is_active == True,
    )
    result = await db.execute(q)
    solutions = result.scalars().all()
    data = [SolutionResponse.model_validate(s).model_dump(mode='json', by_alias=True) for s in solutions]
    return JSONResponse(content=data)


@router.post("/{problem_id}/solutions/generate", response_model=None)
async def generate_problem_solutions(
    problem_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger AI solution generation inline (no Celery required). Requires authentication."""
    import asyncio
    raw_providers = body.get("providers", list(_ALLOWED_PROVIDERS))
    if not isinstance(raw_providers, list):
        raise HTTPException(status_code=400, detail="providers must be a list")
    providers = [p for p in raw_providers if p in _ALLOWED_PROVIDERS]
    if not providers:
        raise HTTPException(status_code=400, detail="No valid providers. Allowed: gemini, openai, claude")

    q = select(Problem).where(Problem.id == problem_id)
    result = await db.execute(q)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Problem not found")

    try:
        from app.ai.solution_orchestrator import SolutionOrchestrator

        def _run_sync():
            orchestrator = SolutionOrchestrator()
            return orchestrator.generate_for_problem(problem_id, providers)

        results = await asyncio.to_thread(_run_sync)
        generated = [p for p, txt in results.items() if txt]
        failed = [p for p in providers if p not in generated]

        if not generated:
            return JSONResponse(
                content={
                    "status": "failed",
                    "generated": [],
                    "failed": failed,
                    "message": "All AI providers failed. Check API keys and quota in backend .env",
                },
                status_code=422,
            )

        return JSONResponse(content={"status": "completed", "generated": generated, "failed": failed})
    except Exception as exc:
        return JSONResponse(
            content={"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.post("/{problem_id}/click", response_model=None)
@limiter.limit("30/minute")
async def track_problem_click(request: Request, problem_id: str, db: AsyncSession = Depends(get_db)):
    """Track when a user clicks on a problem."""
    if not _UUID_RE.match(problem_id):
        return {"ok": True}  # Silently drop invalid IDs
    from app.models.problem import ProblemClick
    click = ProblemClick(problem_id=problem_id)
    db.add(click)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
    return {"ok": True}
