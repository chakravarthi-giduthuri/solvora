"""Analytics service providing aggregated dashboard metrics."""

from __future__ import annotations

import structlog
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import cache_get, cache_set

logger = structlog.get_logger(__name__)

_TRENDING_TTL = 600
_TRENDING_SPARKLINE_DAYS = 7
_TRENDING_TOP_N = 20

_PERIOD_HOURS: dict[str, int] = {
    "24h": 24,
    "7d": 168,
    "30d": 720,
}


async def get_trending_topics(
    db: AsyncSession,
    redis: object,
    period: str = "24h",
) -> list[dict]:
    """Return top trending categories for *period*."""
    if period not in _PERIOD_HOURS:
        period = "24h"

    cache_key = f"analytics:trending:{period}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    topics = await _compute_trending(db, period)
    await cache_set(cache_key, topics, ttl=_TRENDING_TTL)
    return topics


async def _compute_trending(db: AsyncSession, period: str) -> list[dict]:
    hours = _PERIOD_HOURS[period]
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    top_rows = (await db.execute(
        text("""
            SELECT category, COUNT(*) AS count
            FROM problems
            WHERE is_active = true AND category IS NOT NULL AND scraped_at >= :since
            GROUP BY category ORDER BY count DESC LIMIT :top_n
        """),
        {"since": since, "top_n": _TRENDING_TOP_N},
    )).fetchall()

    if not top_rows:
        top_rows = (await db.execute(
            text("""
                SELECT category, COUNT(*) AS count
                FROM problems
                WHERE is_active = true AND category IS NOT NULL
                GROUP BY category ORDER BY count DESC LIMIT :top_n
            """),
            {"top_n": _TRENDING_TOP_N},
        )).fetchall()

    topics: list[dict] = []
    for row in top_rows:
        category = row.category
        sparkline = await _build_sparkline(db, category)
        first = sparkline[0] if sparkline else 0
        last = sparkline[-1] if sparkline else 0
        change = round(((last - first) / max(first, 1)) * 100) if first > 0 else 0
        topics.append({
            "id": category,
            "name": category.replace("-", " ").title(),
            "category": category,
            "count": int(row.count),
            "change": change,
            "sparklineData": sparkline,
        })

    return topics


async def _build_sparkline(db: AsyncSession, category: str) -> list[int]:
    today = datetime.now(timezone.utc).date()
    since_7d = today - timedelta(days=_TRENDING_SPARKLINE_DAYS - 1)

    rows = (await db.execute(
        text("""
            SELECT DATE(scraped_at AT TIME ZONE 'UTC') AS day, COUNT(*) AS count
            FROM problems
            WHERE category = :category AND is_active = true
              AND DATE(scraped_at AT TIME ZONE 'UTC') >= :since
            GROUP BY day ORDER BY day ASC
        """),
        {"category": category, "since": since_7d},
    )).fetchall()

    count_by_day: dict[str, int] = {str(r.day): int(r.count) for r in rows}
    return [
        count_by_day.get(str(since_7d + timedelta(days=i)), 0)
        for i in range(_TRENDING_SPARKLINE_DAYS)
    ]


