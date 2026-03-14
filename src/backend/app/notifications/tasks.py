"""Celery tasks for email notifications and weekly digest."""
from app.core.celery_app import celery_app


@celery_app.task(name="notifications.send_weekly_digests", bind=True, max_retries=3)
def send_weekly_digests_task(self):
    """Send weekly digest emails to users who have enabled digest."""
    import asyncio
    from app.core.database import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from app.models.problem import UserNotificationPrefs, User, Problem
            import json
            from datetime import datetime, timezone, timedelta

            now = datetime.now(timezone.utc)

            result = await db.execute(
                select(UserNotificationPrefs).where(
                    UserNotificationPrefs.digest_enabled == True,
                    UserNotificationPrefs.digest_day == now.isoweekday(),
                    UserNotificationPrefs.digest_hour_utc == now.hour,
                )
            )
            prefs_list = result.scalars().all()

            for prefs in prefs_list:
                try:
                    user_result = await db.execute(select(User).where(User.id == prefs.user_id))
                    user = user_result.scalar_one_or_none()
                    if not user or not user.is_active:
                        continue

                    since = now - timedelta(days=7)
                    q = select(Problem).where(Problem.is_active == True, Problem.created_at >= since)
                    interests = json.loads(prefs.category_interests)
                    if interests:
                        q = q.where(Problem.category.in_(interests))
                    q = q.order_by(Problem.upvotes.desc()).limit(5)
                    prob_result = await db.execute(q)
                    problems = prob_result.scalars().all()

                    if not problems:
                        continue

                    problem_ids = [p.id for p in problems]

                    try:
                        from app.core.config import settings
                        import resend
                        resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
                        if resend.api_key:
                            problem_list = "\n".join([f"- {p.title}" for p in problems])
                            resend.Emails.send({
                                "from": "digest@solvora.io",
                                "to": user.email,
                                "subject": f"Your Solvora Weekly Digest - {now.strftime('%B %d')}",
                                "text": (
                                    f"Hi {user.name},\n\nHere are your top problems this week:\n\n"
                                    f"{problem_list}\n\nVisit https://solvora.io to read more.\n\n"
                                    "Unsubscribe: https://solvora.io/settings/notifications"
                                ),
                            })
                    except Exception:
                        pass  # Email service not configured

                    from app.models.problem import DigestSend
                    import uuid
                    digest = DigestSend(
                        id=str(uuid.uuid4()),
                        user_id=prefs.user_id,
                        problem_ids=json.dumps(problem_ids),
                        status="sent",
                    )
                    db.add(digest)
                except Exception:
                    pass
            await db.commit()

    asyncio.run(_run())
