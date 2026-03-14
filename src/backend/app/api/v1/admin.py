from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.problem import User, Problem, ProblemReport, Category

router = APIRouter()


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/scrapers/status")
async def get_scraper_status(admin: User = Depends(require_admin)):
    return {
        "reddit": {"status": "active", "note": "Managed by Celery beat"},
        "hn": {"status": "active", "note": "Managed by Celery beat"},
        "twitter": {"status": "active", "note": "Managed by Celery beat"},
    }


@router.post("/scrapers/{source}/trigger")
async def trigger_scraper(
    source: str,
    admin: User = Depends(require_admin),
):
    if source not in ("reddit", "hn", "twitter"):
        raise HTTPException(status_code=400, detail="Invalid source")
    if source == "reddit":
        from app.scrapers.tasks import run_reddit_scrape_task
        task = run_reddit_scrape_task.delay()
    elif source == "hn":
        from app.scrapers.tasks import run_hn_scrape_task
        task = run_hn_scrape_task.delay()
    else:
        try:
            from app.scrapers.twitter_scraper import run_twitter_scrape_task
            task = run_twitter_scrape_task.delay()
        except ImportError:
            raise HTTPException(status_code=501, detail="Twitter scraper not configured")
    return {"task_id": task.id}


@router.get("/reports")
async def list_reports(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(ProblemReport)
    if status_filter:
        q = q.where(ProblemReport.status == status_filter)
    result = await db.execute(q.order_by(ProblemReport.created_at.desc()).limit(100))
    reports = result.scalars().all()
    return [
        {"id": r.id, "problem_id": r.problem_id, "reporter_id": r.reporter_id,
         "reason": r.reason, "detail": r.detail, "status": r.status, "created_at": r.created_at.isoformat()}
        for r in reports
    ]


class ReportUpdate(BaseModel):
    status: str
    admin_note: Optional[str] = None


@router.put("/reports/{report_id}")
async def update_report(
    report_id: str,
    body: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(ProblemReport).where(ProblemReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if body.status not in ("pending", "reviewed", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    report.status = body.status
    report.reviewed_by = admin.id
    await db.commit()
    return {"id": report.id, "status": report.status}


@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(User)
    if search:
        q = q.where(User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%"))
    q = q.order_by(User.created_at.desc()).offset((page - 1) * 50).limit(50)
    result = await db.execute(q)
    users = result.scalars().all()
    return [
        {"id": u.id, "email": u.email, "name": u.name, "is_active": u.is_active,
         "is_admin": getattr(u, 'is_admin', False), "created_at": u.created_at.isoformat()}
        for u in users
    ]


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    await db.commit()
    return {"id": user.id, "is_active": user.is_active, "is_admin": getattr(user, 'is_admin', False)}


@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Category).order_by(Category.name))
    cats = result.scalars().all()
    return [{"id": c.id, "name": c.name, "slug": c.slug, "description": c.description} for c in cats]


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


@router.post("/categories", status_code=201)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    import uuid
    cat = Category(id=str(uuid.uuid4()), name=body.name, slug=body.slug, description=body.description)
    db.add(cat)
    await db.commit()
    return {"id": cat.id, "name": cat.name, "slug": cat.slug}


@router.put("/categories/{cat_id}")
async def update_category(
    cat_id: str,
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.name = body.name
    cat.slug = body.slug
    if body.description is not None:
        cat.description = body.description
    await db.commit()
    return {"id": cat.id, "name": cat.name, "slug": cat.slug}


@router.delete("/categories/{cat_id}", status_code=204)
async def delete_category(
    cat_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
