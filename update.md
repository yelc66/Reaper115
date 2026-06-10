## ✨ 新增

- 广告清理新增「去除植入正片文件名的广告前缀」：形如 `489155.com@DLDSS-496-C.mp4` 自动重命名为 `DLDSS-496-C.mp4`（规则：恰六位数字 + `.com@` 开头）。受 `clean_policy.strip_ad_prefix` 开关控制，默认开启。

## 🐛 修复

- 修复爬虫一直卡在 Cloudflare 验证页的问题：改为直接使用 FlareSolverr 返回的渲染后 HTML，绕过把 cookie 回灌到独立 chrome 容器（因出口 IP/指纹跨容器失配导致 cf_clearance 失效）的环节。可用 `flaresolverr_fetch` 开关回退旧方案。
- 修复 CI 构建因 commit message 含多行/特殊字符被当成 shell 命令执行（命令注入）而失败的问题。
