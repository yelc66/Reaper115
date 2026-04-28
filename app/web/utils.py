# -*- coding: utf-8 -*-

import logging
import os
import re
from collections import deque
from datetime import datetime
from typing import Any

import yaml
from fastapi import HTTPException

import init
from app.utils.sqlitelib import SqlLiteLib


LOG_BUFFER: deque[dict[str, str]] = deque(maxlen=500)


class WebLogBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            LOG_BUFFER.append(
                {
                    "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                    "level": record.levelname,
                    "message": self.format(record),
                }
            )
        except Exception:
            pass


def install_log_buffer():
    root_logger = logging.getLogger()
    if any(isinstance(handler, WebLogBufferHandler) for handler in root_logger.handlers):
        return

    handler = WebLogBufferHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(handler)


def db_query_all(sql: str, params: tuple[Any, ...] = ()):
    with SqlLiteLib() as sqlite:
        return sqlite.query_all(sql, params)


def db_query_one(sql: str, params: tuple[Any, ...] = ()):
    with SqlLiteLib() as sqlite:
        return sqlite.query_one(sql, params)


def db_execute(sql: str, params: tuple[Any, ...] = ()):
    with SqlLiteLib() as sqlite:
        sqlite.execute_sql(sql, params)


def read_yaml(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc


def write_yaml(path: str, data: Any):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Write YAML failed: {exc}") from exc


def parse_crawl_date(value: str | None):
    if not value:
        return datetime.now().strftime("%Y-%m-%d")

    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD or YYYYMMDD")


def validate_regex(pattern: str):
    try:
        re.compile(pattern)
    except re.error as exc:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {exc}") from exc


def require_openapi():
    if init.openapi_115 is None:
        raise HTTPException(status_code=503, detail="115 OpenAPI client is not initialized")
    return init.openapi_115
