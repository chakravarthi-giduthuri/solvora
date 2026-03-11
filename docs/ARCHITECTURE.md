# Solvora — System Architecture Document

**Version:** 1.0
**Date:** March 2026
**Status:** Draft
**Classification:** Confidential

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [C4 Context Diagram](#3-c4-context-diagram)
4. [C4 Container Diagram](#4-c4-container-diagram)
5. [Core Components and Modules](#5-core-components-and-modules)
6. [Technology Stack](#6-technology-stack)
7. [Database Design](#7-database-design)
8. [API Design](#8-api-design)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Backend Architecture](#10-backend-architecture)
11. [AI/ML Pipeline](#11-aiml-pipeline)
12. [Security Architecture](#12-security-architecture)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Data Flow Diagrams](#14-data-flow-diagrams)
15. [Integration Points](#15-integration-points)
16. [Scalability Considerations](#16-scalability-considerations)
17. [Non-Functional Requirements Mapping](#17-non-functional-requirements-mapping)
18. [Architecture Decision Records](#18-architecture-decision-records)
19. [Risk Register](#19-risk-register)

---

## 1. System Overview

Solvora is a web-based intelligence dashboard that continuously ingests problem-oriented discussions from social platforms (Reddit and Hacker News in v1.0), applies NLP classification and sentiment analysis, and surfaces AI-generated solutions via Google Gemini, OpenAI GPT, and Anthropic Claude through a single unified interface.

### Core Value Chain

```
Social Platforms  -->  Scrapers  -->  NLP Pipeline  -->  AI Solution Engine  -->  Dashboard
(Reddit / HN)          (Python)       (Classify /         (Gemini / GPT /          (Next.js)
                                       Sentiment)          Claude)
```

### Bounded Contexts (Domain-Driven Design)

| Bounded Context | Responsibility |
|---|---|
| **Ingestion** | Scraping, deduplication, raw storage |
| **Classification** | NLP labeling, sentiment, category assignment |
| **Solution Generation** | AI provider orchestration, response caching |
| **Presentation** | REST API, dashboard rendering, filters |
| **Identity** | Authentication, bookmarks, votes, preferences |
| **Analytics** | Aggregation, trending computation, charting data |

---

## 2. Architecture Principles

1. **Separation of concerns** — Scraping, classification, solution generation, and presentation are independent modules with defined contracts between them.
2. **Cache first** — AI responses are expensive; every generated solution is persisted and re-served until it expires (24-hour TTL by default).
3. **Lazy generation** — AI solutions are not generated automatically for every scraped post. Generation is triggered either by a user request or a background priority queue for high-signal posts.
4. **Cost-aware design** — Free-tier services are chosen as the default runtime. Paid tiers are engaged only when specific usage thresholds are exceeded (documented in the scaling path).
5. **Eventual consistency is acceptable** — The problem feed updates every 15–30 minutes. Strict real-time consistency is out of scope for v1.0.
6. **API rate-limit respect** — All scrapers implement exponential back-off, respect official rate limits, and record quota consumption in a dedicated metrics table.
7. **12-Factor app compliance** — Configuration via environment variables; stateless application processes; backing services treated as attached resources.

---

## 3. C4 Context Diagram

```
+------------------------------------------------------------------+
|                        Solvora System                       |
|                                                                  |
|   +------------------+    +----------------------------+         |
|   |   Ingestion      |    |   AI Solution Engine       |         |
|   |   Workers        |    |   (Orchestrator)           |         |
|   +------------------+    +----------------------------+         |
|                                                                  |
|   +------------------+    +----------------------------+         |
|   |   REST API       |    |   Next.js Dashboard        |         |
|   |   (FastAPI)      |    |   (Frontend)               |         |
|   +------------------+    +----------------------------+         |
+------------------------------------------------------------------+
         |          |               |              |
         v          v               v              v
   [Reddit API] [HN API]    [Gemini / GPT /   [Browser /
    (External)  (External)   Claude APIs]      End User]
                              (External)
```

### External Actors

| Actor | Type | Interaction |
|---|---|---|
| End User | Human | Views dashboard, votes, bookmarks, exports |
| Reddit API | External System | Source of problem posts and comments |
| Hacker News API | External System | Source of technology-oriented problem threads |
| X (Twitter) API v2 | External System | Future source (v2.0); stubbed in v1.0 |
| OpenAI API | External System | GPT-4o / GPT-4o-mini solution generation |
| Google Gemini API | External System | Gemini 1.5 Flash/Pro solution generation |
| Anthropic Claude API | External System | Claude 3.5 Sonnet solution generation |
| Supabase Auth | External System | OAuth2 user identity (Google, email) |

---

## 4. C4 Container Diagram

```
+-------------------------------+     +-------------------------------+
|  Next.js Frontend (Vercel)    |     |  FastAPI Backend (Koyeb)      |
|  - App Router pages           |     |  - /api/problems              |
|  - React components           | --> |  - /api/solutions             |
|  - Zustand state store        |     |  - /api/analytics             |
|  - React Query (data fetch)   |     |  - /api/auth                  |
|  - Recharts charts            |     |  - /api/votes                 |
|  - Tailwind CSS + shadcn/ui   |     |  - /api/bookmarks             |
+-------------------------------+     +---------------+---------------+
                                                      |
                      +--------------------------+    |
                      |  Job Queue               |    |
                      |  Celery Workers (Python) | <--+
                      |  - Scraper tasks         |
                      |  - NLP tasks             |
                      |  - AI solution tasks     |
                      +-----------+--------------+
                                  |
          +-----------------------+---------------------+
          |                       |                     |
+---------+----------+  +---------+---------+  +--------+---------+
|  Neon PostgreSQL   |  |  Upstash Redis    |  |  GitHub Actions  |
|  (Primary DB)      |  |  (Cache + Queue)  |  |  (Cron trigger)  |
|  - problems        |  |  - API response   |  |  - Every 15 min  |
|  - solutions       |  |    cache          |  |  - Every 30 min  |
|  - users           |  |  - Job queue      |  |  - Daily refresh |
|  - votes           |  |  - Rate-limit     |  +------------------+
|  - bookmarks       |  |    counters       |
|  - categories      |  +-------------------+
|  - scrape_log      |
+--------------------+
```

---

## 5. Core Components and Modules

### 5.1 Ingestion Module

**Purpose:** Collect raw posts from external platforms on a schedule.

**Sub-components:**

| Component | Description | Schedule |
|---|---|---|
| `reddit_scraper.py` | Connects via PRAW + OAuth2. Targets r/Advice, r/AskReddit, r/TrueOffMyChest, r/Problems, r/Help, and keyword-filtered feeds. Extracts: title, body, author, upvotes, comment count, subreddit, timestamp, URL. Also scrapes top 5 comments per post. | Every 30 min (new); daily full refresh |
| `hn_scraper.py` | Queries Hacker News Algolia API for "Ask HN" and "Show HN" posts matching problem keywords. No authentication required. | Every 15 min |
| `x_scraper.py` | Stubbed for v1.0. Will integrate X API v2 Bearer Token when budget allows. Searches problem-indicating keywords: "how do I fix", "anyone else struggling with", "frustrated by", etc. Filters retweets and ads. | Disabled v1.0 |
| `deduplication.py` | SHA-256 hash of (platform + source_id) used as idempotency key. Prevents re-inserting already-seen posts. | Runs inline with each scraper |

### 5.2 NLP Classification Module

**Purpose:** Determine whether a scraped post is a genuine problem, assign category, and detect sentiment.

**Sub-components:**

| Component | Technique | Output |
|---|---|---|
| `problem_classifier.py` | Zero-shot classification via Gemini 1.5 Flash (free tier). Prompt: "Is the following post describing a real problem or pain point? Answer YES or NO with a confidence score." | `is_problem: bool`, `confidence: float` |
| `category_tagger.py` | LLM prompt with category taxonomy injected. Categories: Technology, Health, Finance, Relationships, Productivity, Travel, Education, Other. | `category: str` |
| `sentiment_detector.py` | LLM prompt returning one of: Urgent, Frustrated, Curious, Neutral. | `sentiment: str` |
| `summarizer.py` | Generates a 2–3 sentence summary of each post for feed card display. | `summary: str` |

Confidence threshold: posts below 0.65 confidence are routed to a manual review queue (flagged in DB, not shown on dashboard until reviewed).

### 5.3 AI Solution Engine

**Purpose:** Orchestrate solution generation across three AI providers and store results.

**Sub-components:**

| Component | Description |
|---|---|
| `solution_orchestrator.py` | Receives `problem_id`. Checks Redis cache first. On cache miss, dispatches Celery sub-tasks to each enabled provider. Aggregates responses. |
| `openai_adapter.py` | Wraps `openai` SDK. Uses GPT-4o-mini by default; GPT-4o for premium requests. Includes system prompt with problem text, category, sentiment, platform context. |
| `gemini_adapter.py` | Wraps `google-generativeai` SDK. Targets Gemini 1.5 Flash (free tier). Falls back to Gemini 1.5 Pro for complex multi-step problems. |
| `claude_adapter.py` | Wraps `anthropic` SDK. Targets Claude 3.5 Sonnet. Used for nuanced, safety-aware, or relationship-category problems. |
| `cache_manager.py` | Before calling any AI provider: checks Redis for existing solution keyed by `(problem_id, provider)`. TTL: 24 hours. Stores response immediately after generation. |
| `prompt_builder.py` | Constructs the system + user prompt from problem fields. Injects: category, sentiment, platform, summary, and original text. Enforces max token limits per provider. |

### 5.4 REST API Module

**Purpose:** Expose all data to the frontend via a typed, versioned HTTP interface.

Built with FastAPI. All routes are prefixed `/api/v1/`. Auto-generated OpenAPI/Swagger docs at `/docs`.

### 5.5 Frontend Module

**Purpose:** Render the interactive dashboard with real-time-like data via polling.

Built with Next.js 14 (App Router), Tailwind CSS, shadcn/ui, Recharts, Zustand, and React Query.

### 5.6 Identity and Access Module

**Purpose:** Optional user authentication, bookmarks, votes, and preference storage.

Backed by Supabase Auth (email + Google OAuth). JWT tokens validated by FastAPI middleware.

### 5.7 Analytics Module

**Purpose:** Pre-aggregate trending topics, category breakdowns, and volume metrics for dashboard charts.

A background Celery beat task runs hourly to compute and cache aggregated analytics in Redis, avoiding expensive on-demand GROUP BY queries at scale.

---

## 6. Technology Stack

### 6.1 Decision Matrix

| Layer | Choice | Rationale | Alternative Considered |
|---|---|---|---|
| Frontend framework | Next.js 14 (App Router) | SSR for SEO, RSC for performance, native Vercel support | Create React App (no SSR), Remix |
| UI library | Tailwind CSS + shadcn/ui | Utility-first, accessible, composable primitives | MUI, Chakra UI |
| Charts | Recharts | React-native, lightweight, composable | Chart.js (imperative), D3 (complexity) |
| State management | Zustand + React Query | Zustand for UI state; React Query for server state caching and background refetch | Redux Toolkit (boilerplate), SWR |
| Backend runtime | Python / FastAPI | Same language as scrapers/NLP; async by default; auto OpenAPI docs | Node.js + Express (different ecosystem from Python ML libs) |
| Task queue | Celery + Redis (Upstash) | Mature, battle-tested; supports cron via celery-beat; Redis doubles as cache | RQ (simpler but less featured), BullMQ (Node-only) |
| Primary database | Neon PostgreSQL | Serverless, 5GB free, never sleeps, standard Postgres dialect | Supabase Postgres (pauses after 1 week inactive), PlanetScale (MySQL) |
| Cache / queue broker | Upstash Redis | Serverless, 10K commands/day free, REST API, no connection limits | Redis Cloud (30MB limit too small) |
| AI — free primary | Google Gemini 1.5 Flash | 1M tokens/day free; covers all MVP workloads at zero cost | None at this cost point |
| AI — paid secondary | Anthropic Claude 3.5 Sonnet | Nuanced reasoning; superior safety-awareness for sensitive categories | OpenAI GPT-4o (3x more expensive per output token) |
| AI — budget paid | OpenAI GPT-4o-mini | Low-cost general reasoning; use $5 signup credit to start | Gemini 1.5 Pro (cost-equivalent, less ecosystem maturity) |
| Scraping — Reddit | PRAW + OAuth2 | Official library; 100 req/min free; stable | Raw HTTP requests (fragile) |
| Scraping — HN | HN Algolia API | 100% free, no auth, JSON REST | Direct Firebase endpoint (less query flexibility) |
| Scheduling | GitHub Actions (cron) | Free 2,000 min/month; native to Git workflow; triggers HTTP endpoint on Koyeb | Celery beat (adds always-on process cost), cron-job.org |
| Frontend hosting | Vercel | Zero-config Next.js hosting; free CDN; auto HTTPS; preview deploys | Netlify (comparable), AWS Amplify (more setup) |
| Backend hosting | Koyeb | Always-on free tier (no sleep); 512MB RAM sufficient for FastAPI MVP | Render (sleeps on free tier — bad for dashboard UX) |
| Auth | Supabase Auth | Free; email + Google OAuth; JWT; integrates with Neon Postgres | Clerk (free tier; slightly more opinionated) |
| Error monitoring | Sentry | 5K errors/month free; stack traces; performance monitoring | LogRocket (more expensive), Datadog (overkill) |

### 6.2 Full Stack Reference

```
Frontend (Vercel)
  Next.js 14 (App Router + React Server Components)
  TypeScript
  Tailwind CSS 3
  shadcn/ui (Radix UI primitives)
  Recharts 2
  Zustand 4 (UI state)
  TanStack React Query 5 (server state + caching)
  next-auth or Supabase Auth JS SDK

Backend (Koyeb)
  Python 3.11
  FastAPI 0.110
  Pydantic v2 (request/response validation)
  SQLAlchemy 2.0 (async ORM)
  asyncpg (async PostgreSQL driver)
  Celery 5 + celery-beat (task scheduling)
  redis-py (Upstash connection)
  PRAW 7 (Reddit scraper)
  httpx (async HTTP — HN scraper, X stub)
  openai SDK 1.x
  google-generativeai SDK
  anthropic SDK
  python-jose (JWT validation)
  tenacity (retry with exponential back-off)
  structlog (structured logging)

Infrastructure
  Neon PostgreSQL (primary DB)
  Upstash Redis (cache + Celery broker)
  GitHub Actions (cron scheduling)
  Sentry (error tracking)
  Cloudflare (DNS, DDoS, SSL — free plan)
```

---

## 7. Database Design

### 7.1 Schema

#### `categories`
```sql
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(64) NOT NULL UNIQUE,
    slug        VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Seeded values: Technology, Health, Finance, Relationships, Productivity, Travel, Education, Other.

#### `problems`
```sql
CREATE TABLE problems (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        VARCHAR(16) NOT NULL CHECK (platform IN ('reddit','hackernews','twitter')),
    source_id       VARCHAR(256) NOT NULL,           -- platform-native post ID
    source_hash     VARCHAR(64) NOT NULL UNIQUE,     -- SHA-256(platform+source_id)
    title           TEXT NOT NULL,
    body            TEXT,
    url             TEXT NOT NULL,
    author_handle   VARCHAR(128),
    upvotes         INTEGER DEFAULT 0,
    comment_count   INTEGER DEFAULT 0,
    subreddit       VARCHAR(128),                    -- Reddit only
    hashtags        TEXT[],                          -- Twitter only
    category_id     INTEGER REFERENCES categories(id),
    sentiment       VARCHAR(16) CHECK (sentiment IN ('Urgent','Frustrated','Curious','Neutral')),
    summary         TEXT,
    is_problem      BOOLEAN NOT NULL DEFAULT false,
    confidence      NUMERIC(4,3),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    review_required BOOLEAN NOT NULL DEFAULT false,  -- low confidence flag
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_created_at TIMESTAMPTZ
);

CREATE INDEX idx_problems_platform      ON problems(platform);
CREATE INDEX idx_problems_category      ON problems(category_id);
CREATE INDEX idx_problems_sentiment     ON problems(sentiment);
CREATE INDEX idx_problems_scraped_at    ON problems(scraped_at DESC);
CREATE INDEX idx_problems_is_active     ON problems(is_active) WHERE is_active = true;
CREATE INDEX idx_problems_fts           ON problems USING gin(to_tsvector('english', title || ' ' || coalesce(body,'')));
```

#### `solutions`
```sql
CREATE TABLE solutions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id      UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    provider        VARCHAR(16) NOT NULL CHECK (provider IN ('openai','gemini','claude')),
    model_name      VARCHAR(64) NOT NULL,
    solution_text   TEXT NOT NULL,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    rating          NUMERIC(3,2),                   -- computed from votes
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,            -- generated_at + 24h
    UNIQUE(problem_id, provider)
);

CREATE INDEX idx_solutions_problem_id   ON solutions(problem_id);
CREATE INDEX idx_solutions_provider     ON solutions(provider);
```

#### `users`
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(256) UNIQUE NOT NULL,
    name            VARCHAR(128),
    auth_provider   VARCHAR(32) NOT NULL CHECK (auth_provider IN ('email','google')),
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);
```

#### `bookmarks`
```sql
CREATE TABLE bookmarks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id  UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, problem_id)
);

CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);
```

#### `votes`
```sql
CREATE TABLE votes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    solution_id UUID NOT NULL REFERENCES solutions(id) ON DELETE CASCADE,
    vote_type   SMALLINT NOT NULL CHECK (vote_type IN (1, -1)),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, solution_id)
);

CREATE INDEX idx_votes_solution_id ON votes(solution_id);
```

#### `scrape_log`
```sql
CREATE TABLE scrape_log (
    id              SERIAL PRIMARY KEY,
    platform        VARCHAR(16) NOT NULL,
    run_type        VARCHAR(16) NOT NULL CHECK (run_type IN ('incremental','full')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    posts_fetched   INTEGER DEFAULT 0,
    posts_inserted  INTEGER DEFAULT 0,
    posts_skipped   INTEGER DEFAULT 0,
    error_message   TEXT,
    status          VARCHAR(16) NOT NULL DEFAULT 'running' CHECK (status IN ('running','success','failed'))
);
```

#### `filter_presets` (for logged-in users)
```sql
CREATE TABLE filter_presets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(64) NOT NULL,
    filters     JSONB NOT NULL,                     -- {platform, category, sentiment, date_range}
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 7.2 Redis Key Schema

| Key Pattern | TTL | Purpose |
|---|---|---|
| `solution:{problem_id}:{provider}` | 24h | Cached AI solution text |
| `analytics:summary` | 1h | Dashboard analytics aggregation |
| `analytics:trending:{window}` | 30m | Trending topics for 24h/7d/30d windows |
| `rate:{platform}:requests` | 60s | Rolling request counter per platform |
| `problem:feed:{filter_hash}` | 5m | Paginated feed response cache |

---

## 8. API Design

All endpoints follow REST conventions. Base path: `/api/v1`. Responses use `application/json`. Errors conform to RFC 7807 Problem Details.

### 8.1 Standard Response Envelope

```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 1543,
    "took_ms": 34
  }
}
```

### 8.2 Endpoint Reference

#### Problems

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/problems` | Optional | List problems. Query params: `platform`, `category`, `sentiment`, `from_date`, `to_date`, `has_solution`, `page`, `per_page`, `q` (full-text search) |
| GET | `/api/v1/problems/:id` | Optional | Single problem with all solutions |
| GET | `/api/v1/problems/trending` | None | Trending topics. Query param: `window` = `24h` \| `7d` \| `30d` |

#### Solutions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/solutions/:problem_id` | Optional | All AI solutions for a problem |
| POST | `/api/v1/solutions/generate` | Optional | Trigger on-demand solution generation. Body: `{ problem_id, providers[] }` |

#### Votes

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/votes` | Required | Submit or update vote. Body: `{ solution_id, vote_type: 1 \| -1 }` |
| DELETE | `/api/v1/votes/:solution_id` | Required | Retract vote |

#### Analytics

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/analytics/summary` | None | Dashboard KPIs: problems by category, volume by platform, sentiment distribution |
| GET | `/api/v1/analytics/volume` | None | Time-series: problem volume by day. Params: `from_date`, `to_date`, `platform` |
| GET | `/api/v1/analytics/heatmap` | None | Activity by day-of-week and hour |

#### Categories

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/categories` | None | List all categories with post counts |

#### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | None | Email/password login. Returns JWT. |
| POST | `/api/v1/auth/signup` | None | Email signup |
| POST | `/api/v1/auth/oauth/google` | None | Google OAuth callback |
| POST | `/api/v1/auth/logout` | Required | Invalidate session |

#### Bookmarks

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/bookmarks` | Required | List user's bookmarked problems |
| POST | `/api/v1/bookmarks` | Required | Bookmark a problem. Body: `{ problem_id }` |
| DELETE | `/api/v1/bookmarks/:problem_id` | Required | Remove bookmark |

#### Filter Presets

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/presets` | Required | List saved filter presets |
| POST | `/api/v1/presets` | Required | Save a preset. Body: `{ name, filters }` |
| DELETE | `/api/v1/presets/:id` | Required | Delete a preset |

### 8.3 Pagination

All list endpoints accept `page` (default: 1) and `per_page` (default: 20, max: 100). Responses include `meta.total` for frontend pagination controls.

### 8.4 Rate Limiting

API-level rate limits enforced by FastAPI middleware using Upstash Redis sliding-window counters:

| Tier | Limit |
|---|---|
| Anonymous | 60 requests/min |
| Authenticated | 200 requests/min |
| Solution generation | 10 requests/min (anonymous), 30 requests/min (authenticated) |

---

## 9. Frontend Architecture

### 9.1 Directory Structure

```
src/
  app/                         # Next.js App Router
    (public)/
      page.tsx                 # Main problem feed (/)
      problems/[id]/page.tsx   # Problem detail page
      analytics/page.tsx       # Analytics dashboard
      trending/page.tsx        # Trending topics
    (auth)/
      login/page.tsx
      signup/page.tsx
    api/                       # Next.js Route Handlers (BFF layer)
      problems/route.ts
      solutions/route.ts
  components/
    feed/
      ProblemCard.tsx          # Feed list item
      ProblemFeed.tsx          # Paginated list container
      FilterBar.tsx            # Platform / category / sentiment filters
      SearchInput.tsx          # Full-text search
    detail/
      SolutionTabs.tsx         # Provider tabs (Gemini / GPT / Claude)
      VoteButtons.tsx          # Thumbs up/down per solution
      RelatedProblems.tsx      # Sidebar
    analytics/
      CategoryBarChart.tsx
      VolumeLineChart.tsx
      ActivityHeatmap.tsx
      SentimentPieChart.tsx
    trending/
      WordCloud.tsx
      TopicSparkline.tsx
    shared/
      SentimentBadge.tsx
      PlatformIcon.tsx
      CategoryTag.tsx
      ExportButton.tsx         # Export to PDF
      InfiniteScroll.tsx
  store/
    filterStore.ts             # Zustand — active filters, pagination
    authStore.ts               # Zustand — user session
  hooks/
    useProblems.ts             # React Query — problem list
    useProblemDetail.ts        # React Query — single problem + solutions
    useAnalytics.ts            # React Query — analytics data
    useTrending.ts             # React Query — trending topics
  lib/
    api.ts                     # Axios/fetch wrapper with auth headers
    auth.ts                    # Supabase Auth JS helper
  types/
    problem.ts
    solution.ts
    user.ts
    analytics.ts
```

### 9.2 Data Fetching Strategy

| Data | Strategy | Stale Time | Notes |
|---|---|---|---|
| Problem feed | React Query + polling | 5 min | Refetch on window focus |
| Problem detail | React Query | 10 min | Preload on hover |
| Trending topics | React Query | 30 min | Background refetch |
| Analytics | React Query | 1h | Computed server-side |
| User bookmarks | React Query | Infinite | Invalidated on mutation |

### 9.3 Page Specifications

**Main Feed (`/`)**
- Paginated or infinite-scroll list of problems, newest first
- Filter bar: Platform (Reddit, HN), Category (multi-select), Sentiment, Date range, Has AI solution toggle
- Full-text search input
- Trending topics sidebar panel (24h default)
- Each card: platform icon, category tag, sentiment badge, title, 2-sentence summary, AI solution indicator, relative timestamp

**Problem Detail (`/problems/:id`)**
- Full problem text with source link
- Three-tab solution panel (Gemini | OpenAI | Claude) — on-demand load
- Thumbs up/down per solution tab
- Related problems sidebar (same category, last 7 days)
- Share button, Export to PDF button

**Analytics Dashboard (`/analytics`)**
- Bar chart: problems by category (last 30 days)
- Line chart: volume by platform over time (selectable range)
- Heatmap: activity by hour of day and day of week
- Pie chart: sentiment distribution

**Trending Topics (`/trending`)**
- Word cloud of top-25 keywords (24h / 7d / 30d selector)
- Ranked list with sparkline charts per topic

### 9.4 Accessibility

WCAG 2.1 Level AA compliance is required:
- All interactive elements have visible focus indicators.
- Color is never the sole differentiator (sentiment badges include text labels).
- Chart data is also available in accessible table form (toggle).
- Keyboard navigation covers all primary user flows.
- `aria-*` attributes on dynamic regions (filter results, solution tabs).

---

## 10. Backend Architecture

### 10.1 Process Model

```
Koyeb Service: solvora-api
  Process 1: uvicorn main:app --workers 2
    FastAPI application
    - REST request handling
    - Auth middleware (JWT validation)
    - Rate limit middleware (Redis counter)
    - Response caching middleware
    - Celery task dispatch

  Process 2: celery -A tasks worker --loglevel=info
    Task workers (shared process on free tier; separate in prod)
    - ScrapeRedditTask
    - ScrapeHNTask
    - ClassifyProblemTask
    - GenerateSolutionTask
    - ComputeAnalyticsTask

  Process 3 (GitHub Actions — external trigger):
    GET /internal/cron/scrape-reddit   (every 30 min)
    GET /internal/cron/scrape-hn       (every 15 min)
    GET /internal/cron/daily-refresh   (daily 02:00 UTC)
    GET /internal/cron/compute-analytics (hourly)
```

### 10.2 Module Structure

```
backend/
  app/
    main.py                    # FastAPI app factory
    config.py                  # Pydantic settings from env vars
    database.py                # SQLAlchemy async engine + session
    redis_client.py            # Upstash Redis connection
    middleware/
      auth.py                  # JWT Bearer validation
      rate_limit.py            # Sliding window rate limiting
      cache.py                 # Response cache decorator
    routers/
      problems.py
      solutions.py
      votes.py
      analytics.py
      categories.py
      auth.py
      bookmarks.py
      presets.py
      internal.py              # Cron trigger endpoints (IP-restricted)
    services/
      problem_service.py       # Business logic for problems
      solution_service.py      # AI orchestration + cache
      analytics_service.py     # Aggregation queries
      auth_service.py          # Supabase Auth integration
    scrapers/
      reddit_scraper.py
      hn_scraper.py
      x_scraper.py             # Stubbed
      deduplication.py
    nlp/
      problem_classifier.py
      category_tagger.py
      sentiment_detector.py
      summarizer.py
      prompt_templates.py
    ai/
      solution_orchestrator.py
      openai_adapter.py
      gemini_adapter.py
      claude_adapter.py
      cache_manager.py
      prompt_builder.py
    tasks/
      celery_app.py
      scrape_tasks.py
      classify_tasks.py
      solution_tasks.py
      analytics_tasks.py
    models/
      problem.py               # SQLAlchemy ORM models
      solution.py
      user.py
      vote.py
      bookmark.py
      category.py
    schemas/
      problem.py               # Pydantic request/response schemas
      solution.py
      user.py
      analytics.py
    utils/
      hashing.py               # SHA-256 deduplication
      retry.py                 # Tenacity retry decorators
      logging.py               # Structlog configuration
```

### 10.3 Error Handling

- All unhandled exceptions are caught by a global FastAPI exception handler and logged to Sentry.
- AI provider calls use `tenacity` with exponential back-off: 3 retries, base delay 2s, max delay 30s.
- Scraper failures are recorded in `scrape_log` with `status='failed'` and `error_message`.
- Celery tasks implement `max_retries=3` with `countdown=60` between retries.
- HTTP 429 responses from AI providers trigger a 5-minute circuit breaker per provider stored in Redis.

---

## 11. AI/ML Pipeline

### 11.1 Pipeline Stages

```
Stage 1: Ingestion
  Raw post stored in problems table (is_problem=false, category=null)
  Celery task queued: ClassifyProblemTask(problem_id)

Stage 2: Classification (ClassifyProblemTask)
  2a. Problem classifier  --> is_problem, confidence
      If confidence < 0.65: set review_required=true, STOP
      If is_problem=false:  set is_active=false, STOP
  2b. Category tagger     --> category_id
  2c. Sentiment detector  --> sentiment
  2d. Summarizer          --> summary
  UPDATE problems SET is_problem=true, category_id=..., sentiment=..., summary=...
  Celery task queued: GenerateSolutionTask(problem_id, providers=['gemini'])
      (openai/claude added only on user demand or premium config)

Stage 3: Solution Generation (GenerateSolutionTask)
  3a. Check Redis: solution:{problem_id}:{provider} exists?
      YES: serve from cache
      NO:  call provider adapter
  3b. Build prompt (prompt_builder.py)
      System: "You are a helpful assistant. Given the following real-world problem from {platform}..."
      User:   problem.title + problem.body (truncated to max_tokens)
      Context injected: category, sentiment, summary
  3c. Call AI provider (with retry decorator)
  3d. Store in solutions table
  3e. Store in Redis with 24h TTL
  3f. Update solution rating = 0.0 (no votes yet)

Stage 4: Voting Feedback Loop
  User votes (+ or -) on a solution
  POST /api/v1/votes
  Recompute rating: SUM(vote_type) / COUNT(*) normalized to [-1, 1]
  UPDATE solutions SET rating=...

Stage 5: Analytics Aggregation (ComputeAnalyticsTask — hourly)
  GROUP BY category, platform, sentiment, date, hour
  Write aggregated results to Redis (analytics:summary, analytics:trending:*)
  Invalidate feed caches (problem:feed:*)
```

### 11.2 Prompt Templates

**Classification Prompt**
```
System: You are a content classification assistant. Analyze social media posts and determine if they describe a real problem or pain point a person is experiencing.

User: Platform: {platform}
Title: {title}
Body: {body}

Is this post describing a real problem? Answer as JSON: {"is_problem": true/false, "confidence": 0.0-1.0, "reason": "one sentence"}
```

**Category + Sentiment Prompt**
```
System: You are a content tagging assistant.

User: Title: {title}
Body: {body}

Assign ONE category from: [Technology, Health, Finance, Relationships, Productivity, Travel, Education, Other]
Assign ONE sentiment from: [Urgent, Frustrated, Curious, Neutral]
Answer as JSON: {"category": "...", "sentiment": "..."}
```

**Solution Generation Prompt**
```
System: You are a knowledgeable problem-solving assistant. You will be given a real problem posted on {platform}. Provide a clear, actionable, step-by-step solution. Be concise, practical, and empathetic. If the topic involves health or legal matters, advise consulting a professional.

User: Problem Category: {category}
Sentiment: {sentiment}
Platform: {platform}

Problem:
{title}

{body}

Provide a comprehensive solution with numbered steps where applicable.
```

### 11.3 Provider Selection Logic

```
Default (automated, free):    Gemini 1.5 Flash
On user demand (any):         All three providers in parallel (tabs)
Category = Health:            Prefer Claude (safety-aware)
Category = Finance:           Prefer Claude (nuanced)
Budget exceeded (daily cap):  Fall back to Gemini Flash only
```

### 11.4 NLP Confidence Threshold

| Confidence | Action |
|---|---|
| >= 0.80 | Auto-classify and publish |
| 0.65 – 0.79 | Classify and publish; flag for optional review |
| < 0.65 | Hold in review queue; `review_required=true`; not shown on dashboard |

---

## 12. Security Architecture

### 12.1 Secrets Management

- All API keys (Reddit OAuth, HN none, OpenAI, Gemini, Anthropic, Supabase) are stored as environment variables in the Koyeb service dashboard and Vercel project settings.
- No secrets are committed to the Git repository.
- GitHub Actions uses encrypted repository secrets for cron trigger auth token.
- Secrets are rotated every 90 days (tracked via team calendar reminder).

### 12.2 Authentication and Authorization

- Supabase Auth issues JWTs (RS256-signed) on login.
- FastAPI `auth.py` middleware validates JWTs on every protected request using Supabase public key.
- Anonymous access is permitted for read-only endpoints; write operations (votes, bookmarks) require a valid JWT.
- Internal cron endpoints (`/internal/cron/*`) are IP-restricted to GitHub Actions IP ranges and require a shared secret header (`X-Cron-Token`).

### 12.3 Input Validation

- All incoming request bodies are validated by Pydantic v2 schemas before reaching business logic.
- Full-text search queries are parameterized using SQLAlchemy — no raw string interpolation.
- File paths are not accepted from users in v1.0.
- Problem IDs accepted in URL path are validated as UUID format.

### 12.4 Output Sanitization

- AI-generated solution text is stored as plain text and HTML-escaped on frontend render (React does this by default for `{variable}` interpolations).
- No user-supplied HTML is accepted or rendered.

### 12.5 Rate Limiting

- API rate limiting via Redis sliding-window counter (see Section 8.4).
- AI provider calls additionally rate-limited at the service layer with a daily token budget counter in Redis.

### 12.6 Data Compliance

- Reddit and Hacker News data is fetched via official APIs in compliance with their Terms of Service.
- No personally identifiable information beyond public author handles is stored.
- Author handles are stored for attribution only; no profile enrichment or cross-platform correlation.
- GDPR: user accounts include a delete endpoint that hard-deletes user rows and cascades to bookmarks and votes.

### 12.7 Transport Security

- All traffic is HTTPS. Vercel and Koyeb provide automatic TLS certificates.
- Cloudflare is placed in front of both frontend and backend for DDoS protection and WAF (free plan).
- HSTS headers enforced on all responses.
- CORS policy on FastAPI restricts allowed origins to the Vercel frontend domain.

---

## 13. Deployment Architecture

### 13.1 Environment Strategy

| Environment | Frontend | Backend | Database | Notes |
|---|---|---|---|---|
| Development | `localhost:3000` | `localhost:8000` | Local Postgres via Docker | `.env.local` files |
| Staging | Vercel preview deploy | Koyeb staging service | Neon staging branch | Auto-deployed on PR |
| Production | Vercel production | Koyeb production service | Neon main branch | Manual promote |

### 13.2 CI/CD Pipeline

```
Developer pushes to feature branch
  --> GitHub Actions: lint (ruff, eslint) + type-check (mypy, tsc)
  --> GitHub Actions: unit tests (pytest, jest)
  --> Vercel: preview deployment created
  --> PR opened: staging Koyeb deploy triggered via webhook

PR merged to main
  --> GitHub Actions: full test suite
  --> Vercel: production deployment (automatic)
  --> Koyeb: production deployment (manual promote or auto on main push)
```

### 13.3 Infrastructure Diagram

```
Internet
    |
    v
[Cloudflare DNS + WAF + CDN]
    |                   |
    v                   v
[Vercel CDN]      [Koyeb (Always-on)]
[Next.js SSR]     [FastAPI + Celery]
    |                   |
    |             [Upstash Redis]
    |              (cache + queue)
    |                   |
    +-------------------+
                        |
                  [Neon PostgreSQL]
                  (primary database)

Separate trigger path:
[GitHub Actions Cron]
    |
    v
[Koyeb /internal/cron/*]
    |
    v
[Celery Task Queue]
    |
    v
[Reddit API / HN API / AI APIs]
```

### 13.4 Scaling Path (Milestone-Based)

| Milestone | Trigger | Action | Estimated Additional Cost |
|---|---|---|---|
| 100 DAU | Koyeb RAM exhausted | Upgrade Koyeb to paid (1GB RAM) | +$7–10/month |
| 500 DAU | Neon connection pool saturation | Enable Neon connection pooler (PgBouncer built-in) | $0 (included) |
| 500 DAU | Redis command quota exceeded | Upgrade Upstash to pay-as-you-go | +$5–15/month |
| Add X source | Content demand | Enable X API Basic plan | +$100/month |
| Add Claude + GPT | Quality demand | Enable Anthropic + OpenAI billing | +$5–15/month |
| 1,000 DAU | Koyeb capacity | Migrate backend to AWS ECS Fargate (t3.small) | +$20–50/month |
| 2,000 DAU | DB performance | Neon Pro + read replicas | +$19/month |

---

## 14. Data Flow Diagrams

### 14.1 Scraping and Classification Flow

```
[GitHub Actions Cron]
        |
        | HTTP GET /internal/cron/scrape-reddit
        v
[FastAPI Internal Router]
        |
        | Enqueue ScrapeRedditTask
        v
[Celery Worker: ScrapeRedditTask]
        |
        | PRAW API call --> Reddit API
        |                      |
        |               [Raw Posts JSON]
        |                      |
        | Deduplicate (SHA-256 check vs DB)
        |
        | INSERT INTO problems (is_problem=false)
        |
        | Enqueue ClassifyProblemTask(problem_id) x N
        v
[Celery Worker: ClassifyProblemTask]
        |
        | Build classification prompt
        |
        | Call Gemini 1.5 Flash API
        |       |
        |  [is_problem, confidence, category, sentiment]
        |
        | confidence < 0.65? --> set review_required=true, done
        | is_problem=false?   --> set is_active=false, done
        |
        | UPDATE problems SET is_problem=true, category_id, sentiment, summary
        |
        | Enqueue GenerateSolutionTask(problem_id, providers=['gemini'])
        v
[Redis Upstash: Celery Queue]
```

### 14.2 AI Solution Generation Flow

```
[Celery Worker: GenerateSolutionTask]
        |
        | Check Redis: solution:{problem_id}:gemini
        |       HIT  --> skip generation, done
        |       MISS --> continue
        |
        | Build solution prompt (prompt_builder.py)
        |       injects: title, body, category, sentiment, platform
        |
        | Call Gemini 1.5 Flash API (with tenacity retry)
        |       |
        |  [solution_text, token counts]
        |
        | INSERT INTO solutions (problem_id, provider='gemini', ...)
        |
        | SET Redis solution:{problem_id}:gemini EX 86400
        v
[Solution stored and cached]

On-Demand (user clicks "Get Solution" from all 3 providers):
[POST /api/v1/solutions/generate]
        |
        | Dispatch GenerateSolutionTask for each provider in parallel
        | (openai_adapter, gemini_adapter, claude_adapter)
        v
[Celery Workers — parallel execution]
        |
        | Results stored in DB + Redis
        v
[Frontend polls GET /api/v1/solutions/{problem_id}]
```

### 14.3 Frontend Request Flow

```
[Browser]
    |
    | HTTPS GET solvora.vercel.app/
    v
[Vercel Edge Network]
    |
    | React Server Component: fetch /api/v1/problems?page=1
    v
[Koyeb FastAPI]
    |
    | Check Redis: problem:feed:{filter_hash}
    |       HIT  --> return cached JSON (< 1ms)
    |       MISS --> continue
    |
    | SELECT * FROM problems WHERE is_active=true ORDER BY scraped_at DESC
    | (with JOIN on categories, LEFT JOIN on solutions count)
    |
    | Store in Redis with 5m TTL
    |
    | Return JSON response
    v
[Browser — hydrate React components]
    |
    | React Query: background refetch every 5 minutes
    | React Query: refetch on window focus
    v
[Up-to-date feed rendered]
```

### 14.4 User Voting Flow

```
[Browser: user clicks thumbs-up on a Claude solution]
    |
    | POST /api/v1/votes
    | Headers: Authorization: Bearer {jwt}
    | Body: { solution_id, vote_type: 1 }
    v
[FastAPI auth middleware: validate JWT]
    |
    | UPSERT INTO votes (user_id, solution_id, vote_type=1)
    | ON CONFLICT (user_id, solution_id) UPDATE vote_type=1
    |
    | Recompute solution rating:
    | UPDATE solutions SET rating = (SELECT SUM(vote_type)::float / COUNT(*) FROM votes WHERE solution_id=...)
    |
    | Invalidate Redis: solution:{problem_id}:claude
    v
[React Query: invalidate useProblemDetail query]
    |
    | Re-fetch GET /api/v1/problems/:id
    v
[Updated rating displayed]
```

---

## 15. Integration Points

### 15.1 Reddit API (PRAW)

- Auth: OAuth2 Client Credentials (client_id, client_secret, user_agent)
- Rate limit: 100 requests/minute — enforced by PRAW automatically
- Endpoints used: `subreddit.new()`, `subreddit.search()`, `submission.comments`
- Error handling: `prawcore.exceptions.ResponseException` caught; exponential back-off; logged to `scrape_log`

### 15.2 Hacker News Algolia API

- Auth: None required
- Base URL: `https://hn.algolia.com/api/v1/search`
- Query: `tags=ask_hn&query={keyword}&numericFilters=created_at_i>{unix_timestamp}`
- Rate limit: Not documented; conservative 1 request/second enforced in scraper
- No API key needed

### 15.3 OpenAI API

- SDK: `openai` Python SDK v1.x
- Models: `gpt-4o-mini` (default), `gpt-4o` (premium on-demand)
- Auth: `OPENAI_API_KEY` environment variable
- Token budget: Daily counter in Redis; hard cap at 500K tokens/day in MVP
- Error codes handled: 429 (rate limit), 503 (overload), 400 (invalid request)

### 15.4 Google Gemini API

- SDK: `google-generativeai` Python SDK
- Models: `gemini-1.5-flash` (default), `gemini-1.5-pro` (complex problems)
- Auth: `GEMINI_API_KEY` environment variable (Google AI Studio key)
- Free tier: 15 RPM, 1M tokens/day — primary AI for v1.0
- Error codes handled: 429, 503

### 15.5 Anthropic Claude API

- SDK: `anthropic` Python SDK
- Models: `claude-3-5-sonnet-20241022`
- Auth: `ANTHROPIC_API_KEY` environment variable
- Used for: Health and Relationships categories; on-demand multi-provider comparisons
- Error codes handled: 429, 529 (overloaded)

### 15.6 Supabase Auth

- JS SDK: `@supabase/supabase-js` (frontend)
- Python validation: Supabase JWT public key fetched at startup; RS256 JWT validation in FastAPI middleware
- Flows: Email/password, Google OAuth2
- Environment variables: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`

### 15.7 Neon PostgreSQL

- Connection: `asyncpg` driver via SQLAlchemy 2.0 async engine
- Connection string: `DATABASE_URL` environment variable
- Connection pool: min 2, max 10 connections (within Neon free tier limits)
- Migrations: managed via Alembic

### 15.8 Upstash Redis

- Connection: `redis-py` with TLS; Upstash REST API as fallback
- Environment variables: `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`
- Used for: Response cache, Celery broker, rate-limit counters, analytics cache

---

## 16. Scalability Considerations

### 16.1 Stateless API Processes

FastAPI workers are fully stateless — no in-process session state. All state lives in Neon (durable) or Upstash Redis (ephemeral). This allows horizontal scaling by increasing the Koyeb replica count with zero code changes.

### 16.2 Database Query Optimization

- All foreign key columns are indexed.
- The main feed query uses a partial index on `is_active=true` to reduce scan size.
- Full-text search uses a GIN index on `to_tsvector(title || body)` — avoids LIKE scans.
- Analytics aggregations are pre-computed by a background Celery beat task every hour and cached in Redis. The `/api/v1/analytics/*` endpoints serve from Redis, not from live DB GROUP BY queries.
- Long-running queries (trending computation, daily refresh) run as background Celery tasks, not synchronous API calls.

### 16.3 AI Cost Scaling Controls

- All AI solutions are cached in both PostgreSQL and Redis. The same problem re-appearing (common for trending topics) never triggers a duplicate API call.
- Lazy generation: solutions are only generated for problems a user actually views, unless the problem exceeds a viral threshold (100+ upvotes) which triggers pre-generation.
- Daily token budget hard cap enforced per provider via Redis atomic counter. When exceeded, the provider is disabled for the remainder of the day and Gemini Flash serves as universal fallback.
- Model routing: high-traffic periods use Gemini Flash exclusively. Claude and GPT-4o are opt-in per request.

### 16.4 Feed Performance

- Paginated feed responses are cached in Redis for 5 minutes, keyed by filter hash.
- Next.js ISR (Incremental Static Regeneration) is used for the trending and analytics pages, regenerating every 30 minutes at the edge.
- React Query's stale-while-revalidate strategy ensures users always see data immediately from cache while fresh data loads in the background.

### 16.5 Scraper Resilience

- Scraper tasks are idempotent: the SHA-256 deduplication key prevents double-inserts even if a task is retried.
- Each scraper records its run in `scrape_log` with `started_at` and `finished_at`. A watchdog Celery task checks for runs that have been in `running` state for more than 10 minutes and re-queues them.
- Reddit PRAW handles its own rate-limit back-off internally.
- HN scraper tracks the last-fetched `created_at_i` timestamp in Redis to enable incremental fetching.

---

## 17. Non-Functional Requirements Mapping

| Requirement | Target | Architecture Solution |
|---|---|---|
| Dashboard initial load time | < 2 seconds | Next.js RSC pre-renders above-the-fold feed on server; Vercel Edge CDN; React Query client cache |
| AI solution generation latency | < 5 seconds per provider | Parallel Celery tasks per provider; Redis cache serves instant response on hit; Gemini Flash averages ~1–2s |
| Concurrent users | 500+ without degradation | Stateless FastAPI workers; Redis-cached feed; Neon connection pooling; Vercel auto-scales frontend |
| System availability | 99.5% monthly SLA | Koyeb always-on (no cold start); Neon serverless (never sleeps); Upstash serverless; Vercel 99.99% SLA |
| Problem feed refresh | Every 15–30 minutes | GitHub Actions cron at 15-min intervals for HN; 30-min for Reddit; React Query 5-min client polling |
| API key security | Encrypted env vars | Koyeb + Vercel encrypted environment variable stores; no secrets in code or logs |
| Reddit/X ToS compliance | Full compliance | Official PRAW library; X replaced with HN in v1.0; rate-limit monitoring |
| WCAG 2.1 Level AA | Accessibility | shadcn/ui Radix primitives (accessible by default); aria attributes; keyboard nav; visible focus |

---

## 18. Architecture Decision Records

### ADR-001: Python FastAPI over Node.js Express for Backend

**Status:** Accepted
**Context:** The backend must host REST API routes and also run NLP/AI workloads. Python has a richer ML ecosystem.
**Decision:** Use Python 3.11 + FastAPI. Scrapers, NLP classification, and AI adapters are all Python — a single language across the backend removes the polyglot maintenance burden.
**Consequences:** Frontend developers who are JS-only will need to context-switch. FastAPI's async support is adequate for I/O-bound AI API calls.

### ADR-002: Hacker News Replaces X (Twitter) in v1.0

**Status:** Accepted
**Context:** X API Basic plan costs $100/month. The free tier (500 tweets/month) is unusable for a live dashboard.
**Decision:** Replace X with the Hacker News Algolia API for v1.0. HN is free, no authentication required, and surfaces technology-oriented problem discussions well-suited to the target audience.
**Consequences:** The `problems.platform` column retains 'twitter' as a valid value for future use. The X scraper is implemented as a stub module that logs a warning and returns empty results.

### ADR-003: Gemini 1.5 Flash as Primary AI Provider

**Status:** Accepted
**Context:** At 100 problems/day (~80K tokens/day), Gemini 1.5 Flash's 1M token/day free tier covers the full MVP workload at zero cost.
**Decision:** All automated classification and default solution generation uses Gemini 1.5 Flash. Claude and GPT-4o-mini are on-demand only.
**Consequences:** Users who want multi-provider comparison must explicitly request it. Quality may be marginally lower than GPT-4o on complex prompts, but acceptable for MVP validation.

### ADR-004: Lazy AI Solution Generation

**Status:** Accepted
**Context:** Generating solutions for every scraped post automatically would exhaust AI token budgets and increase latency for posts no user ever views.
**Decision:** Background auto-generation is triggered only for high-signal posts (upvotes above threshold). All other solutions are generated on first user view.
**Consequences:** First-view latency for on-demand generation is 1–5 seconds. A loading state must be shown on the frontend during generation.

### ADR-005: Neon over Supabase Postgres for Primary Database

**Status:** Accepted
**Context:** Supabase's free tier pauses the database after 1 week of inactivity, which would cause cold-start delays for the dashboard.
**Decision:** Use Neon PostgreSQL which never pauses, offers 5GB free storage, and supports the same Postgres dialect.
**Consequences:** Neon's serverless connection model requires attention to connection pool limits. PgBouncer-compatible pooling is enabled from day one.

### ADR-006: GitHub Actions for Cron Scheduling

**Status:** Accepted
**Context:** Celery beat would require an always-on process, adding RAM pressure to the Koyeb free tier. GitHub Actions provides 2,000 free minutes/month.
**Decision:** GitHub Actions workflows trigger scraper endpoints on a schedule via HTTP. Actual work runs inside Koyeb Celery workers.
**Consequences:** If GitHub Actions is unavailable, scraping stops until it recovers. An internal watchdog task monitors the last successful scrape time and alerts via Sentry if it exceeds 2x the expected interval.

### ADR-007: Redis (Upstash) as Both Cache and Celery Broker

**Status:** Accepted
**Context:** Two separate services for cache and queue would consume two free-tier allocations. Upstash supports both use cases.
**Decision:** Use a single Upstash Redis instance for API response caching, AI solution caching, rate-limit counters, and Celery task broker.
**Consequences:** A surge in Celery task volume could consume the 10K commands/day free limit faster. A daily budget alarm is set at 8K commands/day to prompt a timely upgrade decision.

---

## 19. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| X API rate limits restrict scraping volume | High (v2.0) | High | Replaced with HN in v1.0. X re-evaluated when revenue available. |
| AI API costs escalate at scale | Medium | High | Daily token budget caps in Redis. Gemini Flash covers MVP entirely for free. Cache-first strategy cuts repeat calls by 60–80%. |
| Reddit/X ToS changes block scraping | Medium | High | Official PRAW library used. ToS monitored quarterly. HN is fallback for v1.0. |
| AI solution quality is inconsistent | Medium | Medium | Voting system surfaces quality signal. Multi-provider comparison enables user self-selection. Low-confidence NLP outputs held for review. |
| NLP classifier mislabels posts | Medium | Low | Confidence threshold (0.65) gates publication. Posts below threshold enter review queue, not dashboard. Retraining pipeline planned for v2.0. |
| Koyeb free tier RAM exhaustion | Medium | Medium | Monitor memory metrics weekly. Upgrade trigger at 80% sustained utilization. |
| Neon connection limit exceeded | Low | Medium | Async SQLAlchemy pool with max 10 connections. Neon's built-in PgBouncer enabled from launch. |
| Upstash daily command limit hit | Low | Medium | Alert at 8K/10K commands. Upgrade to pay-as-you-go ($0.20/100K commands) is immediate. |
| GitHub Actions cron delay or failure | Low | Low | Watchdog task in Celery alerts via Sentry if scrape gap exceeds 2x interval. Manual trigger endpoint available. |

---

*End of Architecture Document*

*This document should be reviewed and updated at the end of each development phase. For questions, contact the Product Team.*
