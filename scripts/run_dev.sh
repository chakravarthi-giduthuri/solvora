#!/bin/bash
# Solvora -- start all development servers in parallel

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Track child PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo "Shutting down development servers..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
        fi
    done
    wait
    echo "All servers stopped."
}

trap cleanup SIGINT SIGTERM

echo "Starting Solvora development servers..."
echo ""

# ---- Backend: FastAPI ----
echo "[backend]  uvicorn on http://localhost:8000"
(cd "$PROJECT_ROOT/src/backend" && uvicorn app.main:app --reload --port 8000) &
PIDS+=($!)

# ---- Background worker: Celery ----
echo "[celery]   worker with 2 concurrency slots"
(cd "$PROJECT_ROOT/src/backend" && celery -A app.celery_app worker --loglevel=info --concurrency 2) &
PIDS+=($!)

# ---- Frontend: Next.js ----
echo "[frontend] next dev on http://localhost:3000"
(cd "$PROJECT_ROOT/src/frontend" && npm run dev) &
PIDS+=($!)

echo ""
echo "All servers started. Press Ctrl+C to stop."
echo ""

# Wait for any child to exit (if one crashes, we stay alive for the others)
wait
