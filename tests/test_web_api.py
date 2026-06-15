"""
Web API 接口测试（不依赖真实 115 / Telegram / Selenium）。

覆盖范围：
  - /api/health
  - /api/auth/status、/api/auth/login
  - /api/dashboard/stats、/api/dashboard/trend
  - /api/sehua  列表/筛选/删除/批量删除/提交离线/批量提交
  - /api/sehua/{id}/post-process、/api/sehua/batch-post-process、/api/sehua/process-status
  - /api/tasks  列表/删除/清空/重试

运行方式：
    python tests/test_web_api.py
"""

import os
import sys
import sqlite3
import tempfile
import types
import logging
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ─── 最小 init mock ───────────────────────────────────────────────────────────

_fake_init = types.ModuleType("init")
_fake_init.logger = logging.getLogger("test_web_api")
_fake_init.logger.setLevel(logging.DEBUG)
if not _fake_init.logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _fake_init.logger.addHandler(_h)

_fake_init.bot_config = {
    "web": {"enable": True, "auth_key": ""},
    "sehuatang_spider": {"sort_by_year_month": False},
}
_fake_init.CRAWL_SEHUA_STATUS = 0
_fake_init.POST_PROCESS_STATUS = 0
_fake_init.openapi_115 = MagicMock()

sys.modules["init"] = _fake_init


# ─── SQLite 临时库辅助 ────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sehua_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_name TEXT,
    av_number TEXT,
    title TEXT,
    movie_type TEXT,
    size TEXT,
    magnet TEXT,
    post_url TEXT,
    publish_date DATETIME,
    pub_url TEXT,
    image_path TEXT,
    save_path TEXT,
    is_download TINYINT DEFAULT 0,
    submitted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS offline_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    save_path TEXT,
    magnet TEXT,
    is_download TINYINT DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS missav_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_name TEXT,
    av_number TEXT,
    title TEXT,
    movie_type TEXT,
    size TEXT,
    magnet TEXT,
    post_url TEXT,
    publish_date DATETIME,
    pub_url TEXT,
    image_path TEXT,
    save_path TEXT,
    is_download TINYINT DEFAULT 0,
    submitted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

