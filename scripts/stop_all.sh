#!/usr/bin/env bash
# Stop the Aether engine and dashboard started by start_all.sh.
# Also stops a listener on these ports when its command is this repo.
set -euo pipefail
source "$(dirname "$0")/common.sh"

stop_matching() {
  local label="$1"
  local pidfile="$2"
  local port="$3"
  local match="$4"
  local pid stopped=0

  pid="$(read_pid "$pidfile")"
  if pid_alive "$pid"; then
    echo "stopping ${label} pid ${pid}"
    kill_pid_tree "$pid"
    wait_until_dead "$pid"
    stopped=1
  fi
  rm -f "$pidfile"

  while read -r pid; do
    [[ -n "$pid" ]] || continue
    if "$match" "$pid"; then
      echo "stopping ${label} listener pid ${pid}"
      kill_pid_tree "$pid"
      wait_until_dead "$pid"
      stopped=1
    fi
  done < <(port_pids "$port")

  if [[ "$stopped" == "0" ]]; then
    echo "${label} is not running"
  else
    echo "${label} stopped"
  fi
}

stop_matching "web" "$WEB_PID" "$WEB_PORT" is_web_proc
stop_matching "engine" "$ENGINE_PID" "$ENGINE_PORT" is_engine_proc
