#!/usr/bin/env bash
# Stop the local Aether stack, then start it again.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/stop_all.sh"
"$DIR/start_all.sh"
