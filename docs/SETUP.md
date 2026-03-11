# Solvora — Setup Guide

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
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/solvora

# Redis (local Docker)
REDIS_URL=redis://localhost:6379/0

# JWT — use any long random string
SECRET_KEY=replace-with-a-long-random-secret

# Reddit API
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USER_AGENT=Solvora/1.0

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
| http://localhost:3000 | Solvora dashboard |
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

---

## Part 2 — Production Deployment (Go Live)

This section covers deploying Solvora to the internet using the free-tier stack from the architecture:
- **Database** — Neon (PostgreSQL, serverless, never sleeps)
- **Redis** — Upstash (serverless, 10K commands/day free)
- **Backend** — Koyeb (always-on free tier, no sleep)
- **Frontend** — Vercel (zero-config Next.js hosting)
- **Scrapers** — GitHub Actions (cron, no server needed)

---

### Deploy Step 1 — Push Code to GitHub

Create a new GitHub repository and push the project:

```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S"
git init
git add .
git commit -m "Initial commit — Solvora"

# Create a repo on github.com named "solvora", then:
git remote add origin https://github.com/YOUR_USERNAME/solvora.git
git branch -M main
git push -u origin main
```

---

### Deploy Step 2 — Neon PostgreSQL (Production Database)

1. Go to https://neon.tech and sign up (free)
2. Click **"New Project"** → name it `solvora`
3. Select the region closest to your users
4. Once created, copy the **Connection string** — it looks like:
   ```
   postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/solvora?sslmode=require
   ```
5. For the backend, you need the **asyncpg** version — replace `postgresql://` with `postgresql+asyncpg://`:
   ```
   postgresql+asyncpg://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/solvora?sslmode=require
   ```
6. Save this — you'll use it as `DATABASE_URL` in all services below

**Run database migrations on Neon:**
```bash
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S/src/backend"
source venv/bin/activate

# Point to Neon (temporarily)
export DATABASE_URL="postgresql+asyncpg://your-neon-connection-string"

# Create tables
python -c "
import asyncio
from app.core.database import engine, Base
from app.models.problem import Problem, Solution, Category, User, Bookmark, Vote
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created on Neon!')
asyncio.run(init())
"

# Seed categories
cd "/Users/chakravarthigiduthuri/Desktop/Project C/project S"
DATABASE_URL="postgresql://your-neon-connection-string" python scripts/seed_categories.py
```

---

### Deploy Step 3 — Upstash Redis (Production Cache)

1. Go to https://upstash.com and sign up (free)
2. Click **"Create Database"** → name it `solvora-cache`
3. Select **Global** replication for lowest latency
4. Once created, go to **Details** tab
5. Copy the **Redis URL** — it looks like:
   ```
   rediss://default:password@global-xxx.upstash.io:6379
   ```
6. Save this — you'll use it as `REDIS_URL` below

---

### Deploy Step 4 — Koyeb (Production Backend)

Koyeb hosts the FastAPI server on an always-on free tier (no sleep).

1. Go to https://www.koyeb.com and sign up (free)
2. Click **"Create App"** → choose **"GitHub"**
3. Connect your GitHub account and select the `solvora` repository
4. Configure the service:
   - **Branch:** `main`
   - **Build command:** `pip install -r src/backend/requirements.txt`
   - **Run command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - **Working directory:** `src/backend`
   - **Port:** `8000`
   - **Instance type:** Free (Nano)

5. Add environment variables (click **"Environment variables"**):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | Your Neon asyncpg connection string |
   | `REDIS_URL` | Your Upstash Redis URL |
   | `SECRET_KEY` | A long random string (generate: `openssl rand -hex 32`) |
   | `REDDIT_CLIENT_ID` | Your Reddit client ID |
   | `REDDIT_CLIENT_SECRET` | Your Reddit client secret |
   | `REDDIT_USER_AGENT` | `Solvora/1.0` |
   | `GEMINI_API_KEY` | Your Gemini API key |
   | `OPENAI_API_KEY` | Your OpenAI API key |
   | `ANTHROPIC_API_KEY` | Your Anthropic API key |
   | `GOOGLE_CLIENT_ID` | Your Google OAuth client ID |
   | `GOOGLE_CLIENT_SECRET` | Your Google OAuth client secret |
   | `ENVIRONMENT` | `production` |
   | `CORS_ORIGINS` | `["https://solvora.vercel.app"]` *(update after Vercel deploy)* |
   | `INTERNAL_API_KEY` | A strong secret key (generate: `openssl rand -hex 24`) |

6. Click **"Deploy"** — Koyeb will build and deploy automatically
7. Once deployed, copy your backend URL — it looks like:
   ```
   https://solvora-backend-xxx.koyeb.app
   ```

**Verify backend is live:**
```bash
curl https://your-koyeb-url.koyeb.app/health
# Should return: {"status":"ok","version":"1.0.0"}
```

---

### Deploy Step 5 — Vercel (Production Frontend)

1. Go to https://vercel.com and sign up with GitHub (free)
2. Click **"Add New Project"** → Import the `solvora` repository
3. Configure:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `src/frontend`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `.next` (auto-detected)

4. Add environment variables (click **"Environment Variables"**):

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://your-koyeb-url.koyeb.app/api/v1` |
   | `NEXTAUTH_SECRET` | Same long random string as backend `SECRET_KEY` |
   | `NEXTAUTH_URL` | `https://your-project.vercel.app` *(Vercel will show you this URL)* |
   | `GOOGLE_CLIENT_ID` | Your Google OAuth client ID |
   | `GOOGLE_CLIENT_SECRET` | Your Google OAuth client secret |

