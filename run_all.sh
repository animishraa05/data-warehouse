#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  FoodFlow Analytics — End-to-End Run Script
# ─────────────────────────────────────────────────────────────
#  Usage:  ./run_all.sh
#
#  This script runs the entire pipeline from scratch:
#    1. Install dependencies
#    2. Generate synthetic data
#    3. Start PostgreSQL via Docker Compose
#    4. Run ETL pipeline
#    5. Run ML forecasting
#    6. Run unit tests
#    7. Launch interactive dashboard
# ─────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_step() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}\n"; }
echo_ok()  { echo -e "${GREEN}✓ $1${NC}"; }
echo_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
echo_err()  { echo -e "${RED}✗ $1${NC}"; }

# ── Step 0: Pre-flight checks ────────────────────────────────
echo_step "Pre-flight checks"

command -v python3 &>/dev/null || { echo_err "python3 not found — install Python 3.10+"; exit 1; }
command -v docker &>/dev/null || { echo_err "docker not found — install Docker"; exit 1; }
command -v docker compose &>/dev/null || docker-compose --version &>/dev/null || { echo_err "docker compose not found"; exit 1; }

echo_ok "Python: $(python3 --version)"
echo_ok "Docker: $(docker --version)"

# ── Step 1: Install Python dependencies ──────────────────────
echo_step "Installing Python dependencies"
pip install -q -r requirements.txt
pip install -q streamlit plotly pytest
echo_ok "All dependencies installed"

# ── Step 2: Generate synthetic data ──────────────────────────
echo_step "Generating synthetic data"
python3 scripts/generate_data.py

RAW_COUNT=$(ls -1 data/raw/*.csv 2>/dev/null | wc -l)
if [ "$RAW_COUNT" -eq 7 ]; then
    echo_ok "All 7 CSV files generated"
else
    echo_err "Expected 7 CSV files, found $RAW_COUNT"
    exit 1
fi

# ── Step 3: Start Data Warehouse ─────────────────────────────
echo_step "Starting PostgreSQL data warehouse"

# Check if already running
if docker ps --format '{{.Names}}' | grep -q foodflow_postgres; then
    echo_ok "PostgreSQL already running"
else
    COMPOSE_CMD="docker compose"
    if ! command -v docker compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    fi

    $COMPOSE_CMD up -d postgres

    echo -n "Waiting for PostgreSQL to be ready"
    for i in $(seq 1 30); do
        sleep 2
        if docker exec foodflow_postgres pg_isready -U dw_user -d foodflow_dw &>/dev/null; then
            echo ""
            echo_ok "PostgreSQL is ready"
            break
        fi
        echo -n "."
    done

    if ! docker exec foodflow_postgres pg_isready -U dw_user -d foodflow_dw &>/dev/null; then
        echo_err "PostgreSQL failed to start within 60s"
        exit 1
    fi
fi

# ── Step 4: Run ETL Pipeline ─────────────────────────────────
echo_step "Running ETL pipeline"
python3 scripts/etl_pipeline.py
echo_ok "ETL complete — star schema loaded"

# ── Step 5: ML Forecasting ───────────────────────────────────
echo_step "Running ML forecast"
python3 scripts/ml_forecast.py
echo_ok "Forecast generated"

# ── Step 6: Unit Tests ───────────────────────────────────────
echo_step "Running unit tests"
python3 -m pytest tests/ -v --tb=short || echo_warn "Some tests failed — review the output above"

# ── Step 7: Launch Dashboard ─────────────────────────────────
echo_step "Starting interactive dashboard"
echo_ok "Dashboard available at http://localhost:8501"
echo -e "${YELLOW}Press Ctrl+C to stop the dashboard${NC}\n"

streamlit run scripts/dashboard_app.py --server.headless true
