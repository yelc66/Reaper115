# -*- coding: utf-8 -*-

import os
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import init
from app.web.routers import crawl, dashboard, sehua, strategy, system, tasks
from app.web.utils import install_log_buffer

_DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")


def create_app():
    app = FastAPI(title="Telegram-115Bot Web API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(dashboard.router)
    app.include_router(sehua.router)
    app.include_router(strategy.router)
    app.include_router(tasks.router)
    app.include_router(crawl.router)
    app.include_router(system.router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    # Serve the built React SPA when the dist directory is present (production).
    # API routes above take precedence because they are registered first.
    if os.path.isdir(_DIST_DIR):
        app.mount("/assets", StaticFiles(directory=os.path.join(_DIST_DIR, "assets")), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str):  # noqa: ARG001
            index = os.path.join(_DIST_DIR, "index.html")
            return FileResponse(index)

    return app


def _run_web_server(host: str, port: int):
    install_log_buffer()
    config = uvicorn.Config(create_app(), host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def start_web_server_in_thread():
    web_config = init.bot_config.get("web", {}) or {}
    if web_config.get("enable", True) is False:
        init.logger.info("Web API disabled by config")
        return None

    host = web_config.get("host", "0.0.0.0")
    port = int(web_config.get("port", 8000))
    thread = threading.Thread(target=_run_web_server, args=(host, port), daemon=True)
    thread.start()
    init.logger.info(f"Web API started on http://{host}:{port}")
    return thread
