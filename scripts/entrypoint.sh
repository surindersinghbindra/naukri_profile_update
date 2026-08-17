#!/bin/bash
# ============================================================
# Entrypoint — Sets up cron schedule and keeps container alive
# ============================================================

set -e

echo "============================================="
echo "🚀 Naukri Profile Updater — Container Starting"
echo "📅 $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "⏰ Schedule: ${CRON_SCHEDULE:-0 8 * * *}"
echo "🎯 Target: ${TARGET_ROLE:-Software Engineer}"
echo "============================================="

# ── Build the cron command ──
# All env vars must be passed to the cron job explicitly
# because cron runs in a minimal environment
CRON_CMD="${CRON_SCHEDULE:-0 8 * * *}"

# Export all current env vars to a file that cron can source
env | grep -E '^(NAUKRI_|RESUME_|TARGET_|HEADLINES|KEY_SKILLS|CRON_|TELEGRAM_|HEADLESS|HUMAN_|MAX_|LOG_|SCREENSHOT_|SESSION_|TZ|PYTHONUNBUFFERED)' > /app/.env.cron

# Create the cron job entry
# python-dotenv in src.main loads .env automatically from /app
CRON_ENTRY="${CRON_CMD} cd /app && xvfb-run --auto-servernum --server-args=\"-screen 0 1366x768x24\" /usr/bin/python -m src.main >> /app/logs/cron.log 2>&1"

# Install the cron job
echo "${CRON_ENTRY}" | crontab -

echo "✅ Cron job installed:"
crontab -l
echo ""

# ── Run once immediately on startup (optional) ──
if [ "${RUN_ON_STARTUP:-true}" = "true" ]; then
    echo "🔄 Running initial update now..."
    cd /app
    xvfb-run --auto-servernum --server-args="-screen 0 1366x768x24" /usr/bin/python -m src.main 2>&1 | tee -a /app/logs/cron.log
    echo ""
    echo "✅ Initial run complete. Cron will handle subsequent runs."
fi

echo "🕐 Cron daemon starting... (container will stay alive)"
echo "   Next run: $(date -d 'tomorrow 08:00' '+%Y-%m-%d %H:%M %Z' 2>/dev/null || echo 'as per schedule')"
echo ""

# Start cron in foreground to keep container alive
cron -f
