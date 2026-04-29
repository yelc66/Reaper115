# -*- coding: utf-8 -*-

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import init
from app.web.utils import db_execute, db_query_all, db_query_one, require_openapi

router = APIRouter(prefix="/api/sehua", tags=["sehua"])
sehua_download_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="Web_Sehua_Download")


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


def _process_manual_download(item: dict):
    title = item.get("title") or f"sehua-{item.get('id')}"
    magnet = item.get("magnet")
    save_path = item.get("save_path")
    info_hash = ""

    if not magnet or not save_path:
        init.logger.warn(f"[Web][涩花] {title} 缺少磁力或保存路径，跳过后处理")
        return

    try:
        init.logger.info(f"[Web][涩花] 开始检查手动离线任务: {title}")
        download_success, resource_name, info_hash = init.openapi_115.check_offline_download_success(magnet)

        if not download_success:
            init.logger.warn(f"[Web][涩花] {title} 离线未完成或超时，暂不标记为已下载")
            return

        final_path = f"{save_path}/{resource_name}"
        init.logger.info(f"[Web][涩花] {title} 离线完成，开始广告清理: {final_path}")

        if init.openapi_115.is_directory(final_path):
            init.openapi_115.auto_clean_all(final_path)
        else:
            temp_folder = Path(resource_name).stem
            init.openapi_115.create_dir_for_file(save_path, temp_folder)
            init.openapi_115.move_file(final_path, f"{save_path}/{temp_folder}")
            final_path = f"{save_path}/{temp_folder}"
            init.openapi_115.auto_clean_all(final_path)

        db_execute("UPDATE sehua_data SET is_download = 1 WHERE id = ?", (item["id"],))
        init.logger.info(f"[Web][涩花] {title} 手动离线后处理完成")

    except Exception as exc:
        init.logger.error(f"[Web][涩花] {title} 手动离线后处理失败: {exc}")
    finally:
        if info_hash:
            time.sleep(1)
            init.openapi_115.del_offline_task(info_hash, del_source_file=0)


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
    sehua_download_executor.submit(_process_manual_download, dict(item))
    return {"ok": True, "id": item_id, "save_path": item["save_path"], "processing": True}


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
            sehua_download_executor.submit(_process_manual_download, dict(row))
        else:
            failed.append(row["id"])

    return {"ok": len(failed) == 0, "submitted": submitted, "failed": failed, "processing": submitted}


@router.delete("/{item_id}")
def delete_one(item_id: int):
    exists = db_query_one("SELECT COUNT(*) FROM sehua_data WHERE id = ?", (item_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Sehua item not found")
    db_execute("DELETE FROM sehua_data WHERE id = ?", (item_id,))
    return {"ok": True}
