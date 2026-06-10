# -*- coding: utf-8 -*-
"""项目版本号 —— 全局唯一真源。

只改本文件的 __version__，以下全部自动同步：
  - Telegram bot 使用手册 / 启动消息（app/115bot.py:get_version）
  - Web 后端 /api/system/status → 前端侧边栏
  - Docker 镜像标签 / GitHub Release（.github/workflows 从此处提取）

发布新版本：改下面的 __version__（如 "1.0.1"，不带 v 前缀），
并在根目录 update.md 写本次更新说明（仅作 Release notes，不含版本号）。
版本号规范（语义化）：修 bug +0.0.1，加功能 +0.1.0，不兼容的大改 +1.0.0。
"""

__version__ = "1.0.0"
