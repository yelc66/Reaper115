# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Telegram-115Bot** is a Telegram bot that manages 115 Network Disk: offline downloads, sehua spider, directory sync, and STRM file generation for Emby.

The active development branch is **`feature/sehua-web`**, which narrows the bot to sehua-only crawling and adds a FastAPI web management UI. Phase 1 (Python backend cleanup) and Phase 2 (FastAPI routes) are complete; Phase 3 (React web UI) is next.

---

## Running & Building

```bash
# Local Docker build
docker build -t 115bot:latest .
docker compose up -d

# Run inside container with live config
docker exec -it tg-bot-115 python 115bot.py
```

For local development without Docker, set `TG115_DEBUG=1` — this switches all paths from `/config/…` to project-local `config/…`, `tmp/`, `app/images/`:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p config tmp && cp app/config.yaml.example config/config.yaml
# fill bot_token, allowed_user, 115_app_id in config/config.yaml
TG115_DEBUG=1 python app/115bot.py
```

There are no test commands — the project has no automated test suite.

---

## Architecture

### Entry & Startup Flow

`app/115bot.py` is the entry point. On startup:
1. `init.init()` — loads YAML config, creates logger, creates SQLite tables, creates `/tmp`
2. A background thread starts `queue_worker` (the TG message send loop)
3. `init.initialize_115open()` — initializes the 115 Open API client
4. All handlers are registered into `python-telegram-bot`'s `Application`
5. `start_scheduler_in_thread()` — APScheduler runs sehua spider + retry tasks on cron
6. `start_web_server_in_thread()` — FastAPI Web API starts in a daemon thread when `web.enable` is true

### Global State (`app/init.py`)

All shared state lives as module-level globals in `init.py` and is accessed via `import init` throughout every file:

| Global | Type | Purpose |
|---|---|---|
| `init.bot_config` | dict | Loaded from `/config/config.yaml` |
| `init.logger` | Logger | Custom logger (file + console) |
| `init.openapi_115` | OpenAPI_115 | 115 Open Platform client |
| `init.CRAWL_SEHUA_STATUS` | int | 0=idle, 1=running (prevents concurrent crawls) |
| `init.tg_user_client` | None | Stub — telethon removed in sehua-web branch |
| `init.DB_FILE` | str | `/config/db.db` |

### Database (SQLite via `app/utils/sqlitelib.py`)

Used as a context manager: `with SqlLiteLib() as sqlite: sqlite.query_all(sql)`.

Key tables:
- `sehua_data` — crawled sehua resources (main table for sehua-web)
- `offline_task` — failed downloads pending retry

### Message Queue (`app/utils/message_queue.py`)

Background `asyncio.Queue` runs in its own thread/event loop. All TG notifications from sync worker threads use `add_task_to_queue(user_id, photo_url, message)` — never call `bot.send_message` directly from a non-async context.

### 115 API (`app/core/open_115.py`)

Wraps the 115 Open Platform REST API. Key methods used everywhere:
- `offline_download_specify_path(url, path)` — submit offline download
- `get_offline_tasks()` — poll task status
- `del_offline_task(info_hash)` — delete cloud task
- `auto_clean_all(path)` — remove ad files from directory
- `rename(old_path, new_name)` — rename in 115
- `get_files_from_dir(path)` — list files

### Sehua Spider (`app/core/sehua_spider.py`)

Uses SeleniumBase (with optional remote Selenium via `REMOTE_SELENIUM_URL`) or FlareSolverr (`FLARESOLVERR_URL`) to scrape sehuatang.net. Sections and save paths come from `config.yaml` → `sehua_spider.sections`. Filter rules are in `/config/crawling_strategy.yaml`.

Two entry points:
- `sehua_spider_start()` — scheduled, crawls yesterday
- `sehua_spider_by_date(date)` — manual via `/csh` command

### STRM / Emby Integration (`app/utils/media_utils.py`)

After successful offline download:
1. `create_strm_file(115_path, file_list)` — writes `.strm` files to `strm_root`
2. `notice_emby_scan_library(115_path)` — POSTs to Emby API

`strm_mode` in config controls behavior: `strm_302` (OpenList), `strm_local` (CD2 mount), or `disable`.

### Scheduler (`app/core/scheduler.py`)

APScheduler `BlockingScheduler` in a daemon thread. Active jobs on `feature/sehua-web`:
- `sehua_spider_task` — cron, configurable time (default 03:00)
- `offline_task_retry_task` — cron 09:00 and 18:00
- `retry_failed_downloads` — interval every 12h
- `clear_request_count_task` — cron midnight

### Web API (`app/web/`)

Phase 2 is implemented. `app/web/server.py` creates the FastAPI app, mounts routers, enables CORS for the development frontend, and can be started alongside `115bot.py`.

Routers:
- `dashboard.py` — `GET /api/dashboard/stats`, `GET /api/dashboard/trend`
- `sehua.py` — paginated `sehua_data` list, single download, batch download, delete
- `strategy.py` — CRUD for `crawling_strategy.yaml`, regex test endpoint
- `tasks.py` — retry queue list, retry, delete, clear pending tasks
- `crawl.py` — manual crawl trigger, crawl status, SSE log stream
- `system.py` — token/client status, config read/write

---

## Configuration Files

- `/config/config.yaml` — main config (copied from `app/config.yaml.example`)
- `/config/crawling_strategy.yaml` — sehua section filter rules (regex per section)
- `/config/db.db` — SQLite database
- `/config/115_tokens.json` — 115 OAuth tokens (managed by `open_115.py`)

---

## Key Patterns

**Handler registration**: every handler file exposes `register_*_handlers(application)`. Only call these in `115bot.py`.

**Auth check**: every TG command handler starts with `if not init.check_user(usr_id): return`.

**Sehua-web branch deletions**: the following modules were removed and must not be re-imported — `aria2`, `cover_capture`, `fast_telethon`, `telethon`, `subscribe_movie`, `av_daily_update`, `javbus`, `t66y`, `video_downloader`, `auth_handler`, `rss_handler`, `aria2_handler`, `av_download_handler`, `subscribe_movie_handler`.

---

## Completed Phase 2

`app/web/` now contains the FastAPI server and 6 routers:

```
app/web/server.py            # FastAPI app, mount routers, start uvicorn alongside 115bot.py
app/web/routers/dashboard.py # GET /api/dashboard/stats, /trend
app/web/routers/sehua.py     # CRUD on sehua_data table
app/web/routers/strategy.py  # crawling_strategy.yaml management
app/web/routers/tasks.py     # offline_task retry queue
app/web/routers/crawl.py     # POST /api/crawl/trigger, SSE log stream
app/web/routers/system.py    # token status, config read/write
```

FastAPI dependencies are already in `requirements.txt`: `fastapi`, `uvicorn[standard]`, `sse-starlette`.

Verification already run:

```bash
python3 -m compileall app
TG115_DEBUG=1 PYTHONPATH="$PWD:$PWD/app:$PWD/app/utils:$PWD/app/core:$PWD/app/handlers" .venv/bin/python -c "import init; init.init(); from fastapi.testclient import TestClient; from app.web.server import create_app; client=TestClient(create_app()); print(client.get('/api/health').json())"
```

## Completed Phase 3

`web-ui/` contains a Vite + React 18 + TypeScript frontend. Stack: Tailwind CSS, React Router v6, TanStack Query v5, Axios, Zustand, Recharts, Lucide icons.

```
web-ui/src/
  main.tsx                  # QueryClient + BrowserRouter bootstrap
  App.tsx                   # Route tree (6 pages + AppLayout shell)
  api/client.ts             # Axios instance (VITE_API_BASE_URL)
  api/queries.ts            # All API call functions (dashboard/sehua/strategy/tasks/crawl/system)
  api/types.ts              # TypeScript types matching FastAPI response shapes
  components/AppLayout.tsx  # Responsive sidebar + header shell
  components/ui.tsx         # Button, Card, Badge, Input, Select, Textarea, PageHeader, etc.
  store/ui.ts               # Zustand sidebar open/close state
  lib/utils.ts              # cn(), formatDateTime(), formatNumber(), errorMessage()
  pages/Dashboard.tsx       # Stats cards, 30-day trend line chart, section pie, recent table
  pages/SehuaData.tsx       # Paginated table, keyword/section/status filters, batch download
  pages/Strategy.tsx        # Rule CRUD form + live regex test
  pages/Tasks.tsx           # Retry queue table, retry/delete/clear all
  pages/Crawl.tsx           # Date picker trigger + SSE real-time log viewer
  pages/System.tsx          # Status badges, path list, JSON config editor
```

Production integration:
- `app/web/server.py` serves `app/web/dist/` as static files with SPA fallback when the dist dir exists.
- `Dockerfile` uses a two-stage build: Node 20 builds `web-ui/` → dist is copied into the Python image at `/app/web/dist/`.
- In dev, run Vite dev server (`npm run dev` in `web-ui/`) and the FastAPI backend separately; the Vite proxy forwards `/api` to `http://127.0.0.1:8000`.

Dev setup:
```bash
cd web-ui && cp .env.example .env   # VITE_API_BASE_URL=http://127.0.0.1:8000
npm install && npm run dev          # http://localhost:5173
```
