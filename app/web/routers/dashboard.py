# -*- coding: utf-8 -*-

from fastapi import APIRouter, Query

from app.web.utils import db_query_all, db_query_one

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats():
    total = db_query_one("SELECT COUNT(*) FROM sehua_data") or 0
    # is_download: 0=未提交 1=已提交离线 2=后处理完成
    submitted = db_query_one("SELECT COUNT(*) FROM sehua_data WHERE is_download = 1") or 0
    finished = db_query_one("SELECT COUNT(*) FROM sehua_data WHERE is_download = 2") or 0
    downloaded = submitted + finished
    pending = db_query_one("SELECT COUNT(*) FROM sehua_data WHERE is_download = 0") or 0
    retry_pending = db_query_one("SELECT COUNT(*) FROM offline_task WHERE is_download = 0") or 0

    by_section = db_query_all(
        """
        SELECT section_name, COUNT(*) AS total,
               SUM(CASE WHEN is_download >= 1 THEN 1 ELSE 0 END) AS downloaded,
               SUM(CASE WHEN is_download = 2 THEN 1 ELSE 0 END) AS finished
        FROM sehua_data
        GROUP BY section_name
        ORDER BY total DESC
        """
    )
    recent = db_query_all(
        """
        SELECT id, section_name, title, publish_date, is_download, created_at
        FROM sehua_data
        ORDER BY created_at DESC
        LIMIT 10
        """
    )

    return {
        "total": total,
        "downloaded": downloaded,
        "submitted": submitted,
        "finished": finished,
        "pending": pending,
        "retry_pending": retry_pending,
        "by_section": by_section,
        "recent": recent,
    }


@router.get("/trend")
def get_trend(days: int = Query(30, ge=1, le=365)):
    rows = db_query_all(
        """
        SELECT date(publish_date) AS date,
               COUNT(*) AS total,
               SUM(CASE WHEN is_download >= 1 THEN 1 ELSE 0 END) AS downloaded
        FROM sehua_data
        WHERE date(publish_date) >= date('now', ?)
        GROUP BY date(publish_date)
        ORDER BY date(publish_date)
        """,
        (f"-{days} days",),
    )
    return {"days": days, "items": rows}
