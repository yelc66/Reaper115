# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.web.utils import db_execute, db_query_all, db_query_one, require_openapi

router = APIRouter(prefix="/api/sehua", tags=["sehua"])


class BatchDownloadRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


def _build_filters(section: str | None, status: int | None, keyword: str | None):
    filters = []
    params = []
    if section:
        filters.append("section_name = ?")
        params.append(section)
    if status is not None:
        filters.append("is_download = ?")
        params.append(status)
    if keyword:
        filters.append("(title LIKE ? OR av_number LIKE ? OR magnet LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    return where, params


@router.get("")
def list_sehua(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    section: str | None = None,
    status: int | None = Query(None, ge=0, le=1),
    keyword: str | None = None,
):
    where, params = _build_filters(section, status, keyword)
    total = db_query_one(f"SELECT COUNT(*) FROM sehua_data {where}", tuple(params)) or 0
    offset = (page - 1) * size
    items = db_query_all(
        f"""
        SELECT id, section_name, av_number, title, movie_type, size, magnet,
               post_url, publish_date, pub_url, image_path, save_path,
               is_download, created_at
        FROM sehua_data
        {where}
        ORDER BY publish_date DESC, created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [size, offset]),
    )
    return {"page": page, "size": size, "total": total, "items": items}


@router.post("/{item_id}/download")
def download_one(item_id: int):
    rows = db_query_all("SELECT * FROM sehua_data WHERE id = ?", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Sehua item not found")

    item = rows[0]
    openapi = require_openapi()
    ok = openapi.offline_download_specify_path(item["magnet"], item["save_path"])
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to submit offline download")
    return {"ok": True, "id": item_id, "save_path": item["save_path"]}


@router.post("/batch-download")
def batch_download(payload: BatchDownloadRequest):
    if not payload.ids:
        raise HTTPException(status_code=400, detail="ids cannot be empty")

    placeholders = ",".join(["?"] * len(payload.ids))
    rows = db_query_all(f"SELECT * FROM sehua_data WHERE id IN ({placeholders})", tuple(payload.ids))
    if not rows:
        raise HTTPException(status_code=404, detail="No sehua items found")

    openapi = require_openapi()
    submitted = []
    failed = []
    for row in rows:
        ok = openapi.offline_download_specify_path(row["magnet"], row["save_path"])
        if ok:
            submitted.append(row["id"])
        else:
            failed.append(row["id"])

    return {"ok": len(failed) == 0, "submitted": submitted, "failed": failed}


@router.delete("/{item_id}")
def delete_one(item_id: int):
    exists = db_query_one("SELECT COUNT(*) FROM sehua_data WHERE id = ?", (item_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Sehua item not found")
    db_execute("DELETE FROM sehua_data WHERE id = ?", (item_id,))
    return {"ok": True}
