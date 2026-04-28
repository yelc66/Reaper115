好，基于我们所有对话，整理完整的项目规划文档。

---

# Sehua-Web 项目规划

## 项目目标

从 Telegram-115bot 分支出 `feature/sehua-web`，专注涩花资源的**自动抓取 → 策略过滤 → 离线入 115 → 广告清理**，并提供 Web 管理界面，保留精简版 TG Bot 通知。

---

## 当前进度

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1 | 已完成 | Python 后端清理，保留涩花核心、115 OpenAPI、下载/同步/视频转存、STRM/Emby |
| Phase 2 | 已完成 | FastAPI server、6 个 API routers、SSE 日志流、Web 启动线程、Docker 端口映射 |
| Phase 3 | 待执行 | 新会话实现 `web-ui/` 前端 |

Phase 2 已验证：

```bash
python3 -m compileall app
TG115_DEBUG=1 PYTHONPATH="$PWD:$PWD/app:$PWD/app/utils:$PWD/app/core:$PWD/app/handlers" .venv/bin/python -c "import init; init.init(); from fastapi.testclient import TestClient; from app.web.server import create_app; client=TestClient(create_app()); print(client.get('/api/health').json())"
```

---

## 开发环境

- **Python**：3.12
- **Node.js**：20 LTS（前端构建）
- **Docker**：27+
- **Docker Compose**：v2

---

## 整体架构

```
┌──────────────────────────────────────────────────┐
│                  docker-compose                  │
│                                                  │
│  ┌─────────────────────────────────────────┐     │
│  │           bot（主容器）                  │     │
│  │  - Python TG Bot（精简）                 │     │
│  │  - FastAPI Web Server（新增）            │     │
│  │  - 涩花爬虫调度                          │     │
│  │  - 115 离线任务                          │     │
│  │  不再内置 Chrome                        │     │
│  └────────────┬────────────────────────────┘     │
│               │                                  │
│     ┌─────────┴──────────┐                       │
│     ▼                    ▼                       │
│  ┌──────────┐    ┌──────────────────┐            │
│  │  selenium │    │  flaresolverr    │            │
│  │ standalone│    │  CF盾处理        │            │
│  │  -chrome  │    │  :8191          │            │
│  │  2GB shm  │    └──────────────────┘            │
│  └──────────┘                                    │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │  volumes                                 │    │
│  │  /config  /app/images  /tmp              │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

---

## Docker 服务说明

| 服务 | 镜像 | 说明 |
|---|---|---|
| `bot` | 自建（项目 Dockerfile）| 主服务，无 Chrome |
| `selenium` | `selenium/standalone-chrome:latest` | 独立浏览器，`shm_size: 2gb` |
| `flaresolverr` | `ghcr.io/flaresolverr/flaresolverr:latest` | CF 验证，可选 |

主容器通过环境变量找到两个服务：
```
REMOTE_SELENIUM_URL=http://selenium:4444/wd/hub
FLARESOLVERR_URL=http://flaresolverr:8191/v1
```
代码已支持，无需改动。

---

## 现有代码处理清单

### 删除（不需要）

```
handlers/auth_handler.py         115扫码授权（新版不支持）

handlers/subscribe_movie_handler.py  电影订阅
handlers/av_download_handler.py  AV下载命令
handlers/rss_handler.py          RSS订阅
handlers/aria2_handler.py        Aria2推送
core/av_daily_update.py          Javbee日更
core/subscribe_movie.py          电影订阅
core/javbus.py                   JavBus
core/t66y.py                     草榴1024
core/video_downloader.py         视频下载
utils/fast_telethon.py           大文件上传
utils/aria2.py                   Aria2客户端
utils/cover_capture.py           封面截图
```

### 保留功能

```
core/sehua_spider.py             涩花爬虫（核心）
core/open_115.py                 115 API客户端
core/selenium_browser.py         浏览器封装
utils/ai.py                      AI重命名
utils/message_queue.py           TG消息队列
utils/sqlitelib.py               SQLite工具
utils/logger.py                  日志
utils/alioss.py                  OSS（图片上传）
utils/utils.py                   通用工具
handlers/download_handler.py     磁力下载TG交互 自动识别
handlers/video_handler.py        视频转存 自动识别上传视频
handlers/sync_handler.py         目录同步
```

### 精简（改现有文件）

```
core/offline_task_retry.py       只保留涩花相关函数（已完成）
core/scheduler.py                只保留涩花定时任务
handlers/crawl_handler.py        只保留 /csh
handlers/offline_task_handler.py 只保留 /rl，修复import
init.py                          删除 aria2_client/tg_user_client/CRAWL_JAV_STATUS
115bot.py                        删除无用handler注册
```

### 新增

```
utils/media_utils.py             create_strm_file + notice_emby_scan_library（已完成）
web/server.py                    FastAPI入口（已完成）
web/utils.py                     DB/YAML/日志流共享工具（已完成）
web/routers/dashboard.py         Dashboard统计与趋势（已完成）
web/routers/sehua.py             涩花数据查询与离线提交（已完成）
web/routers/strategy.py          策略CRUD与正则测试（已完成）
web/routers/tasks.py             离线重试队列（已完成）
web/routers/crawl.py             爬取触发、状态、SSE实时日志（已完成）
web/routers/system.py            系统状态、配置读写（已完成）
```

---

## TG Bot（保留命令）

| 命令 | 功能 |
|---|---|
| `/start` | 帮助 |
| `/reload` | 重载配置 |
| `/csh [日期]` | 手动触发涩花爬取 |
| `/rl` | 查看/清空重试列表 |

通知功能全保留（离线完成后推送）。

---

## Web 前端

### 技术栈

```
Vite + React 18 + TypeScript
shadcn/ui + Tailwind CSS
React Router v6
TanStack Query v5
Axios
Zustand
Recharts（shadcn chart 内置）
```

### 初始化命令

```bash
npm create vite@latest web-ui -- --template react-ts
cd web-ui
npx shadcn@latest init
npm install react-router-dom @tanstack/react-query axios zustand
```

Phase 3 新会话从这里开始。前端开发时建议用 `VITE_API_BASE_URL=http://127.0.0.1:8000` 指向后端；后端 API 已在 Phase 2 提供。

