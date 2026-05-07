#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export TG115_DEBUG="${TG115_DEBUG:-1}"
export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/app:$ROOT_DIR/app/utils:$ROOT_DIR/app/core:$ROOT_DIR/app/handlers"

exec "$ROOT_DIR/.venv/bin/python" -c "import init; init.init(); init.initialize_115open(); import uvicorn; from app.web.server import create_app; uvicorn.run(create_app(), host='127.0.0.1', port=8115, log_level='info')"
