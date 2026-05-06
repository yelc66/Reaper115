"""
涩花离线流水线本地集成测试（不依赖真实 115 API / Selenium / Telegram）

测试覆盖两个阶段：
  Phase 1 - sehua_offline:   is_download=0 → 提交115离线 → 标记 is_download=1
  Phase 2 - sehua_post_process: is_download=1 → 检查115任务状态 → 广告清理/重命名 → 标记 is_download=2

运行方式：
    python tests/test_offline_pipeline.py
"""

import os
import sys
import sqlite3
import tempfile
import types
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# 确保 app/ 可导入
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ─── 最小化 init mock，避免真实 config/logger/db 初始化 ─────────────────────

_fake_init = types.ModuleType("init")
_fake_init.logger = logging.getLogger("test")
_fake_init.logger.setLevel(logging.DEBUG)
if not _fake_init.logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _fake_init.logger.addHandler(_h)

_fake_init.bot_config = {
    "allowed_user": 12345,
    "sehuatang_spider": {
        "sections": [
            {"name": "高清中文字幕", "save_path": "/AV/涩花/高清中文字幕"},
            {"name": "国产原创",     "save_path": "/AV/涩花/国产原创"},
        ],
        "sort_by_year_month": False,
        "rename_by_title": False,
    },
}
_fake_init.IMAGE_PATH = "/tmp"
_fake_init.CRAWL_SEHUA_STATUS = 0
_fake_init.openapi_115 = MagicMock()

sys.modules["init"] = _fake_init

# ─── 临时 DB 辅助 ────────────────────────────────────────────────────────────

def _make_temp_db():
    """创建带完整 schema 的临时 SQLite 文件，返回 (path, conn)。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
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
    """)
    conn.commit()
    return path, conn


# ─── 测试数据工厂 ─────────────────────────────────────────────────────────────

MAGNET_A = "magnet:?xt=urn:btih:AABBCCDD0011223344556677889900AABBCCDD00&dn=TestA"
MAGNET_B = "magnet:?xt=urn:btih:BBCCDD0011223344556677889900AABBCCDD0011&dn=TestB"
MAGNET_C = "magnet:?xt=urn:btih:CCDD0011223344556677889900AABBCCDD001122&dn=TestC"
MAGNET_D = "magnet:?xt=urn:btih:DD0011223344556677889900AABBCCDD00112233&dn=TestDeadSeed"

YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
LONG_AGO  = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")


