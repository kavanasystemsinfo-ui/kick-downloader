#!/bin/bash
# Kick Video Downloader - Simple script

DOWNLOAD_DIR="/opt/kick-downloader/downloads"

# Create directory
mkdir -p "$DOWNLOAD_DIR"

# Check URL
if [ -z "$1" ]; then
    echo "Usage: $0 <kick_url> [mp4|mp3]"
    exit 1
fi

URL="$1"
FORMAT="${2:-mp4}"

# Download with yt-dlp
if [ "$FORMAT" = "mp3" ]; then
    yt-dlp -x --audio-format mp3 -o "$DOWNLOAD_DIR/%(title)s.%(ext)s" "$URL"
else
    yt-dlp -o "$DOWNLOAD_DIR/%(title)s.%(ext)s" "$URL"
fi

echo "Downloaded to: $DOWNLOAD_DIR"