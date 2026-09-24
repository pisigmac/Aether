#!/usr/bin/env bash
# Report whether the Aether engine and dashboard are up.
set -euo pipefail
source "$(dirname "$0")/common.sh"

report() {
  local label="$1"
  local url="$2"
  local pidfile="$3"
  local port="$4"
  local pid code listeners
  pid="$(read_pid "$pidfile")"
  code="$(http_code "$url")"
  listeners="$(port_pids "$port" | paste -sd, -)"
  if [[ "$code" == "200" ]]; then
    printf "%-8s up      %s\n" "$label" "$url"
  elif [[ "$code" == "000" ]]; then
    printf "%-8s down    %s\n" "$label" "$url"
  else
    printf "%-8s http %s  %s\n" "$label" "$code" "$url"
  fi
  if pid_alive "$pid"; then
    echo "         pid ${pid}  (managed)"
  elif [[ -n "$listeners" ]]; then
    echo "         port ${port} listeners: ${listeners}"
  fi
}

report "engine" "http://127.0.0.1:${ENGINE_PORT}/health" "$ENGINE_PID" "$ENGINE_PORT"
report "web" "http://127.0.0.1:${WEB_PORT}/" "$WEB_PID" "$WEB_PORT"
echo "data     ${AETHER_DATA_DIR}"
echo "logs     ${ENGINE_LOG}"
echo "         ${WEB_LOG}"
