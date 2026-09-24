#!/usr/bin/env bash
# Follow the engine and dashboard logs written by start_all.sh.
set -euo pipefail
source "$(dirname "$0")/common.sh"

touch "$ENGINE_LOG" "$WEB_LOG"
echo "following $ENGINE_LOG"
echo "following $WEB_LOG"
tail -n 40 -f "$ENGINE_LOG" "$WEB_LOG"
