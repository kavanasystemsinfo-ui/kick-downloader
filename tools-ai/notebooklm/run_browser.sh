#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_DIR="${NOTEBOOKLM_CHROME_PROFILE:-$SCRIPT_DIR/chrome_profile}"
CDP_PORT="${CDP_PORT:-9222}"
CHROME_BIN="${CHROME_BIN:-}"

if [[ -z "$CHROME_BIN" ]]; then
  for candidate in google-chrome chromium chromium-browser chrome; do
    if command -v "$candidate" >/dev/null 2>&1; then
      CHROME_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$CHROME_BIN" ]]; then
  echo "Chrome or Chromium was not found. Set CHROME_BIN to the browser executable path." >&2
  exit 1
fi

mkdir -p "$PROFILE_DIR"

"$CHROME_BIN" \
  --remote-debugging-port="$CDP_PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --disable-extensions \
  --no-first-run \
  --no-default-browser-check \
  about:blank &

echo "NotebookLM CDP endpoint: http://localhost:$CDP_PORT"
echo "Run: python \"$SCRIPT_DIR/notebook_bridge.py\" --cdp-endpoint http://localhost:$CDP_PORT --notebook-url <notebook-url> --chat-prompt '<prompt>'"
wait "$!"
