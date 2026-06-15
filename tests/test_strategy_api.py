"""
策略 API 测试。

策略规则 CRUD 已下沉到 config.yaml（sehuatang_spider.sections[].rules /
missav_spider.lists[].rules），经 /api/system/config 读写；规则匹配语义由
test_strategy_matching.py 覆盖。本文件覆盖现存的 /api/strategy/test 正则测试端点。

运行方式：
    python tests/test_strategy_api.py
"""

import os
import sys
import types
import logging
import unittest
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

fake_init = types.ModuleType("init")
fake_init.logger = logging.getLogger("test_strategy_api")
fake_init.logger.addHandler(logging.NullHandler())
fake_init.bot_config = {"web": {"enable": True, "auth_key": ""}}
fake_init.openapi_115 = MagicMock()
sys.modules["init"] = fake_init

from app.web.server import create_app
from fastapi.testclient import TestClient


class StrategyTestEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(), raise_server_exceptions=False)

    def test_pattern_matches_title(self):
        r = self.client.post("/api/strategy/test",
                             json={"pattern": "无码字幕", "title": "SSIS-001 无码字幕"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["matched"])

    def test_pattern_case_insensitive(self):
        r = self.client.post("/api/strategy/test",
                             json={"pattern": "ssis", "title": "SSIS-001"})
        self.assertTrue(r.json()["matched"])

    def test_pattern_no_match(self):
        r = self.client.post("/api/strategy/test",
                             json={"pattern": "广告", "title": "SSIS-001 无码字幕"})
        self.assertFalse(r.json()["matched"])

    def test_invalid_regex_rejected(self):
        r = self.client.post("/api/strategy/test",
                             json={"pattern": "[unclosed", "title": "anything"})
        self.assertNotEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
