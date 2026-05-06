#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/web-ui"
BACKEND_LOG="$ROOT_DIR/tmp/dev-backend.log"
FRONTEND_LOG="$ROOT_DIR/tmp/dev-frontend.log"

BACKEND_PID=""
FRONTEND_PID=""
TAIL_PID=""

usage() {
  cat <<'EOF'
Usage: scripts/start-dev.sh [--api-only|--bot] [--check-browser] [--skip-install]

Starts the local development stack:
  - backend: FastAPI API only by default, or the full Telegram bot with --bot
  - frontend: Vite dev server

Options:
  --api-only      Start only the FastAPI backend thread entrypoint (default)
  --bot           Start app/115bot.py through scripts/dev.sh
  --check-browser Check the configured remote Selenium browser and exit
  --skip-install  Do not create venv/install npm packages automatically
  -h, --help      Show this help

Environment overrides:
  BACKEND_PORT=8000
  FRONTEND_HOST=127.0.0.1
  FRONTEND_PORT=5173
  VITE_API_BASE_URL=http://127.0.0.1:8000
EOF
}

MODE="api-only"
CHECK_BROWSER=0
SKIP_INSTALL=0
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:${BACKEND_PORT}}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --api-only)
      MODE="api-only"
      ;;
    --bot)
      MODE="bot"
      ;;
    --check-browser)
      CHECK_BROWSER=1
      ;;
    --skip-install)
      SKIP_INSTALL=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

log() {
  printf '[start-dev] %s\n' "$*"
}

install_hint_for_pip() {
  cat >&2 <<'EOF'
Python venv was found, but pip/ensurepip is missing.

On Ubuntu 24.04 / WSL2, install the venv package and recreate the virtualenv:

  sudo apt update
  sudo apt install -y python3.12-venv python3-pip
  rm -rf .venv
  ./scripts/start-dev.sh

EOF
}

cleanup() {
  log "stopping dev processes..."
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$TAIL_PID" ] && kill -0 "$TAIL_PID" 2>/dev/null; then
    kill "$TAIL_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cd "$ROOT_DIR"
mkdir -p config tmp

if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/.env.example" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  log "created .env from .env.example"
fi

if [ ! -f "$ROOT_DIR/config/config.yaml" ] && [ -f "$ROOT_DIR/config/config.yaml.example" ]; then
  cp "$ROOT_DIR/config/config.yaml.example" "$ROOT_DIR/config/config.yaml"
  log "created config/config.yaml from config/config.yaml.example"
fi

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

if [ ! -f "$WEB_DIR/.env" ]; then
  printf 'VITE_API_BASE_URL=%s\n' "$VITE_API_BASE_URL" > "$WEB_DIR/.env"
  log "created web-ui/.env"
fi

if [ "$SKIP_INSTALL" -eq 0 ]; then
  if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
    if command -v python3.12 >/dev/null 2>&1; then
      python3.12 -m venv "$ROOT_DIR/.venv"
    elif command -v python3 >/dev/null 2>&1; then
      python3 -m venv "$ROOT_DIR/.venv"
    else
      echo "Python 3.12 is required, but python3.12/python3 was not found." >&2
      exit 1
    fi
    log "created Python virtualenv at .venv"
  fi

  if ! "$ROOT_DIR/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
    if "$ROOT_DIR/.venv/bin/python" -m ensurepip --upgrade >/dev/null 2>&1; then
      "$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip
    else
      install_hint_for_pip
      exit 1
    fi
  fi

  if [ ! -f "$ROOT_DIR/.venv/.requirements-installed" ] || [ "$ROOT_DIR/requirements.txt" -nt "$ROOT_DIR/.venv/.requirements-installed" ]; then
    "$ROOT_DIR/.venv/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"
    touch "$ROOT_DIR/.venv/.requirements-installed"
  fi

  if [ ! -d "$WEB_DIR/node_modules" ]; then
    if ! command -v npm >/dev/null 2>&1; then
      echo "npm was not found. Install Node.js 20+ first, then rerun this script." >&2
      exit 1
    fi
    (cd "$WEB_DIR" && npm ci)
    log "installed web-ui npm dependencies"
  fi
elif [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo ".venv is missing. Rerun without --skip-install to create it automatically." >&2
  exit 1
fi

if [ -f "$ROOT_DIR/config/config.yaml" ] && [ "$MODE" = "bot" ] && grep -Eq 'your_bot_token|your_user_id|your_115_app_id|your_access_token|your_refresh_token' "$ROOT_DIR/config/config.yaml"; then
  log "warning: config/config.yaml still contains placeholder values; backend may fail until required values are filled."
fi

export TG115_DEBUG=1
export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/app:$ROOT_DIR/app/utils:$ROOT_DIR/app/core:$ROOT_DIR/app/handlers"

if [ "$CHECK_BROWSER" -eq 1 ]; then
  "$ROOT_DIR/.venv/bin/python" - <<'PY'
import init
from app.core.selenium_browser import check_browser_health

init.init()
ok, message = check_browser_health()
if ok:
    init.logger.info(message)
else:
    init.logger.error(f"浏览器检测失败：{message}")
    raise SystemExit(1)
PY
  exit $?
fi

if "$ROOT_DIR/.venv/bin/python" - "$BACKEND_PORT" "$FRONTEND_PORT" <<'PY'
import socket
import sys

busy = []
for raw_port in sys.argv[1:]:
    port = int(raw_port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            busy.append(str(port))

if busy:
    print(",".join(busy))
    sys.exit(1)
PY
then
  :
else
  echo "Port already in use. Free these ports or override BACKEND_PORT/FRONTEND_PORT." >&2
  exit 1
fi

log "backend mode: $MODE"
if [ "$MODE" = "bot" ]; then
  "$ROOT_DIR/scripts/dev.sh" >"$BACKEND_LOG" 2>&1 &
else
  "$ROOT_DIR/.venv/bin/python" -c "import init; init.init(); init.initialize_115open(); import uvicorn; from app.web.server import create_app; uvicorn.run(create_app(), host='127.0.0.1', port=${BACKEND_PORT}, log_level='info')" >"$BACKEND_LOG" 2>&1 &
fi
BACKEND_PID="$!"

log "frontend API base: $VITE_API_BASE_URL"
(cd "$WEB_DIR" && VITE_API_BASE_URL="$VITE_API_BASE_URL" VITE_DEV_HOST="$FRONTEND_HOST" npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT") >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID="$!"

log "backend log: $BACKEND_LOG"
log "frontend log: $FRONTEND_LOG"
log "frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
log "backend:  http://127.0.0.1:${BACKEND_PORT}/api/health"
log "press Ctrl+C to stop both processes"

tail -n +1 -F "$BACKEND_LOG" "$FRONTEND_LOG" &
TAIL_PID="$!"

wait -n "$BACKEND_PID" "$FRONTEND_PID"
