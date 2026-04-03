#!/bin/bash
# Rotate collector log — keeps last 7 days
# Add to cron: 0 19 * * * bash /home/opc/train-punctuality-service/scripts/rotate_log.sh

LOG=/home/opc/collector.log
if [ -f "$LOG" ] && [ $(stat -c%s "$LOG" 2>/dev/null || echo 0) -gt 1048576 ]; then
    mv "$LOG" "$LOG.$(date '+%Y%m%d')"
    find /home/opc/ -name 'collector.log.*' -mtime +7 -delete
fi
