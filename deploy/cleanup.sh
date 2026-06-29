#!/bin/bash
# Cleanup old downloaded files from kick-downloader
# Runs every 30 min via cron

DOWNLOAD_DIR="/opt/kick-downloader/downloads"
MAX_AGE_MIN=120  # Delete files older than 2 hours
MAX_DISK_PCT=85  # Emergency cleanup if disk >85% full

# Emergency cleanup if disk is too full
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt "$MAX_DISK_PCT" ]; then
    echo "⚠️ Disk at ${DISK_USAGE}% - emergency cleanup"
    find "$DOWNLOAD_DIR" -type f -mmin +30 -delete
    echo "Cleaned files older than 30 min"
fi

# Normal cleanup - remove files older than MAX_AGE_MIN
DELETED=$(find "$DOWNLOAD_DIR" -type f -mmin "+$MAX_AGE_MIN" -delete -print | wc -l)
echo "Normal cleanup: deleted $DELETED file(s) older than ${MAX_AGE_MIN}min"

# Show remaining disk
df -h / | tail -1