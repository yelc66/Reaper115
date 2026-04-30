# -*- coding: utf-8 -*-

import os
import json
import asyncio

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import init
from app.web.utils import read_yaml, write_yaml

router = APIRouter(prefix="/api/system", tags=["system"])


class ConfigUpdateRequest(BaseModel):
    config: dict


def _has_real_value(value, placeholder: str) -> bool:
    return bool(value) and str(value).strip().lower() != placeholder.lower()


@router.get("/status")
def system_status():
    token_file_exists = os.path.exists(init.TOKEN_FILE)
    openapi_ready = False
    user_info = None
    if init.openapi_115 is not None:
        try:
            user_info = init.openapi_115.get_user_info()
            openapi_ready = user_info is not None
        except Exception as exc:
            init.logger.warn(f"获取115用户信息失败: {exc}")

    return {
        "openapi_ready": openapi_ready,
        "token_file_exists": token_file_exists,
        "crawl_running": init.CRAWL_SEHUA_STATUS == 1,
        "debug_mode": init.debug_mode,
        "paths": {
            "config": init.CONFIG_FILE,
            "strategy": init.STRATEGY_FILE,
            "db": init.DB_FILE,
            "token": init.TOKEN_FILE,
        },
        "user_info": user_info,
    }


@router.get("/config")
def get_config():
    return {"config": read_yaml(init.CONFIG_FILE)}


@router.put("/config")
def update_config(payload: ConfigUpdateRequest):
    write_yaml(init.CONFIG_FILE, payload.config)
    init.load_yaml_config()
    return {"ok": True, "config": init.bot_config}


@router.post("/test/telegram")
def test_telegram_config():
    bot_token = init.bot_config.get("bot_token", "")
    allowed_user = init.bot_config.get("allowed_user", "")

    if not _has_real_value(bot_token, "your_bot_token"):
        raise HTTPException(status_code=400, detail="Telegram Bot Token 未填写")
    if not _has_real_value(allowed_user, "your_user_id"):
        raise HTTPException(status_code=400, detail="Telegram 授权用户 ID 未填写")

    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Telegram 连接失败: {exc}") from exc

    if response.status_code != 200 or not payload.get("ok"):
        description = payload.get("description") if isinstance(payload, dict) else response.text
        raise HTTPException(status_code=400, detail=f"Telegram Token 验证失败: {description}")

    bot_info = payload.get("result", {})
    return {
        "ok": True,
        "message": f"Telegram 验证通过: @{bot_info.get('username', 'unknown')}",
        "bot": bot_info,
    }


def _load_115_tokens():
    try:
        if os.path.exists(init.TOKEN_FILE):
            with open(init.TOKEN_FILE, "r", encoding="utf-8") as token_file:
                return json.load(token_file) or {}
    except Exception as exc:
        init.logger.warn(f"读取115 Token文件失败: {exc}")
    return {}


def _save_115_tokens(access_token: str, refresh_token: str):
    os.makedirs(os.path.dirname(init.TOKEN_FILE), exist_ok=True)
    with open(init.TOKEN_FILE, "w", encoding="utf-8") as token_file:
        json.dump({"access_token": access_token, "refresh_token": refresh_token}, token_file)


def _test_115_user_info(access_token: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": init.USER_AGENT,
    }
    response = requests.get("https://proapi.115.com/open/user/info", headers=headers, timeout=10)
    try:
        return response.json()
    except Exception:
        return {"code": response.status_code, "message": response.text}


def _refresh_115_access_token(refresh_token: str):
    response = requests.post(
        "https://passportapi.115.com/open/refreshToken",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": init.USER_AGENT},
        data={"refresh_token": refresh_token},
        timeout=10,
    )
    try:
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"115 Token 刷新失败: {response.text}") from exc

    if response.status_code == 200 and isinstance(payload, dict) and payload.get("state"):
        token_data = payload.get("data") or {}
        access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token")
        if access_token and new_refresh_token:
            _save_115_tokens(access_token, new_refresh_token)
            if init.openapi_115 is not None:
                init.openapi_115.access_token = access_token
                init.openapi_115.refresh_token = new_refresh_token
            return access_token, new_refresh_token

    raise HTTPException(status_code=400, detail=f"115 Token 刷新失败: {payload.get('message', 'unknown error')}")


@router.post("/test/115")
def test_115_config():
    token_file = _load_115_tokens()
    access_token = init.bot_config.get("access_token", "")
    refresh_token = init.bot_config.get("refresh_token", "")

    if not _has_real_value(access_token, "your_access_token"):
        access_token = token_file.get("access_token") or getattr(init.openapi_115, "access_token", "")
    if not _has_real_value(refresh_token, "your_refresh_token"):
        refresh_token = token_file.get("refresh_token") or getattr(init.openapi_115, "refresh_token", "")

    if not access_token:
        app_id = init.bot_config.get("115_app_id", "")
        if _has_real_value(app_id, "your_115_app_id"):
            raise HTTPException(status_code=400, detail="115 App ID 已保存，但还没有可用 Token，请先完成扫码授权")
        raise HTTPException(status_code=400, detail="115 Access Token 未填写")

    payload = _test_115_user_info(access_token)
    if isinstance(payload, dict) and payload.get("code") == 0:
        return {"ok": True, "message": "115 验证通过", "user": payload.get("data")}

    code = payload.get("code") if isinstance(payload, dict) else None
    if code in (40140125, 40140116, 40140119) and refresh_token:
        access_token, _ = _refresh_115_access_token(refresh_token)
        payload = _test_115_user_info(access_token)
        if isinstance(payload, dict) and payload.get("code") == 0:
            return {"ok": True, "message": "115 验证通过，Token 已刷新", "user": payload.get("data")}

    message = payload.get("message") if isinstance(payload, dict) else "unknown error"
    raise HTTPException(status_code=400, detail=f"115 验证失败: {message}")


# ---------- 115 扫码授权 ----------

_qr_session: dict = {}


@router.get("/115/qrcode")
def get_115_qrcode():
    app_id = init.bot_config.get("115_app_id", "")
    if not _has_real_value(app_id, "your_115_app_id"):
        raise HTTPException(status_code=400, detail="115 App ID 未填写，请先在配置管理中填写")

    if init.openapi_115 is None:
        from app.core.open_115 import OpenAPI_115
        init.openapi_115 = OpenAPI_115.__new__(OpenAPI_115)
        init.openapi_115.access_token = ""
        init.openapi_115.refresh_token = ""
        init.openapi_115.lock = __import__("threading").Lock()
        init.openapi_115.refresh_lock = __import__("threading").Lock()

    try:
        session = init.openapi_115.auth_pkce_get_qr(app_id)
        _qr_session.clear()
        _qr_session.update(session)
        return {"ok": True, "qr_b64": session["qr_b64"]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/115/qrcode/status")
async def poll_115_qrcode_status():
    if not _qr_session:
        raise HTTPException(status_code=400, detail="请先获取二维码")

    async def event_stream():
        while True:
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: init.openapi_115.auth_pkce_poll(
                        _qr_session["uid"],
                        _qr_session["time"],
                        _qr_session["sign"],
                        _qr_session["verifier"],
                        _qr_session["app_id"],
                    ),
                )
                yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
                if result["done"]:
                    if result["status"] == "success":
                        init.initialize_115open()
                    break
            except Exception as exc:
                yield f"data: {json.dumps({'status': 'error', 'done': True, 'message': str(exc)})}\n\n"
                break
            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
