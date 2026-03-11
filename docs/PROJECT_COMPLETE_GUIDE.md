# Solvora — Complete Project Guide

> From concept to production: everything about how Solvora was built and deployed.

---

## Table of Contents

1. [What Is Solvora?](#1-what-is-solvora)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Backend Architecture](#4-backend-architecture)
   - 4.1 [Configuration & Settings](#41-configuration--settings)
   - 4.2 [Database Layer](#42-database-layer)
   - 4.3 [Data Models](#43-data-models)
   - 4.4 [Authentication System](#44-authentication-system)
   - 4.5 [API Endpoints](#45-api-endpoints)
   - 4.6 [Scrapers](#46-scrapers)
   - 4.7 [NLP Classifier](#47-nlp-classifier)
   - 4.8 [AI Solution Orchestrator](#48-ai-solution-orchestrator)
   - 4.9 [Celery Task Queue](#49-celery-task-queue)
   - 4.10 [Redis Caching & Rate Limiting](#410-redis-caching--rate-limiting)
   - 4.11 [Security Middleware](#411-security-middleware)
5. [Frontend Architecture](#5-frontend-architecture)
   - 5.1 [Pages & Routing](#51-pages--routing)
   - 5.2 [Components](#52-components)
   - 5.3 [State Management](#53-state-management)
   - 5.4 [API Client](#54-api-client)
6. [Data Pipeline (End-to-End Flow)](#6-data-pipeline-end-to-end-flow)
7. [Local Development Setup](#7-local-development-setup)
8. [Docker & Docker Compose](#8-docker--docker-compose)
9. [Cloud Services Setup](#9-cloud-services-setup)
   - 9.1 [Neon (PostgreSQL)](#91-neon-postgresql)
   - 9.2 [Upstash (Redis)](#92-upstash-redis)
   - 9.3 [Reddit API](#93-reddit-api)
   - 9.4 [Google OAuth](#94-google-oauth)
   - 9.5 [AI APIs](#95-ai-apis)
10. [Deployment — Backend (Railway)](#10-deployment--backend-railway)
    - 10.1 [API Service](#101-api-service)
    - 10.2 [Celery Worker Service](#102-celery-worker-service)
    - 10.3 [Celery Beat Service](#103-celery-beat-service)
11. [Deployment — Frontend (Vercel)](#11-deployment--frontend-vercel)
12. [Environment Variables Reference](#12-environment-variables-reference)
13. [Problems Fixed During Deployment](#13-problems-fixed-during-deployment)
14. [Post-Deployment Verification](#14-post-deployment-verification)
15. [Ongoing Automated Pipeline](#15-ongoing-automated-pipeline)

---

## 1. What Is Solvora?

Solvora is a **problem aggregation and AI solution platform**. It automatically:

1. Scrapes problem-oriented posts from Reddit and Hacker News on a schedule
2. Uses Gemini 1.5 Flash (NLP) to classify each post: is it a real problem? What category? What sentiment?
3. Stores classified problems in a PostgreSQL database
4. On demand (or for viral posts automatically), generates solutions using three AI providers: **Gemini**, **OpenAI**, and **Claude**
5. Presents everything in a Next.js dashboard where users can browse problems, filter by category/platform/sentiment, read AI solutions, bookmark problems, and vote on solutions

The project was conceived as a tool to surface real human pain points from social media and provide structured, AI-generated responses to them.

---

## 2. Tech Stack

### Backend
| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.110.0 |
| ASGI server | Uvicorn | 0.29.0 |
| ORM | SQLAlchemy (async) | 2.0.29 |
| Async DB driver | asyncpg | 0.29.0 |
| Sync DB driver | psycopg2-binary | 2.9.9 |
| Migrations | Alembic | 1.13.1 |
| Data validation | Pydantic v2 | 2.7.0 |
| Task queue | Celery | 5.3.6 |
| Redis client | redis-py | 5.0.4 |
| JWT auth | PyJWT | 2.8.0 |
| Password hashing | bcrypt | 4.1.3 |
| Reddit scraper | PRAW | 7.7.1 |
| AI - Gemini | google-generativeai | 0.5.4 |
| AI - OpenAI | openai | 1.30.1 |
| AI - Claude | anthropic | 0.26.0 |
| Rate limiting | slowapi | 0.1.9 |
| Error monitoring | sentry-sdk | 2.3.1 |
| Structured logging | structlog | 24.1.0 |
| Retry logic | tenacity | 8.3.0 |
| Python version | Python | 3.11 |

### Frontend
| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js | 14.2.35 |
| Language | TypeScript | 5.x |
| UI components | Radix UI | various |
| Styling | Tailwind CSS | 3.4.4 |
| HTTP client | Axios | 1.7.2 |
| Server state | TanStack React Query | 5.40.0 |
| Client state | Zustand | 4.5.2 |
| Auth | NextAuth.js | 4.24.13 |
| Charts | Recharts | 2.12.7 |
| Icons | Lucide React | 0.395.0 |
| Date utils | date-fns | 3.6.0 |
| Node version | Node.js | 20 |

### Infrastructure
| Service | Provider | Purpose |
|---|---|---|
| PostgreSQL | Neon | Primary database |
| Redis | Upstash | Task queue broker + response cache |
| Backend hosting | Railway | FastAPI app + Celery services |
| Frontend hosting | Vercel | Next.js app |
| Source control | GitHub | `chakravarthi-giduthuri/solvora` |

---

## 3. Project Structure

```
project S/
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── config/
│   ├── docker-compose.yml      # Local / self-hosted full-stack
│   └── koyeb.yml               # Alternative PaaS config
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── SETUP.md
│   └── PROJECT_COMPLETE_GUIDE.md  ← this file
├── scripts/
│   ├── setup.sh                # One-shot local dev setup
│   ├── run_dev.sh              # Start all services locally
│   ├── seed_categories.py      # Populate categories table
│   ├── backfill_categories.py  # Assign categories to existing problems
│   └── backfill_sentiment.py   # Assign sentiments to existing problems
└── src/
    ├── backend/
    │   ├── .env                # Local secrets (git-ignored)
    │   ├── .env.example        # Template for secrets
    │   ├── .railwayignore      # Exclude venv/ from Railway uploads
    │   ├── Dockerfile          # Multi-stage production image
    │   ├── requirements.txt    # Python dependencies
    │   ├── celerybeat-schedule.db  # Beat scheduler state (local)
    │   ├── app/
    │   │   ├── main.py         # FastAPI app factory + middleware
    │   │   ├── celery_app.py   # Legacy celery reference (unused)
    │   │   ├── core/
    │   │   │   ├── config.py       # Pydantic settings (env vars)
    │   │   │   ├── database.py     # Async + sync SQLAlchemy engines
    │   │   │   ├── security.py     # JWT, bcrypt, token revocation
    │   │   │   ├── redis_client.py # Redis connection + cache helpers
    │   │   │   ├── limiter.py      # slowapi rate limiter instance
    │   │   │   └── celery_app.py   # Celery app + beat schedule
    │   │   ├── models/
    │   │   │   └── problem.py  # All SQLAlchemy models
    │   │   ├── schemas/
    │   │   │   ├── problem.py  # Pydantic request/response schemas
    │   │   │   └── auth.py     # Auth-related schemas
    │   │   ├── api/v1/
    │   │   │   ├── problems.py     # GET/POST /problems
    │   │   │   ├── solutions.py    # GET/POST /solutions
    │   │   │   ├── analytics.py    # GET /analytics
    │   │   │   ├── categories.py   # GET /categories
    │   │   │   ├── auth.py         # POST /auth/login|signup|logout
    │   │   │   ├── votes.py        # POST /votes
    │   │   │   ├── bookmarks.py    # GET/POST/DELETE /bookmarks
    │   │   │   └── internal.py     # POST /internal/scrape (INTERNAL_API_KEY)
    │   │   ├── services/
    │   │   │   ├── auth_service.py         # User creation, Google OAuth
    │   │   │   └── analytics_service.py    # Trending topics, aggregations
    │   │   ├── scrapers/
    │   │   │   ├── base_scraper.py     # Shared _save_posts logic
    │   │   │   ├── reddit_scraper.py   # PRAW Reddit scraper
    │   │   │   └── hn_scraper.py       # HN Algolia API scraper
    │   │   ├── nlp/
    │   │   │   ├── classifier.py   # Gemini NLP classifier
    │   │   │   └── tasks.py        # Celery tasks: scrape + classify
    │   │   └── ai/
    │   │       ├── gemini_adapter.py       # Gemini solution generator
    │   │       ├── openai_adapter.py       # OpenAI solution generator
    │   │       ├── claude_adapter.py       # Claude solution generator
    │   │       ├── solution_orchestrator.py # Cache + circuit breaker
    │   │       └── tasks.py                # Celery task: batch generate
    │   └── tests/
    │       ├── conftest.py
    │       ├── test_auth_api.py
    │       └── test_problems_api.py
    └── frontend/
        ├── .env.local          # Local frontend secrets (git-ignored)
        ├── .env.example        # Template
        ├── Dockerfile          # Multi-stage Next.js image
        ├── package.json
        ├── tsconfig.json
        ├── tailwind.config.ts
        └── src/
            ├── app/            # Next.js App Router pages
            │   ├── layout.tsx          # Root layout
            │   ├── page.tsx            # Landing page
            │   ├── providers.tsx       # NextAuth + React Query providers
            │   ├── globals.css
            │   ├── dashboard/
            │   │   ├── layout.tsx      # Dashboard shell
            │   │   └── page.tsx        # Main problem feed
            │   ├── problems/[id]/
            │   │   └── page.tsx        # Problem detail + AI solutions
            │   ├── analytics/
            │   │   └── page.tsx        # Charts and stats
            │   ├── bookmarks/
            │   │   ├── page.tsx
            │   │   └── BookmarksClient.tsx
            │   └── auth/
            │       ├── login/
            │       └── signup/
            ├── components/
            │   ├── layout/         # Navbar, ThemeProvider
            │   ├── dashboard/      # ProblemFeed, ProblemCard, FilterSidebar, TrendingTopics
            │   ├── analytics/      # VolumeLineChart, CategoryBarChart, SentimentPieChart, ActivityHeatmap
            │   ├── problems/       # SolutionTabs, PrintButton
            │   └── ui/             # Radix-based primitives (Button, Card, Toast, etc.)
            ├── lib/
            │   ├── api.ts          # Axios client + all API functions
            │   └── utils.ts        # cn() helper (clsx + tailwind-merge)
            ├── store/
            │   ├── authStore.ts    # Zustand auth state
            │   └── filterStore.ts  # Zustand filter state (sidebar)
            └── types/
                └── index.ts        # All TypeScript interfaces
```

---

## 4. Backend Architecture

### 4.1 Configuration & Settings

**File:** `app/core/config.py`

All configuration is read from environment variables via Pydantic `BaseSettings`. The `.env` file is loaded automatically in development. In production (Railway), environment variables are injected directly.

```python
class Settings(BaseSettings):
    DATABASE_URL: str          # Neon asyncpg connection string
    REDIS_URL: str             # Upstash Redis URL
    SECRET_KEY: str            # JWT signing key (min 16 chars)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USER_AGENT: str

    GEMINI_API_KEY: str
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    SENTRY_DSN: str = ""
    CORS_ORIGINS: List[str]
    ENVIRONMENT: str = "development"
    INTERNAL_API_KEY: str      # For internal scraper trigger endpoints
```

A validator warns (but does not crash) if `SECRET_KEY` or `INTERNAL_API_KEY` are using insecure defaults. In production these must be replaced with randomly generated hex strings.

---

### 4.2 Database Layer

**File:** `app/core/database.py`

Two engines are created from the same `DATABASE_URL`:

**Async engine** (used by FastAPI request handlers):
- Driver: `asyncpg`
- `create_async_engine` with `pool_pre_ping=True`
- SSL is handled by stripping `?sslmode=require` from the URL and passing `ssl=True` in `connect_args` (asyncpg does not accept sslmode as a query parameter)

**Sync engine** (used by Celery workers):
- Driver: `psycopg2`
- The async URL's `postgresql+asyncpg://` prefix is replaced with `postgresql+psycopg2://`
- `pool_size=5`, `max_overflow=10`

Tables are created on startup via:
```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

The `get_db()` dependency provides a scoped `AsyncSession` to each FastAPI route, with automatic commit on success and rollback on exception.

---

### 4.3 Data Models

**File:** `app/models/problem.py`

Seven SQLAlchemy models, all using the `Mapped[]` typed annotation style:

#### Problem
The central table. Represents one scraped post.

| Column | Type | Notes |
|---|---|---|
| id | UUID string | Primary key |
| platform | string(32) | `reddit` or `hackernews` |
| title | string(512) | Post title |
| body | text | Post body / self-text |
| url | string(1024) | Unique source URL |
| source_id | string(128) | Platform's native ID |
| author_handle | string(128) | Username |
| upvotes | int | Score / upvote count |
| comment_count | int | |
| subreddit | string(128) | Reddit subreddit name |
| category | string(64) | NLP-assigned: Technology, Health, etc. |
| sentiment | string(32) | `urgent`, `frustrated`, `curious`, `neutral` |
| summary | text | 2-sentence NLP summary |
| is_problem | bool | NLP classification result |
| confidence_score | float | 0.0–1.0 NLP confidence |
| is_active | bool | Soft-delete flag |
| created_at | timestamp | |
| updated_at | timestamp | Auto-updated |
| scraped_at | timestamp | When the scraper ingested it |

Unique constraint: `(source_id, platform)` — prevents duplicate scraping.

#### Solution
AI-generated solutions for a Problem. One row per provider per problem.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| problem_id | UUID | FK → problems.id (CASCADE) |
| provider | string(32) | `gemini`, `openai`, `claude` |
| solution_text | text | The AI-generated answer |
| model_name | string(64) | e.g. `gemini-2.0-flash` |
| rating | int | Net vote score |
| generated_at | timestamp | |
| is_active | bool | |

#### Category
Lookup table for the 9 categories used in filtering.

| Column | Type | Notes |
|---|---|---|
| id | UUID | |
| name | string(64) | e.g. `Technology` |
| slug | string(64) | e.g. `technology` |
| description | text | |

The 9 categories: Technology, Health, Finance, Relationships, Productivity, Travel, Education, Career, Other.

#### User
Registered users who can bookmark and vote.

| Column | Type | Notes |
|---|---|---|
| id | UUID | |
| email | string(255) | Unique |
| name | string(128) | |
| hashed_password | string(255) | Null for Google OAuth users |
| auth_provider | string(32) | `email` or `google` |
| is_active | bool | |
| created_at | timestamp | |

#### Bookmark
Many-to-many between User and Problem. Unique constraint on `(user_id, problem_id)`.

#### Vote
User votes on Solutions. `vote_type` is `+1` or `-1`. Unique constraint on `(user_id, solution_id)`.

#### ProblemClick
Analytics table. One row per click event on a problem card. Used to compute trending topics.

---

### 4.4 Authentication System

**File:** `app/core/security.py`

**JWT-based authentication** using HS256 algorithm.

- **Password hashing**: `bcrypt` with salt via `bcrypt.hashpw()`
- **Token creation**: `PyJWT` encodes `{sub: user_id, exp: ..., iat: ...}`
- **Token verification**: Validates signature, checks `exp`, `sub`, `iat` are present
- **Token revocation**: On logout, the token is added to a Redis denylist (`revoked:{token_prefix}`) with TTL equal to the token's remaining lifetime. Every authenticated request checks this denylist.
- **Optional auth**: `get_optional_user()` returns `None` if no token is present, used for routes that work for both logged-in and anonymous users

**Auth endpoints** (`app/api/v1/auth.py`):

| Method | Path | Description | Rate limit |
|---|---|---|---|
| POST | `/api/v1/auth/signup` | Create account (email+password) | 3/hour |
| POST | `/api/v1/auth/login` | Login, returns JWT | 5/minute |
| POST | `/api/v1/auth/oauth/google` | Exchange Google OAuth code for JWT | — |
| POST | `/api/v1/auth/logout` | Revoke token | — |
| GET | `/api/v1/auth/me` | Get current user info | — |

**Google OAuth flow:**
1. Frontend redirects user to Google
2. Google redirects back with a `code`
3. Frontend sends `code` + `redirect_uri` to `/api/v1/auth/oauth/google`
4. Backend exchanges the code with Google's token endpoint
5. Backend fetches user profile from Google
6. Backend creates or fetches the User row (`auth_provider = 'google'`)
7. Backend returns a JWT — same flow as email login from here

---

### 4.5 API Endpoints

**Base path:** `/api/v1/`

#### Problems (`/problems`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/problems` | Optional | List problems with filtering, pagination, sorting |
| GET | `/problems/{id}` | No | Get one problem with its solutions |
| GET | `/problems/trending` | No | Trending topics (24h / 7d / 30d) |
| POST | `/problems/{id}/solutions/generate` | Required | Trigger AI solution generation |
| GET | `/problems/{id}/solutions` | No | Get solutions for a problem |
| POST | `/problems/{id}/click` | No | Track click (analytics) |

**Filtering parameters for `GET /problems`:**
- `platform` — `reddit` or `hackernews`
- `category` — any of the 9 categories
- `sentiment` — `urgent`, `frustrated`, `curious`, `neutral`
- `date_from`, `date_to` — ISO date strings
- `has_solution` — boolean
- `search` — full-text search on title + body (ILIKE)
- `sort_by` — `upvotes`, `comments`, or default (newest first)
- `page`, `per_page` — pagination

Responses are cached in Redis for 120 seconds using an MD5 hash of all parameters as the cache key.

#### Solutions (`/solutions`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/solutions/{id}/vote` | Required | Upvote or downvote a solution |

#### Analytics (`/analytics`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/analytics/summary` | No | Total counts, category distribution, sentiment breakdown |
| GET | `/analytics/dashboard` | No | Time series data for charts |

#### Categories (`/categories`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/categories` | No | List all 9 categories |

#### Bookmarks (`/bookmarks`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/bookmarks` | Required | List user's bookmarks |
| POST | `/bookmarks/` | Required | Add bookmark |
| DELETE | `/bookmarks/{problem_id}` | Required | Remove bookmark |

#### Internal (`/internal`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/internal/scrape/reddit` | `X-Internal-Key` header | Trigger Reddit scrape task |
| POST | `/internal/scrape/hn` | `X-Internal-Key` header | Trigger HN scrape task |
| POST | `/internal/classify` | `X-Internal-Key` header | Trigger classification task |

These endpoints require the `INTERNAL_API_KEY` in the `X-Internal-Key` header. They are used for manual triggering and monitoring — not exposed publicly.

#### Health
```
GET /health  →  {"status": "ok", "version": "1.0.1"}
```

---

### 4.6 Scrapers

#### Reddit Scraper (`app/scrapers/reddit_scraper.py`)

Uses **PRAW** (Python Reddit API Wrapper) in read-only mode. No login credentials required — only OAuth2 app credentials (client ID + secret).

**Targets:**

Subreddits (100 posts each, newest first):
- r/Advice
- r/AskReddit
- r/TrueOffMyChest
- r/Problems
- r/Help

Keywords (50 posts each, Reddit-wide search):
- "how do I fix"
- "need help with"
- "frustrated by"
- "problem with"
- "anyone know how"

**Per post, extracted fields:** `source_id`, `title`, `body`, `author`, `upvotes`, `comment_count`, `subreddit`, `created_at`, `url`, `platform`, and the top 5 comments.

**Deduplication:** `BaseScraper._save_posts()` uses `ON CONFLICT DO NOTHING` on the `(source_id, platform)` unique constraint. Returns counts of `inserted` vs `skipped`.

**One run yields approximately 737 posts** (500 from subreddits + 237 unique from keywords after deduplication).

#### HN Scraper (`app/scrapers/hn_scraper.py`)

Uses the **HN Algolia API** (`hn.algolia.com/api/v1/search`). No authentication required.

Same 5 keywords, 50 posts each. Filters to `ask_hn` and `show_hn` post types.

**One run yields approximately 250 posts** (all keywords combined, before deduplication against existing DB rows).

---

### 4.7 NLP Classifier

**File:** `app/nlp/classifier.py`

Uses **Gemini 1.5 Flash** in zero-shot mode to classify scraped posts.

**Per post, the classifier determines:**
- `is_problem`: bool — is this post describing a real problem?
- `confidence`: float 0–1 — how confident is the model?
- `category`: one of 9 categories (or empty string)
- `sentiment`: `urgent`, `frustrated`, `curious`, `neutral`
- `summary`: 2-sentence problem summary

**Skips posts with body shorter than 20 characters** (cost control).

**Flags `review_required`** if confidence < 0.65.

**Batch processing:** Groups posts into batches of 10 with a 1-second sleep between batches (rate control).

**Retry policy:** `tenacity` exponential backoff, up to 3 attempts per API call (2–30 second wait).

**Prompt structure:** A fixed template asking Gemini to respond with a strict JSON schema. The parser strips accidental markdown code fences (` ```json `) that Gemini occasionally wraps its output in.

---

### 4.8 AI Solution Orchestrator

**File:** `app/ai/solution_orchestrator.py`

Generates solutions from all three AI providers for a given problem. Runs synchronously (used by Celery workers and called via `asyncio.to_thread()` from FastAPI).

**Three adapters:**
- `GeminiAdapter` — uses `gemini-2.0-flash`
- `OpenAIAdapter` — uses `gpt-4o-mini`
- `ClaudeAdapter` — uses `claude-haiku-4-5-20251001`

**Generation workflow per provider:**

1. **Cache check** — Redis key `solution:{problem_id}:{provider}`, TTL 24 hours. If cached, return immediately.
2. **Circuit breaker check** — If the provider has tripped its circuit breaker, skip it.
3. **Generate** — Call the provider adapter.
4. **On success** — Store in Redis cache AND upsert into the `solutions` database table.
5. **On failure** — Increment the rolling error counter. If 3 errors occur within 5 minutes, trip the circuit breaker (disables provider for 5 minutes).

**Redis keys:**
- `solution:{problem_id}:{provider}` — Cached solution text (TTL 24h)
- `cb:{provider}:open` — Circuit breaker open flag (TTL 5min)
- `cb:{provider}:errors` — Rolling error counter (TTL 5min)

The solution prompt is built from the problem's `title`, `body`, `category`, and `sentiment`. Each adapter formats the prompt for its specific model.

---

### 4.9 Celery Task Queue

**Config file:** `app/core/celery_app.py`

Celery handles all background processing. The broker and result backend are both Upstash Redis.

**SSL handling for Upstash (TLS):**

Upstash provides a `rediss://` URL (TLS). Celery's broker requires the plain `redis://` URL when SSL options are passed as a dict:

```python
_celery_redis_url = settings.REDIS_URL.replace("rediss://", "redis://", 1)
_is_tls = settings.REDIS_URL.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _is_tls else None

celery_app = Celery(
    "solvora",
    broker=_celery_redis_url,
    backend="cache+memory://",   # In-memory — tasks are fire-and-forget
    include=["app.nlp.tasks", "app.ai.tasks"],
)
celery_app.conf.update(
    broker_use_ssl=_ssl_opts,
    ...
)
```

**Why `cache+memory://` backend?** Celery's Redis result backend also has SSL complications with Upstash. Since Solvora's tasks are fire-and-forget (results are persisted to PostgreSQL directly, not via Celery results), using an in-memory backend avoids the issue entirely.

**Registered tasks:**
- `scrapers.run_hn_scrape` — Scrape Hacker News
- `scrapers.run_reddit_scrape` — Scrape Reddit
- `nlp.classify_new_posts` — Classify unclassified posts in DB
- `ai.batch_generate_for_viral_posts` — Generate solutions for high-engagement problems
- `ai.generate_solutions` — Generate solutions for a specific problem

**Beat schedule (cron jobs):**

| Task | Schedule | Purpose |
|---|---|---|
| `scrapers.run_hn_scrape` | Every 15 minutes | Fetch new HN posts |
| `scrapers.run_reddit_scrape` | Every 30 minutes | Fetch new Reddit posts |
| `nlp.classify_new_posts` | Every 30 minutes | Classify accumulated unclassified posts |
| `ai.batch_generate_for_viral_posts` | Every hour (on the hour) | Generate solutions for popular problems |

---

### 4.10 Redis Caching & Rate Limiting

**File:** `app/core/redis_client.py`

The Redis client uses `aioredis.from_url()` with the raw `REDIS_URL`. With `redis-py` 5.x, `rediss://` URLs are handled natively — SSL is established automatically without additional configuration.

**Cache helper functions:**
- `cache_get(key)` — Returns deserialized Python object or `None`
- `cache_set(key, value, ttl=300)` — Serializes to JSON and stores with TTL

**Rate limiting** (`app/core/limiter.py`):

Uses `slowapi` (a FastAPI-compatible port of Flask-Limiter). The limiter is attached to `app.state.limiter` and applied per-route with `@limiter.limit("N/period")` decorators.

Applied limits:
- `/auth/signup` — 3 requests per hour
- `/auth/login` — 5 requests per minute
- `/problems/{id}/click` — 30 requests per minute

---

### 4.11 Security Middleware

**File:** `app/main.py`

**SecurityHeadersMiddleware** (custom `BaseHTTPMiddleware`) adds:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=()`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (production only)

**CORS middleware** restricts origins to the list in `CORS_ORIGINS`.

**Docs disabled in production:** `/docs`, `/redoc`, `/openapi.json` all return 404 when `ENVIRONMENT=production`.

**Uvicorn proxy headers:** The production Docker command includes `--proxy-headers --forwarded-allow-ips='*'` so that Railway's TLS-terminating reverse proxy is trusted. Without this, redirect URLs generated by FastAPI use `http://` instead of `https://`.

---

## 5. Frontend Architecture

### 5.1 Pages & Routing

Uses Next.js 14 **App Router** (`/src/app/`).

| Route | Page | Description |
|---|---|---|
| `/` | `app/page.tsx` | Landing/marketing page |
| `/dashboard` | `app/dashboard/page.tsx` | Main problem feed |
| `/problems/[id]` | `app/problems/[id]/page.tsx` | Problem detail + AI solutions |
| `/analytics` | `app/analytics/page.tsx` | Charts and statistics |
| `/bookmarks` | `app/bookmarks/page.tsx` | User's saved problems |
| `/auth/login` | `app/auth/login/page.tsx` | Login form |
| `/auth/signup` | `app/auth/signup/page.tsx` | Sign-up form |

`app/providers.tsx` wraps the app with `SessionProvider` (NextAuth) and `QueryClientProvider` (React Query).

---

### 5.2 Components

#### Dashboard
- **`ProblemFeed`** — Main feed. Uses React Query to fetch paginated problems. Handles loading skeletons, empty states, and infinite pagination.
- **`ProblemCard`** — One card per problem. Shows title, platform badge, category, sentiment, upvotes, comment count, solution count. Clicking tracks the click and navigates to the detail page.
- **`FilterSidebar`** — Left sidebar with filters: platform, category, sentiment, sort order, date range, has-solution toggle. State managed by `filterStore` (Zustand).
- **`TrendingTopics`** — Small panel showing trending categories based on click activity.

#### Analytics
- **`VolumeLineChart`** — Problem volume over time using Recharts `LineChart`
- **`CategoryBarChart`** — Bar chart of problem count per category
- **`SentimentPieChart`** — Pie chart of sentiment distribution
- **`ActivityHeatmap`** — GitHub-style heatmap of daily scraping activity

#### Problems
- **`SolutionTabs`** — Tabbed interface showing Gemini / OpenAI / Claude solutions for a problem. Each tab has a "Generate" button that calls the backend.
- **`PrintButton`** — Triggers `window.print()` with print-optimized CSS

#### UI Primitives
All in `components/ui/`. Built on top of **Radix UI** unstyled primitives with Tailwind CSS styling, following the shadcn/ui pattern:
- `Button`, `Card`, `Badge`, `Avatar`, `Input`, `Label`
- `Dialog`, `DropdownMenu`, `Tabs`, `Switch`, `Separator`, `Skeleton`
- `SearchBar`, `Toast`

---

### 5.3 State Management

**Zustand stores:**

`authStore.ts` — Persisted to `sessionStorage`:
```typescript
{
  user: UserResponse | null,
  token: string | null,
  setAuth: (user, token) => void,
  clearAuth: () => void,
}
```

`filterStore.ts` — In-memory only:
```typescript
{
  platform: string | null,
  category: string | null,
  sentiment: string | null,
  sortBy: string,
  dateFrom: string | null,
  dateTo: string | null,
  hasSolution: boolean | null,
  search: string,
  // setters for each field
}
```

**React Query** handles all server state: problem lists, problem detail, categories, analytics, solutions. It provides automatic caching, background refetching, and loading/error states.

---

### 5.4 API Client

**File:** `src/lib/api.ts`

A single Axios instance configured with:
- `baseURL`: `NEXT_PUBLIC_API_URL` (env var) or `http://localhost:8000/api/v1`
- `timeout`: 15 seconds
- `Content-Type: application/json`

**Request interceptor:** Reads the JWT from `sessionStorage` (via `authStore`) and attaches it as `Authorization: Bearer {token}`.

**Response interceptor:** On 401, clears the stored token and redirects to `/auth/login`.

Exported functions map one-to-one to backend endpoints:
`getProblems`, `getProblem`, `getTrending`, `getSolutions`, `generateSolutions`, `submitVote`, `getAnalytics`, `getCategories`, `login`, `signup`, `addBookmark`, `removeBookmark`, `getBookmarks`, `trackProblemClick`, `getDashboardAnalytics`.

---

## 6. Data Pipeline (End-to-End Flow)

```
[Celery Beat — every 30min]
        │
        ▼
[Reddit Scraper / HN Scraper]
  - Connects to Reddit (PRAW) or HN Algolia API
  - Fetches new posts matching target subreddits/keywords
  - Deduplicates via ON CONFLICT DO NOTHING
  - Inserts into problems table
        │
        ▼
[Celery Beat — every 30min]
        │
        ▼
[NLP Classifier — classify_new_posts task]
  - Fetches unclassified problems (is_problem IS NULL or category IS NULL)
  - For each post:
      → Sends title + body to Gemini 1.5 Flash
      → Gemini returns JSON: {is_problem, confidence, category, sentiment, summary}
  - Updates problems table with classification results
        │
        ▼
[Celery Beat — every 1 hour]
        │
        ▼
[AI Solution Orchestrator — batch_generate_for_viral_posts task]
  - Queries for problems with is_problem=True and upvotes > threshold
  - For each viral problem, calls SolutionOrchestrator.generate_for_problem()
  - SolutionOrchestrator:
      1. Checks Redis cache (solution:{problem_id}:{provider})
      2. Checks circuit breaker (cb:{provider}:open)
      3. Calls Gemini / OpenAI / Claude adapter
      4. On success: stores in Redis + upserts in solutions table
      5. On failure: increments error counter, trips circuit breaker at threshold 3
        │
        ▼
[User visits Solvora dashboard]
  - Next.js frontend calls GET /api/v1/problems
  - FastAPI checks Redis cache first (key = MD5 hash of filter params)
  - If cached: returns immediately
  - If not: queries PostgreSQL, serializes, caches for 120s, returns
        │
        ▼
[User clicks problem card]
  - Frontend calls POST /api/v1/problems/{id}/click (tracked)
  - Frontend navigates to /problems/{id}
  - Detail page shows problem + existing solutions
  - User can click "Generate" to trigger on-demand AI solution generation
  - On-demand generation runs in asyncio.to_thread() (no Celery needed for single problem)
        │
        ▼
[User votes on a solution]
  - POST /api/v1/solutions/{id}/vote
  - Updates votes table, recalculates solution.rating
```

---

## 7. Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop (for local PostgreSQL + Redis)

### Step 1: Clone the repository

```bash
git clone https://github.com/chakravarthi-giduthuri/solvora.git
cd solvora
```

### Step 2: Start local services

```bash
docker compose -f config/docker-compose.yml up -d db redis
```

This starts PostgreSQL on port 5432 and Redis on port 6379.

### Step 3: Backend setup

```bash
cd src/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env template
cp .env.example .env
# Edit .env with your API keys
```

Minimum required values in `.env` for local dev:
```env
DATABASE_URL=postgresql+asyncpg://solvora:solvora_dev_password@localhost:5432/solvora
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=any-random-32-char-string-for-dev
INTERNAL_API_KEY=dev-internal-key
GEMINI_API_KEY=your-key         # needed for NLP classification
REDDIT_CLIENT_ID=your-id        # needed for Reddit scraping
REDDIT_CLIENT_SECRET=your-secret
REDDIT_USER_AGENT=Solvora/1.0
```

### Step 4: Start the backend

```bash
# Terminal 1: FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker
celery -A app.core.celery_app worker --loglevel=info -c 2

# Terminal 3: Celery beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info
```

The API is now available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Step 5: Seed categories

```bash
python scripts/seed_categories.py
```

This inserts the 9 categories into the `categories` table.

### Step 6: Frontend setup

```bash
cd src/frontend

npm install

cp .env.example .env.local
# Edit .env.local:
```

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXTAUTH_SECRET=any-local-secret
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

```bash
npm run dev
```

Frontend is available at `http://localhost:3000`.

---

## 8. Docker & Docker Compose

**File:** `config/docker-compose.yml`

Five services:

| Service | Port | Image |
|---|---|---|
| `db` | 5432 | postgres:16-alpine |
| `redis` | 6379 | redis:7-alpine |
| `backend` | 8000 | Built from `src/backend/Dockerfile` |
| `celery_worker` | — | Same Dockerfile, override CMD |
| `celery_beat` | — | Same Dockerfile, override CMD |
| `frontend` | 3000 | Built from `src/frontend/Dockerfile` |

The backend and Celery services share the same Docker image, only differing in the startup command:
- `backend`: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- `celery_worker`: `celery -A app.celery_app worker --loglevel=info -c 4`
- `celery_beat`: `celery -A app.celery_app beat --loglevel=info`

Health checks on `db` and `redis` ensure dependent services wait for them to be ready before starting.

**Backend Dockerfile** (`src/backend/Dockerfile`) — multi-stage:
1. **Stage 1 (builder)**: `python:3.11-slim`, installs gcc + libpq-dev, runs `pip install --prefix=/install`
2. **Stage 2 (runtime)**: Fresh `python:3.11-slim`, copies only built packages from Stage 1, creates a non-root `appuser`, copies application code

Final CMD:
```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
```

`${PORT:-8000}` — defaults to 8000 locally, picks up Railway's injected `$PORT` in production.
`--proxy-headers` — trusts Railway's TLS-terminating reverse proxy, ensuring HTTPS redirects are generated correctly.

**`.railwayignore`** (`src/backend/.railwayignore`):
```
venv/
__pycache__/
*.pyc
*.pyo
celerybeat-schedule.db
tests/
```
This prevents the 333MB `venv/` directory from being uploaded to Railway, which would cause TLS `BadRecordMac` errors due to the massive payload size.

---

## 9. Cloud Services Setup

### 9.1 Neon (PostgreSQL)

1. Create a free account at [neon.tech](https://neon.tech)
2. Create a new project → Region: choose closest to Railway deployment
3. From the Connection Details panel, copy the **asyncpg** connection string

Format:
```
postgresql+asyncpg://user:password@ep-xxx.region.neon.tech/dbname?sslmode=require
```

The `?sslmode=require` is stripped by `database.py` and converted to `ssl=True` in `connect_args` (asyncpg-compatible format).

Tables are created automatically on first startup via `Base.metadata.create_all`.

### 9.2 Upstash (Redis)

1. Create a free account at [upstash.com](https://upstash.com)
2. Create a new Database → Type: Redis → Region: choose closest to Railway
3. Enable TLS (enabled by default)
4. Copy the **Redis URL** from the database details

Format:
```
rediss://default:password@main-falcon-xxxxx.upstash.io:6379
```

Note: `rediss://` (double-s) indicates TLS. Celery and redis-py handle this differently:
- **redis-py** (used by FastAPI cache): handles `rediss://` natively in v5.x
- **Celery**: requires URL to be `redis://` + SSL options dict → handled in `celery_app.py`

### 9.3 Reddit API

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click "create another app..."
3. Type: **script**
4. Name: Solvora (or any name)
5. Redirect URI: `http://localhost:8080` (not used for read-only scraping)
6. Copy `client_id` (shown under the app name) and `client_secret`

Set in `.env`:
```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=Solvora/1.0 by u/yourusername
```

PRAW uses OAuth2 client credentials flow in read-only mode — no user login required.

### 9.4 Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select existing)
3. Go to **APIs & Services → OAuth consent screen**
   - User Type: External
   - Fill in app name, support email, developer email
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs — add both:
     - `http://localhost:3000/api/auth/callback/google` (local dev / frontend NextAuth)
     - `https://your-vercel-app.vercel.app/api/auth/callback/google` (production frontend)
5. Copy `Client ID` and `Client Secret`

Set in both backend `.env` and frontend `.env.local`:
```env
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

### 9.5 AI APIs

**Google Gemini:**
- [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) → Create API Key
- Set `GEMINI_API_KEY`

**OpenAI:**
- [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → Create new secret key
- Set `OPENAI_API_KEY`

**Anthropic (Claude):**
- [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) → Create Key
- Set `ANTHROPIC_API_KEY`

Gemini is also used for NLP classification (not just solution generation), so it is the most critical key. Without it, posts will not be classified.

---

## 10. Deployment — Backend (Railway)

Railway hosts three separate services from the same GitHub repository, all using the same `src/backend/Dockerfile`.

### 10.1 API Service

**Steps:**
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub Repo
2. Select `chakravarthi-giduthuri/solvora`
3. Set **Root Directory** to `src/backend`
4. Railway auto-detects the Dockerfile and builds it

**Start command** (in Dockerfile CMD, not overridden):
```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
```

**Environment variables** (set in Railway dashboard → Variables):
```env
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
REDIS_URL=rediss://default:pass@main-falcon-xxxxx.upstash.io:6379
SECRET_KEY=<64-char hex: python -c "import secrets; print(secrets.token_hex(32))">
INTERNAL_API_KEY=<64-char hex>
ENVIRONMENT=production
CORS_ORIGINS=["https://your-app.vercel.app"]
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=Solvora/1.0
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SENTRY_DSN=...   (optional)
```

After first deploy, verify:
```bash
curl https://your-railway-url.up.railway.app/health
# Expected: {"status":"ok","version":"1.0.1"}
```

### 10.2 Celery Worker Service

1. In the same Railway project, click **+ Add Service → GitHub Repo**
2. Select same repo, set **Root Directory** to `src/backend`
3. In Service Settings → **Custom Start Command**:
   ```
   celery -A app.core.celery_app worker --loglevel=info -c 4
   ```
4. Set all the same environment variables as the API service (DATABASE_URL, REDIS_URL, SECRET_KEY, GEMINI_API_KEY, REDDIT_CLIENT_ID, etc.)

The worker registers these task names:
- `scrapers.run_hn_scrape`
- `scrapers.run_reddit_scrape`
- `nlp.classify_new_posts`
- `ai.batch_generate_for_viral_posts`
- `ai.generate_solutions`

Verify the worker is running by checking Railway logs — you should see:
```
celery@hostname v5.3.6 ready.
```

### 10.3 Celery Beat Service

1. Add another service, same repo + same root directory
2. **Custom Start Command**:
   ```
   celery -A app.core.celery_app beat --loglevel=info
   ```
3. Same environment variables

Beat only needs `REDIS_URL` to queue tasks, but it's safest to give it all variables.

**Note:** Only run ONE instance of Celery beat at a time. Multiple beat instances will queue duplicate tasks.

---

## 11. Deployment — Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
2. Select `chakravarthi-giduthuri/solvora`
3. Set **Root Directory** to `src/frontend`
4. Framework preset: **Next.js** (auto-detected)

**Environment variables** (set in Vercel Project Settings → Environment Variables):
```env
NEXT_PUBLIC_API_URL=https://your-railway-api.up.railway.app/api/v1
NEXTAUTH_SECRET=<32-char hex: openssl rand -hex 32>
NEXTAUTH_URL=https://your-vercel-app.vercel.app
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

After deploying, copy the Vercel URL and:
1. Update `CORS_ORIGINS` in the Railway API service to include the Vercel URL
2. Add the Vercel URL to the Google OAuth authorized redirect URIs

**Auto-deploy:** Both Railway and Vercel are connected to the GitHub repo. Every push to `main` triggers an automatic redeploy of both services.

---

## 12. Environment Variables Reference

### Backend (Railway / `.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Neon asyncpg connection string |
| `REDIS_URL` | Yes | Upstash Redis URL (`rediss://`) |
| `SECRET_KEY` | Yes | JWT signing key — min 32 chars, random hex |
| `INTERNAL_API_KEY` | Yes | Auth key for `/internal/*` endpoints |
| `ENVIRONMENT` | Yes | `production` or `development` |
| `CORS_ORIGINS` | Yes | JSON array: `["https://your-app.vercel.app"]` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Default: 30 |
| `REDDIT_CLIENT_ID` | Yes | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Yes | Reddit app client secret |
| `REDDIT_USER_AGENT` | Yes | e.g. `Solvora/1.0` |
| `GEMINI_API_KEY` | Yes | Google Gemini API key (NLP + solutions) |
| `OPENAI_API_KEY` | No | OpenAI API key (solutions only) |
| `ANTHROPIC_API_KEY` | No | Anthropic API key (solutions only) |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `SENTRY_DSN` | No | Sentry error tracking DSN |

### Frontend (Vercel / `.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend base URL + `/api/v1` |
| `NEXTAUTH_SECRET` | Yes | NextAuth signing secret — random hex |
| `NEXTAUTH_URL` | Yes | Full frontend URL (no trailing slash) |
| `GOOGLE_CLIENT_ID` | Yes | Same as backend |
| `GOOGLE_CLIENT_SECRET` | Yes | Same as backend |

---

## 13. Problems Fixed During Deployment

This section documents every significant issue encountered during the deployment process and how it was resolved. These are real lessons that apply to anyone deploying a similar stack.

---

### Issue 1: `authOptions` exported from Next.js route file

**Error:** TypeScript build error — Next.js App Router route files only allow HTTP method exports (`GET`, `POST`, etc.). Exporting `authOptions` caused a build failure.

**Fix:** Removed the `export` keyword from `authOptions` in `src/app/api/auth/[...nextauth]/route.ts`:
```ts
// Before (broken)
export const authOptions = { ... }

// After (correct)
const authOptions = { ... }
```

---

### Issue 2: TypeScript interface conflict in `toast.tsx`

**Error:** `ToastData` interface extended `ToastProps` and re-declared `title` as `ReactNode` (which includes `null`), but the parent `ToastProps.title` was `string | undefined`. TypeScript rejects narrowing via extension.

**Fix:** Used `Omit` to exclude the conflicting fields:
```ts
// Before (broken)
interface ToastData extends ToastProps { title: ReactNode; ... }

// After (correct)
interface ToastData extends Omit<ToastProps, 'title' | 'description' | 'action'> {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}
```

---

### Issue 3: Missing `bcrypt` module on Railway

**Error:** `ModuleNotFoundError: No module named 'bcrypt'` — the password hashing dependency was missing from `requirements.txt`.

**Fix:** Added `bcrypt==4.1.3` to `requirements.txt`.

---

### Issue 4: Railway 502 — hardcoded port

**Error:** The backend returned 502 immediately after deploying. Railway injects the port via `$PORT` environment variable, but the Dockerfile was hardcoding port 8000.

**Fix:** Changed the `CMD` in `Dockerfile`:
```dockerfile
# Before
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# After
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
```

---

### Issue 5: 307 redirect using `http://` instead of `https://`

**Error:** FastAPI was generating `http://` redirect URLs when Railway's load balancer was terminating TLS. This caused an infinite redirect loop for trailing-slash URLs.

**Fix:** Added `--proxy-headers --forwarded-allow-ips='*'` to the uvicorn command. This tells uvicorn to trust the `X-Forwarded-Proto: https` header from Railway's proxy, so redirects use `https://`.

---

### Issue 6: 333MB `venv/` being uploaded to Railway

**Error:** Railway uploads included the `venv/` folder (333MB), causing TLS `BadRecordMac` errors during upload — the payload was too large for the TLS connection to handle.

**Fix:** Created `src/backend/.railwayignore`:
```
venv/
__pycache__/
*.pyc
*.pyo
celerybeat-schedule.db
tests/
```

---

### Issue 7: Celery Redis SSL certificate error

**Error:** `E_REDIS_SSL_CERT_REQS_MISSING_INVALID` — Celery's Redis broker integration requires `ssl_cert_reqs` to be specified when using TLS, but it doesn't work directly with `rediss://` URLs.

**Fix:** In `app/core/celery_app.py`:
```python
import ssl
_celery_redis_url = settings.REDIS_URL.replace("rediss://", "redis://", 1)
_is_tls = settings.REDIS_URL.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _is_tls else None

celery_app = Celery(
    "solvora",
    broker=_celery_redis_url,         # redis:// (not rediss://)
    backend="cache+memory://",         # avoids Redis backend SSL complications
    ...
)
celery_app.conf.update(
    broker_use_ssl=_ssl_opts,          # pass SSL options separately
    ...
)
```

---

### Issue 8: `null://` is not a valid Celery backend

**Error:** `kombu.exceptions.EncodeError: null:// not found` — `null://` was tried as a "discard results" backend but is not valid in Celery 5.x.

**Fix:** Used `cache+memory://` instead, which stores results in worker process memory (effectively discarded when worker restarts, which is acceptable since results are persisted to PostgreSQL directly).

---

### Issue 9: Wrong Celery config file being modified

**Problem:** The project has two celery config files:
- `app/celery_app.py` — legacy, unused
- `app/core/celery_app.py` — the real one, imported by `app.nlp.tasks` and `app.ai.tasks`

Initial fixes were applied to the wrong file.

**Fix:** Always modify `app/core/celery_app.py`. The task modules (`app.nlp.tasks`, `app.ai.tasks`) import `celery_app` from `app.core.celery_app`.

---

### Issue 10: Categories table was empty

**Symptom:** The dashboard category filter showed nothing. The `/api/v1/categories` endpoint returned `[]`.

**Cause:** The `Category` model defines the table schema, but no seed data was inserted. The NLP classifier writes category names directly into `problems.category` as a string — it does not use foreign keys to the `categories` table. The `categories` table is a separate lookup table for the frontend filter UI.

**Fix:** Ran the seed script against the production database:
```bash
railway run python3 scripts/seed_categories.py
```

This inserted 9 rows into the `categories` table.

---

### Issue 11: Railway Celery worker missing environment variables

**Error:** `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from string 'your-super-secret-key-change-in-production'` — the worker was using `SECRET_KEY` as the `DATABASE_URL` because `DATABASE_URL` was not set.

**Cause:** Railway's "shared variables" feature between services didn't copy variables correctly. The worker had `SECRET_KEY` but not `DATABASE_URL`.

**Fix:** Set all environment variables explicitly on each service using the Railway dashboard's "Raw Editor" (paste the full env block as key=value pairs). Do not rely on shared variables between services.

---

### Issue 12: `CORS_ORIGINS` JSON array rejected by Railway CLI

**Error:** `Invalid variable format` when trying to set `CORS_ORIGINS=["https://app.vercel.app"]` via `railway variable set`.

**Cause:** Railway CLI parses the value incorrectly when it contains brackets and quotes.

**Fix:** Set this variable through the Railway dashboard UI or Raw Editor, not via CLI.

---

### Issue 13: `gh` CLI config permission error

**Error:** `mkdir /Users/chakravarthigiduthuri/.config/gh: permission denied`

**Fix:**
```bash
sudo mkdir -p /Users/chakravarthigiduthuri/.config/gh
sudo chown -R chakravarthigiduthuri /Users/chakravarthigiduthuri/.config
```

---

## 14. Post-Deployment Verification

After deploying all services, run through this checklist:

### Backend
```bash
# Health check
curl https://your-api.up.railway.app/health
# Expected: {"status":"ok","version":"1.0.1"}

# Check security headers
curl -I https://your-api.up.railway.app/health
# Expected headers: x-frame-options: DENY, x-content-type-options: nosniff

# Confirm /docs is disabled in production
curl -s -o /dev/null -w "%{http_code}" https://your-api.up.railway.app/docs
# Expected: 404

# Check categories are seeded
curl https://your-api.up.railway.app/api/v1/categories | python3 -m json.tool
# Expected: array of 9 category objects

# Check problems are loading
curl "https://your-api.up.railway.app/api/v1/problems?per_page=5" | python3 -m json.tool
# Expected: {"items": [...], "total": 964, ...}
```

### Frontend
- Visit `https://your-app.vercel.app` — landing page loads
- Navigate to `/dashboard` — problem feed loads with problems
- Category filter sidebar shows all 9 categories
- Email signup creates account and redirects to dashboard
- Google OAuth login completes and returns to dashboard
- Clicking a problem card shows the detail page
- Clicking "Generate" on solution tab generates AI response
- Bookmarking a problem works (requires login)

### Celery
Check Railway worker logs for:
```
celery@hostname v5.3.6 ready.
Task scrapers.run_hn_scrape[...] received
Task scrapers.run_hn_scrape[...] succeeded
```

---

## 15. Ongoing Automated Pipeline

Once all services are deployed and running, the system is fully self-sustaining:

### Scraping
- Every **15 minutes**: HN scraper fetches ~250 posts, inserts new ones (deduplication via unique constraint)
- Every **30 minutes**: Reddit scraper fetches ~737 posts, inserts new ones

### Classification
- Every **30 minutes**: NLP classifier picks up all unclassified posts (those without `category` or `is_problem` set) and runs them through Gemini 1.5 Flash in batches of 10

### AI Solutions
- Every **hour**: The orchestrator finds high-engagement problems (`is_problem=True`, `upvotes > threshold`) and generates solutions from Gemini, OpenAI, and Claude if not already cached

### Monitoring
- Railway dashboard shows real-time logs for all three services
- Celery logs show task received / succeeded / failed events with timing
- Sentry (if configured) captures runtime errors with full stack traces
- The `/health` endpoint provides a simple uptime check for external monitoring tools

### Data growth
The database grows continuously as new problems are scraped. The deduplication constraint ensures each post is stored exactly once regardless of how many times it appears in scraper results. Over time, the `problems` table will contain thousands of classified problems with AI solutions.

### Redeploying
- Any push to the `main` branch of `chakravarthi-giduthuri/solvora` triggers:
  - Automatic redeploy of the Railway API service
  - Automatic redeploy of the Railway Celery worker service
  - Automatic redeploy of the Railway Celery beat service
  - Automatic redeploy of the Vercel frontend
- Database schema changes require running `alembic upgrade head` via Railway's shell after deploying