async def get_analytics_summary_data(db: AsyncSession) -> dict:
    """Return summary analytics matching AnalyticsSummary frontend type."""
    total_row = (await db.execute(text("SELECT COUNT(*) FROM problems WHERE is_active = true"))).scalar_one()
    sol_row = (await db.execute(text("SELECT COUNT(*) FROM solutions WHERE is_active = true"))).scalar_one()
    problems_with_sol = (await db.execute(
        text("SELECT COUNT(DISTINCT problem_id) FROM solutions WHERE is_active = true")
    )).scalar_one()

    solved_rate = (problems_with_sol / max(total_row, 1))
    avg_sol = (int(sol_row) / max(total_row, 1))

    cat_rows = (await db.execute(text("""
        SELECT category, COUNT(*) AS count
        FROM problems WHERE is_active = true AND category IS NOT NULL
        GROUP BY category ORDER BY count DESC
    """))).fetchall()

    total_cat = sum(int(r.count) for r in cat_rows) or 1
    problems_by_category = [
        {"category": r.category.replace("-", " ").title(), "count": int(r.count), "percentage": round(int(r.count) / total_cat * 100, 1)}
        for r in cat_rows
    ]

    vol_rows = (await db.execute(text("""
        SELECT DATE(scraped_at AT TIME ZONE 'UTC') AS day,
               SUM(CASE WHEN platform='reddit' THEN 1 ELSE 0 END) AS reddit,
               SUM(CASE WHEN platform='hackernews' THEN 1 ELSE 0 END) AS hackernews,
               COUNT(*) AS total
        FROM problems WHERE is_active = true
          AND scraped_at >= NOW() - INTERVAL '30 days'
        GROUP BY day ORDER BY day ASC
    """))).fetchall()

    volume_over_time = [
        {"date": str(r.day), "reddit": int(r.reddit), "hackernews": int(r.hackernews), "total": int(r.total)}
        for r in vol_rows
    ]

    sent_rows = (await db.execute(text("""
        SELECT sentiment, COUNT(*) AS count
        FROM problems WHERE is_active = true AND sentiment IS NOT NULL
        GROUP BY sentiment
    """))).fetchall()
    sentiment_dist = {"urgent": 0, "frustrated": 0, "curious": 0, "neutral": 0}
    for r in sent_rows:
        if r.sentiment in sentiment_dist:
            sentiment_dist[r.sentiment] = int(r.count)

    plat_rows = (await db.execute(text("""
        SELECT platform, COUNT(*) AS count FROM problems WHERE is_active=true GROUP BY platform
    """))).fetchall()
    platform_breakdown = {"reddit": 0, "hackernews": 0}
    for r in plat_rows:
        if r.platform in platform_breakdown:
            platform_breakdown[r.platform] = int(r.count)

    return {
        "totalProblems": int(total_row),
        "totalSolutions": int(sol_row),
        "solvedRate": round(solved_rate, 4),
        "avgSolutionsPerProblem": round(avg_sol, 2),
        "problemsByCategory": problems_by_category,
        "topCategories": problems_by_category[:5],
        "volumeOverTime": volume_over_time,
        "sentimentDistribution": sentiment_dist,
        "activityHeatmap": [],
        "platformBreakdown": platform_breakdown,
    }


