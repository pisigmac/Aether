#!/usr/bin/env bash
# Start the Aether engine and the Next.js dashboard.
# Ports default to 18100 and 13100. Override with AETHER_ENGINE_PORT and AETHER_WEB_PORT.
set -euo pipefail
source "$(dirname "$0")/common.sh"

start_engine() {
  local code pid bin
  code="$(http_code "http://127.0.0.1:${ENGINE_PORT}/health")"
  if [[ "$code" == "200" ]]; then
    echo "engine already up  http://127.0.0.1:${ENGINE_PORT}/health"
    return 0
  fi
  if [[ -n "$(port_pids "$ENGINE_PORT")" ]]; then
    echo "port ${ENGINE_PORT} is in use and /health did not return 200" >&2
    return 1
  fi
  bin="$(engine_bin)"
  (
    cd "$ENGINE_DIR"
    # A new session so stop_all can signal this process without touching the caller.
    setsid "$bin" aether.api:app \
      --host "$ENGINE_HOST" \
      --port "$ENGINE_PORT" \
      --reload \
      --reload-dir "$ENGINE_DIR/aether" \
      >>"$ENGINE_LOG" 2>&1 &
    echo $! >"$ENGINE_PID"
  )
  pid="$(read_pid "$ENGINE_PID")"
  wait_for_url "http://127.0.0.1:${ENGINE_PORT}/health" "engine"
  echo "engine started  pid ${pid}  http://127.0.0.1:${ENGINE_PORT}/health"
}

start_web() {
  local code pid
  code="$(http_code "http://127.0.0.1:${WEB_PORT}/")"
  if [[ "$code" == "200" ]]; then
    echo "web already up  http://127.0.0.1:${WEB_PORT}/"
    return 0
  fi
  if [[ -n "$(port_pids "$WEB_PORT")" ]]; then
    echo "port ${WEB_PORT} is in use and / did not return 200" >&2
    return 1
  fi
  if [[ ! -d "$WEB_DIR/node_modules" ]]; then
    echo "web dependencies are missing. From web/: npm install" >&2
    return 1
  fi
  (
    cd "$WEB_DIR"
    setsid npm run dev -- -p "$WEB_PORT" >>"$WEB_LOG" 2>&1 &
    echo $! >"$WEB_PID"
  )
  pid="$(read_pid "$WEB_PID")"
  wait_for_url "http://127.0.0.1:${WEB_PORT}/" "web"
  echo "web started  pid ${pid}  http://127.0.0.1:${WEB_PORT}/"
}

start_engine
start_web
echo "radar  http://127.0.0.1:${WEB_PORT}/radar"
echo "logs   $ENGINE_LOG"
echo "       $WEB_LOG"
