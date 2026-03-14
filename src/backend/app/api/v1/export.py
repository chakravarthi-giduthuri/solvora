import io
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.redis_client import cache_get, cache_set
from app.models.problem import Problem, Solution

router = APIRouter()


@router.get("/{problem_id}/export")
@limiter.limit("10/hour")
async def export_problem(
    request: Request,
    problem_id: str,
    format: str = Query("markdown", regex="^(markdown|pdf)$"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"export:{problem_id}:{format}"
    cached = await cache_get(cache_key)

    result = await db.execute(
        select(Problem).where(Problem.id == problem_id, Problem.is_active == True)
    )
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    sol_result = await db.execute(
        select(Solution).where(Solution.problem_id == problem_id, Solution.is_active == True)
    )
    solutions = sol_result.scalars().all()

    md_lines = [
        f"# {problem.title}",
        f"",
        f"**Platform**: {problem.platform}",
        f"**Category**: {problem.category or 'N/A'}",
        f"**Upvotes**: {problem.upvotes}",
        f"**Source**: {problem.url}",
        f"",
        f"## Problem Description",
        f"",
        problem.body or "",
        f"",
    ]
    for i, sol in enumerate(solutions, 1):
        md_lines += [
            f"## Solution {i} ({sol.provider})",
            f"",
            sol.solution_text,
            f"",
        ]
    markdown_content = "\n".join(md_lines)

    if format == "markdown":
        if not cached:
            await cache_set(cache_key, markdown_content, ttl=3600)
        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=problem-{problem_id}.md"},
        )
    else:
        try:
            import markdown as md_lib
            import weasyprint
            html_content = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
            <style>body{{font-family:sans-serif;max-width:800px;margin:auto;padding:2rem}}
            h1{{color:#1a1a2e}}h2{{color:#16213e}}</style></head>
            <body>{md_lib.markdown(markdown_content)}</body></html>"""
            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=problem-{problem_id}.pdf"},
            )
        except ImportError:
            raise HTTPException(status_code=501, detail="PDF export requires weasyprint package")
