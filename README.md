# Solvora

**AI-powered problem aggregator** — scrapes real problems from Reddit and Hacker News, surfaces them in a clean feed, and generates AI solutions using Gemini / OpenAI / Claude.

## What it does

- Aggregates community problems from Reddit, Hacker News, and user submissions
- Auto-classifies problems by sentiment (urgent, frustrated, curious, neutral) and category
- Generates AI-powered solutions on demand
- Full-text search, platform/sentiment/category/date filters
- Problem of the Day, leaderboard, bookmarks, user profiles
- Real-time new-problem notifications via SSE
- Admin panel to manage scrapers, users, and reports

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL (Neon) |
| Cache | Redis (Upstash) with in-memory L1 cache |
| Auth | NextAuth.js — Google OAuth + email/password |
| Scraping | PRAW (Reddit), Algolia HN API — built-in scheduler |
| AI | Gemini, OpenAI, Anthropic Claude |
| Deployment | Vercel (frontend) + Railway (backend) |

## Project structure

```
src/
├── frontend/          # Next.js app
│   └── src/
│       ├── app/       # Pages (App Router)
│       ├── components/
│       ├── lib/       # API client, utils
│       └── store/     # Zustand stores
└── backend/           # FastAPI app
    └── app/
        ├── api/v1/    # REST endpoints
        ├── models/    # SQLAlchemy models
        ├── scrapers/  # HN + Reddit scrapers
        ├── schemas/   # Pydantic schemas
        └── core/      # Config, DB, security
```

## Local development

### Prerequisites
- Node 20+, Python 3.11+, Docker (for PostgreSQL + Redis)

### Backend

```bash
cd src/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd src/frontend
npm install
cp .env.local.example .env.local   # fill in your values
npm run dev
```

### Docker (full stack)

```bash
docker compose -f config/docker-compose.yml up
```

## Environment variables

### Backend (`src/backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing secret (generate with `openssl rand -hex 32`) |
| `INTERNAL_API_KEY` | Key for internal scraper endpoints |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `REDDIT_CLIENT_ID` | Reddit API client ID |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret |
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `ADMIN_EMAILS` | Comma-separated emails granted admin access |
| `ENVIRONMENT` | `development` or `production` |

### Frontend (`src/frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API URL (e.g. `https://api.solvora.app/api/v1`) |
| `NEXTAUTH_URL` | Frontend URL (e.g. `https://solvora.app`) |
| `NEXTAUTH_SECRET` | NextAuth signing secret (generate with `openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

## Deployment

- **Frontend**: Deploy `src/frontend` to [Vercel](https://vercel.com) — set Root Directory to `src/frontend`
- **Backend**: Deploy `src/backend` to [Railway](https://railway.app) — uses the included Dockerfile
- **Database**: [Neon](https://neon.tech) (serverless PostgreSQL)
- **Redis**: [Upstash](https://upstash.com) (serverless Redis)

Scrapers run automatically inside the backend process (HN every 15 min, Reddit every 30 min). No separate worker needed.

## License

MIT
