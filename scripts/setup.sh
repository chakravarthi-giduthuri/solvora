#!/bin/bash
# Solvora -- development setup

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Setting up Solvora..."
echo "Project root: $PROJECT_ROOT"

# ---- Dependency checks ----
check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "ERROR: '$1' is required but not installed." >&2
        exit 1
    fi
    echo "  [ok] $1 found"
}

echo ""
echo "Checking required tools..."
check_command python3
check_command node
check_command docker

# ---- Environment file ----
echo ""
echo "Setting up environment..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo "  [ok] .env created from .env.example — please fill in secrets before running"
    else
        echo "  [warn] .env.example not found; skipping .env creation"
    fi
else
    echo "  [ok] .env already exists"
fi

# ---- Backend dependencies ----
echo ""
echo "Installing backend dependencies..."
pip install -r "$PROJECT_ROOT/src/backend/requirements.txt"
echo "  [ok] backend dependencies installed"

# ---- Frontend dependencies ----
echo ""
echo "Installing frontend dependencies..."
(cd "$PROJECT_ROOT/src/frontend" && npm install)
echo "  [ok] frontend dependencies installed"

# ---- Start infrastructure services ----
echo ""
echo "Starting database and cache services..."
(cd "$PROJECT_ROOT/config" && docker compose up -d db redis)
echo "  [ok] postgres and redis started"

# Give postgres a moment to initialise before running migrations
echo "  Waiting for postgres to be ready..."
sleep 3

# ---- Database migrations ----
echo ""
echo "Running database migrations..."
(cd "$PROJECT_ROOT/src/backend" && alembic upgrade head)
echo "  [ok] migrations applied"

echo ""
echo "Setup complete!"
echo "Run: cd config && docker compose up"
echo "  or: bash scripts/run_dev.sh"
