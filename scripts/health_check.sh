#!/bin/bash
# Health check for train collector on Oracle VM
# Usage: bash scripts/health_check.sh

cd /home/opc/train-punctuality-service || exit 1

echo "=== Train Collector Health Check ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

# 1. Cron status
echo "--- Cron Job ---"
if crontab -l 2>/dev/null | grep -q daily_collector; then
    echo "✅ Cron is scheduled"
    crontab -l 2>/dev/null | grep daily_collector
else
    echo "❌ Cron NOT found"
fi
echo ""

# 2. Last collection run
echo "--- Last Run ---"
if [ -f /home/opc/collector.log ]; then
    LAST_LINE=$(tail -1 /home/opc/collector.log)
    LAST_TIME=$(echo "$LAST_LINE" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}')
    echo "Last log entry: $LAST_TIME"
    echo "Last 5 lines:"
    tail -5 /home/opc/collector.log
else
    echo "❌ No collector.log found"
fi
echo ""

# 3. DB stats
echo "--- Database Stats ---"
python3 -c "
from src.db.database import get_connection
conn = get_connection()
runs = conn.execute('SELECT COUNT(*) FROM daily_runs').fetchone()[0]
stops = conn.execute('SELECT COUNT(*) FROM daily_stop_times').fetchone()[0]
latest = conn.execute('SELECT MAX(run_date) FROM daily_runs').fetchone()[0]
trains = conn.execute('SELECT COUNT(DISTINCT train_number) FROM daily_runs').fetchone()[0]
print(f'Total runs: {runs}')
print(f'Total stop records: {stops}')
print(f'Unique trains collected: {trains}')
print(f'Latest run_date: {latest}')
" 2>&1
echo ""

# 4. Disk & memory
echo "--- System Resources ---"
echo "Memory:"
free -m | grep -E 'Mem|Swap'
echo "Disk:"
df -h / | tail -1
echo ""

# 5. Log size
echo "--- Log Size ---"
if [ -f /home/opc/collector.log ]; then
    ls -lh /home/opc/collector.log | awk '{print $5}'
else
    echo "No log file"
fi

# 6. Errors in last 24h
echo ""
echo "--- Errors (last 24h) ---"
if [ -f /home/opc/collector.log ]; then
    TODAY=$(date '+%Y-%m-%d')
    ERR_COUNT=$(grep -c "ERROR\|Failed\|Traceback" /home/opc/collector.log 2>/dev/null || echo 0)
    if [ "$ERR_COUNT" -gt 0 ]; then
        echo "⚠️  $ERR_COUNT error(s) found. Recent:"
        grep "ERROR\|Failed" /home/opc/collector.log | tail -3
    else
        echo "✅ No errors"
    fi
else
    echo "No log file"
fi
