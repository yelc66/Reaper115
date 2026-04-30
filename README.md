<div align="center">
    <h1>Reaper115</h1>
    <p>Sehua crawler + 115 offline downloader with a web management UI</p>
</div>

A Python-based Telegram bot focused on sehua content crawling and 115 Network Disk offline downloads, paired with a FastAPI + React web management dashboard.

## Features

- **Sehua Spider**
  - Automatically crawls sehuatang.net on a daily schedule
  - Configurable sections and save paths
  - Title filter rules with regex matching via web UI
  - Optional cover image notifications via Telegram

- **Web Management UI**
  - Dashboard with crawl stats and trends
  - Browse and download crawled sehua resources
  - Strategy rule CRUD (per-section filter rules with regex test)
  - Manual crawl trigger with real-time SSE log stream
  - Offline task retry queue management
  - System config and connectivity check

- **115 Offline Download**
  - Submit resources directly to 115 Network Disk
  - Based on 115 Open Platform API for stable performance
  - Retry queue for failed downloads

## Quick Start

### Requirements

- Docker + Docker Compose
- 115 Open Platform App ID ([apply here](https://open.115.com/))
- A Telegram bot token

### Deploy with Docker Compose

1. **Clone and configure**
   ```bash
   git clone https://github.com/yelc668/Reaper115.git
   cd Reaper115
   mkdir -p config tmp
   cp app/config.yaml.example config/config.yaml
   ```

   Edit `config/config.yaml` — minimum required fields:
   - `bot_token` — Telegram bot token
   - `allowed_user` — your Telegram user ID
   - `115_app_id` — from 115 Open Platform

2. **Start**
   ```bash
   docker compose up -d
   ```

   The bot starts on Telegram and the web UI is available at `http://<host>:8000`.

3. **Build locally** (optional)
   ```bash
   docker build -t reaper115-bot:latest .
   docker compose up -d
   ```

### Local Development

For local development without Docker, set `TG115_DEBUG=1` to use project-local paths:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p config tmp
cp app/config.yaml.example config/config.yaml
# fill bot_token, allowed_user, 115_app_id in config/config.yaml
TG115_DEBUG=1 python app/115bot.py
```

Web UI dev server (proxies API to `http://127.0.0.1:8000`):

```bash
cd web-ui && cp .env.example .env   # set VITE_API_BASE_URL=http://127.0.0.1:8000
npm install && npm run dev          # http://localhost:5173
```

## Configuration

All options are documented in `app/config.yaml.example`.

### Key spider options (`sehuatang_spider` in `config.yaml`)

| Key                 | Default | Description                                              |
|---------------------|---------|----------------------------------------------------------|
| `enable`            | false   | Master switch for the spider                             |
| `notify_me`         | true    | Send Telegram notification on each successful download   |
| `notify_with_image` | true    | Attach cover image; false = text-only, skips image fetch |
| `sort_by_year_month`| false   | Create year/month subdirectories in save path            |
| `sections`          | []      | List of `{name, save_path}` sections to crawl            |

### Crawl schedule

By default the spider runs at **03:00** daily. Configurable in `config.yaml` under `scheduler`.

### Selenium / FlareSolverr

The spider uses SeleniumBase. Two options for bypassing Cloudflare:

- **FlareSolverr** (recommended): set `FLARESOLVERR_URL` env var and uncomment the `flaresolverr` service in `docker-compose.yaml`
- **Remote Selenium**: set `REMOTE_SELENIUM_URL` and uncomment the `chrome` service

### Proxy

Set `HTTP_PROXY` / `HTTPS_PROXY` env vars in `docker-compose.yaml` if needed.

## Bot Commands

| Command        | Description                          |
|----------------|--------------------------------------|
| `/start`       | Show help                            |
| `/reload`      | Reload configuration from disk       |
| `/rl`          | Show offline retry list              |
| `/csh_yesterday` | Crawl yesterday's sehua data       |
| `/csh_today`   | Crawl today's sehua data             |
| `/csh_7days`   | Crawl recent 7 days of sehua data    |
| `/q`           | Cancel current conversation          |

Custom sehua crawls are still available by manually sending `/csh YYYYMMDD`.

## Directory Structure

```
.
├── app/
│   ├── 115bot.py              # Entry point
│   ├── config.yaml.example    # Configuration template
│   ├── core/                  # Spider, scheduler, 115 API client
│   ├── handlers/              # Telegram command handlers
│   ├── init.py                # Global state and startup
│   ├── utils/                 # DB, message queue, helpers
│   └── web/                   # FastAPI server and routers
├── web-ui/                    # Vite + React 18 + TypeScript frontend
├── config/                    # Runtime config (gitignored)
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```

## Web UI Stack

Vite · React 18 · TypeScript · Tailwind CSS · TanStack Query v5 · React Router v6 · Recharts

Pages: Dashboard · Sehua Data · Strategy · Crawl · Tasks · Config · System

## License

MIT License — see [LICENSE](LICENSE)

## Disclaimer

This project is for educational and research purposes only. Comply with all applicable laws and regulations. Users assume all risks.
