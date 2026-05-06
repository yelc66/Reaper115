# -*- coding: utf-8 -*-

import asyncio
import json
import threading
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

import init
from app.web.utils import LOG_BUFFER, parse_crawl_date_range

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

CRAWL_MODE_LABELS = {
    "today": "今天",
    "yesterday": "昨天",
    "7days": "七天",
}


class CrawlTriggerRequest(BaseModel):
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    mode: str | None = None


def _run_crawl(crawl_mode: str):
    try:
        from app.core.sehuatang_spider import sehuatang_spider_by_date

        sehuatang_spider_by_date(crawl_mode)
    except Exception as exc:
        init.logger.error(f"Web triggered crawl failed: {exc}")
    finally:
        init.CRAWL_SEHUA_STATUS = 0


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _buf(level: str, message: str):
    """Write directly to LOG_BUFFER (bypasses logging handlers)."""
    LOG_BUFFER.append({"time": _ts(), "level": level, "message": message})


@router.post("/trigger")
def trigger_crawl(payload: CrawlTriggerRequest):
    init.logger.info(
        f"Web API crawl payload: mode={payload.mode}, date={payload.date}, start_date={payload.start_date}, end_date={payload.end_date}"
    )
    crawl_mode = payload.mode
    if not crawl_mode:
        if payload.start_date or payload.date or payload.end_date:
            start_date, end_date = parse_crawl_date_range(payload.start_date or payload.date, payload.end_date)
            crawl_mode = "7days" if start_date != end_date else start_date
        else:
            crawl_mode = "yesterday"
    if init.CRAWL_SEHUA_STATUS == 1:
        raise HTTPException(status_code=409, detail="Crawl task is already running")

    init.CRAWL_SEHUA_STATUS = 1
    thread = threading.Thread(target=_run_crawl, args=(crawl_mode,), daemon=True)
    thread.start()
    crawl_label = CRAWL_MODE_LABELS.get(crawl_mode, crawl_mode)
    init.logger.info(f"Web API triggered sehua crawl: {crawl_label}")

    _buf("INFO", f"抓取已触发：{crawl_label}")

    return {"ok": True, "mode": crawl_mode, "date": crawl_label}


@router.get("/status")
def crawl_status():
    return {"running": init.CRAWL_SEHUA_STATUS == 1}


@router.get("/logs")
async def stream_logs(request: Request):
    async def generate():
        # Immediately send a handshake so we can verify the SSE pipeline is alive
        yield {
            "event": "log",
            "id": "0",
            "data": json.dumps({"time": _ts(), "level": "INFO", "message": "SSE 连接成功"}, ensure_ascii=False),
        }

        index = max(len(LOG_BUFFER) - 50, 0)
        event_id = 1
        while True:
            if await request.is_disconnected():
                break

            while index < len(LOG_BUFFER):
                item = LOG_BUFFER[index]
                index += 1
                event_id += 1
                yield {
                    "event": "log",
                    "id": str(event_id),
                    "data": json.dumps(item, ensure_ascii=False),
                }
            await asyncio.sleep(1)

    return EventSourceResponse(generate(), ping=15)
