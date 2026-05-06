# Reaper115 Web UI kit

Recreation of the Vite + React 18 + Tailwind admin from `web-ui/` in plain React + JSX (no build). Visuals are copied 1:1 from the source — the goal is pixel-fidelity, not a working backend.

## Screens (click-thru)

1. **Login** — single password card
2. **Dashboard** — system status panel + 4 stat cards + 30-day trend + section donut + recent table
3. **Sehua data** — filter row, paginated table, batch actions
4. **Strategy** — crawler config + rules table + regex tester
5. **Tasks** — failed-retry queue
6. **Crawl** — date presets + SSE log stream

## Files

```
index.html        ← stage; sidebar + header; routes between screens via state
shell.jsx         ← AppShell (Sidebar, TopBar, Page wrapper) + global mock data
ui.jsx            ← Button, Card, Badge, Input, Select, Switch, EmptyState, …
icons.jsx         ← inline Lucide-style SVG components used by the kit
Login.jsx
Dashboard.jsx
SehuaData.jsx
Strategy.jsx
Tasks.jsx
Crawl.jsx
```

## How to read

Open `index.html` directly. The bottom-left brand block in the sidebar is real; everything inside the main panel is mocked but visually accurate. Click any nav item to swap pages.
