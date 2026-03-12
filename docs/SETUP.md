# ProbSolve AI — Setup Guide

**Version:** 1.0
**Date:** March 2026

---

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| Docker Desktop | latest | https://docker.com |

---

## Step 1 — Get Your API Keys

### Reddit API (free)
1. Go to https://www.reddit.com/prefs/apps
2. Click **"create another app"** → choose **script**
3. Fill in any name and redirect URI (`http://localhost:8080`)
4. Copy: **client_id** (under the app name) and **secret**

### Google Gemini (free — 1M tokens/day)
1. Go to https://aistudio.google.com
2. Click **"Get API Key"** → Create API key
3. Copy the key

### OpenAI (paid — use $5 signup credit)
1. Go to https://platform.openai.com/api-keys
2. Create new secret key → copy it

### Anthropic Claude (paid)
1. Go to https://console.anthropic.com
2. API Keys → Create Key → copy it

### Google OAuth (for "Login with Google")
1. Go to https://console.cloud.google.com
2. APIs & Services → Credentials → **Create OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Authorized redirect URIs: `http://localhost:3000/api/auth/callback/google`
5. Copy **Client ID** and **Client Secret**

---

## Step 2 — Configure Environment Files

Open a terminal and navigate to the project root:

```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S"
```

### Backend `.env`

```bash
cp src/backend/.env.example src/backend/.env
```

Open `src/backend/.env` and fill in your keys:

```env
# Database (local Docker Postgres)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/probsolveai

# Redis (local Docker)
REDIS_URL=redis://localhost:6379/0

# JWT — use any long random string
SECRET_KEY=replace-with-a-long-random-secret

# Reddit API
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USER_AGENT=ProbSolveAI/1.0

# AI APIs
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# App
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000"]
INTERNAL_API_KEY=dev-internal-key-123
```

### Frontend `.env.local`

```bash
cp src/frontend/.env.example src/frontend/.env.local
```

Open `src/frontend/.env.local` and fill in:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXTAUTH_SECRET=replace-with-a-long-random-secret
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

---

## Step 3 — Start Database & Redis

```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S"
docker compose -f config/docker-compose.yml up -d db redis
```

Wait ~10 seconds, then verify both are healthy:

```bash
docker compose -f config/docker-compose.yml ps
# db and redis should both show "healthy"
```

---

## Step 4 — Backend Setup

```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/backend"

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Mac / Linux
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Create database tables
python -c "
import asyncio
from app.core.database import engine, Base
from app.models.problem import Problem, Solution, Category, User, Bookmark, Vote
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created!')
asyncio.run(init())
"

# Seed categories
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S"
python scripts/seed_categories.py
```

---

## Step 5 — Run the Backend (3 terminals)

**Terminal 1 — FastAPI server:**
```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/backend"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Expected: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 — Celery worker** (scraper + AI jobs):
```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/backend"
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info -c 4
```

**Terminal 3 — Celery beat** (cron scheduler):
```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/backend"
source venv/bin/activate
celery -A app.celery_app beat --loglevel=info
```

---

## Step 6 — Run the Frontend

**Terminal 4:**
```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/frontend"
npm install
npm run dev
```
Expected: `ready started server on 0.0.0.0:3000`

---

## Step 7 — Verify Everything Works

| URL | Expected |
|-----|----------|
| http://localhost:3000 | ProbSolve AI dashboard |
| http://localhost:8000/docs | FastAPI Swagger UI |
| http://localhost:8000/health | `{"status":"ok","version":"1.0.0"}` |

Quick API checks:

```bash
# Categories (should return 15 seeded categories)
curl http://localhost:8000/api/v1/categories

# Problems feed (empty until scrapers run)
curl http://localhost:8000/api/v1/problems
```

---

## Step 8 — Populate Initial Data

Manually trigger the scrapers to get the first batch of posts:

```bash
# Trigger Reddit scrape
curl -X POST http://localhost:8000/api/v1/internal/scrape/reddit \
  -H "X-Internal-Api-Key: dev-internal-key-123"

# Trigger HN scrape
curl -X POST http://localhost:8000/api/v1/internal/scrape/hn \
  -H "X-Internal-Api-Key: dev-internal-key-123"
```

Watch **Terminal 2** (Celery worker) — posts will appear as they are scraped and classified. After ~2 minutes, refresh http://localhost:3000 to see the feed populated.

After the initial scrape, the schedulers take over automatically:
- Reddit: every 30 minutes
- Hacker News: every 15 minutes
- NLP classification: every 10 minutes

---

## Alternative: Run Everything with Docker

Skip Steps 3–6 and run the full stack in one command:

```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S"

# Copy env files first (Steps 2 still required)
docker compose -f config/docker-compose.yml up --build
```

This starts all 6 services: `db`, `redis`, `backend`, `celery_worker`, `celery_beat`, `frontend`.

---

## Running Tests

```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/backend"
source venv/bin/activate
pytest tests/ -v
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `connection refused` on port 5432 | Docker Desktop is not running — start it |
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate`, then `pip install -r requirements.txt` |
| `REDDIT_CLIENT_ID not set` | Check `src/backend/.env` is filled in correctly |
| Frontend shows blank page | Check browser console — likely `NEXT_PUBLIC_API_URL` is wrong or backend is not running |
| Celery worker crashes immediately | Make sure Redis is running: `docker compose -f config/docker-compose.yml ps` |
| `asyncpg` connection error | Ensure `DATABASE_URL` uses `postgresql+asyncpg://` not `postgresql://` |
| Google OAuth not working | Check redirect URI in Google Cloud Console matches exactly: `http://localhost:3000/api/auth/callback/google` |

---

## Project Structure Reference

```
project S/
├── src/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/v1/        # REST endpoints
│   │   │   ├── models/        # SQLAlchemy DB models
│   │   │   ├── schemas/       # Pydantic schemas
│   │   │   ├── scrapers/      # Reddit + HN scrapers
│   │   │   ├── nlp/           # NLP classifier (Gemini zero-shot)
│   │   │   ├── ai/            # Gemini / OpenAI / Claude adapters
│   │   │   ├── services/      # Auth + analytics services
│   │   │   └── core/          # Config, DB, Redis, security
│   │   ├── tests/             # pytest test suite
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── frontend/
│       ├── src/
│       │   ├── app/           # Next.js App Router pages
│       │   ├── components/    # React components
│       │   ├── store/         # Zustand state stores
│       │   ├── lib/           # API client + utilities
│       │   └── types/         # TypeScript interfaces
│       ├── package.json
│       └── .env.example
├── config/
│   ├── docker-compose.yml
│   └── koyeb.yml
├── scripts/
│   ├── setup.sh
│   ├── run_dev.sh
│   └── seed_categories.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── SETUP.md               ← you are here
└── .github/
    └── workflows/ci.yml
```
