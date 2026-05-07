# -*- coding: utf-8 -*-

import os
import secrets
import threading

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import init
from app.core.selenium_browser import check_browser_health
from app.web.routers import crawl, dashboard, sehua, strategy, system, tasks
from app.web.utils import install_log_buffer

_DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")
_AUTH_EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/login",
}


class LoginRequest(BaseModel):
    key: str = ""


def _get_auth_key() -> str:
    env_key = os.getenv("WEB_AUTH_KEY", "").strip()
    if env_key:
        return env_key

    web_config = init.bot_config.get("web", {}) or {}
    return str(web_config.get("auth_key", "") or "").strip()


def _auth_required() -> bool:
    return bool(_get_auth_key())


def _is_authorized(candidate: str | None) -> bool:
    auth_key = _get_auth_key()
    if not auth_key:
        return True
    return secrets.compare_digest(candidate or "", auth_key)


def create_app():
    install_log_buffer()
    app = FastAPI(title="Telegram-115Bot Web API", version="0.1.0")

    @app.on_event("startup")
    def check_browser_on_startup():
        install_log_buffer()
        if not init.bot_config.get("sehuatang_spider", {}).get("enable", False):
            init.logger.info("启动浏览器检测跳过：涩花爬虫未启用")
            return

        ok, message = check_browser_health()
        if ok:
            init.logger.info(message)
        else:
            init.logger.error(f"启动浏览器检测未通过：{message}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def require_web_auth(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path.startswith("/api/") and path not in _AUTH_EXEMPT_PATHS:
            key = request.headers.get("x-web-auth-key") or request.query_params.get("key")
            if not _is_authorized(key):
                return JSONResponse({"detail": "Web UI authentication required"}, status_code=401)

        return await call_next(request)

    @app.get("/api/auth/status")
    def auth_status():
        return {"auth_required": _auth_required()}

    @app.post("/api/auth/login")
    def auth_login(payload: LoginRequest):
        if not _is_authorized(payload.key):
            raise HTTPException(status_code=401, detail="认证密钥不正确")
        return {"ok": True, "auth_required": _auth_required()}

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
    class _Config(uvicorn.Config):
        def configure_logging(self) -> None:
            super().configure_logging()
            install_log_buffer()  # re-install after every uvicorn logging reset

    config = _Config(create_app(), host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def start_web_server_in_thread():
    web_config = init.bot_config.get("web", {}) or {}
    if web_config.get("enable", True) is False:
        init.logger.info("Web API disabled by config")
        return None

    host = web_config.get("host", "0.0.0.0")
    port = int(web_config.get("port", 8115))
    thread = threading.Thread(target=_run_web_server, args=(host, port), daemon=True)
    thread.start()
    init.logger.info(f"Web API started on http://{host}:{port}")
    return thread
