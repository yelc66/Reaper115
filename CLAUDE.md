# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Telegram-115Bot** is a Telegram bot that manages 115 Network Disk: offline downloads, sehua spider, directory sync, and advertisement file cleanup.

The active branch is **`feature/sehua-web`** — bot narrowed to sehua-only crawling with a FastAPI + React web management UI. All three phases are complete and deployed together.

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

Web UI dev (runs against the FastAPI backend at `http://127.0.0.1:8000`):

```bash
cd web-ui && cp .env.example .env   # VITE_API_BASE_URL=http://127.0.0.1:8000
npm install && npm run dev          # http://localhost:5173
```

No automated test suite exists.

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

| Global                    | Type        | Purpose                                        |
| ------------------------- | ----------- | ---------------------------------------------- |
| `init.bot_config`         | dict        | Loaded from `/config/config.yaml`              |
| `init.logger`             | Logger      | Custom logger (file + console)                 |
| `init.openapi_115`        | OpenAPI_115 | 115 Open Platform client                       |
| `init.CRAWL_SEHUA_STATUS` | int         | 0=idle, 1=running (prevents concurrent crawls) |
| `init.DB_FILE`            | str         | `/config/db.db`                                |
| `init.STRATEGY_FILE`      | str         | `/config/crawling_strategy.yaml`               |

`TG115_DEBUG=1` switches `STRATEGY_FILE`, `DB_FILE`, etc. to project-local `config/` paths.

### Database (SQLite via `app/utils/sqlitelib.py`)

Used as a context manager: `with SqlLiteLib() as sqlite: sqlite.query_all(sql)`.

Key tables:

- `sehua_data` — crawled sehua resources
- `offline_task` — failed downloads pending retry

### Message Queue (`app/utils/message_queue.py`)

Background `asyncio.Queue` runs in its own thread/event loop. All TG notifications from sync worker threads use `add_task_to_queue(user_id, photo_url, message)` — never call `bot.send_message` directly from a non-async context. Pass `photo_url=None` for text-only messages.

### 115 API (`app/core/open_115.py`)

Wraps the 115 Open Platform REST API. Key methods used everywhere:

- `offline_download_specify_path(url, path)` — submit offline download
- `get_offline_tasks()` — poll task status
- `del_offline_task(info_hash)` — delete cloud task
- `auto_clean_all(path)` — remove ad files from directory
- `rename(old_path, new_name)` — rename in 115
- `get_files_from_dir(path)` — list files

### Sehua Spider (`app/core/sehuatang_spider.py`)

Uses SeleniumBase (with optional remote Selenium via `REMOTE_SELENIUM_URL`) or FlareSolverr (`FLARESOLVERR_URL`) to scrape sehuatang.net. Sections and save paths come from `config.yaml → sehuatang_spider.sections`.

Two entry points:

- `sehuatang_spider_start()` — scheduled, crawls yesterday
- `sehuatang_spider_by_date(date)` — manual via `/csh` command

Filter logic reads `crawling_strategy.yaml` on every invocation via `is_title_allowed(section_name, title)` and `match_strategy(result)`. Both use `_get_section_rules(config, site, section)` — pass `'sehuatang'` as site for the current spider.

Cover image download is controlled by `sehuatang_spider.notify_with_image` in `config.yaml` (default `true`). When `false`, `image_path` is skipped entirely and notifications fall back to text-only.

### Scheduler (`app/core/scheduler.py`)

APScheduler `BlockingScheduler` in a daemon thread. Active jobs:

- `sehuatang_spider_task` — cron, configurable time (default 03:00)
- `offline_task_retry_task` — cron 09:00 and 18:00
- `retry_failed_downloads` — interval every 12h
- `clear_request_count_task` — cron midnight

### Web API (`app/web/`)

`app/web/server.py` creates the FastAPI app, mounts routers, enables CORS for the development frontend, serves `app/web/dist/` as static files with SPA fallback when the dist dir exists.

