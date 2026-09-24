#!/usr/bin/env bash
# Install Aether in one shot: clone, engine, dashboard, demo fixture, then start.
#   curl -fsSL https://raw.githubusercontent.com/pisigmac/Aether/main/install.sh | bash
# From a checkout you already have: ./install.sh
# Skip launch with AETHER_START=0. Choose a directory with AETHER_HOME.
set -euo pipefail

if [[ "${AETHER_INSTALL_RERUN:-}" != "1" ]]; then
  case "${BASH_SOURCE[0]:-}" in
    bash | - | "")
      tmp="$(mktemp)"
      cat >"$tmp"
      AETHER_INSTALL_RERUN=1 exec bash "$tmp" </dev/null
      ;;
  esac
fi

REPO_URL="${AETHER_REPO_URL:-https://github.com/pisigmac/Aether.git}"
ENGINE_PORT="${AETHER_ENGINE_PORT:-18100}"
WEB_PORT="${AETHER_WEB_PORT:-13100}"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Aether needs $1. $2" >&2
    exit 1
  fi
}

need git "Install git, then run this again."
need python3 "Install Python 3.10 or newer."
need node "Install Node.js 18 or newer."
need npm "Install Node.js 18 or newer, which includes npm."

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Aether needs Python 3.10 or newer. This is " + sys.version.split()[0])
PY

node -e 'const major = Number(process.versions.node.split(".")[0]); if (major < 18) { console.error("Aether needs Node.js 18 or newer. This is " + process.versions.node); process.exit(1); }'

find_checkout() {
  local script_dir candidate
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$script_dir/engine/pyproject.toml" && -f "$script_dir/web/package.json" ]]; then
    echo "$script_dir"
    return 0
  fi
  candidate="$(cd "$script_dir/../.." 2>/dev/null && pwd || true)"
  if [[ "$(basename "$script_dir")" == "public" && -n "$candidate" && -f "$candidate/engine/pyproject.toml" ]]; then
    echo "$candidate"
    return 0
  fi
  return 1
}

if ROOT="$(find_checkout)"; then
  echo "Installing into the checkout at $ROOT"
else
  ROOT="${AETHER_HOME:-$HOME/Aether}"
  if [[ -d "$ROOT/.git" ]]; then
    echo "Updating $ROOT"
    git -C "$ROOT" pull --ff-only
  elif [[ -e "$ROOT" ]]; then
    echo "$ROOT already exists and is not an Aether git checkout." >&2
    echo "Set AETHER_HOME to an empty path and run this again." >&2
    exit 1
  else
    echo "Cloning $REPO_URL into $ROOT"
    if [[ -n "${AETHER_REF:-}" ]]; then
      git clone --depth 1 --branch "$AETHER_REF" "$REPO_URL" "$ROOT" || exit 1
    else
      git clone --depth 1 "$REPO_URL" "$ROOT" || exit 1
    fi
  fi
fi

if [[ ! -f "$ROOT/engine/pyproject.toml" || ! -f "$ROOT/web/package.json" ]]; then
  echo "$ROOT does not look like Aether (missing engine/ or web/)." >&2
  exit 1
fi

echo "Creating the engine environment"
python3 -m venv "$ROOT/engine/.venv"
"$ROOT/engine/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/engine/.venv/bin/python" -m pip install -e "$ROOT/engine[dev]"

echo "Installing the dashboard"
(cd "$ROOT/web" && npm install)

if [[ ! -d "$ROOT/fixtures/polyglot-debt/.git" ]]; then
  echo "Seeding the demo repository"
  "$ROOT/engine/.venv/bin/python" "$ROOT/fixtures/polyglot-debt/seed_git.py"
fi

echo
echo "Installed Aether in $ROOT"
if [[ "${AETHER_START:-1}" == "1" ]]; then
  AETHER_ENGINE_PORT="$ENGINE_PORT" AETHER_WEB_PORT="$WEB_PORT" "$ROOT/scripts/start_all.sh"
else
  echo "Start it with:  $ROOT/scripts/start_all.sh"
  echo "Engine   http://127.0.0.1:${ENGINE_PORT}/health"
  echo "Bulletin http://127.0.0.1:${WEB_PORT}/"
fi
