# Solvora — Deployment Guide

## Section 1 — Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Production Stack                          │
│                                                                 │
│   ┌──────────────┐        ┌──────────────────┐                 │
│   │   Frontend   │ ──────▶│   Backend API    │                 │
│   │   (Vercel)   │  HTTPS │   (Railway)      │                 │
│   └──────────────┘        └────────┬─────────┘                 │
│                                    │                             │
│                          ┌─────────┴─────────┐                 │
│                          │                   │                  │
│                   ┌──────▼──────┐    ┌───────▼──────┐         │
│                   │ PostgreSQL  │    │    Redis      │         │
│                   │   (Neon)    │    │  (Upstash)    │         │
│                   └─────────────┘    └───────┬───────┘         │
│                                              │                  │
│                                    ┌─────────▼──────────┐      │
│                                    │  Celery Worker     │      │
│                                    │  Celery Beat       │      │
│                                    │  (Railway workers) │      │
│                                    └────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow:** User browser → Vercel (Next.js SSR/static) → Railway (FastAPI) → Neon (PostgreSQL) + Upstash (Redis)
**Background jobs:** Celery worker pulls tasks from Redis queue; Celery beat schedules periodic scrape jobs.

---

## Section 2 — Prerequisites

### Tools
| Tool | Minimum Version |
|------|----------------|
| Node.js | 20+ |
| Python | 3.11+ |
| Docker Desktop | latest |
| Git | 2.x+ |

### Accounts required
- **Vercel** — frontend hosting (vercel.com)
- **Railway** — backend API + Celery workers (railway.app)
- **Neon** — managed PostgreSQL (neon.tech)
- **Upstash** — managed Redis (upstash.com)
- **Google Cloud Console** — OAuth 2.0 credentials (console.cloud.google.com)
- **Sentry** *(optional but recommended)* — error tracking (sentry.io)

---

## Section 3 — Set Up Cloud Services (one-time)

### 3a. Neon PostgreSQL

