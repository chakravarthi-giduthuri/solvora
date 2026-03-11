#!/usr/bin/env python3
"""Seed the categories table with the default Solvora taxonomy."""

from __future__ import annotations

import sys
import os

# Allow running from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

CATEGORIES: list[str] = [
    "Technology",
    "Health",
    "Finance",
    "Relationships",
    "Productivity",
    "Travel",
    "Education",
    "Career",
    "Legal",
    "Mental Health",
    "Environment",
    "Food",
    "Housing",
    "Transportation",
    "Other",
]


def get_database_url() -> str:
    """Read DATABASE_URL from the environment or src/backend/.env file."""
    from dotenv import load_dotenv  # type: ignore[import]

    # Try src/backend/.env first, then project root .env
    base = os.path.dirname(__file__)
    for candidate in [
        os.path.join(base, '..', 'src', 'backend', '.env'),
        os.path.join(base, '..', '.env'),
    ]:
        if os.path.exists(candidate):
            load_dotenv(candidate)
            break

    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Ensure src/backend/.env exists and contains DATABASE_URL."
        )
    # Seed script uses sync psycopg2 — strip asyncpg dialect and sslmode
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    # Remove sslmode query param for psycopg2 (pass via connect_args instead)
    if "sslmode=" in url:
        import re
        url = re.sub(r'[?&]sslmode=[^&]*', '', url).rstrip('?').rstrip('&')
    return url


def seed_categories(database_url: str) -> None:
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        existing: set[str] = set(
            row[0]
            for row in session.execute(text("SELECT name FROM categories")).fetchall()
        )

        inserted = 0
        for name in CATEGORIES:
            if name not in existing:
                slug = name.lower().replace(" ", "-")
                session.execute(
                    text("INSERT INTO categories (id, name, slug) VALUES (:id, :name, :slug)"),
                    {"id": str(__import__('uuid').uuid4()), "name": name, "slug": slug},
                )
                inserted += 1
                print(f"  [+] {name}")
            else:
                print(f"  [ ] {name} (already exists)")

        session.commit()

    print(f"\nDone. {inserted} categories inserted, {len(CATEGORIES) - inserted} skipped.")


def main() -> None:
    print("Seeding categories table...")
    database_url = get_database_url()
    seed_categories(database_url)


if __name__ == "__main__":
    main()