### 页面模块

| 页面 | 核心功能 |
|---|---|
| Dashboard | 统计卡片 + 趋势折线图 + 版块饼图 + 最近活动 |
| 涩花数据 | 分页表格、版块/日期/状态筛选、手动离线、批量操作 |
| 策略管理 | 策略增删改、广告过滤规则、正则实时测试 |
| 离线任务 | 重试队列查看、单条重试、清空 |
| 爬取控制 | 日期触发、状态指示、**SSE实时日志滚动** |
| 系统 | Token状态、配置编辑、日志级别 |

---

## Web 后端 API

```
GET  /api/dashboard/stats
GET  /api/dashboard/trend?days=30

GET  /api/sehua?page&size&section&status&keyword
POST /api/sehua/{id}/download
POST /api/sehua/batch-download

GET  /api/strategy/rules
POST /api/strategy/rules
PUT  /api/strategy/rules/{id}
DELETE /api/strategy/rules/{id}
POST /api/strategy/test

GET  /api/tasks
POST /api/tasks/{id}/retry
DELETE /api/tasks/{id}
DELETE /api/tasks/all

POST /api/crawl/trigger
GET  /api/crawl/status
GET  /api/crawl/logs          ← SSE stream

GET  /api/system/status
GET  /api/system/config
PUT  /api/system/config
```

---

## 新增依赖

### Python

```
fastapi
uvicorn[standard]
sse-starlette
```

### 前端

```
react-router-dom
@tanstack/react-query
axios
zustand
```

---

## 项目目录结构

```
Telegram-115bot/
├── app/
│   ├── core/
│   │   ├── sehua_spider.py
│   │   ├── open_115.py
│   │   ├── selenium_browser.py
│   │   ├── offline_task_retry.py   ← 已精简
│   │   └── scheduler.py            ← 待精简
│   ├── handlers/
│   │   ├── crawl_handler.py        ← 待精简
│   │   └── offline_task_handler.py ← 待修复
│   ├── utils/
│   │   ├── ai.py
│   │   ├── media_utils.py          ← 已新建
│   │   ├── message_queue.py
│   │   ├── sqlitelib.py
│   │   ├── logger.py
│   │   ├── alioss.py
│   │   └── utils.py
│   ├── web/                        ← 全部新增
│   │   ├── server.py
│   │   └── routers/
│   │       ├── dashboard.py
│   │       ├── sehua.py
│   │       ├── strategy.py
│   │       ├── tasks.py
│   │       ├── crawl.py
│   │       └── system.py
│   ├── images/
│   ├── init.py                     ← 待精简
│   └── 115bot.py                   ← 待精简
│
├── web-ui/                         ← 全部新增
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                 ← shadcn生成
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Header.tsx
│   │   │   └── shared/
│   │   │       ├── DataTable.tsx
│   │   │       ├── StatusBadge.tsx
│   │   │       └── LogViewer.tsx   ← SSE日志窗口
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── SehuaData.tsx
│   │   │   ├── Strategy.tsx
│   │   │   ├── Tasks.tsx
│   │   │   ├── CrawlControl.tsx
│   │   │   └── System.tsx
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── dashboard.ts
│   │   │   ├── sehua.ts
│   │   │   ├── strategy.ts
│   │   │   ├── tasks.ts
│   │   │   ├── crawl.ts
│   │   │   └── system.ts
│   │   ├── types/index.ts
│   │   ├── hooks/
│   │   │   └── useCrawlLogs.ts    ← SSE hook
│   │   └── store/
│   │       └── crawlStore.ts
│   ├── package.json
│   └── vite.config.ts
│
├── config/
│   ├── config.yaml
│   └── crawling_strategy.yaml
│
├── Dockerfile                      ← 去掉Chrome，改轻量镜像
├── docker-compose.yaml             ← 新增selenium + flaresolverr服务
└── requirements.txt                ← 新增fastapi/uvicorn/sse-starlette
```

---

## 执行顺序

```
Phase 1  Python 后端精简（剩余4个文件）
Phase 2  FastAPI web/server.py + 6个路由
Phase 3  web-ui 脚手架初始化 + shadcn/ui 安装
Phase 4  前端6个页面开发
Phase 5  Dockerfile + docker-compose 更新
Phase 6  本地联调测试
Phase 7  提交推送
```

---
