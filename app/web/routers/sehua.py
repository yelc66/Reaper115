# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import init
from app.web.utils import db_execute, db_query_all, db_query_one, require_openapi

router = APIRouter(prefix="/api/sehua", tags=["sehua"])
sehua_download_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="Web_Sehua_Download")
sehua_process_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Web_Sehua_Process")


class BatchDownloadRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


class BatchDeleteRequest(BaseModel):
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

    if not magnet or not save_path:
        init.logger.warn(f"[Web][涩花] {title} 缺少磁力或保存路径，跳过")
        return

    # 提交成功后直接标记 is_download=1，后处理由下次调度的 sehua_post_process 完成
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_execute(
        "UPDATE sehua_data SET is_download=1, submitted_at=? WHERE id=?",
        (now_str, item["id"])
    )
    init.logger.info(f"[Web][涩花] {title} 已提交离线，后处理等待下次调度")


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


@router.delete("/batch-delete")
def batch_delete(payload: BatchDeleteRequest):
    if not payload.ids:
        raise HTTPException(status_code=400, detail="ids cannot be empty")
    placeholders = ",".join(["?"] * len(payload.ids))
    deleted = db_query_one(f"SELECT COUNT(*) FROM sehua_data WHERE id IN ({placeholders})", tuple(payload.ids)) or 0
    db_execute(f"DELETE FROM sehua_data WHERE id IN ({placeholders})", tuple(payload.ids))
    return {"ok": True, "deleted": deleted}


@router.delete("/{item_id}")
def delete_one(item_id: int):
    exists = db_query_one("SELECT COUNT(*) FROM sehua_data WHERE id = ?", (item_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Sehua item not found")
    db_execute("DELETE FROM sehua_data WHERE id = ?", (item_id,))
    return {"ok": True}


def _process_single_item(item: dict) -> bool:
    """
    对单条 is_download=1 的条目执行去广告+重命名，成功后标记 is_download=2。

    save_path 存的是板块路径（如 /AV/涩花/高清中文字幕），资源实际落在
    save_path/<115任务名> 子目录下，必须先查 115 任务列表拿到任务名才能定位。
    """
    from app.core.offline_task_retry import _rename_by_title
    from app.utils.utils import get_magnet_hash

    item_id = item["id"]
    title = item.get("title") or f"sehua-{item_id}"
    save_path = item.get("save_path")
    magnet = item.get("magnet")

    if not save_path:
        init.logger.warning(f"[Web][涩花后处理] {title} 缺少 save_path，跳过")
        return False

    if not magnet:
        init.logger.warning(f"[Web][涩花后处理] {title} 缺少 magnet，跳过")
        return False

    openapi = init.openapi_115
    if not openapi:
        init.logger.warning(f"[Web][涩花后处理] openapi_115 未初始化，跳过")
        return False

    # 查 115 任务列表，找到该磁链对应的任务名（即实际下载后的文件/文件夹名）
    item_hash = (get_magnet_hash(magnet) or '').upper()
    offline_tasks = openapi.get_offline_tasks()
    if not offline_tasks:
        init.logger.warning(f"[Web][涩花后处理] {title} 获取115任务列表失败，跳过")
        return False

    task_map = {t['info_hash'].upper(): t for t in offline_tasks}
    task = task_map.get(item_hash)
    if not task:
        init.logger.warning(f"[Web][涩花后处理] {title} 在115任务列表中未找到对应任务，hash={item_hash}，跳过")
        return False

    resource_name = task.get('name', '')
    if not resource_name:
        init.logger.warning(f"[Web][涩花后处理] {title} 115任务缺少 name 字段，跳过")
        return False

    # sort_by_year_month 支持
    from app.core.offline_task_retry import add_year_month_to_path
    sort_by_ym = init.bot_config.get('sehuatang_spider', {}).get('sort_by_year_month', False)
    actual_save_path = add_year_month_to_path(sort_by_ym, save_path)
    final_path = f"{actual_save_path}/{resource_name}"

    try:
        if openapi.is_directory(final_path):
            init.logger.info(f"[Web][涩花后处理] {title} 开始广告清理: {final_path}")
            openapi.auto_clean_all(final_path)
            _rename_by_title(final_path, title)
        else:
            init.logger.info(f"[Web][涩花后处理] {title} 为单文件，跳过广告清理和重命名")
    except Exception as e:
        init.logger.error(f"[Web][涩花后处理] {title} 处理失败: {e}")
        return False

    db_execute("UPDATE sehua_data SET is_download=2 WHERE id=?", (item_id,))
    init.logger.info(f"[Web][涩花后处理] {title} 处理完成 ✓")
    return True


def _run_batch_post_process(items: list[dict]):
    """批量后处理入口，在线程池中顺序执行。"""
    init.POST_PROCESS_STATUS = 1
    total = len(items)
    init.logger.info(f"[Web][涩花后处理] 开始批量处理，共 {total} 条")
    ok_count = 0
    fail_count = 0
    try:
        for item in items:
            success = _process_single_item(item)
            if success:
                ok_count += 1
            else:
                fail_count += 1
    finally:
        init.POST_PROCESS_STATUS = 0
        init.logger.info(f"[Web][涩花后处理] 批量处理完成：成功 {ok_count}，失败/跳过 {fail_count}，共 {total} 条")


@router.get("/process-status")
def process_status():
    return {"running": init.POST_PROCESS_STATUS == 1}


@router.post("/{item_id}/post-process")
def post_process_one(item_id: int):
    rows = db_query_all("SELECT * FROM sehua_data WHERE id = ?", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Sehua item not found")

    item = dict(rows[0])
    if item.get("is_download") != 1:
        raise HTTPException(status_code=400, detail="只有 is_download=1（待后处理）的条目才能执行后处理")

    if init.POST_PROCESS_STATUS == 1:
        raise HTTPException(status_code=409, detail="后处理任务正在运行中，请稍候")

    sehua_process_executor.submit(_run_batch_post_process, [item])
    return {"ok": True, "id": item_id, "processing": True}


@router.post("/batch-post-process")
def batch_post_process():
    """对所有 is_download=1 的条目执行批量后处理。"""
    if init.POST_PROCESS_STATUS == 1:
        raise HTTPException(status_code=409, detail="后处理任务正在运行中，请稍候")

    items = db_query_all("SELECT * FROM sehua_data WHERE is_download=1 ORDER BY submitted_at ASC")
    if not items:
        return {"ok": True, "count": 0, "message": "没有待后处理的条目"}

    rows = [dict(item) for item in items]
    sehua_process_executor.submit(_run_batch_post_process, rows)
    return {"ok": True, "count": len(rows), "processing": True}
