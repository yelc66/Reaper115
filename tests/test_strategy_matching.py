"""
策略规则匹配测试。

运行方式：
    python tests/test_strategy_matching.py
"""

import os
import sys
import logging
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.core import sehuatang_spider


SECTION = "高清中文字幕"


class StrategyMatchingTest(unittest.TestCase):
    def _patch_strategy(self, rules):
        # 规则现在从 init.bot_config['sehuatang_spider']['sections'][].rules 读取
        # （_active_strategy_rules），不再走 read_yaml_file。
        fake_init = type("Init", (), {
            "bot_config": {"sehuatang_spider": {"sections": [{"name": SECTION, "rules": rules}]}},
            "logger": logging.getLogger("test_strategy_matching"),
        })()
        return patch.object(sehuatang_spider, "init", fake_init)

    def test_include_rule_allows_matching_title(self):
        with self._patch_strategy([
            {"name": "字幕", "pattern": "无码字幕", "kind": "include", "active": True, "save_path": "/AV/字幕"},
        ]):
            self.assertTrue(sehuatang_spider.is_title_allowed(SECTION, "SSIS-001 无码字幕"))
            matched, save_path = sehuatang_spider.match_strategy({
                "section_name": SECTION,
                "title": "SSIS-001 无码字幕",
                "save_path": "/AV/default",
            })
            self.assertTrue(matched)
            self.assertEqual(save_path, "/AV/字幕")

    def test_exclude_rule_blocks_matching_title(self):
        with self._patch_strategy([
            {"name": "广告", "pattern": "广告", "kind": "exclude", "active": True},
        ]):
            self.assertFalse(sehuatang_spider.is_title_allowed(SECTION, "SSIS-001 广告"))
            matched, save_path = sehuatang_spider.match_strategy({
                "section_name": SECTION,
                "title": "SSIS-001 广告",
                "save_path": "/AV/default",
            })
            self.assertFalse(matched)
            self.assertIsNone(save_path)

    def test_disabled_rule_is_ignored(self):
        with self._patch_strategy([
            {"name": "停用排除", "pattern": "广告", "kind": "exclude", "active": False},
        ]):
            self.assertTrue(sehuatang_spider.is_title_allowed(SECTION, "SSIS-001 广告"))
            matched, save_path = sehuatang_spider.match_strategy({
                "section_name": SECTION,
                "title": "SSIS-001 广告",
                "save_path": "/AV/default",
            })
            self.assertTrue(matched)
            self.assertEqual(save_path, "/AV/default")


if __name__ == "__main__":
    unittest.main()