1. Go to [neon.tech](https://neon.tech) → Sign up / Log in
2. Click **New Project** → name it `solvora`
3. Select a region close to your Railway backend
4. After creation, open the project dashboard → **Connection Details**
5. Copy the connection string — it looks like:
   ```
   postgresql+asyncpg://user:password@ep-xxx-yyy.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
6. Save this as your `DATABASE_URL` (used in Railway backend env vars)

> **Note:** The `?sslmode=require` suffix is required. Neon enforces TLS.

### 3b. Upstash Redis

1. Go to [upstash.com](https://upstash.com) → Sign up / Log in
2. Click **Create Database** → name it `solvora-redis`
3. Select **Global** for low-latency or the same region as Railway
4. After creation, open the database → **Details** tab
5. Copy the **Redis URL** — it looks like:
   ```
   redis://default:password@global-xxx-yyy.upstash.io:6379
   ```
6. Save this as your `REDIS_URL`

### 3c. Google OAuth (production)

1. Go to [Google Cloud Console](https://console.cloud.google.com) → select or create a project
2. Navigate to **APIs & Services → Credentials**
3. Click **Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Web application**
5. Add the following **Authorized redirect URIs**:
   - Frontend callback: `https://YOUR_APP.vercel.app/api/auth/callback/google`
   - Backend callback: `https://YOUR_BACKEND.up.railway.app/auth/google`
6. Click **Create** — copy the **Client ID** and **Client Secret**
7. Save these as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (used in both backend and frontend)

> Replace `YOUR_APP` and `YOUR_BACKEND` with your actual Vercel/Railway URLs once deployed.

### 3d. Sentry (optional but recommended)

1. Go to [sentry.io](https://sentry.io) → Sign up / Log in
2. Click **Create Project** → choose **FastAPI**
3. Copy the **DSN** — it looks like:
   ```
   https://abc123@o123456.ingest.sentry.io/789012
   ```
4. Save this as `SENTRY_DSN`

---

## Section 4 — Generate Production Secrets

Run these locally to generate cryptographically secure secrets. **Never reuse dev secrets in production.**

```bash
# SECRET_KEY — used for JWT signing (backend)
python -c "import secrets; print(secrets.token_hex(32))"

# INTERNAL_API_KEY — guards internal/admin endpoints (backend)
python -c "import secrets; print(secrets.token_hex(32))"

# NEXTAUTH_SECRET — signs NextAuth.js sessions (frontend)
openssl rand -hex 32
```

Store the output values securely (e.g., in a password manager) — you'll paste them into Railway and Vercel env vars.

---

## Section 5 — Deploy Backend (Railway)

### 5.1 Create the API service

1. Go to [railway.app](https://railway.app) → **New Project**
2. Click **Deploy from GitHub repo** → authorize and select your repo
3. Set the **Root Directory** to `src/backend`
4. Railway auto-detects the `Dockerfile` in `src/backend/` — verify it is selected
5. Click **Deploy**

### 5.2 Add backend environment variables

In Railway → your service → **Variables** tab, add all of the following:

```
# Database
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.neon.tech/neondb?sslmode=require

# Redis
REDIS_URL=redis://default:password@global-xxx.upstash.io:6379

# Auth
SECRET_KEY=<generated-64-char-hex>
INTERNAL_API_KEY=<generated-64-char-hex>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
ENVIRONMENT=production
CORS_ORIGINS=["https://YOUR_APP.vercel.app"]

# Reddit API
REDDIT_CLIENT_ID=<your-reddit-client-id>
REDDIT_CLIENT_SECRET=<your-reddit-client-secret>
REDDIT_USER_AGENT=Solvora/1.0

# AI APIs
GEMINI_API_KEY=<your-gemini-api-key>
OPENAI_API_KEY=<your-openai-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>

# Google OAuth
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>

# Sentry (optional)
SENTRY_DSN=<your-sentry-dsn>
```

> **CORS_ORIGINS:** You'll update this after deploying the frontend. For now you can set a placeholder; just redeploy the backend after you have the Vercel URL.

### 5.3 After deploy

1. Copy your Railway backend URL from the service dashboard (e.g. `https://solvora-api.up.railway.app`)
2. Open the Railway **Shell** tab and run database migrations:
   ```bash
   alembic upgrade head
   ```

### 5.4 Add Celery worker service

1. In Railway → your project → **New Service → GitHub Repo** → same repo, same root `src/backend`
2. Go to the new service → **Settings → Deploy** → override **Start Command**:
   ```bash
   celery -A app.celery_app worker --loglevel=info -c 4
   ```
3. Add the same environment variables as the API service (or use Railway's **shared variables** feature)
4. Deploy

### 5.5 Add Celery beat service

1. Add another service → same repo, root `src/backend`
2. Override **Start Command**:
   ```bash
   celery -A app.celery_app beat --loglevel=info
   ```
3. Add the same environment variables
4. Deploy

> The three services (API, worker, beat) all use `src/backend/Dockerfile` — Railway builds them identically; only the start command differs.

---

## Section 6 — Deploy Frontend (Vercel)

### 6.1 Create the project

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. **Import Git Repository** → select your repo
3. Set **Root Directory** to `src/frontend`
4. Framework preset: **Next.js** (auto-detected)

### 6.2 Add frontend environment variables

In Vercel → project → **Settings → Environment Variables**, add:

```
NEXT_PUBLIC_API_URL=https://solvora-api.up.railway.app/api/v1
NEXTAUTH_SECRET=<generated-64-char-hex>
NEXTAUTH_URL=https://YOUR_APP.vercel.app
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
```

> Set all variables for **Production** environment (and optionally Preview).

### 6.3 Deploy

1. Click **Deploy**
2. Copy the Vercel URL once live (e.g. `https://solvora.vercel.app`)

### 6.4 Update backend CORS

1. Go back to Railway → backend API service → **Variables**
2. Update `CORS_ORIGINS` to your actual Vercel URL:
   ```
   CORS_ORIGINS=["https://solvora.vercel.app"]
   ```
3. Railway will auto-redeploy the backend

### 6.5 Update Google OAuth redirect URIs

1. Return to Google Cloud Console → your OAuth client
2. Add the actual URIs now that you have both URLs:
   - `https://YOUR_APP.vercel.app/api/auth/callback/google`
   - `https://solvora-api.up.railway.app/auth/google`

---

## Section 7 — Post-Deploy Verification Checklist

Run through these checks after every fresh deployment:

- [ ] **Health check:** `curl https://solvora-api.up.railway.app/health` returns `{"status":"ok"}`
- [ ] **Frontend loads** at your Vercel URL without console errors
- [ ] **Email/password login** works end-to-end
- [ ] **Google OAuth login** completes and redirects correctly
- [ ] **Problems feed loads** (confirms DB connection from backend)
- [ ] **Bookmark a problem** (confirms auth + DB write path)
- [ ] **Security headers present:**
  ```bash
  curl -I https://solvora-api.up.railway.app/health
  # Should include: x-frame-options: DENY
  ```
- [ ] **API docs disabled in production:** `curl https://solvora-api.up.railway.app/docs` returns 404
- [ ] **Celery worker running:** call the scrape trigger endpoint with your `INTERNAL_API_KEY`:
  ```bash
  curl -X POST https://solvora-api.up.railway.app/internal/scrape \
    -H "X-Internal-Key: <your-INTERNAL_API_KEY>"
  ```

---

## Section 8 — Alternative: Self-Hosted via Docker Compose

Use this path to deploy on a VPS (DigitalOcean, Hetzner, Linode, etc.).

### 8.1 Prepare the server

```bash
# Install Docker Engine (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 8.2 Clone the repo

```bash
git clone https://github.com/YOUR_ORG/solvora.git
cd solvora
```

### 8.3 Create root `.env` file

Create a `.env` file at the **project root** (same level as `config/`):

```bash
# Database (internal Docker network)
DATABASE_URL=postgresql+asyncpg://solvora:STRONG_PASSWORD@db:5432/solvora

# Redis (internal Docker network)
REDIS_URL=redis://redis:6379/0

# Auth
SECRET_KEY=<generated-64-char-hex>
INTERNAL_API_KEY=<generated-64-char-hex>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
ENVIRONMENT=production
CORS_ORIGINS=["https://yourdomain.com"]

# Reddit API
REDDIT_CLIENT_ID=<your-reddit-client-id>
REDDIT_CLIENT_SECRET=<your-reddit-client-secret>
REDDIT_USER_AGENT=Solvora/1.0

# AI APIs
GEMINI_API_KEY=<your-gemini-api-key>
OPENAI_API_KEY=<your-openai-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>

# Google OAuth
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>

# Sentry (optional)
SENTRY_DSN=<your-sentry-dsn>

# Postgres container vars
POSTGRES_DB=solvora
POSTGRES_USER=solvora
POSTGRES_PASSWORD=STRONG_PASSWORD
```

Also create `src/frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://yourdomain.com/api/v1
NEXTAUTH_SECRET=<generated-64-char-hex>
NEXTAUTH_URL=https://yourdomain.com
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
```

### 8.4 Production tweak: disable hot reload

Edit `config/docker-compose.yml` — change the backend `command` from:
```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
to:
```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Remove the `volumes` mounts for backend, celery_worker, and celery_beat (those are for dev only).

### 8.5 Start the stack

```bash
docker compose -f config/docker-compose.yml up -d
```

### 8.6 Run migrations

```bash
docker compose -f config/docker-compose.yml exec backend alembic upgrade head
```

### 8.7 Set up Nginx reverse proxy + SSL

Install Nginx and Certbot:
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/solvora`:
```nginx
server {
    server_name yourdomain.com;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable and obtain SSL:
```bash
sudo ln -s /etc/nginx/sites-available/solvora /etc/nginx/sites-enabled/
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

---

## Section 9 — Updating / Redeploying

### Automatic (recommended)

Both Railway and Vercel watch your Git repository:
- Push to the `main` branch → Railway and Vercel automatically redeploy
- No manual action needed for code-only changes

### Manual redeploy

```bash
# Railway
railway up

# Vercel
vercel --prod
```

### Database migrations after an update

Whenever a deployment includes new Alembic migration files, run:

**Railway:**
1. Railway dashboard → backend API service → **Shell** tab
2. Run: `alembic upgrade head`

**Self-hosted:**
```bash
docker compose -f config/docker-compose.yml exec backend alembic upgrade head
```

> Always run migrations **before** the new backend code serves traffic when possible. Railway's deploy can be paused until migrations succeed using Railway's [deploy hooks](https://docs.railway.app/deploy/deployments#deploy-hooks).
