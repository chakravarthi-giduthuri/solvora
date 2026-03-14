"""Solvora v2.0 schema migration script.

Applies all v2.0 schema changes using ADD COLUMN IF NOT EXISTS and
CREATE TABLE IF NOT EXISTS — safe to re-run multiple times.

Usage:
    DATABASE_URL=postgresql://... python scripts/migrate_v2.py

Requires: psycopg2-binary (already in requirements.txt)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

# Auto-load .env from src/backend/.env
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # psycopg2 does not accept asyncpg-style URLs; normalise if needed
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()

    migrations: list[tuple[str, str]] = [
        # --- New columns on problems ---
        (
            "problems.potd_date",
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS potd_date DATE",
        ),
        (
            "problems.share_count",
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS share_count INTEGER NOT NULL DEFAULT 0",
        ),
        (
            "problems.source",
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS source VARCHAR(16) NOT NULL DEFAULT 'scraped'",
        ),
        (
            "problems.tags_auto",
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS tags_auto TEXT",
        ),
        # --- tags table ---
        (
            "CREATE TABLE tags",
            """
            CREATE TABLE IF NOT EXISTS tags (
                id          VARCHAR(36)  PRIMARY KEY,
                name        VARCHAR(64)  NOT NULL UNIQUE,
                slug        VARCHAR(64)  NOT NULL UNIQUE,
                use_count   INTEGER      NOT NULL DEFAULT 0,
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
            """,
        ),
        # --- problem_tags table ---
        (
            "CREATE TABLE problem_tags",
            """
            CREATE TABLE IF NOT EXISTS problem_tags (
                problem_id  VARCHAR(36) NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
                tag_id      VARCHAR(36) NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (problem_id, tag_id),
                CONSTRAINT uq_problem_tag UNIQUE (problem_id, tag_id)
            )
            """,
        ),
        # --- filter_presets table ---
        (
            "CREATE TABLE filter_presets",
            """
            CREATE TABLE IF NOT EXISTS filter_presets (
                id          VARCHAR(36)  PRIMARY KEY,
                user_id     VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name        VARCHAR(64)  NOT NULL,
                filters     TEXT         NOT NULL,
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_user_preset_name UNIQUE (user_id, name)
            )
            """,
        ),
        # --- index for POTD lookups ---
        (
            "INDEX idx_problems_potd_date",
            "CREATE INDEX IF NOT EXISTS idx_problems_potd_date ON problems (potd_date) WHERE potd_date IS NOT NULL",
        ),
        # --- Phase 2: Update platform check constraint to include 'user' ---
        (
            "problems.ck_platform add user",
            "ALTER TABLE problems DROP CONSTRAINT IF EXISTS ck_platform",
        ),
        (
            "problems.ck_platform recreate",
            "ALTER TABLE problems ADD CONSTRAINT ck_platform CHECK (platform IN ('reddit','hackernews','twitter','user'))",
        ),
        # --- Phase 2: User profile fields ---
        (
            "users.bio",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT",
        ),
        (
            "users.avatar_url",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512)",
        ),
        (
            "users.is_admin",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false",
        ),
        (
            "users.username",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(64)",
        ),
        (
            "INDEX idx_users_username",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username) WHERE username IS NOT NULL",
        ),
        # --- Phase 2: submitted_by_user_id on problems ---
        (
            "problems.submitted_by_user_id",
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS submitted_by_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL",
        ),
        # --- Phase 2: comments table ---
        (
            "CREATE TABLE comments",
            """
            CREATE TABLE IF NOT EXISTS comments (
                id          VARCHAR(36)  PRIMARY KEY,
                solution_id VARCHAR(36)  NOT NULL REFERENCES solutions(id) ON DELETE CASCADE,
                user_id     VARCHAR(36)  NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
                parent_id   VARCHAR(36)  REFERENCES comments(id)           ON DELETE CASCADE,
                body        TEXT         NOT NULL,
                is_active   BOOLEAN      NOT NULL DEFAULT true,
                is_flagged  BOOLEAN      NOT NULL DEFAULT false,
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
            """,
        ),
        (
            "INDEX idx_comments_solution_id",
            "CREATE INDEX IF NOT EXISTS ix_comments_solution_id ON comments (solution_id)",
        ),
        (
            "INDEX idx_comments_user_id",
            "CREATE INDEX IF NOT EXISTS ix_comments_user_id ON comments (user_id)",
        ),
        # --- Phase 2: user_notification_prefs table ---
        (
            "CREATE TABLE user_notification_prefs",
            """
            CREATE TABLE IF NOT EXISTS user_notification_prefs (
                user_id           VARCHAR(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                digest_enabled    BOOLEAN     NOT NULL DEFAULT false,
                digest_day        INTEGER     NOT NULL DEFAULT 1 CHECK (digest_day BETWEEN 1 AND 7),
                digest_hour_utc   INTEGER     NOT NULL DEFAULT 8  CHECK (digest_hour_utc BETWEEN 0 AND 23),
                category_interests TEXT       NOT NULL DEFAULT '[]',
                notify_on_comment BOOLEAN     NOT NULL DEFAULT true,
                notify_on_vote    BOOLEAN     NOT NULL DEFAULT false,
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
        ),
        # --- Phase 2: digest_sends table ---
        (
            "CREATE TABLE digest_sends",
            """
            CREATE TABLE IF NOT EXISTS digest_sends (
                id          VARCHAR(36)  PRIMARY KEY,
                user_id     VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                sent_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                problem_ids TEXT         NOT NULL DEFAULT '[]',
                status      VARCHAR(16)  NOT NULL DEFAULT 'sent' CHECK (status IN ('sent','failed'))
            )
            """,
        ),
        # --- Phase 2: problem_reports table ---
        (
            "CREATE TABLE problem_reports",
            """
            CREATE TABLE IF NOT EXISTS problem_reports (
                id          VARCHAR(36)  PRIMARY KEY,
                problem_id  VARCHAR(36)  NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
                reporter_id VARCHAR(36)  NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
                reason      VARCHAR(32)  NOT NULL CHECK (reason IN ('spam','inappropriate','duplicate','other')),
                detail      TEXT,
                status      VARCHAR(16)  NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','reviewed','dismissed')),
                reviewed_by VARCHAR(36)  REFERENCES users(id),
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_problem_reporter UNIQUE (problem_id, reporter_id)
            )
            """,
        ),
    ]

    print(f"Connecting to database...")
    print(f"Running {len(migrations)} migration steps...\n")

    for label, sql in migrations:
        try:
            cur.execute(sql)
            print(f"  OK  {label}")
        except Exception as exc:
            print(f"  FAIL {label}: {exc}", file=sys.stderr)
            cur.close()
            conn.close()
            sys.exit(1)

    cur.close()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