async def get_dashboard_data(db: AsyncSession) -> dict[str, Any]:
    """Full dashboard data for the analytics page."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # ── KPI metrics ──────────────────────────────────────────────────────────
    total_now = (await db.execute(text(
        "SELECT COUNT(*) FROM problems WHERE is_active = true"
    ))).scalar_one()

    total_week_ago = (await db.execute(text(
        "SELECT COUNT(*) FROM problems WHERE is_active = true AND scraped_at < :since"
    ), {"since": week_ago})).scalar_one()

    total_solutions = (await db.execute(text(
        "SELECT COUNT(*) FROM solutions WHERE is_active = true"
    ))).scalar_one()

    solutions_week_ago = (await db.execute(text(
        "SELECT COUNT(*) FROM solutions WHERE is_active = true AND generated_at < :since"
    ), {"since": week_ago})).scalar_one()

    problems_with_sol = (await db.execute(text(
        "SELECT COUNT(DISTINCT problem_id) FROM solutions WHERE is_active = true"
    ))).scalar_one()

    solution_rate = round(int(problems_with_sol) / max(int(total_now), 1) * 100, 1)

    # Check if problem_clicks table exists
    try:
        total_clicks = (await db.execute(text(
            "SELECT COUNT(*) FROM problem_clicks"
        ))).scalar_one()
        clicks_this_week = (await db.execute(text(
            "SELECT COUNT(*) FROM problem_clicks WHERE clicked_at >= :since"
        ), {"since": week_ago})).scalar_one()
        clicks_last_week = (await db.execute(text(
            "SELECT COUNT(*) FROM problem_clicks WHERE clicked_at >= :from_ AND clicked_at < :to_"
        ), {"from_": two_weeks_ago, "to_": week_ago})).scalar_one()
        clicks_table_exists = True
    except Exception:
        total_clicks = 0
        clicks_this_week = 0
        clicks_last_week = 0
        clicks_table_exists = False

    def pct_change(now_val: int, prev_val: int) -> int:
        if prev_val == 0:
            return 100 if now_val > 0 else 0
        return round((now_val - prev_val) / prev_val * 100)

    kpis = {
        "totalProblems": int(total_now),
        "totalProblemsChange": pct_change(int(total_now), int(total_week_ago)),
        "totalClicks": int(total_clicks),
        "totalClicksChange": pct_change(int(clicks_this_week), int(clicks_last_week)),
        "solutionRate": solution_rate,
        "solutionRateChange": 0,
        "totalSolutions": int(total_solutions),
        "totalSolutionsChange": pct_change(int(total_solutions), int(solutions_week_ago)),
    }

    # ── Top clicked problems ──────────────────────────────────────────────────
    top_clicked: list[dict] = []
    if clicks_table_exists and int(total_clicks) > 0:
        rows = (await db.execute(text("""
            SELECT pc.problem_id, p.title, p.category,
                   COUNT(*) AS total_clicks,
                   SUM(CASE WHEN pc.clicked_at >= :since THEN 1 ELSE 0 END) AS week_clicks,
                   SUM(CASE WHEN pc.clicked_at >= :prev_from AND pc.clicked_at < :since THEN 1 ELSE 0 END) AS prev_clicks,
                   (SELECT COUNT(*) > 0 FROM solutions s WHERE s.problem_id = pc.problem_id AND s.is_active = true) AS has_solution
            FROM problem_clicks pc
            JOIN problems p ON p.id = pc.problem_id
            GROUP BY pc.problem_id, p.title, p.category
            ORDER BY total_clicks DESC
            LIMIT 10
        """), {"since": week_ago, "prev_from": two_weeks_ago})).fetchall()

        for r in rows:
            top_clicked.append({
                "id": str(r.problem_id),
                "title": r.title,
                "category": (r.category or "other").replace("-", " ").title(),
                "clicks": int(r.total_clicks),
                "clicksChange": pct_change(int(r.week_clicks), int(r.prev_clicks)),
                "hasSolution": bool(r.has_solution),
            })
    else:
        # Fallback: use upvotes as proxy for popularity
        rows = (await db.execute(text("""
            SELECT p.id, p.title, p.category, p.upvotes,
                   (SELECT COUNT(*) FROM solutions s WHERE s.problem_id = p.id AND s.is_active = true) AS sol_count
            FROM problems p
            WHERE p.is_active = true
            ORDER BY p.upvotes DESC
            LIMIT 10
        """))).fetchall()

        for r in rows:
            top_clicked.append({
                "id": str(r.id),
                "title": r.title,
                "category": (r.category or "other").replace("-", " ").title(),
                "clicks": int(r.upvotes),
                "clicksChange": 0,
                "hasSolution": int(r.sol_count) > 0,
            })

    # ── Category distribution ────────────────────────────────────────────────
    cat_rows = (await db.execute(text("""
        SELECT
            p.category,
            COUNT(*) AS total,
            COUNT(DISTINCT s.problem_id) AS with_solution,
            SUM(CASE WHEN p.scraped_at >= :since THEN 1 ELSE 0 END) AS this_week,
            SUM(CASE WHEN p.scraped_at >= :prev_from AND p.scraped_at < :since THEN 1 ELSE 0 END) AS last_week
        FROM problems p
        LEFT JOIN solutions s ON s.problem_id = p.id AND s.is_active = true
        WHERE p.is_active = true AND p.category IS NOT NULL
        GROUP BY p.category
        ORDER BY total DESC
    """), {"since": week_ago, "prev_from": two_weeks_ago})).fetchall()

    grand_total = sum(int(r.total) for r in cat_rows) or 1

    category_distribution = []
    for r in cat_rows:
        total_c = int(r.total)
        with_sol = int(r.with_solution)
        this_wk = int(r.this_week)
        last_wk = int(r.last_week)
        category_distribution.append({
            "category": r.category,
            "name": r.category.replace("-", " ").title(),
            "count": total_c,
            "percentage": round(total_c / grand_total * 100, 1),
            "solutionCount": with_sol,
            "solutionRate": round(with_sol / max(total_c, 1) * 100, 1),
            "change": pct_change(this_wk, last_wk),
        })

    return {
        "kpis": kpis,
        "topClickedProblems": top_clicked,
        "categoryDistribution": category_distribution,
    }
