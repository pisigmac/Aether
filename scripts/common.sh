# Shared paths for the Aether local scripts. Source this file; do not run it.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "source scripts/common.sh from another script" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.aether/run"
ENGINE_DIR="$ROOT/engine"
WEB_DIR="$ROOT/web"

ENGINE_HOST="${AETHER_ENGINE_HOST:-127.0.0.1}"
ENGINE_PORT="${AETHER_ENGINE_PORT:-18100}"
WEB_HOST="${AETHER_WEB_HOST:-0.0.0.0}"
WEB_PORT="${AETHER_WEB_PORT:-13100}"

ENGINE_PID="$RUN_DIR/engine.pid"
WEB_PID="$RUN_DIR/web.pid"
ENGINE_LOG="$RUN_DIR/engine.log"
WEB_LOG="$RUN_DIR/web.log"

export AETHER_DATA_DIR="${AETHER_DATA_DIR:-$ENGINE_DIR/data}"
if [[ -z "${AETHER_MODEL_PATH+x}" && -f "$AETHER_DATA_DIR/time_machine.json" ]]; then
  export AETHER_MODEL_PATH="$AETHER_DATA_DIR/time_machine.json"
fi
export AETHER_CORS_ORIGINS="${AETHER_CORS_ORIGINS:-http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}}"
export NEXT_PUBLIC_AETHER_API="${NEXT_PUBLIC_AETHER_API:-http://127.0.0.1:${ENGINE_PORT}}"
export NEXT_PUBLIC_SITE_URL="${NEXT_PUBLIC_SITE_URL:-http://127.0.0.1:${WEB_PORT}}"

mkdir -p "$RUN_DIR" "$AETHER_DATA_DIR"

engine_bin() {
  if [[ -x "$ENGINE_DIR/.venv/bin/uvicorn" ]]; then
    echo "$ENGINE_DIR/.venv/bin/uvicorn"
  elif command -v uvicorn >/dev/null 2>&1; then
    command -v uvicorn
  else
    echo "uvicorn is missing. From engine/: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
    return 1
  fi
}

http_code() {
  curl -sS -o /dev/null -w "%{http_code}" --max-time 3 "$1" 2>/dev/null || echo "000"
}

pid_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  tr -cd '0-9' <"$file"
}

cmdline() {
  local pid="$1"
  if [[ -r "/proc/$pid/cmdline" ]]; then
    tr '\0' ' ' <"/proc/$pid/cmdline"
  else
    ps -p "$pid" -o args= 2>/dev/null || true
  fi
}

proc_cwd() {
  readlink "/proc/$1/cwd" 2>/dev/null || true
}

is_engine_proc() {
  local cmd
  cmd="$(cmdline "$1")"
  [[ "$cmd" == *"aether.api:app"* && "$cmd" == *"--port ${ENGINE_PORT}"* ]]
}

is_web_proc() {
  local cmd cwd
  cmd="$(cmdline "$1")"
  cwd="$(proc_cwd "$1")"
  [[ "$cwd" == "$WEB_DIR"* || "$cmd" == *"$WEB_DIR"* ]] || return 1
  [[ "$cmd" == *"next dev"* || "$cmd" == *"next-server"* || "$cmd" == *"npm run dev"* ]]
}

port_pids() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u
  fi
}

kill_pid_tree() {
  local pid="$1"
  local child
  pid_alive "$pid" || return 0
  while read -r child; do
    [[ -n "$child" ]] && kill_pid_tree "$child"
  done < <(ps -o pid= --ppid "$pid" 2>/dev/null || true)
  kill -TERM "$pid" 2>/dev/null || true
}

wait_until_dead() {
  local pid="$1"
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    pid_alive "$pid" || return 0
    sleep 0.3
  done
  kill -KILL "$pid" 2>/dev/null || true
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local i code
  for i in $(seq 1 40); do
    code="$(http_code "$url")"
    if [[ "$code" =~ ^[23] ]]; then
      return 0
    fi
    sleep 0.5
  done
  echo "$label did not answer at $url. See the log under $RUN_DIR." >&2
  return 1
}
