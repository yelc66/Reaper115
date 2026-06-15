"""missav 爬虫 + Web API 测试（不依赖真实 Selenium / 115 / FlareSolverr）。

三层覆盖：
  TestMissavParse    —— 纯解析/选择/策略函数（合成 HTML，无 DB）
  TestSaveMissav2db  —— save_missav2db 入库：策略过滤 / hash 去重 / 完整性校验（临时 SQLite）
  TestMissavWebApi   —— /api/missav 路由：list/download/delete/post-process/trigger（FastAPI TestClient）

运行方式：
    python tests/test_missav.py
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

# ─── 最小 init mock（必须在导入 missav_spider 之前注入，模块顶层 import init）────

_fake_init = types.ModuleType("init")
_fake_init.logger = logging.getLogger("test_missav")
_fake_init.logger.setLevel(logging.CRITICAL)  # 测试时静音
if not _fake_init.logger.handlers:
    _fake_init.logger.addHandler(logging.NullHandler())

_fake_init.bot_config = {
    "web": {"enable": True, "auth_key": ""},
    "missav_spider": {"sort_by_year_month": False, "enable": True, "lists": []},
}
_fake_init.CRAWL_SEHUA_STATUS = 0
_fake_init.CRAWL_MISSAV_STATUS = 0
_fake_init.POST_PROCESS_STATUS = 0
_fake_init.MISSAV_POST_PROCESS_STATUS = 0
_fake_init.TEMP = tempfile.gettempdir()
_fake_init.USER_AGENT = "test-agent"
_fake_init.openapi_115 = MagicMock()

sys.modules["init"] = _fake_init

from app.core import missav_spider  # noqa: E402


# ─── 合成详情页 HTML：og:title/og:image + magnet 表（字幕 [SUB] / 无字幕）─────

def _detail_html(rows, og_title="START-583 Some Title", og_image="https://img.cdn/cover.jpg"):
    """rows: list of (marker, size_text, btih)。marker 为 '[SUB]' 或 '无字幕'。"""
    tr = "\n".join(
        f'<tr><td>START-583</td><td>{mk}</td><td>{sz}</td>'
        f'<td><a href="magnet:?xt=urn:btih:{bt}&amp;dn=x">下载</a></td></tr>'
        for mk, sz, bt in rows
    )
    return f"""<html><head>
    <meta property="og:title" content="{og_title}">
    <meta property="og:image" content="{og_image}">
    <title>fallback</title>
    </head><body><table>{tr}</table></body></html>"""


# ─── TestCase 1：纯解析 / 选择 / 策略 ─────────────────────────────────────────

class TestMissavParse(unittest.TestCase):
    def setUp(self):
        _fake_init.bot_config["missav_spider"]["lists"] = []

    # ---- _parse_size_bytes ----
    def test_parse_size_units(self):
        self.assertEqual(missav_spider._parse_size_bytes("foo 1.5GB bar"), int(1.5 * 1024 ** 3))
        self.assertEqual(missav_spider._parse_size_bytes("700 MB"), 700 * 1024 ** 2)
        self.assertEqual(missav_spider._parse_size_bytes("512KB"), 512 * 1024)

    def test_parse_size_missing(self):
        self.assertEqual(missav_spider._parse_size_bytes(""), -1)
        self.assertEqual(missav_spider._parse_size_bytes("no size here"), -1)
        self.assertEqual(missav_spider._parse_size_bytes(None), -1)

    # ---- _av_number_from_url ----
    def test_av_number_from_url(self):
        self.assertEqual(missav_spider._av_number_from_url("https://missav.ws/en/start-583"), "START-583")
        self.assertEqual(missav_spider._av_number_from_url("https://missav.ws/en/start-583/"), "START-583")

    # ---- _extract_detail_links ----
    def test_extract_links_excludes_nav_and_dedups(self):
        html = """
        <a href="https://missav.ws/en/today-hot">nav</a>
        <a href="https://missav.ws/en/start-583">film</a>
        <a href="https://missav.ws/en/start-583">dup</a>
        <a href="https://missav.ws/en/ssis-456">film2</a>
        <a href="https://missav.ws/en/genres">nav2</a>
        <a href="https://missav.ws/en/123456">numeric</a>
        """
        links = missav_spider._extract_detail_links(html, max_items=10)
        self.assertIn("https://missav.ws/en/start-583", links)
        self.assertIn("https://missav.ws/en/ssis-456", links)
        self.assertIn("https://missav.ws/en/123456", links)
        self.assertNotIn("https://missav.ws/en/today-hot", links)
        self.assertNotIn("https://missav.ws/en/genres", links)
        self.assertEqual(len(links), 3)  # 去重后 3 个

    def test_extract_links_respects_max_items(self):
        html = "".join(f'<a href="https://missav.ws/en/abc-{i}00">x</a>' for i in range(10))
        self.assertEqual(len(missav_spider._extract_detail_links(html, max_items=3)), 3)

    # ---- _select_best_magnet：字幕优先，否则容量最大 ----
    def test_select_subtitle_first_even_if_smaller(self):
        from bs4 import BeautifulSoup
        html = _detail_html([("[SUB]", "1.0GB", "SUBSMALL"),
                             ("无字幕", "5.0GB", "NOSUBBIG"),
                             ("无字幕", "2.0GB", "NOSUBSML")])
        magnet, movie_type, size = missav_spider._select_best_magnet(BeautifulSoup(html, "html.parser"))
        self.assertIn("SUBSMALL", magnet)
        self.assertEqual(movie_type, "中文字幕")
        self.assertEqual(size, "1.0GB")

    def test_select_largest_when_no_subtitle(self):
        from bs4 import BeautifulSoup
        html = _detail_html([("无字幕", "3.0GB", "BIG"), ("无字幕", "1.0GB", "SMALL")])
        magnet, movie_type, size = missav_spider._select_best_magnet(BeautifulSoup(html, "html.parser"))
        self.assertIn("BIG", magnet)
        self.assertEqual(movie_type, "无字幕")

    def test_select_largest_subtitle_among_subs(self):
        from bs4 import BeautifulSoup
        html = _detail_html([("[SUB]", "2.0GB", "SUBBIG"),
                             ("[SUB]", "1.0GB", "SUBSML"),
                             ("无字幕", "9.0GB", "HUGE")])
        magnet, movie_type, _ = missav_spider._select_best_magnet(BeautifulSoup(html, "html.parser"))
        self.assertIn("SUBBIG", magnet)
        self.assertEqual(movie_type, "中文字幕")

    def test_select_no_false_positive_on_wuzimu(self):
        """回归 B4：'无字幕' 不得被裸 '字幕' 误判为字幕版。"""
        from bs4 import BeautifulSoup
        html = _detail_html([("无字幕", "1.0GB", "ONLY")])
        _, movie_type, _ = missav_spider._select_best_magnet(BeautifulSoup(html, "html.parser"))
        self.assertEqual(movie_type, "无字幕")

    def test_select_empty(self):
        from bs4 import BeautifulSoup
        self.assertEqual(missav_spider._select_best_magnet(BeautifulSoup("<html></html>", "html.parser")),
                         (None, None, None))

    # ---- parse_detail ----
    def test_parse_detail_full(self):
        html = _detail_html([("[SUB]", "1.5GB", "AABBCC")])
        result = missav_spider.parse_detail(html, "https://missav.ws/en/start-583", "today-hot")
        self.assertEqual(result["av_number"], "START-583")
        self.assertEqual(result["list_name"], "today-hot")
        self.assertEqual(result["title"], "START-583 Some Title")
        self.assertEqual(result["post_url"], "https://img.cdn/cover.jpg")
        self.assertIn("AABBCC", result["magnet"])
        self.assertEqual(result["movie_type"], "中文字幕")

    def test_parse_detail_title_fallback_to_av_number(self):
        html = "<html><head></head><body><table></table></body></html>"
        result = missav_spider.parse_detail(html, "https://missav.ws/en/abp-999", "today-hot")
        self.assertEqual(result["title"], "ABP-999")
        self.assertIsNone(result["magnet"])

    # ---- 策略：_hits_exclude_rule / is_title_allowed / match_strategy ----
    def _set_rules(self, rules):
        _fake_init.bot_config["missav_spider"]["lists"] = [
            {"name": "today-hot", "save_path": "/AV/missav/hot", "rules": rules}]

    def test_hits_exclude_rule(self):
        self._set_rules([{"name": "no-vr", "kind": "exclude", "pattern": "VR", "active": True}])
        self.assertTrue(missav_spider._hits_exclude_rule("today-hot", "SSVR-1"))
        self.assertFalse(missav_spider._hits_exclude_rule("today-hot", "SSIS-1"))

    def test_is_title_allowed_no_rules_passes(self):
        self._set_rules([])
        self.assertTrue(missav_spider.is_title_allowed("today-hot", "anything"))

    def test_is_title_allowed_include_and_exclude(self):
        self._set_rules([
            {"name": "want", "kind": "include", "pattern": "中文字幕", "active": True},
            {"name": "drop", "kind": "exclude", "pattern": "VR", "active": True},
        ])
        self.assertTrue(missav_spider.is_title_allowed("today-hot", "好片 中文字幕"))
        self.assertFalse(missav_spider.is_title_allowed("today-hot", "普通片无字幕"))   # 不含 include
        self.assertFalse(missav_spider.is_title_allowed("today-hot", "中文字幕 VR"))    # 命中 exclude

    def test_match_strategy_returns_rule_save_path(self):
        self._set_rules([
            {"name": "want", "kind": "include", "pattern": "中文字幕",
             "active": True, "save_path": "/AV/missav/sub"},
        ])
        ok, path = missav_spider.match_strategy(
            {"list_name": "today-hot", "title": "X 中文字幕", "save_path": "/AV/missav/hot"})
        self.assertTrue(ok)
        self.assertEqual(path, "/AV/missav/sub")

    def test_match_strategy_exclude_rejects(self):
        self._set_rules([{"name": "drop", "kind": "exclude", "pattern": "VR", "active": True}])
        ok, path = missav_spider.match_strategy(
            {"list_name": "today-hot", "title": "X VR", "save_path": "/AV/missav/hot"})
        self.assertFalse(ok)
        self.assertIsNone(path)


# ─── 临时 SQLite 辅助（仅 missav_data）────────────────────────────────────────

_MISSAV_SCHEMA = """
CREATE TABLE IF NOT EXISTS missav_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_name TEXT, av_number TEXT, title TEXT, movie_type TEXT, size TEXT,
    magnet TEXT, post_url TEXT, publish_date DATETIME, pub_url TEXT,
    image_path TEXT, save_path TEXT,
    is_download TINYINT DEFAULT 0, submitted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

