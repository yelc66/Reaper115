# Phase 3 Handoff

This file is the starting point for the next session.

## Status

Phase 2 is complete. The FastAPI backend is implemented under `app/web/` and is wired into `app/115bot.py`.

Implemented API surface:

```text
GET    /api/health
GET    /api/dashboard/stats
GET    /api/dashboard/trend?days=30
GET    /api/sehua?page&size&section&status&keyword
POST   /api/sehua/{id}/download
POST   /api/sehua/batch-download
DELETE /api/sehua/{id}
GET    /api/strategy/rules
POST   /api/strategy/rules
PUT    /api/strategy/rules/{id}
DELETE /api/strategy/rules/{id}
POST   /api/strategy/test
GET    /api/tasks
POST   /api/tasks/{id}/retry
DELETE /api/tasks/all
DELETE /api/tasks/{id}
POST   /api/crawl/trigger
GET    /api/crawl/status
GET    /api/crawl/logs
GET    /api/system/status
GET    /api/system/config
PUT    /api/system/config
```

## Verification Already Run

```bash
python3 -m compileall app
TG115_DEBUG=1 PYTHONPATH="$PWD:$PWD/app:$PWD/app/utils:$PWD/app/core:$PWD/app/handlers" .venv/bin/python -c "import init; init.init(); from fastapi.testclient import TestClient; from app.web.server import create_app; client=TestClient(create_app()); print(client.get('/api/health').json())"
```

## Phase 3 Target

Create `web-ui/` as a Vite + React 18 + TypeScript frontend.

Planned stack:

```text
Vite
React 18
TypeScript
shadcn/ui
Tailwind CSS
React Router v6
TanStack Query v5
Axios
Zustand
Recharts
```

Planned pages:

- Dashboard: stats cards, trend chart, section distribution, recent activity
- Sehua Data: paginated table, section/status/keyword filters, single and batch download
- Strategy: rule CRUD, regex test
- Tasks: retry queue, retry/delete/clear
- Crawl: date trigger, status, SSE log viewer
- System: token/client status, config editor

Suggested dev API base:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```