MAGNET_A = "magnet:?xt=urn:btih:AABBCCDD0011223344556677889900AABBCCDD00&dn=TestA"
MAGNET_B = "magnet:?xt=urn:btih:BBCCDD0011223344556677889900AABBCCDD0011&dn=TestB"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.executemany(
        """
        INSERT INTO sehua_data
            (section_name, av_number, title, movie_type, size, magnet,
             post_url, publish_date, pub_url, save_path, is_download, submitted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            ("高清中文字幕", "SSIS-001", "SSIS-001 无码字幕",   "无码", "1.5G", MAGNET_A,
             "https://example.com/c1.jpg", "2026-04-28", "https://sehuatang.net/t/1",
             "/AV/涩花/高清中文字幕", 0, None),
            ("国产原创",     "N/A",     "【麻豆】某某某 4K",   "无码", "2.0G", MAGNET_B,
             "https://example.com/c2.jpg", "2026-04-27", "https://sehuatang.net/t/2",
             "/AV/涩花/国产原创", 1, NOW),
            ("亚洲有码原创", "MIDV-010", "MIDV-010 某女优",    "有码", "2.5G", None,
             "https://example.com/c3.jpg", "2026-04-26", "https://sehuatang.net/t/3",
             "/AV/涩花/亚洲有码原创", 2, NOW),
        ],
    )
    conn.executemany(
        """
        INSERT INTO offline_task
            (title, save_path, magnet, is_download, retry_count)
        VALUES (?,?,?,?,?)
        """,
        [
            ("Task-A", "/AV/test", MAGNET_A, 0, 0),
            ("Task-B", "/AV/test", MAGNET_B, 1, 2),
        ],
    )
    conn.commit()
    return path, conn


def _make_fake_sqlite(db_path):
    class _FS:
        def __init__(self):
            self._conn = None
        def __enter__(self):
            self._conn = sqlite3.connect(db_path)
            self._conn.row_factory = sqlite3.Row
            return self
        def __exit__(self, *a):
            self._conn.commit()
            self._conn.close()
        def query_all(self, sql, params=()):
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]
        def query_one(self, sql, params=()):
            cur = self._conn.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None
        def execute_sql(self, sql, params=()):
            self._conn.execute(sql, params)
    return _FS()


# ─── 测试基类：每个 test 用独立临时 DB ───────────────────────────────────────

class _BaseWebTest(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _make_db()
        self.conn.close()
        self._db_patcher = patch(
            "app.web.utils.SqlLiteLib",
            side_effect=lambda *a, **kw: _make_fake_sqlite(self.db_path),
        )
        self._db_patcher.start()

        # reset 全局状态
        _fake_init.POST_PROCESS_STATUS = 0
        _fake_init.CRAWL_SEHUA_STATUS = 0
        _fake_init.bot_config["web"]["auth_key"] = ""
        _fake_init.openapi_115 = MagicMock()

        from app.web.server import create_app
        from fastapi.testclient import TestClient
        self.client = TestClient(create_app(), raise_server_exceptions=False)

    def tearDown(self):
        self._db_patcher.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)


# ─── Health & Auth ────────────────────────────────────────────────────────────

class TestHealth(_BaseWebTest):
    def test_health_returns_ok(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})


class TestAuth(_BaseWebTest):
    def test_auth_status_no_key_required(self):
        resp = self.client.get("/api/auth/status")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["auth_required"])

    def test_auth_status_key_configured(self):
        _fake_init.bot_config["web"]["auth_key"] = "secret"
        resp = self.client.get("/api/auth/status")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["auth_required"])

    def test_login_correct_key(self):
        _fake_init.bot_config["web"]["auth_key"] = "secret"
        resp = self.client.post("/api/auth/login", json={"key": "secret"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    def test_login_wrong_key_returns_401(self):
        _fake_init.bot_config["web"]["auth_key"] = "secret"
        resp = self.client.post("/api/auth/login", json={"key": "wrong"})
        self.assertEqual(resp.status_code, 401)

    def test_protected_endpoint_without_key_returns_401(self):
        _fake_init.bot_config["web"]["auth_key"] = "secret"
        resp = self.client.get("/api/dashboard/stats")
        self.assertEqual(resp.status_code, 401)

    def test_protected_endpoint_with_correct_key(self):
        _fake_init.bot_config["web"]["auth_key"] = "secret"
        resp = self.client.get("/api/dashboard/stats", headers={"x-web-auth-key": "secret"})
        self.assertEqual(resp.status_code, 200)

    def test_protected_endpoint_key_as_query_param(self):
        _fake_init.bot_config["web"]["auth_key"] = "secret"
        resp = self.client.get("/api/dashboard/stats?key=secret")
        self.assertEqual(resp.status_code, 200)


# ─── Dashboard ────────────────────────────────────────────────────────────────

class TestDashboard(_BaseWebTest):
    def test_stats_fields_present(self):
        resp = self.client.get("/api/dashboard/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in ("total", "downloaded", "submitted", "finished", "pending", "retry_pending"):
            self.assertIn(key, data, f"missing key: {key}")

    def test_stats_counts_match_seed_data(self):
        resp = self.client.get("/api/dashboard/stats")
        data = resp.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["pending"], 1)    # is_download=0
        self.assertEqual(data["submitted"], 1)  # is_download=1
        self.assertEqual(data["finished"], 1)   # is_download=2

    def test_trend_returns_items(self):
        resp = self.client.get("/api/dashboard/trend?days=30")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("days", data)
        self.assertIn("items", data)
        self.assertEqual(data["days"], 30)

    def test_trend_invalid_days(self):
        resp = self.client.get("/api/dashboard/trend?days=0")
        self.assertEqual(resp.status_code, 422)


# ─── Sehua 列表/筛选 ──────────────────────────────────────────────────────────

class TestSehuaList(_BaseWebTest):
    def test_list_all_returns_three_rows(self):
        resp = self.client.get("/api/sehua")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 3)

    def test_filter_by_status_pending(self):
        resp = self.client.get("/api/sehua?status=0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["is_download"], 0)

    def test_filter_by_status_submitted(self):
        resp = self.client.get("/api/sehua?status=1")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["is_download"], 1)

    def test_filter_by_status_finished_rejected(self):
        # The API currently caps status at le=1; status=2 is a validation error
        resp = self.client.get("/api/sehua?status=2")
        self.assertEqual(resp.status_code, 422)

    def test_filter_by_section(self):
        resp = self.client.get("/api/sehua?section=国产原创")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["section_name"], "国产原创")

    def test_filter_by_keyword(self):
        resp = self.client.get("/api/sehua?keyword=无码字幕")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertIn("无码字幕", data["items"][0]["title"])

    def test_pagination(self):
        resp = self.client.get("/api/sehua?page=1&size=2")
        data = resp.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 2)

    def test_invalid_page_size_rejected(self):
        resp = self.client.get("/api/sehua?size=0")
        self.assertEqual(resp.status_code, 422)


# ─── Sehua 删除 ───────────────────────────────────────────────────────────────

class TestSehuaDelete(_BaseWebTest):
    def test_delete_existing_item(self):
        resp = self.client.delete("/api/sehua/1")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        # 确认已从列表消失
        resp2 = self.client.get("/api/sehua")
        self.assertEqual(resp2.json()["total"], 2)

    def test_delete_nonexistent_returns_404(self):
        resp = self.client.delete("/api/sehua/9999")
        self.assertEqual(resp.status_code, 404)

    def test_batch_delete(self):
        resp = self.client.request(
            "DELETE",
            "/api/sehua/batch-delete",
            json={"ids": [1, 2]},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["deleted"], 2)
        resp2 = self.client.get("/api/sehua")
        self.assertEqual(resp2.json()["total"], 1)

    def test_batch_delete_empty_ids_returns_400(self):
        resp = self.client.request("DELETE", "/api/sehua/batch-delete", json={"ids": []})
        self.assertEqual(resp.status_code, 400)


# ─── Sehua 提交离线下载 ───────────────────────────────────────────────────────

class TestSehuaDownload(_BaseWebTest):
    def test_download_one_success(self):
        _fake_init.openapi_115.offline_download_specify_path.return_value = True
        resp = self.client.post("/api/sehua/1/download")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["id"], 1)

    def test_download_one_not_found_returns_404(self):
        _fake_init.openapi_115.offline_download_specify_path.return_value = True
        resp = self.client.post("/api/sehua/9999/download")
        self.assertEqual(resp.status_code, 404)

    def test_download_one_openapi_failure_returns_502(self):
        _fake_init.openapi_115.offline_download_specify_path.return_value = False
        resp = self.client.post("/api/sehua/1/download")
        self.assertEqual(resp.status_code, 502)

    def test_download_one_no_openapi_returns_503(self):
        _fake_init.openapi_115 = None
        resp = self.client.post("/api/sehua/1/download")
        self.assertEqual(resp.status_code, 503)

    def test_batch_download_success(self):
        _fake_init.openapi_115.offline_download_specify_path.return_value = True
        resp = self.client.post("/api/sehua/batch-download", json={"ids": [1, 2]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(1, data["submitted"])
        self.assertIn(2, data["submitted"])

    def test_batch_download_partial_failure(self):
        # id=1 成功，id=2 失败
        _fake_init.openapi_115.offline_download_specify_path.side_effect = (
            lambda magnet, path: magnet == MAGNET_A
        )
        resp = self.client.post("/api/sehua/batch-download", json={"ids": [1, 2]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn(1, data["submitted"])
        self.assertIn(2, data["failed"])

    def test_batch_download_empty_ids_returns_400(self):
        resp = self.client.post("/api/sehua/batch-download", json={"ids": []})
        self.assertEqual(resp.status_code, 400)


# ─── Sehua 后处理 ─────────────────────────────────────────────────────────────

class TestSehuaPostProcess(_BaseWebTest):
    def test_process_status_idle(self):
        resp = self.client.get("/api/sehua/process-status")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["running"])

    def test_post_process_one_non_submitted_returns_400(self):
        # id=1 is_download=0，应返回 400
        resp = self.client.post("/api/sehua/1/post-process")
        self.assertEqual(resp.status_code, 400)

    def test_post_process_one_while_running_returns_409(self):
        _fake_init.POST_PROCESS_STATUS = 1
        resp = self.client.post("/api/sehua/2/post-process")
        self.assertEqual(resp.status_code, 409)

    def test_post_process_one_valid_item_accepted(self):
        # id=2 is_download=1
        resp = self.client.post("/api/sehua/2/post-process")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    def test_batch_post_process_while_running_returns_409(self):
        _fake_init.POST_PROCESS_STATUS = 1
        resp = self.client.post("/api/sehua/batch-post-process")
        self.assertEqual(resp.status_code, 409)

    def test_batch_post_process_no_pending_returns_ok(self):
        # 清空 is_download=1 的行
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE sehua_data SET is_download=2 WHERE is_download=1")
        conn.commit()
        conn.close()

        resp = self.client.post("/api/sehua/batch-post-process")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["count"], 0)

    def test_batch_post_process_queues_submitted_items(self):
        resp = self.client.post("/api/sehua/batch-post-process")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertGreater(data["count"], 0)


# ─── Tasks ────────────────────────────────────────────────────────────────────

class TestTasks(_BaseWebTest):
    def test_list_tasks_returns_all(self):
        resp = self.client.get("/api/tasks")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["items"]), 2)

    def test_delete_task(self):
        resp = self.client.delete("/api/tasks/1")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        resp2 = self.client.get("/api/tasks")
        self.assertEqual(len(resp2.json()["items"]), 1)

    def test_delete_nonexistent_task_returns_404(self):
        resp = self.client.delete("/api/tasks/9999")
        self.assertEqual(resp.status_code, 404)

    def test_clear_tasks_removes_pending_only(self):
        # id=1 is_download=0（待处理），id=2 is_download=1（完成）
        resp = self.client.delete("/api/tasks/all")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        # is_download=1 的 Task-B 应保留
        resp2 = self.client.get("/api/tasks")
        items = resp2.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["is_download"], 1)

    def test_retry_task_success(self):
        _fake_init.openapi_115.offline_download_specify_path.return_value = True
        resp = self.client.post("/api/tasks/1/retry")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        # retry_count 应该增加
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT retry_count FROM offline_task WHERE id=1").fetchone()
        conn.close()
        self.assertEqual(row[0], 1)

    def test_retry_task_failure_returns_502(self):
        _fake_init.openapi_115.offline_download_specify_path.return_value = False
        resp = self.client.post("/api/tasks/1/retry")
        self.assertEqual(resp.status_code, 502)
        # retry_count 在失败时也应增加
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT retry_count FROM offline_task WHERE id=1").fetchone()
        conn.close()
        self.assertEqual(row[0], 1)

    def test_retry_nonexistent_task_returns_404(self):
        resp = self.client.post("/api/tasks/9999/retry")
        self.assertEqual(resp.status_code, 404)

    def test_retry_task_no_openapi_returns_503(self):
        _fake_init.openapi_115 = None
        resp = self.client.post("/api/tasks/1/retry")
        self.assertEqual(resp.status_code, 503)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main(verbosity=2)
