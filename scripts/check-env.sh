#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

test -x .venv/bin/python
.venv/bin/python --version

.venv/bin/python - <<'PY'
import fastapi
import uvicorn
import seleniumbase
import telegram
import yaml
import sse_starlette
print("python imports ok")
PY

test -f config/config.yaml
test -d tmp

if [ -d "/Applications/Google Chrome.app" ]; then
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
else
  echo "Google Chrome not found under /Applications" >&2
  exit 1
fi

test -x .venv/lib/python3.12/site-packages/seleniumbase/drivers/chromedriver
.venv/lib/python3.12/site-packages/seleniumbase/drivers/chromedriver --version

echo "dev environment ok"