5. Click **"Deploy"**
6. Once deployed, copy your frontend URL — it looks like:
   ```
   https://solvora.vercel.app
   ```

---

### Deploy Step 6 — Update CORS & OAuth Redirect URIs

Now that you have live URLs, update two things:

**A. Update CORS on Koyeb:**
- Go to Koyeb → Your service → Environment variables
- Update `CORS_ORIGINS` to: `["https://solvora.vercel.app"]`
- Redeploy (Koyeb does this automatically when you save)

**B. Update Google OAuth:**
- Go to https://console.cloud.google.com
- APIs & Services → Credentials → Your OAuth client
- Add to **Authorized redirect URIs**:
  ```
  https://solvora.vercel.app/api/auth/callback/google
  ```
- Save

**C. Update Vercel `NEXTAUTH_URL`:**
- Go to Vercel → Project → Settings → Environment Variables
- Update `NEXTAUTH_URL` to your actual Vercel URL
- Redeploy: Vercel → Deployments → Redeploy

---

### Deploy Step 7 — GitHub Actions Cron Scrapers

The scrapers run automatically via GitHub Actions (no extra server needed).

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Add these repository secrets:

   | Secret | Value |
   |--------|-------|
   | `PRODUCTION_API_URL` | `https://your-koyeb-url.koyeb.app` |
   | `INTERNAL_API_KEY` | Same value as Koyeb `INTERNAL_API_KEY` |

3. The workflow at `.github/workflows/ci.yml` already has the cron jobs configured:
   - Reddit scraper: every 30 minutes
   - HN scraper: every 15 minutes

4. To trigger manually before the first cron fires:
   - Go to GitHub → Actions → **CI** workflow → **Run workflow**
   - Or run these curl commands from your terminal:
   ```bash
   # Trigger Reddit scrape on production
   curl -X POST https://your-koyeb-url.koyeb.app/api/v1/internal/scrape/reddit \
     -H "X-Internal-Api-Key: your-internal-api-key"

   # Trigger HN scrape on production
   curl -X POST https://your-koyeb-url.koyeb.app/api/v1/internal/scrape/hn \
     -H "X-Internal-Api-Key: your-internal-api-key"
   ```

---

### Deploy Step 8 — Connect Custom Domain (Optional)

If you have a domain (e.g., `solvora.ai`):

**Frontend on Vercel:**
1. Vercel → Project → Settings → **Domains**
2. Add `solvora.ai` and `www.solvora.ai`
3. Add the DNS records Vercel shows you at your domain registrar
4. Update `NEXTAUTH_URL` env var to `https://solvora.ai`
5. Update Google OAuth redirect URI to `https://solvora.ai/api/auth/callback/google`

**Backend on Koyeb:**
1. Koyeb → App → Settings → **Custom domain**
2. Add `api.solvora.ai`
3. Add the CNAME record at your domain registrar
4. Update Vercel `NEXT_PUBLIC_API_URL` to `https://api.solvora.ai/api/v1`
5. Update Koyeb `CORS_ORIGINS` to `["https://solvora.ai"]`

---

### Production Checklist

Before announcing Solvora is live, verify each item:

```
Infrastructure
[ ] Neon DB is connected and tables exist
[ ] Upstash Redis is connected
[ ] Koyeb backend responds at /health
[ ] Vercel frontend loads without errors

Functionality
[ ] Dashboard loads and shows problem feed
[ ] Filters and search work
[ ] Problem detail page opens
[ ] AI solutions generate on demand
[ ] Analytics page shows charts
[ ] Login with email works
[ ] Login with Google works
[ ] Bookmarks save and persist

Scrapers
[ ] Reddit scrape triggered manually returns data
[ ] HN scrape triggered manually returns data
[ ] GitHub Actions cron jobs show in Actions tab

Security
[ ] CORS_ORIGINS only allows your Vercel domain
[ ] All API keys are in env vars, not in code
[ ] INTERNAL_API_KEY is a strong random secret
[ ] HTTPS enforced on all endpoints (Vercel + Koyeb both auto-handle this)
```

---

### Production Troubleshooting

| Problem | Fix |
|---------|-----|
| Koyeb deploy fails at build | Check build logs — likely a missing package in `requirements.txt` |
| Frontend shows "Failed to fetch" | `NEXT_PUBLIC_API_URL` is wrong or Koyeb service is sleeping |
| Google login fails on prod | OAuth redirect URI not added for production domain in Google Console |
| `CORS blocked` error in browser | Update `CORS_ORIGINS` on Koyeb to include your Vercel URL |
| Scrapers not running | Check GitHub Actions tab — secrets `PRODUCTION_API_URL` and `INTERNAL_API_KEY` may be missing |
| Neon DB connection timeout | Add `?sslmode=require` to the end of your `DATABASE_URL` |
| Solutions not generating | Check Koyeb logs — AI API keys may not be set correctly |
| Vercel build fails | Check that `src/frontend` is set as root directory in Vercel project settings |

---

### Cost Summary (Monthly at Launch)

| Service | Free Tier | Paid If You Exceed |
|---------|-----------|-------------------|
| Neon PostgreSQL | 5 GB storage, 191 compute hours | $19/mo for Pro |
| Upstash Redis | 10K commands/day, 256 MB | $10/mo for Pay-as-you-go |
| Koyeb (backend) | 1 service, 512 MB RAM | $5.04/mo per extra service |
| Vercel (frontend) | 100 GB bandwidth, unlimited deploys | $20/mo for Pro |
| GitHub Actions | 2,000 minutes/month | $0.008/min after |
| Gemini API | 1M tokens/day | $0.075 per 1M tokens |
| **Total at launch** | **$0/month** | Scales with usage |

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
