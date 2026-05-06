"""
策略 API 保存/读取测试。

运行方式：
    python3 tests/test_strategy_api.py
"""

import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

fake_init = types.ModuleType("init")
fake_init.STRATEGY_FILE = "config/crawling_strategy.yaml"
sys.modules["init"] = fake_init

from app.web.routers import strategy


class StrategyApiTest(unittest.TestCase):
    def _temp_strategy_file(self):
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False)
        temp.write("{}\n")
        temp.close()
        self.addCleanup(lambda: os.path.exists(temp.name) and os.unlink(temp.name))
        return temp.name

    def test_create_exclude_rule_preserves_kind_in_response_and_yaml(self):
        path = self._temp_strategy_file()
        with patch.object(strategy.init, "STRATEGY_FILE", path):
            response = strategy.create_rule(strategy.StrategyRule(
                site="sehuatang",
                section_name="高清中文字幕",
                name="广告",
                pattern="广告",
                save_path="",
                kind="exclude",
                active=True,
            ))

            self.assertEqual(response["item"]["kind"], "exclude")
            self.assertTrue(response["item"]["active"])

            listed = strategy.list_rules()
            self.assertEqual(listed["items"][0]["kind"], "exclude")

            with open(path, "r", encoding="utf-8") as file:
                saved = yaml.safe_load(file)
            self.assertEqual(saved["sehuatang"]["高清中文字幕"][0]["kind"], "exclude")

    def test_missing_kind_defaults_to_include(self):
        path = self._temp_strategy_file()
        with open(path, "w", encoding="utf-8") as file:
            yaml.safe_dump({
                "sehuatang": {
                    "高清中文字幕": [
                        {"name": "破解", "pattern": "无码破解", "save_path": ""},
                    ],
                },
            }, file, allow_unicode=True, sort_keys=False)

        with patch.object(strategy.init, "STRATEGY_FILE", path):
            listed = strategy.list_rules()

        self.assertEqual(listed["items"][0]["kind"], "include")
        self.assertTrue(listed["items"][0]["active"])


if __name__ == "__main__":
    unittest.main()
