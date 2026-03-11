"""Backfill sentiment for existing posts that have NULL sentiment.

Run from project root:
    cd src/backend && python ../../scripts/backfill_sentiment.py
"""
from __future__ import annotations

import sys
import os

# Allow running from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, "..", "src", "backend")
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv

# Try to load .env
for env_path in [
    os.path.join(backend_dir, ".env"),
    os.path.join(script_dir, "..", ".env"),
]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Strip asyncpg prefix for psycopg2
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
elif database_url.startswith("asyncpg://"):
    database_url = database_url.replace("asyncpg://", "postgresql://", 1)

from sqlalchemy import create_engine, text

URGENT_KEYWORDS = [
    "urgent", "emergency", "asap", "immediately", "critical", "help me",
    "please help", "broken", "crash", "error", "failing", "not working",
    "can't access", "cannot access", "data loss", "stuck",
]
FRUSTRATED_KEYWORDS = [
    "frustrated", "annoying", "ridiculous", "awful", "terrible", "horrible",
    "why is", "why does", "sick of", "fed up", "hate this", "worst",
    "unacceptable", "waste of time", "disgrace", "disappointed",
]
CURIOUS_KEYWORDS = [
    "how do i", "how does", "how can", "why does", "what is", "what are",
    "anyone know", "is it possible", "wondering", "curious",
    "explain", "understand", "learn", "best way", "anyone else",
]


def infer_sentiment(title: str, body: str) -> str:
    combined = f"{title} {body}".lower()
    for kw in URGENT_KEYWORDS:
        if kw in combined:
            return "urgent"
    for kw in FRUSTRATED_KEYWORDS:
        if kw in combined:
            return "frustrated"
    for kw in CURIOUS_KEYWORDS:
        if kw in combined:
            return "curious"
    return "neutral"


engine = create_engine(database_url)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, title, body FROM problems WHERE sentiment IS NULL")).fetchall()
    print(f"Found {len(rows)} posts without sentiment")

    updated = 0
    for row in rows:
        sentiment = infer_sentiment(row.title or "", row.body or "")
        conn.execute(
            text("UPDATE problems SET sentiment = :s WHERE id = :id"),
            {"s": sentiment, "id": row.id},
        )
        updated += 1

    conn.commit()
    print(f"Updated {updated} posts with inferred sentiment")

    # Show distribution
    dist = conn.execute(
        text("SELECT sentiment, COUNT(*) as cnt FROM problems GROUP BY sentiment ORDER BY cnt DESC")
    ).fetchall()
    print("\nSentiment distribution:")
    for row in dist:
        print(f"  {row.sentiment}: {row.cnt}")