Routers in `app/web/routers/`:

- `dashboard.py` — `GET /api/dashboard/stats`, `GET /api/dashboard/trend`
- `sehua.py` — paginated `sehua_data` list, single download, batch download, delete
- `strategy.py` — CRUD for `crawling_strategy.yaml` rules, regex test endpoint
- `tasks.py` — offline_task retry queue list, retry, delete, clear
- `crawl.py` — `POST /api/crawl/trigger`, crawl status, SSE log stream
- `system.py` — token/client status, config read/write, Telegram/115 connectivity test

Shared utilities in `app/web/utils.py`: `read_yaml`, `write_yaml`, `validate_regex`, `parse_crawl_date`, `db_query_all/one/execute`.

---

## Configuration Files

- `/config/config.yaml` — main config (copied from `app/config.yaml.example`)
- `/config/crawling_strategy.yaml` — title filter rules, structured as `{site → section → [rules]}`
- `/config/db.db` — SQLite database
- `/config/115_tokens.json` — 115 OAuth tokens (managed by `open_115.py`)

### `crawling_strategy.yaml` format

```yaml
sehuatang:
  高清中文字幕:
    - name: 无码字幕
      pattern: 无码字幕        # regex, case-insensitive
      save_path: /AV/涩花/无码字幕
  亚洲有码原创:
    - name: 某规则
      pattern: .*关键词.*
      save_path: /AV/涩花/xxx

another_site:                  # future sites go here at the top level
  某分类:
    - name: 规则
      pattern: .*
      save_path: /AV/xxx
```

A section with no rules = all titles pass. The strategy router flattens this to a list with sequential integer IDs for the REST API, then rebuilds the nested structure on write.

### Key `config.yaml` options under `sehuatang_spider`

| Key                  | Default | Purpose                                             |
|----------------------|---------|-----------------------------------------------------|
| `enable`             | false   | Master switch for the spider                        |
| `notify_me`          | true    | Send TG notification on each successful download    |
| `notify_with_image`  | true    | Attach cover image to notification; false = text only, skips download |
| `sort_by_year_month` | false   | Create year/month subdirectories in save path       |
| `sections`           | []      | List of `{name, save_path}` to crawl                |

---

## Web UI (`web-ui/`)

Vite + React 18 + TypeScript. Stack: Tailwind CSS, React Router v6, TanStack Query v5, Axios, Zustand, Recharts, Lucide icons.

```
web-ui/src/
  api/client.ts       # Axios instance (VITE_API_BASE_URL)
  api/dto.ts          # Raw FastAPI response shapes (snake_case)
  api/models.ts       # Frontend domain types (camelCase)
  api/mappers.ts      # mapXxx() and toXxxDto() conversion functions
  api/queries.ts      # All API call functions using mappers
  api/types.ts        # Re-exports from models (legacy, keep for compatibility)
  components/ui.tsx   # Button, Card, Badge, Input, Select, Textarea, PageHeader, Switch, etc.
  pages/Strategy.tsx  # Crawler config panel (sehuatang_spider settings) + strategy rules CRUD
```

The DTO → model → mapper pattern means: `dto.ts` mirrors the API exactly, `models.ts` is what the UI uses (camelCase), `mappers.ts` converts between them. Add fields in all three when extending the API.

Production: `Dockerfile` uses a two-stage build — Node 20 builds `web-ui/` → dist copied into Python image at `/app/web/dist/`.

---

## Key Patterns

**Handler registration**: every handler file exposes `register_*_handlers(application)`. Only call these in `115bot.py`.

**Auth check**: every TG command handler starts with `if not init.check_user(usr_id): return`.

**Deleted modules** (must not be re-imported): `aria2`, `cover_capture`, `fast_telethon`, `telethon`, `subscribe_movie`, `av_daily_update`, `javbus`, `t66y`, `video_downloader`, `auth_handler`, `rss_handler`, `aria2_handler`, `av_download_handler`, `subscribe_movie_handler`.
