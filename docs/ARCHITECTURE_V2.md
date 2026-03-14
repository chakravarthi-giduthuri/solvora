# Solvora v2.0 Architecture Document

**Date**: 2026-03-12
**Status**: Approved for implementation
**Author**: System Architecture Designer

---

## Table of Contents

1. [System Context](#system-context)
2. [Database Schema Changes](#1-database-schema-changes)
3. [New Backend API Endpoints](#2-new-backend-api-endpoints)
4. [New Frontend Pages and Components](#3-new-frontend-pages-and-components)
5. [Infrastructure Changes](#4-infrastructure-changes)
6. [Phased Implementation Roadmap](#5-phased-implementation-roadmap)
7. [Architecture Decision Records](#6-architecture-decision-records)

---

## System Context

### v1.0 Stack (Unchanged)

```
┌─────────────────────────────────────────────────────────────────┐
│  Vercel                       Railway                           │
│  ┌─────────────────┐         ┌───────────────────────────────┐  │
│  │  Next.js 14     │ HTTPS   │  FastAPI (async)              │  │
│  │  App Router     │◄───────►│  /api/v1/*                    │  │
│  │  SSR + CSR      │         │                               │  │
│  └─────────────────┘         │  Celery Worker + Beat         │  │
│                               │  (scrape / classify / AI)    │  │
│                               └───────────────────────────────┘  │
│                                        │           │              │
│                               ┌────────┘    ┌──────┘             │
│                               ▼             ▼                     │
│                         Neon (Postgres) Upstash (Redis)          │
└─────────────────────────────────────────────────────────────────┘
```

### v2.0 Additions

Two new external services are introduced:

- **Email Service** (Resend or SendGrid) — weekly digest, notification emails
- **Twitter/X API v2** — fourth scraper data source

All other infrastructure (Railway, Vercel, Neon, Upstash) is retained and extended.

---

## 1. Database Schema Changes

### Conventions Followed

- All primary keys remain `String(36)` UUID matching the existing `Problem`, `User`, and `Solution` pattern
- All timestamps are `DateTime(timezone=True)` with `utcnow` default (matches existing `utcnow()` helper)
- `is_active` soft-delete column is added to every new deletable table
- `CheckConstraint` guards are added for all enum-valued columns (matching `ck_platform`, `ck_sentiment` precedent)
- New SQLAlchemy relationships follow the existing `back_populates` + `cascade="all, delete-orphan"` pattern

---

### 1.1 Modified: `problems` table

#### New columns

| Column | Type | Nullable | Default | Purpose |
|---|---|---|---|---|
| `submitted_by_user_id` | `String(36)` FK `users.id` | YES | NULL | Links user-submitted problems to their author |
| `source` | `String(16)` | NO | `'scraped'` | Distinguishes `'scraped'` from `'user_submitted'` |
| `tags_auto` | `Text` | YES | NULL | JSON array of AI-detected tag names |
| `potd_date` | `Date` | YES | NULL | Set to the calendar date when selected as Problem of the Day |
| `share_count` | `Integer` | NO | `0` | Incremented by the share-button endpoint |

#### New constraint

```sql
ALTER TABLE problems
    ADD CONSTRAINT ck_source
    CHECK (source IN ('scraped', 'user_submitted'));
```

#### New indexes

```sql
CREATE INDEX ix_problems_submitted_by ON problems (submitted_by_user_id)
    WHERE submitted_by_user_id IS NOT NULL;

CREATE INDEX ix_problems_potd_date ON problems (potd_date)
    WHERE potd_date IS NOT NULL;

CREATE INDEX ix_problems_source ON problems (source);
```

#### Note on `platform` CHECK constraint

The existing `ck_platform` constraint restricts platform to `('reddit','hackernews','twitter')`. Twitter is already present. No migration is needed for the Twitter scraper.

---

### 1.2 New table: `tags`

Canonical tag registry. Tags are either user-created or auto-detected by the NLP classifier.

```sql
CREATE TABLE tags (
    id          VARCHAR(36)  PRIMARY KEY,
    name        VARCHAR(64)  NOT NULL UNIQUE,
    slug        VARCHAR(64)  NOT NULL UNIQUE,
    source      VARCHAR(16)  NOT NULL DEFAULT 'user',  -- 'user' | 'ai'
    use_count   INTEGER      NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CHECK (source IN ('user', 'ai'))
);

CREATE INDEX ix_tags_slug       ON tags (slug);
CREATE INDEX ix_tags_use_count  ON tags (use_count DESC);
```

---

### 1.3 New table: `problem_tags`

Many-to-many join between problems and tags.

```sql
CREATE TABLE problem_tags (
    problem_id  VARCHAR(36)  NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    tag_id      VARCHAR(36)  NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
    added_by    VARCHAR(16)  NOT NULL DEFAULT 'user',  -- 'user' | 'ai'
    PRIMARY KEY (problem_id, tag_id),
    CHECK (added_by IN ('user', 'ai'))
);

CREATE INDEX ix_problem_tags_tag_id  ON problem_tags (tag_id);
```

---

### 1.4 New table: `comments`

Threaded discussion on solutions. Self-referential FK enables two-level nesting (comment + replies). Deeper nesting is intentionally not supported in v2.0 (see ADR-001).

```sql
CREATE TABLE comments (
    id          VARCHAR(36)  PRIMARY KEY,
    solution_id VARCHAR(36)  NOT NULL REFERENCES solutions(id)  ON DELETE CASCADE,
    user_id     VARCHAR(36)  NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
    parent_id   VARCHAR(36)  REFERENCES comments(id)            ON DELETE CASCADE,
    body        TEXT         NOT NULL,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    is_flagged  BOOLEAN      NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX ix_comments_solution_id  ON comments (solution_id);
CREATE INDEX ix_comments_user_id      ON comments (user_id);
CREATE INDEX ix_comments_parent_id    ON comments (parent_id)
    WHERE parent_id IS NOT NULL;
```

---

### 1.5 New table: `user_notification_prefs`

Per-user notification and digest configuration.

```sql
CREATE TABLE user_notification_prefs (
    user_id                VARCHAR(36)   PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    digest_enabled         BOOLEAN       NOT NULL DEFAULT false,
    digest_day             INTEGER       NOT NULL DEFAULT 1,   -- 1=Mon … 7=Sun
    digest_hour_utc        INTEGER       NOT NULL DEFAULT 8,   -- 0-23
    category_interests     TEXT          NOT NULL DEFAULT '[]', -- JSON array of category slugs
    notify_on_comment      BOOLEAN       NOT NULL DEFAULT true,
    notify_on_vote         BOOLEAN       NOT NULL DEFAULT false,
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CHECK (digest_day     BETWEEN 1 AND 7),
    CHECK (digest_hour_utc BETWEEN 0 AND 23)
);
```

---

### 1.6 New table: `digest_sends`

Audit log of every digest email dispatched.

```sql
CREATE TABLE digest_sends (
    id          VARCHAR(36)  PRIMARY KEY,
    user_id     VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sent_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    problem_ids TEXT         NOT NULL DEFAULT '[]',  -- JSON array
    status      VARCHAR(16)  NOT NULL DEFAULT 'sent', -- 'sent' | 'failed'
    CHECK (status IN ('sent', 'failed'))
);

CREATE INDEX ix_digest_sends_user_id  ON digest_sends (user_id);
CREATE INDEX ix_digest_sends_sent_at  ON digest_sends (sent_at DESC);
```

---

### 1.7 New table: `filter_presets`

Saved, named filter combinations per user.

```sql
CREATE TABLE filter_presets (
    id          VARCHAR(36)  PRIMARY KEY,
    user_id     VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(128) NOT NULL,
    filters     TEXT         NOT NULL,  -- JSON blob of ProblemsParams
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE INDEX ix_filter_presets_user_id  ON filter_presets (user_id);
```

---

### 1.8 Modified: `users` table

#### New columns

| Column | Type | Nullable | Default | Purpose |
|---|---|---|---|---|
| `bio` | `Text` | YES | NULL | Public profile bio |
| `avatar_url` | `String(512)` | YES | NULL | Profile picture URL (CDN or OAuth-provided) |
| `is_admin` | `Boolean` | NO | `false` | Gates access to `/admin` routes |
| `username` | `String(64)` | YES | NULL | URL-safe public handle for `/profile/[username]` |

#### New indexes

```sql
CREATE UNIQUE INDEX ix_users_username ON users (username)
    WHERE username IS NOT NULL;
```

---

### 1.9 New table: `problem_reports`

User-flagged content submitted for admin review.

```sql
CREATE TABLE problem_reports (
    id          VARCHAR(36)  PRIMARY KEY,
    problem_id  VARCHAR(36)  NOT NULL REFERENCES problems(id)  ON DELETE CASCADE,
    reporter_id VARCHAR(36)  NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    reason      VARCHAR(32)  NOT NULL,  -- 'spam'|'inappropriate'|'duplicate'|'other'
    detail      TEXT,
    status      VARCHAR(16)  NOT NULL DEFAULT 'pending', -- 'pending'|'reviewed'|'dismissed'
    reviewed_by VARCHAR(36)  REFERENCES users(id),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (problem_id, reporter_id),
    CHECK (reason  IN ('spam', 'inappropriate', 'duplicate', 'other')),
    CHECK (status  IN ('pending', 'reviewed', 'dismissed'))
);

CREATE INDEX ix_problem_reports_status  ON problem_reports (status);
```

---

### Summary: Schema Migration Plan

Alembic migrations should be applied in this order:

1. `add_columns_users` — bio, avatar_url, is_admin, username
2. `add_columns_problems` — submitted_by_user_id, source, tags_auto, potd_date, share_count
3. `create_tags_and_problem_tags`
4. `create_comments`
5. `create_filter_presets`
6. `create_user_notification_prefs`
7. `create_digest_sends`
8. `create_problem_reports`

Each migration is independent and non-destructive on existing rows.

---

## 2. New Backend API Endpoints

### Conventions Followed

- All new routes are registered in `app/main.py` under `/api/v1/` matching `app.include_router(...)` pattern
- Caching follows `cache_get` / `cache_set` from `app/core/redis_client.py` with explicit TTL
- Rate limiting uses the existing `@limiter.limit("N/period")` decorator from `app/core/limiter.py`
- Auth uses `Depends(get_current_user)` for required auth, `Depends(get_optional_user)` for optional
- Internal scraper endpoints use the existing `_verify` HMAC check from `app/api/v1/internal.py`

---

### Feature 1: User-Submitted Problems

**File**: `app/api/v1/problems.py` (extend existing router)

```
POST /api/v1/problems
```
- Auth: Required (`get_current_user`)
- Rate limit: `5/hour` per user
- Body: `{ title: str, body: str, category: str | null, tags: list[str] }`
- Logic: Insert problem with `source="user_submitted"`, `submitted_by_user_id=user.id`, `platform="user"`. Fire `generate_solutions_task.delay(problem_id, ["gemini","openai","claude"])` immediately.
- Response: `ProblemResponse` (201)
- Cache: Invalidates `problems:*` namespace keys via `SCAN + DELETE` pattern (matches existing pattern used after scraper runs)

---

### Feature 2: Solution Comments

**File**: `app/api/v1/comments.py` (new router)

```
GET  /api/v1/solutions/{solution_id}/comments
```
- Auth: Optional
- Cache key: `comments:{solution_id}` TTL 60s
- Response: `list[CommentResponse]` (flat list with `parent_id` field for client-side nesting)

```
POST /api/v1/solutions/{solution_id}/comments
```
- Auth: Required
- Rate limit: `20/hour`
- Body: `{ body: str, parent_id: str | null }`
- Validates `parent_id` belongs to same `solution_id` when provided
- Response: `CommentResponse` (201)
- Cache: Invalidates `comments:{solution_id}`

```
DELETE /api/v1/comments/{comment_id}
```
- Auth: Required — comment owner or admin
- Sets `is_active=false` (soft delete)
- Response: `204`

```
POST /api/v1/comments/{comment_id}/flag
```
- Auth: Required
- Sets `is_flagged=true` on comment
- Response: `{ flagged: true }`

---

### Feature 3: Email Digest and Notifications

**File**: `app/api/v1/notifications.py` (new router)

```
GET  /api/v1/notifications/prefs
```
- Auth: Required
- Response: `UserNotificationPrefsResponse`

```
PUT  /api/v1/notifications/prefs
```
- Auth: Required
- Body: `{ digest_enabled: bool, digest_day: int, digest_hour_utc: int, category_interests: list[str], notify_on_comment: bool, notify_on_vote: bool }`
- Upserts `user_notification_prefs` row
- Response: `UserNotificationPrefsResponse`

---

### Feature 4: Saved Filter Presets

**File**: `app/api/v1/filter_presets.py` (new router)

```
GET    /api/v1/filter-presets
```
- Auth: Required
- Cache key: `filter_presets:{user_id}` TTL 120s
- Response: `list[FilterPresetResponse]`

```
POST   /api/v1/filter-presets
```
- Auth: Required
- Body: `{ name: str, filters: ProblemsParams }` — `filters` is validated against the same schema used by `GET /problems`
- Response: `FilterPresetResponse` (201)
- Invalidates `filter_presets:{user_id}`

```
DELETE /api/v1/filter-presets/{preset_id}
```
- Auth: Required — preset owner only
- Response: `204`
- Invalidates `filter_presets:{user_id}`

---

### Feature 5: Search Autocomplete

**File**: `app/api/v1/problems.py` (extend existing router)

```
GET /api/v1/problems/autocomplete?q={query}
```
- Auth: Optional
- Rate limit: `60/minute` (higher tolerance because it fires on each keystroke)
- Query param: `q` (min 2 chars, max 64 chars — validated server-side)
- Cache key: `autocomplete:{md5(q.lower())}` TTL 300s
- DB query: `SELECT id, title FROM problems WHERE is_active=true AND title ILIKE :q LIMIT 8 ORDER BY upvotes DESC`
- Response: `list[{ id: str, title: str }]`

Note: This must be registered before the `/{problem_id}` route in `problems.py` to prevent path conflict with FastAPI's route resolution order.

---

### Feature 6: User Profile Pages

**File**: `app/api/v1/profiles.py` (new router)

```
GET /api/v1/profiles/{username}
```
- Auth: Optional
- Cache key: `profile:{username}` TTL 120s
- Aggregates: problem count (submitted), bookmark count, vote count, recent activity
- Response: `UserProfileResponse` containing `{ id, username, name, bio, avatar_url, created_at, stats: { submitted_count, bookmark_count, vote_count }, recent_submissions: list[ProblemResponse] }`

```
PUT /api/v1/profiles/me
```
- Auth: Required
- Body: `{ bio: str | null, avatar_url: str | null, username: str | null }`
- Validates username is URL-safe (`^[a-zA-Z0-9_-]{3,32}$`) and unique
- Response: `UserProfileResponse`
- Invalidates `profile:{old_username}` and `profile:{new_username}`

---

### Feature 7: Problem Tags

**File**: `app/api/v1/tags.py` (new router)

```
GET /api/v1/tags?q={query}
```
- Auth: Optional
- Cache key: `tags:search:{md5(q)}` TTL 300s
- Returns up to 20 matching tags sorted by `use_count DESC`
- Response: `list[TagResponse]`

```
POST /api/v1/problems/{problem_id}/tags
```
- Auth: Required
- Rate limit: `10/minute`
- Body: `{ tags: list[str] }` (max 5 tags per call, each name max 32 chars)
- Creates missing tags, creates `problem_tags` join rows, increments `use_count`
- Response: `list[TagResponse]`

```
DELETE /api/v1/problems/{problem_id}/tags/{tag_id}
```
- Auth: Required — original tagger or admin only
- Removes `problem_tags` row, decrements `use_count`
- Response: `204`

---

### Feature 8: Solution Export

**File**: `app/api/v1/export.py` (new router)

```
GET /api/v1/problems/{problem_id}/export?format={pdf|markdown}
```
- Auth: Optional (anonymous export is permitted)
- Rate limit: `10/hour` per IP to prevent abuse
- `format=markdown` — server renders Markdown string inline, returns `Content-Type: text/markdown` with `Content-Disposition: attachment`
- `format=pdf` — renders via `weasyprint` or `reportlab` library, returns `Content-Type: application/pdf`
- Cache key: `export:{problem_id}:{format}` TTL 3600s (export content rarely changes)
- Response: File download

---

### Feature 9: Twitter/X Scraper

**File**: `app/api/v1/internal.py` (extend existing router)

```
POST /api/v1/internal/scrape/twitter
```
- Auth: `X-Internal-Api-Key` header (same HMAC check used by existing `/scrape/reddit` and `/scrape/hn`)
- Enqueues `run_twitter_scrape_task.delay()`
- Response: `{ status: "accepted", task_id: str }`

---

### Feature 12: Leaderboard

**File**: `app/api/v1/leaderboard.py` (new router)

```
GET /api/v1/leaderboard?type={problems|solutions|categories}&period={24h|7d|30d}
```
- Auth: Optional
- Cache key: `leaderboard:{type}:{period}` TTL 600s (10 min — matches `trending` TTL)
- `type=problems` — orders by `upvotes + comment_count` within period window
- `type=solutions` — orders by `rating` (sum of positive votes) within period
- `type=categories` — orders by problem volume within period
- Response: `LeaderboardResponse { items: list, type, period, generated_at }`

---

### Feature 13: Problem of the Day

**File**: `app/api/v1/problems.py` (extend existing router)

```
GET /api/v1/problems/potd
```
- Auth: Optional
- Cache key: `potd:{YYYY-MM-DD}` TTL = seconds until midnight UTC (cache expires exactly at next day boundary)
- Queries `problems WHERE potd_date = current_date AND is_active = true LIMIT 1`
- Response: `ProblemResponse` or `404` when none is set yet for today

---

### Feature 14: Real-Time Updates via SSE

**File**: `app/api/v1/stream.py` (new router)

```
GET /api/v1/stream/problems
```
- Auth: Optional
- Protocol: HTTP Server-Sent Events (`text/event-stream`)
- Behaviour: Polls Redis key `sse:new_problem_count` every 5 seconds. When the counter increments (written by the scraper tasks), pushes `event: new_problems\ndata: {"count": N}\n\n` to all connected clients. Resets counter after broadcast.
- No persistent connections to Postgres — counter is maintained exclusively in Redis
- Response headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no` (required for Railway proxy)

Redis key pattern:
```
sse:new_problem_count   → integer, incremented by scraper tasks, reset after each SSE broadcast
```

---

### Feature 15 + 16: Custom Date Range Analytics and CSV Export

**File**: `app/api/v1/analytics.py` (extend existing router)

```
GET /api/v1/analytics/custom?date_from={ISO8601}&date_to={ISO8601}
```
- Auth: Optional
- Validates `date_from` < `date_to`, max range 365 days
- Cache key: `analytics:custom:{date_from}:{date_to}` TTL 3600s
- Returns same shape as existing `/analytics/summary` filtered to the specified window
- Response: `AnalyticsSummary`

```
GET /api/v1/analytics/export?date_from={ISO8601}&date_to={ISO8601}&format=csv
```
- Auth: Required (prevents scraping)
- Rate limit: `5/hour`
- Streams CSV via `StreamingResponse` with `Content-Type: text/csv`
- Columns: `date, platform, category, sentiment, problem_count, solution_count, avg_confidence`
- No Redis cache (streaming response; low request frequency expected)

---

### Feature 17: Admin Panel

**File**: `app/api/v1/admin.py` (new router)

All routes require `current_user.is_admin == True` via a new `require_admin` dependency that wraps `get_current_user`.

```
GET    /api/v1/admin/scrapers/status
```
- Returns Celery task history summary for all three scraper tasks using Celery's inspect API
- Response: `{ reddit: ScraperStatus, hn: ScraperStatus, twitter: ScraperStatus }`

```
POST   /api/v1/admin/scrapers/{source}/trigger
```
- `source` in `('reddit', 'hn', 'twitter')`
- Enqueues the corresponding scraper task immediately
- Response: `{ task_id: str }`

```
GET    /api/v1/admin/categories
POST   /api/v1/admin/categories
PUT    /api/v1/admin/categories/{id}
DELETE /api/v1/admin/categories/{id}
```
- Full CRUD for categories (currently `GET /categories` is read-only)

```
GET    /api/v1/admin/reports?status={pending|reviewed|dismissed}
PUT    /api/v1/admin/reports/{report_id}
```
- List and update flagged content reports
- `PUT` body: `{ status: 'reviewed' | 'dismissed', admin_note: str | null }`

```
GET    /api/v1/admin/users?search={query}&page={n}
PUT    /api/v1/admin/users/{user_id}
```
- User listing and moderation (activate/deactivate, grant/revoke admin)

### Feature 11: Share Buttons (backend-only component)

**File**: `app/api/v1/problems.py` (extend existing router)

```
POST /api/v1/problems/{problem_id}/share
```
- Auth: Optional
- Rate limit: `20/minute` per IP
- Increments `problems.share_count`; used for analytics
- Response: `{ share_count: int }`

OG preview images and share URLs are generated entirely on the frontend (see Section 3). No dedicated backend endpoint for OG meta — this is handled by Next.js `generateMetadata` in SSR.

---

## 3. New Frontend Pages and Components

### Routing Decisions

Pages that must be indexed by search engines use **SSR via `generateMetadata` + server components**. All interactive UI within those pages is isolated in client components. User-specific pages (profile editing, admin panel) are client-rendered. This decision follows the existing `/problems/[id]` page's `"use client"` pattern but adds a server-component wrapper for SEO.

---

### Feature 1: User-Submitted Problems

**New route**: `/problems/submit`
- SSR: No (form page, requires auth)
- Key components:
  - `ProblemSubmitForm` — controlled form with Zod validation; fields: title, body, category select, tag input
  - `TagInput` — combobox that hits `GET /api/v1/tags?q=` for autocomplete suggestions
- State: React Query mutation `useSubmitProblem()` — on success redirects to `/problems/[id]`

---

### Feature 2: Solution Comments

**Modified page**: `/problems/[id]`
- Adds `CommentThread` component below each `SolutionCard`
- Key components:
  - `CommentThread` — renders flat list from API, groups replies client-side using `parent_id`
  - `CommentItem` — single comment with reply affordance, upvote, flag button
  - `CommentComposer` — textarea + submit; optimistic update via React Query `useMutation`
- State: `useQuery(['comments', solutionId])` per solution; separate query cache entries prevent full-page refetch on new comment

---

### Feature 3: Email Digest Settings

**New route**: `/settings/notifications`
- SSR: No
- Key components:
  - `DigestToggle` — enable/disable weekly digest
  - `CategoryInterestSelector` — multi-select of existing categories (loaded from `GET /categories`)
  - `DigestSchedulePicker` — day-of-week and hour selectors
- State: `useQuery('notificationPrefs')` + `useMutation` for save; Zustand is not appropriate here (server-owned state)

---

### Feature 4: Saved Filter Presets

**Modified page**: `/dashboard`
- Key components:
  - `FilterPresetBar` — horizontal scrollable list of saved preset pills above the filter row
  - `SavePresetModal` — name input dialog triggered from the existing filter panel "Save" button
  - `PresetPill` — clickable, applies preset filters via Zustand filter store; has delete button
- State: `useQuery('filterPresets')` for list; applying a preset writes to the existing Zustand `filterStore` (no duplication of state)

---

### Feature 5: Search Autocomplete

**Modified component**: existing `SearchBar` in `/dashboard`
- Wraps existing `<input>` with `useCombobox` from `@headlessui/react` (already a shadcn/ui dependency)
- Fires `GET /api/v1/problems/autocomplete?q=` with 300ms debounce
- Renders dropdown list of up to 8 suggestions; arrow key navigation; Enter selects
- State: local `useState` only — no global state needed; results are ephemeral

---

### Feature 6: User Profile Pages

**New route**: `/profile/[username]`
- SSR: Yes — server component fetches `GET /api/v1/profiles/{username}`, calls `generateMetadata` for OG tags
- Key components:
  - `ProfileHeader` — avatar, name, username, bio, join date, stats badges
  - `ProfileActivityFeed` — tabbed: Submitted Problems / Bookmarks / Comments
  - `EditProfileModal` — bio + avatar URL fields; client component, guarded by `current_user.id === profile.id`
- State: Server component passes data as props; client tabs use React Query with `enabled: false` until tab is activated

---

### Feature 7: Problem Tags

**Modified page**: `/problems/[id]`
- Key components:
  - `TagList` — renders existing tags as pills; appears below problem title
  - `AddTagInput` — inline combobox (reuses `TagInput` from the submit form) visible to authenticated users
- State: `useQuery(['tags', problemId])` + `useMutation` for add/remove

---

### Feature 8: Solution Export

**Modified page**: `/problems/[id]`
- Adds an Export dropdown button to the problem detail header
- Key components:
  - `ExportMenu` — shadcn/ui `DropdownMenu` with "Download PDF" and "Download Markdown" items
  - On click: `window.open('/api/v1/problems/{id}/export?format=pdf', '_blank')` — browser handles the file download; no client-side state needed

---

### Feature 10: SEO and SSR

**Modified page**: `/problems/[id]`
- Refactored to a **hybrid page**: outer Server Component calls `generateMetadata` + fetches initial data via `fetch` with `next: { revalidate: 300 }` (ISR — 5 minute stale window). Inner client components use React Query hydration for interactive parts (voting, comments).
- `generateMetadata` returns:
  ```ts
  {
    title: problem.title,
    description: problem.summary ?? problem.body.slice(0, 160),
    openGraph: {
      title, description, type: 'article',
      url: `https://solvora.io/problems/${problem.id}`,
      images: [{ url: `https://solvora.io/og?title=${encodeURIComponent(title)}` }]
    },
    twitter: { card: 'summary_large_image', ... }
  }
  ```
- OG image: Edge function at `/app/og/route.tsx` using Next.js `ImageResponse` — renders problem title and category as a 1200x630 image. No external image service needed.

---

### Feature 11: Share Buttons

**Modified page**: `/problems/[id]`
- Key components:
  - `ShareButtonGroup` — renders Twitter and LinkedIn share buttons
  - Twitter: `https://twitter.com/intent/tweet?text={title}&url={canonical_url}` as direct link
  - LinkedIn: `https://www.linkedin.com/sharing/share-offsite/?url={canonical_url}` as direct link
  - On click, fires `POST /api/v1/problems/{id}/share` for analytics (fire-and-forget, no await)
- State: No state — pure links + fire-and-forget API call

---

### Feature 12: Leaderboard

**New route**: `/leaderboard`
- SSR: Yes (server component with ISR `revalidate: 600`)
- Key components:
  - `LeaderboardTabs` — Problems / Solutions / Categories tabs; client component
  - `LeaderboardTable` — sortable table with rank, title, metric, change indicator
  - `PeriodSelector` — 24h / 7d / 30d toggle; changes React Query key, triggers re-fetch
- State: React Query `useLeaderboard(type, period)` — separate from Zustand (not global app state)

---

### Feature 13: Problem of the Day

**Modified page**: `/` (homepage, `app/page.tsx`)
- Adds `PotdBanner` component above the main feed
- Server component fetches `GET /api/v1/problems/potd` at build/ISR time (`revalidate: 3600`)
- Key components:
  - `PotdBanner` — prominent card with "Problem of the Day" badge, title, category, link to `/problems/[id]`
  - Falls back gracefully (renders nothing) when no POTD is set

---

### Feature 14: Real-Time Updates via SSE

**Modified page**: `/dashboard`
- Key components:
  - `NewProblemsNotice` — floating banner at top of feed: "5 new problems — click to refresh"
  - Uses `EventSource` API in a `useEffect` within a `"use client"` component
  - On `new_problems` event: increments a local counter displayed in the banner; does NOT auto-reload
  - On banner click: calls `queryClient.invalidateQueries(['problems'])` to trigger React Query refetch
- State: `useState` for `newCount`; `useRef` for `EventSource` instance (cleanup on unmount)

---

### Feature 15 + 16: Custom Date Range Analytics and CSV Export

**Modified page**: `/analytics`
- Key components:
  - `DateRangePicker` — shadcn/ui `Calendar` in a popover; sets `date_from` / `date_to` in local state
  - `ExportCsvButton` — triggers `GET /api/v1/analytics/export?...` as a file download; guarded by auth
  - Existing `AnalyticsCharts` already uses React Query; add a new query key `['analytics', 'custom', dateFrom, dateTo]`
- State: `useState` for date range; React Query for data fetching (not Zustand — this is page-scoped state)

---

### Feature 17: Admin Panel

**New route**: `/admin`
- SSR: No — client-rendered, guarded by `current_user.is_admin` check
- Sub-routes handled by Next.js parallel routes or simple tab state:
  - `/admin` — overview dashboard
  - `/admin/scrapers` — scraper status table + trigger buttons
  - `/admin/categories` — category CRUD table
  - `/admin/reports` — flagged content queue
  - `/admin/users` — user list with moderation actions
- Key components:
  - `AdminLayout` — sidebar nav, restricted to admins via middleware redirect
  - `ScraperStatusCard` — shows last run time, items scraped, status badge; "Trigger" button
  - `CategoryEditor` — inline editable table
  - `ReportQueue` — paginated table with approve/dismiss actions
  - `UserTable` — searchable, paginated; toggle active/admin status
- State: React Query for all data (no Zustand — all state is server-owned and paginated)
- Middleware: Add to `middleware.ts`: if `pathname.startsWith('/admin')` and user is not admin, redirect to `/dashboard`

---

## 4. Infrastructure Changes

### 4.1 New Services

#### Email Service (Resend — recommended)

Resend is preferred over SendGrid because its API is simpler (single `POST /emails`), its Node.js and Python SDKs are first-party, and it has a generous free tier (3,000 emails/month). SendGrid is a valid alternative with identical integration points.

- **Environment variable**: `RESEND_API_KEY`
- Python client: `resend` package added to `requirements.txt`
- Used by: `send_digest_email_task` Celery task

#### Twitter/X API v2

- **Environment variables**: `TWITTER_BEARER_TOKEN`
- No OAuth required — Bearer token is sufficient for search and recent tweets endpoints
- Python client: `tweepy` package (already a standard Python Twitter library)
- Scraper file: `app/scrapers/twitter_scraper.py` (follows `BaseScraper` ABC — implements `scrape()` method calling `tweepy.Client.search_recent_tweets`)

---

### 4.2 New Celery Tasks

All new tasks follow the existing pattern in `app/nlp/tasks.py` and `app/ai/tasks.py`: `@celery_app.task(bind=True, max_retries=N, soft_time_limit=N)`.

| Task name | File | Schedule | Purpose |
|---|---|---|---|
| `scrapers.run_twitter_scrape` | `app/nlp/tasks.py` | Every 30 min (same as Reddit) | Scrape Twitter/X for problem posts |
| `notifications.send_weekly_digests` | `app/notifications/tasks.py` | Every hour (beat checks against `digest_day` + `digest_hour_utc` per user) | Send personalised email digests |
| `content.select_potd` | `app/content/tasks.py` | Daily at 00:05 UTC | Selects highest-upvote problem not featured in last 30 days, sets `potd_date = today` |
| `content.auto_tag_problems` | `app/content/tasks.py` | Every 30 min | Calls NLP classifier on problems where `tags_auto IS NULL`, writes JSON tag array back to `problems.tags_auto` and inserts `problem_tags` rows |

Add to `celery_app.py` beat schedule:

```python
"scrape-twitter-every-30min": {
    "task": "scrapers.run_twitter_scrape",
    "schedule": crontab(minute="*/30"),
},
"send-digests-hourly": {
    "task": "notifications.send_weekly_digests",
    "schedule": crontab(minute=5),
},
"select-potd-daily": {
    "task": "content.select_potd",
    "schedule": crontab(hour=0, minute=5),
},
"auto-tag-problems-every-30min": {
    "task": "content.auto_tag_problems",
    "schedule": crontab(minute="*/30"),
},
```

---

### 4.3 New Redis Key Patterns

Follows existing naming conventions: `{namespace}:{identifier}` with explicit TTL on every key.

| Key Pattern | Type | TTL | Written by | Read by |
|---|---|---|---|---|
| `comments:{solution_id}` | JSON string | 60s | Comment POST handler | Comment GET handler |
| `autocomplete:{md5(q)}` | JSON string | 300s | Autocomplete GET handler | Autocomplete GET handler |
| `profile:{username}` | JSON string | 120s | Profile GET handler | Profile GET handler |
| `filter_presets:{user_id}` | JSON string | 120s | Preset handlers | Preset GET handler |
| `leaderboard:{type}:{period}` | JSON string | 600s | Leaderboard GET handler | Leaderboard GET handler |
| `potd:{YYYY-MM-DD}` | JSON string | until midnight | POTD Celery task | POTD GET handler |
| `export:{problem_id}:{format}` | Binary/string | 3600s | Export GET handler | Export GET handler |
| `sse:new_problem_count` | Integer | no TTL | Scraper tasks (INCR) | SSE stream handler |
| `tags:search:{md5(q)}` | JSON string | 300s | Tag GET handler | Tag GET handler |
| `analytics:custom:{from}:{to}` | JSON string | 3600s | Analytics custom GET | Analytics custom GET |

---

### 4.4 Environment Variables to Add

Add to both `.env` (local) and Railway environment configuration:

```bash
# Email
RESEND_API_KEY=re_...

# Twitter/X
TWITTER_BEARER_TOKEN=AAAA...

# PDF Export (optional - only if using WeasyPrint)
# No additional env vars needed; WeasyPrint is a pip package

# OG Image (no external service - handled by Next.js Edge Runtime)
# No additional env vars needed

# Feature flags (optional, for gradual rollout)
FEATURE_SSE_ENABLED=true
FEATURE_TWITTER_SCRAPER_ENABLED=true
```

Add to Vercel environment configuration:

```bash
# Already present: NEXT_PUBLIC_API_URL
# New:
NEXT_PUBLIC_SSE_ENABLED=true
```

---

### 4.5 New Python Package Dependencies

Add to `requirements.txt`:

```
tweepy>=4.14.0          # Twitter/X API v2 client
resend>=0.8.0           # Email delivery
weasyprint>=61.0        # PDF export (alternatively: reportlab>=4.0)
```

---

### 4.6 New npm Package Dependencies

Add to `package.json`:

```json
"@headlessui/react": "^2.0.0"
```

Note: Most v2.0 frontend features can be built with existing shadcn/ui components (Dialog, DropdownMenu, Combobox, Calendar). `@headlessui/react` may already be a transitive dependency of shadcn/ui — confirm before adding explicitly.

---

## 5. Phased Implementation Roadmap

### Prioritisation Criteria

- **Impact**: Size of user-facing improvement
- **Effort**: Engineering days (backend + frontend combined)
- **Dependencies**: Features with no external dependencies ship first
- **Risk**: Features requiring new external services are deferred until Phase 2

---

### Phase 1 — Highest Impact, Lowest Effort (Weeks 1–3)

These features use only existing infrastructure (no new services, no new Celery tasks beyond trivial additions) and deliver the highest immediate user value.

| # | Feature | Backend Effort | Frontend Effort | Notes |
|---|---|---|---|---|
| 5 | Search Autocomplete | Small (1 endpoint, Redis cache) | Small (debounced input, dropdown) | No new tables |
| 4 | Saved Filter Presets | Small (1 table, 3 endpoints) | Small (reuses Zustand filter store) | `filter_presets` table only |
| 13 | Problem of the Day | Small (1 column, 1 endpoint, 1 Celery task) | Small (banner component) | `potd_date` column on existing table |
| 10 | SEO / SSR | None (data already exists) | Medium (refactor `/problems/[id]` to hybrid SSR) | ISR with 5-min revalidation |
| 11 | Share Buttons | Tiny (1 endpoint for analytics) | Small (link components + OG edge function) | OG image with Next.js `ImageResponse` |
| 14 | Real-Time SSE | Small (1 endpoint, 1 Redis key, scraper INCR) | Small (EventSource in useEffect) | No new tables |
| 7 | Problem Tags | Medium (2 tables, 3 endpoints, 1 Celery task) | Small (tag pills + combobox input) | `tags`, `problem_tags` tables |

**Phase 1 Milestone**: Users can find content faster (autocomplete, tags), the site is indexable (SSR), and the feed feels live (SSE banner + POTD).

---

### Phase 2 — Medium Complexity (Weeks 4–9)

These features add new tables, new external services, or require non-trivial data aggregations.

| # | Feature | Backend Effort | Frontend Effort | Notes |
|---|---|---|---|---|
| 1 | User-Submitted Problems | Medium (column + endpoint + immediate Celery job) | Medium (submit form page) | Extends existing `problems` table and `generate_solutions_task` |
| 2 | Solution Comments | Medium (`comments` table, 4 endpoints) | Medium (thread component, optimistic updates) | Most complex frontend state in Phase 2 |
| 6 | User Profile Pages | Medium (2 columns on users, 2 endpoints) | Medium (new page, tabbed activity feed) | Requires `username` column migration |
| 12 | Leaderboard | Small (1 endpoint, complex SQL) | Medium (tabbed table with ISR) | No new tables; leverages existing `votes`, `upvotes` |
| 15 | Custom Date Range Analytics | Small (1 endpoint, extends existing service) | Small (date picker, new query key) | Extends existing analytics pattern |
| 16 | Analytics CSV Export | Small (streaming response, auth-gated) | Small (button, file download) | Extends Phase 2 analytics work |
| 9 | Twitter/X Scraper | Medium (new scraper + Celery task + `tweepy`) | None | New external API dependency |
| 8 | Solution Export | Medium (`weasyprint` dependency, PDF rendering) | Small (dropdown menu) | New pip dependency; test render quality early |

**Phase 2 Milestone**: The platform is a full community product — users submit problems, comment, build profiles, and the analytics suite is complete.

---

### Phase 3 — Advanced Features (Weeks 10+, Ongoing)

These features require operational care, external services, or are lower on user impact relative to engineering investment.

| # | Feature | Backend Effort | Frontend Effort | Notes |
|---|---|---|---|---|
| 3 | Email Digest / Notifications | High (Resend integration, Celery beat, `user_notification_prefs`, digest rendering) | Medium (settings page) | External service dependency; email deliverability requires SPF/DKIM DNS setup |
| 17 | Admin Panel | High (6+ endpoints, auth guard, Celery inspect integration) | High (full CRUD UI, 5 sub-pages) | Lowest user-facing impact; highest internal operational value |

**Phase 3 Milestone**: The platform has operational tooling for content moderation and automated user engagement via digest emails.

---

## 6. Architecture Decision Records

### ADR-001: Comments Limited to Two Levels of Nesting

**Context**: Comments can have replies. Unlimited nesting (Reddit-style) requires either recursive DB queries or a nested set / closure table — both add significant complexity.

**Decision**: Comments support one level of replies only. `parent_id` references a top-level comment. Any comment with a `parent_id` cannot itself be a parent (`parent_id IS NULL` check enforced in the POST handler).

**Consequences**: Simpler flat DB query. Client groups by `parent_id`. If three-level nesting becomes a product requirement in v3, the schema supports it by removing the application-layer constraint.

---

### ADR-002: SSE Over WebSockets for Real-Time Feed Updates

**Context**: Feature 14 requires notifying connected clients when new problems arrive.

**Decision**: Use HTTP Server-Sent Events (SSE) rather than WebSockets.

**Rationale**:
- SSE is unidirectional (server → client), which matches the use case exactly
- FastAPI supports SSE natively via `StreamingResponse` with `text/event-stream`
- No additional infrastructure (no Redis Pub/Sub channel, no WebSocket upgrade) is needed — the SSE handler polls a single Redis key
- WebSockets require sticky sessions or a message broker; Railway's routing does not guarantee sticky sessions without configuration

**Consequences**: Clients cannot push data to the server over the SSE connection, which is acceptable because the use case is read-only notification.

---

### ADR-003: OG Images via Next.js Edge Runtime, Not External Service

**Context**: Feature 11 (Share Buttons) requires per-problem OG preview images.

**Decision**: Implement OG images as a Next.js Edge Function at `/app/og/route.tsx` using the `next/og` `ImageResponse` API.

**Rationale**:
- Zero infrastructure cost — runs on Vercel Edge at no marginal cost
- Images are generated on-demand and cached by Vercel's CDN
- No dependency on Cloudinary, Imgix, or similar paid services

**Consequences**: OG image rendering is limited to fonts and CSS supported by the Satori renderer (used by `next/og` internally). Complex SVG or image composition is not supported.

---

### ADR-004: PDF Export via WeasyPrint, Not Headless Chrome

**Context**: Feature 8 requires PDF generation server-side.

**Decision**: Use `weasyprint` (Python) rather than Puppeteer/Playwright (headless Chromium).

**Rationale**:
- WeasyPrint runs in-process with the FastAPI worker — no separate subprocess or sidecar container
- Puppeteer requires a Chromium binary (~300MB), which increases Railway Docker image size and cold-start time significantly
- Problem+solutions content is structured text; WeasyPrint handles it well without complex CSS

**Consequences**: WeasyPrint does not render JavaScript. All export content must be server-side rendered Markdown/HTML. If rich interactive export is needed in the future, a headless browser can replace it without changing the API contract.

---

### ADR-005: Admin Panel Uses Existing JWT Auth, Not Separate Session

**Context**: Feature 17 (Admin Panel) needs to restrict access to admin users.

**Decision**: Reuse the existing JWT `get_current_user` dependency. Add `require_admin` as a thin wrapper that raises `403` if `current_user.is_admin is False`.

**Rationale**:
- No separate admin credential store; no second login flow; consistent with existing auth patterns
- `is_admin` flag on `users` table is the simplest representation
- Admin routes are protected by both JWT validity and the `is_admin` flag check

**Consequences**: Admin access is revoked by setting `is_admin=False` on the user record — no token invalidation is needed because the flag is checked on every request.

---

### ADR-006: Filter Presets Stored in Postgres, Not Browser LocalStorage

**Context**: Feature 4 (Saved Filter Presets) could be implemented purely client-side using `localStorage` or the existing Zustand persist store (which uses `sessionStorage`).

**Decision**: Store presets in Postgres (`filter_presets` table) with a backend CRUD API.

**Rationale**:
- Presets are durable across devices and browsers
- The existing `FilterPreset` TypeScript type in `src/frontend/src/types/index.ts` already implies a server-owned entity with `id` and `createdAt` fields — this was designed with server storage in mind
- Client-only storage would prevent the feature from working on mobile or after clearing browser data

**Consequences**: Requires authentication. Anonymous users cannot save presets.

---

*End of Solvora v2.0 Architecture Document*
