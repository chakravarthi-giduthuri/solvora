import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.core.redis_client import get_redis

router = APIRouter()


@router.get("/problems")
async def problem_stream():
    async def event_generator():
        while True:
            try:
                r = await get_redis()
                count_bytes = await r.get("sse:new_problem_count")
                count = int(count_bytes) if count_bytes else 0
                if count > 0:
                    await r.set("sse:new_problem_count", 0)
                yield f"data: {count}\n\n"
            except Exception:
                yield "data: 0\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