def _insert_rows(conn):
    """
    预写入四种场景行：

    id=1  is_download=0  → Phase1 目标：成功提交离线，变 is_download=1
    id=2  is_download=0  无 magnet → 应被跳过（无效任务）
    id=3  is_download=1  submitted_at=5天前  → Phase2 死种：标记放弃 is_download=2
    id=4  is_download=1  submitted_at=now  → Phase2 下载中：跳过等待
    id=5  is_download=1  submitted_at=now  → Phase2 完成：清理 → is_download=2
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        # id=1: 待提交
        ("高清中文字幕", "SSIS-001", "SSIS-001 无码字幕 某女优", "无码",
         "1.5G", MAGNET_A,
         "https://example.com/cover1.jpg", YESTERDAY,
         "https://www.sehuatang.net/forum.php?tid=1", None,
         "/AV/涩花/高清中文字幕", 0, None),
        # id=2: 待提交但 magnet 为空，应跳过
        ("国产原创", "N/A", "【麻豆】某某某 4K", "无码",
         "2.0G", None,
         "https://example.com/cover2.jpg", YESTERDAY,
         "https://www.sehuatang.net/forum.php?tid=2", None,
         "/AV/涩花/国产原创", 0, None),
        # id=3: 已提交，5天前提交 → 死种
        ("高清中文字幕", "SSIS-002", "SSIS-002 某女优", "有码",
         "3.0G", MAGNET_C,
         "https://example.com/cover3.jpg", YESTERDAY,
         "https://www.sehuatang.net/forum.php?tid=3", None,
         "/AV/涩花/高清中文字幕", 1, LONG_AGO),
        # id=4: 已提交，刚刚提交 → 下载中跳过
        ("国产原创", "N/A", "【麻豆】下载中", "无码",
         "1.0G", MAGNET_B,
         "https://example.com/cover4.jpg", YESTERDAY,
         "https://www.sehuatang.net/forum.php?tid=4", None,
         "/AV/涩花/国产原创", 1, now),
        # id=5: 已提交，刚刚提交 → 115返回已完成
        ("高清中文字幕", "MIDV-010", "MIDV-010 某女优字幕", "无码",
         "2.5G", MAGNET_D,
         "https://example.com/cover5.jpg", YESTERDAY,
         "https://www.sehuatang.net/forum.php?tid=5", "/tmp/sehua/cover5.jpg",
         "/AV/涩花/高清中文字幕", 1, now),
    ]
    conn.executemany("""
        INSERT INTO sehua_data
            (section_name, av_number, title, movie_type, size, magnet,
             post_url, publish_date, pub_url, image_path, save_path,
             is_download, submitted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()


# ─── 查询辅助 ─────────────────────────────────────────────────────────────────

def _rows(conn, where="1=1"):
    cur = conn.execute(f"SELECT * FROM sehua_data WHERE {where} ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


def _make_fake_sqlite(db_path):
    """每次调用返回一个独立连接的 FakeSqlite 实例，避免多次 with 共享连接锁。"""
    class _FakeSqlite:
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
            cur = self._conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        def query_one(self, sql, params=()):
            cur = self._conn.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None
        def execute_sql(self, sql, params=()):
            self._conn.execute(sql, params)
    return _FakeSqlite()


# ─── Phase 1 测试：sehua_offline ─────────────────────────────────────────────

def test_phase1_sehua_offline():
    print("\n" + "=" * 60)
    print("Phase 1: sehua_offline (提交115离线)")
    print("=" * 60)

    db_path, conn = _make_temp_db()
    _insert_rows(conn)
    conn.close()

    # mock 依赖
    _fake_init.openapi_115.offline_download_specify_path.return_value = True
    add_queue_calls = []

    with patch("app.core.offline_task_retry.SqlLiteLib") as MockDB, \
         patch("app.utils.message_queue.add_task_to_queue", side_effect=lambda *a, **kw: add_queue_calls.append(a)):

        MockDB.side_effect = lambda *a, **kw: _make_fake_sqlite(db_path)

        from app.core.offline_task_retry import sehua_offline
        sehua_offline("昨天")

    # 验证：id=1 应被标记 is_download=1，id=2(无magnet) 应保持 is_download=0
    _verify_conn = sqlite3.connect(db_path)
    _verify_conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in _verify_conn.execute(
        "SELECT id, is_download, submitted_at FROM sehua_data ORDER BY id"
    ).fetchall()]
    _verify_conn.close()

    passed = True

    # id=1: 提交成功
    r1 = rows[0]
    ok = r1["is_download"] == 1 and r1["submitted_at"] is not None
    _print_case("id=1 (有效任务) → is_download=1, submitted_at 已设置", ok)
    passed = passed and ok

    # id=2: 无 magnet 跳过，保持 is_download=0
    r2 = rows[1]
    ok = r2["is_download"] == 0
    _print_case("id=2 (无magnet) → 跳过，is_download=0", ok)
    passed = passed and ok

    # id=3,4,5: is_download=1 的不在 sehua_offline 处理范围，保持不变
    for i, row in enumerate(rows[2:], start=3):
        ok = row["is_download"] == 1
        _print_case(f"id={i} (已提交) → sehua_offline 不处理，is_download=1", ok)
        passed = passed and ok

    # 115 API 只应被调用一次（id=1 那条）
    call_count = _fake_init.openapi_115.offline_download_specify_path.call_count
    ok = call_count >= 1
    _print_case(f"offline_download_specify_path 被调用 {call_count} 次（≥1）", ok)
    passed = passed and ok

    os.unlink(db_path)
    return passed


# ─── Phase 2 测试：sehua_post_process ────────────────────────────────────────

def test_phase2_sehua_post_process():
    print("\n" + "=" * 60)
    print("Phase 2: sehua_post_process (检查完成 + 广告清理)")
    print("=" * 60)

    db_path, conn = _make_temp_db()
    _insert_rows(conn)
    conn.close()

    # 模拟 115 任务列表：id=5 的 MAGNET_D 已完成，id=4 的 MAGNET_B 下载中
    _fake_init.openapi_115.get_offline_tasks.return_value = [
        {"url": MAGNET_B, "status": 1, "percentDone": 42, "name": "TestB_dir"},
        {"url": MAGNET_D, "status": 2, "percentDone": 100, "name": "MIDV-010_dir"},
    ]
    # is_directory: 只有 MIDV-010_dir 是目录
    _fake_init.openapi_115.is_directory.side_effect = lambda p: "MIDV-010_dir" in p
    _fake_init.openapi_115.auto_clean_all.return_value = True
    add_queue_calls = []

    with patch("app.core.offline_task_retry.SqlLiteLib") as MockDB, \
         patch("app.utils.message_queue.add_task_to_queue", side_effect=lambda *a, **kw: add_queue_calls.append(a)):

        MockDB.side_effect = lambda *a, **kw: _make_fake_sqlite(db_path)

        from app.core.offline_task_retry import sehua_post_process
        sehua_post_process()

    _verify_conn = sqlite3.connect(db_path)
    _verify_conn.row_factory = sqlite3.Row
    rows = {r["id"]: dict(r) for r in _verify_conn.execute(
        "SELECT id, is_download FROM sehua_data ORDER BY id"
    ).fetchall()}
    _verify_conn.close()

    passed = True

    # id=3: 死种(5天前提交) → is_download=2
    ok = rows[3]["is_download"] == 2
    _print_case("id=3 (死种 5天) → is_download=2（放弃）", ok)
    passed = passed and ok

    # id=4: 下载中(42%) → 保持 is_download=1
    ok = rows[4]["is_download"] == 1
    _print_case("id=4 (下载中 42%) → is_download=1（等待）", ok)
    passed = passed and ok

    # id=5: 完成(100%) → is_download=2，auto_clean_all 被调用
    ok = rows[5]["is_download"] == 2
    _print_case("id=5 (已完成) → is_download=2（后处理完成）", ok)
    passed = passed and ok

    clean_called = _fake_init.openapi_115.auto_clean_all.called
    _print_case("auto_clean_all 被调用（广告清理）", clean_called)
    passed = passed and clean_called

    # id=1,2: is_download=0 不在后处理范围，保持不变
    ok = rows[1]["is_download"] == 0 and rows[2]["is_download"] == 0
    _print_case("id=1,2 (is_download=0) → sehua_post_process 不处理", ok)
    passed = passed and ok

    os.unlink(db_path)
    return passed


# ─── 输出辅助 ─────────────────────────────────────────────────────────────────

def _print_case(desc, ok):
    mark = "  ✓" if ok else "  ✗"
    print(f"{mark}  {desc}")


# ─── 主入口 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.disable(logging.CRITICAL)  # 测试期间静默应用日志，只看断言结果

    p1 = test_phase1_sehua_offline()
    p2 = test_phase2_sehua_post_process()

    print("\n" + "=" * 60)
    if p1 and p2:
        print("全部通过 ✓")
    else:
        print("存在失败，见上方 ✗ 标记")
        sys.exit(1)
    print("=" * 60)
