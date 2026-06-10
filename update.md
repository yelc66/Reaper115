## ✨ 新增

- Web 管理界面侧边栏显示当前版本号，更新后一眼可见。
- Telegram bot 使用手册与启动消息显示当前版本号。
- 引入语义化版本号机制：`app/version.py` 为唯一版本真源，bot / Web / 镜像标签 / GitHub Release 全部据此同步。本文件仅作发布说明（Release notes）。

## 🐛 修复

- 修复爬虫一直卡在 Cloudflare 验证页的问题：改为直接使用 FlareSolverr 返回的渲染后 HTML，绕过把 cookie 回灌到独立 chrome 容器（因出口 IP/指纹跨容器失配导致 cf_clearance 失效）的环节。可用 `flaresolverr_fetch` 开关回退旧方案。
- 修复 CI 构建因 commit message 含多行/特殊字符被当成 shell 命令执行（命令注入）而失败的问题。
