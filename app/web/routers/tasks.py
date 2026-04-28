# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException

from app.web.utils import db_execute, db_query_all, db_query_one, require_openapi

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks():
    items = db_query_all(
        """
        SELECT id, title, save_path, magnet, is_download, retry_count, completed_at, created_at
        FROM offline_task
        ORDER BY is_download ASC, created_at DESC
        """
    )
    return {"items": items}


@router.post("/{task_id}/retry")
def retry_task(task_id: int):
    rows = db_query_all("SELECT * FROM offline_task WHERE id = ?", (task_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Offline task not found")

    task = rows[0]
    openapi = require_openapi()
    ok = openapi.offline_download_specify_path(task["magnet"], task["save_path"])
    if not ok:
        db_execute("UPDATE offline_task SET retry_count = retry_count + 1 WHERE id = ?", (task_id,))
        raise HTTPException(status_code=502, detail="Failed to submit retry")

    db_execute("UPDATE offline_task SET retry_count = retry_count + 1 WHERE id = ?", (task_id,))
    return {"ok": True, "id": task_id}


@router.delete("/all")
def clear_tasks():
    db_execute("DELETE FROM offline_task WHERE is_download = 0")
    return {"ok": True}


@router.delete("/{task_id}")
def delete_task(task_id: int):
    exists = db_query_one("SELECT COUNT(*) FROM offline_task WHERE id = ?", (task_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Offline task not found")
    db_execute("DELETE FROM offline_task WHERE id = ?", (task_id,))
    return {"ok": True}