MAGNET_A = "magnet:?xt=urn:btih:AABBCCDD0011223344556677889900AABBCCDD00&dn=A"
MAGNET_B = "magnet:?xt=urn:btih:BBCCDD0011223344556677889900AABBCCDD0011&dn=B"


def _make_fake_sqlite(db_path):
    class _FS:
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
            row = self._conn.execute(sql, params).fetchone()
            return row[0] if row else None
        def execute_sql(self, sql, params=()):
            self._conn.execute(sql, params)
    return _FS()


def _new_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(_MISSAV_SCHEMA)
    conn.commit()
    conn.close()
    return path


def _count(db_path):
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM missav_data").fetchone()[0]
    conn.close()
    return n


# ─── TestCase 2：save_missav2db 入库逻辑 ──────────────────────────────────────

class TestSaveMissav2db(unittest.TestCase):
    def setUp(self):
        self.db_path = _new_db()
        _fake_init.bot_config["missav_spider"]["lists"] = []  # 无规则 = 全通过
        self._patcher = patch.object(
            missav_spider, "SqlLiteLib",
            side_effect=lambda *a, **kw: _make_fake_sqlite(self.db_path))
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _record(self, **over):
        rec = {
            "list_name": "today-hot", "av_number": "START-583", "title": "X 中文字幕",
            "movie_type": "中文字幕", "size": "1.5GB", "magnet": MAGNET_A,
            "post_url": "https://i/c.jpg", "publish_date": "2026-06-15",
            "pub_url": "https://missav.ws/en/start-583", "image_path": None,
            "save_path": "/AV/missav/hot",
        }
        rec.update(over)
        return rec

    def test_valid_record_inserted(self):
        missav_spider.save_missav2db([self._record()])
        self.assertEqual(_count(self.db_path), 1)

    def test_duplicate_magnet_hash_skipped(self):
        missav_spider.save_missav2db([self._record()])
        # 同 hash、不同 av_number 再来一次 → 去重跳过
        missav_spider.save_missav2db([self._record(av_number="OTHER-1")])
        self.assertEqual(_count(self.db_path), 1)

    def test_incomplete_record_skipped(self):
        missav_spider.save_missav2db([self._record(title=None)])
        self.assertEqual(_count(self.db_path), 0)

    def test_missing_magnet_skipped(self):
        missav_spider.save_missav2db([self._record(magnet=None)])
        self.assertEqual(_count(self.db_path), 0)

    def test_strategy_excluded_title_skipped(self):
        _fake_init.bot_config["missav_spider"]["lists"] = [{
            "name": "today-hot", "save_path": "/AV/missav/hot",
            "rules": [{"name": "drop", "kind": "exclude", "pattern": "中文字幕", "active": True}],
        }]
        missav_spider.save_missav2db([self._record(title="片 中文字幕")])
        self.assertEqual(_count(self.db_path), 0)


