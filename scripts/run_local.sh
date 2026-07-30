#!/bin/bash
# ============================================================
# 🧪 Local Test Runner — Watch the automation in a REAL browser
# ============================================================
#
# This script runs the Naukri updater LOCALLY (no Docker needed)
# with a VISIBLE browser window so you can watch it work.
#
# Prerequisites:
#   1. Python 3.10+ installed
#   2. .env file configured with your credentials
#   3. Resume PDF placed in resumes/ directory
#
# Usage:
#   chmod +x scripts/run_local.sh
#   ./scripts/run_local.sh              # Full run (visible browser)
#   ./scripts/run_local.sh --dry-run    # Login test only
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "============================================="
echo "🧪 Naukri Profile Updater — Local Test Mode"
echo "📅 $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "🖥️  Browser: VISIBLE (you'll see it!)"
echo "============================================="

# ── Check for .env file ──
if [ ! -f ".env" ]; then
    echo ""
    echo "❌ .env file not found!"
    echo ""
    echo "   Create it from the template:"
    echo "   cp .env.example .env"
    echo "   Then fill in your NAUKRI_EMAIL and NAUKRI_PASSWORD"
    echo ""
    exit 1
fi

# ── Setup Python virtual environment ──
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

if ! python -c "import playwright, requests, pandas, streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
fi

# ── Install Playwright browsers ──
echo "🌐 Ensuring Playwright Chromium is installed..."
python -m playwright install chromium

# ── Create required directories ──
mkdir -p logs session_storage

# ── Override HEADLESS to false for visible browser ──
export HEADLESS=false
export LOG_DIR=logs
export SCREENSHOT_DIR=logs
export SESSION_DIR=session_storage

echo ""
echo "🚀 Starting Naukri updater with VISIBLE browser..."
echo "   Watch the browser window to see it login and update your profile!"
echo ""

# Run the script — pass any arguments (like --dry-run)
python -m src.main "$@"

echo ""
echo "✅ Done! Check logs/ directory for detailed output."
