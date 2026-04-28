# -*- coding: utf-8 -*-

import asyncio
import json
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

import init
from app.web.utils import LOG_BUFFER, parse_crawl_date

router = APIRouter(prefix="/api/crawl", tags=["crawl"])


class CrawlTriggerRequest(BaseModel):
    date: str | None = None


def _run_crawl(date: str):
    try:
        from app.core.sehua_spider import sehua_spider_by_date

        sehua_spider_by_date(date)
    except Exception as exc:
        init.logger.error(f"Web triggered crawl failed: {exc}")
        init.CRAWL_SEHUA_STATUS = 0


@router.post("/trigger")
def trigger_crawl(payload: CrawlTriggerRequest):
    date = parse_crawl_date(payload.date)
    if init.CRAWL_SEHUA_STATUS == 1:
        raise HTTPException(status_code=409, detail="Crawl task is already running")

    init.CRAWL_SEHUA_STATUS = 1
    thread = threading.Thread(target=_run_crawl, args=(date,), daemon=True)
    thread.start()
    init.logger.info(f"Web API triggered sehua crawl: {date}")
    return {"ok": True, "date": date}


@router.get("/status")
def crawl_status():
    return {"running": init.CRAWL_SEHUA_STATUS == 1}


@router.get("/logs")
async def stream_logs(request: Request):
    async def generate():
        index = max(len(LOG_BUFFER) - 50, 0)
        event_id = 0
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