# ─── TestCase 3：Web API /api/missav ──────────────────────────────────────────

def _seed_web_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(_MISSAV_SCHEMA)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.executemany(
        """INSERT INTO missav_data
           (list_name, av_number, title, movie_type, size, magnet, post_url,
            publish_date, pub_url, image_path, save_path, is_download, submitted_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            ("today-hot", "START-001", "START-001 中文字幕", "中文字幕", "1.5G", MAGNET_A,
             "https://i/1.jpg", "2026-06-14", "https://missav.ws/en/start-001",
             None, "/AV/missav/hot", 0, None),
            ("today-hot", "START-002", "START-002 无字幕", "无字幕", "3.0G", MAGNET_B,
             "https://i/2.jpg", "2026-06-13", "https://missav.ws/en/start-002",
             None, "/AV/missav/hot", 1, now),
        ],
    )
    conn.commit()
    conn.close()


class TestMissavWebApi(unittest.TestCase):
    def setUp(self):
        self.db_path = _new_db()
        _seed_web_db(self.db_path)
        self._db_patcher = patch(
            "app.web.utils.SqlLiteLib",
            side_effect=lambda *a, **kw: _make_fake_sqlite(self.db_path))
        self._db_patcher.start()

        _fake_init.MISSAV_POST_PROCESS_STATUS = 0
        _fake_init.CRAWL_MISSAV_STATUS = 0
        _fake_init.bot_config["web"]["auth_key"] = ""
        _fake_init.openapi_115 = MagicMock()
        _fake_init.openapi_115.offline_download_specify_path.return_value = True

        from app.web.server import create_app
        from fastapi.testclient import TestClient
        self.client = TestClient(create_app(), raise_server_exceptions=False)

    def tearDown(self):
        self._db_patcher.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_list(self):
        r = self.client.get("/api/missav")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(len(body["items"]), 2)

    def test_list_filter_by_status(self):
        r = self.client.get("/api/missav", params={"status": 0})
        self.assertEqual(r.json()["total"], 1)

    def test_list_filter_by_section(self):
        r = self.client.get("/api/missav", params={"section": "today-hot"})
        self.assertEqual(r.json()["total"], 2)
        r2 = self.client.get("/api/missav", params={"section": "nope"})
        self.assertEqual(r2.json()["total"], 0)

    def test_download_one(self):
        r = self.client.post("/api/missav/1/download")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        _fake_init.openapi_115.offline_download_specify_path.assert_called()

    def test_download_one_not_found(self):
        self.assertEqual(self.client.post("/api/missav/999/download").status_code, 404)

    def test_delete_one(self):
        self.assertEqual(self.client.delete("/api/missav/1").status_code, 200)
        self.assertEqual(self.client.get("/api/missav").json()["total"], 1)

    def test_batch_delete(self):
        r = self.client.request("DELETE", "/api/missav/batch-delete", json={"ids": [1, 2]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["deleted"], 2)
        self.assertEqual(self.client.get("/api/missav").json()["total"], 0)

    def test_post_process_requires_is_download_1(self):
        # id=1 是 is_download=0 → 400
        self.assertEqual(self.client.post("/api/missav/1/post-process").status_code, 400)

    def test_crawl_status_endpoint(self):
        r = self.client.get("/api/missav/crawl-status")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["running"])

    def test_trigger_conflict_when_running(self):
        _fake_init.CRAWL_MISSAV_STATUS = 1
        r = self.client.post("/api/missav/trigger")
        self.assertEqual(r.status_code, 409)

    def test_trigger_disabled(self):
        _fake_init.bot_config["missav_spider"]["enable"] = False
        try:
            r = self.client.post("/api/missav/trigger")
            self.assertEqual(r.status_code, 400)
        finally:
            _fake_init.bot_config["missav_spider"]["enable"] = True


if __name__ == "__main__":
    unittest.main(verbosity=2)
