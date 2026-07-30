#!/bin/bash
# ============================================================
# Healthcheck — Verifies cron daemon is running
# ============================================================

# Check if cron process is alive
pgrep cron > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Cron daemon is not running"
    exit 1
fi

# Check if the log file was written to in the last 25 hours
# (allows for daily schedule with some buffer)
LOG_FILE="/app/logs/cron.log"
if [ -f "$LOG_FILE" ]; then
    LAST_MOD=$(stat -c %Y "$LOG_FILE" 2>/dev/null || stat -f %m "$LOG_FILE" 2>/dev/null)
    NOW=$(date +%s)
    AGE=$(( NOW - LAST_MOD ))

    # 90000 seconds = 25 hours
    if [ $AGE -gt 90000 ]; then
        echo "⚠️  Log file hasn't been updated in over 25 hours"
        exit 1
    fi
fi

echo "✅ Healthy"
exit 0
