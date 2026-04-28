# -*- coding: utf-8 -*-

import os

from fastapi import APIRouter
from pydantic import BaseModel

import init
from app.web.utils import read_yaml, write_yaml

router = APIRouter(prefix="/api/system", tags=["system"])


class ConfigUpdateRequest(BaseModel):
    config: dict


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
