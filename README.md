<div align="center">
    <h1>Reaper115</h1>
    <p>涩花资源抓取 + 115 离线下载 + Web 管理后台</p>
</div>

Reaper115 是一个基于 Python 的 Telegram Bot 项目，聚焦涩花资源自动抓取、策略过滤、115 网盘离线下载和失败任务重试，并提供 FastAPI + React 构建的 Web 管理后台。

## 功能特性

- **涩花资源抓取**
  - 支持按计划自动抓取 sehuatang.net（默认每天 03:00）
  - 支持配置不同分区和保存路径，灵活的 YAML 规则过滤
  - 通过 Web UI 管理标题过滤规则，支持正则在线测试
  - Telegram 通知，可选附带封面图

- **Web 管理后台**
  - 仪表盘展示抓取统计（总量、已下载、按分区）和时间趋势折线图
  - 浏览、检索和下载已抓取资源，支持按分区/状态/关键词筛选
  - 管理分区策略规则，支持规则增删改查和正则在线验证
  - 手动触发抓取任务（今日/昨日/近 7 天/自定义日期），通过 SSE 实时查看日志
  - 管理 115 离线任务失败重试队列，支持单条/全部重试
  - 下载后处理：自动清理广告文件、按标题重命名、按年月归档
  - 系统配置编辑、Telegram / 115 连接测试、扫码登录 115

- **115 离线下载**
  - 基于 115 Open Platform API，支持 OAuth2 PKCE 扫码授权
  - 提交 magnet/ed2k 离线下载，自动重试失败任务
  - 下载完成后自动执行清理（广告文件/小文件）和目录重命名

## 快速开始

### 环境要求

- Docker + Docker Compose
- 115 Open Platform App ID（[申请入口](https://open.115.com/)）
- Telegram Bot Token

### 使用 Docker Compose 部署

1. **克隆并初始化配置**

   ```bash
   git clone https://github.com/yelc66/Reaper115.git
   cd Reaper115
   mkdir -p config tmp
   cp app/config.yaml.example config/config.yaml
   ```

   编辑 `config/config.yaml`，以下字段为**必填项**：

   | 配置项                                 | 说明                                                                                                               |
   | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
   | `bot_token`                            | Telegram Bot Token                                                                                                 |
   | `allowed_user`                         | 允许使用 Bot 的 Telegram 用户 ID                                                                                   |
   | `115_app_id`                           | 115 Open Platform App ID                                                                                           |
   | `access_token` / `refresh_token`       | 115 授权令牌（与 `115_app_id` 二选一填写：直接粘贴已有 Token，或填写 `115_app_id` 后通过 Web UI 扫码登录自动获取） |
   | `sehuatang_spider.flaresolverr_url`    | FlareSolverr 服务地址（与 `remote_selenium_url` 二选一，推荐使用此方式）                                           |
   | `sehuatang_spider.remote_selenium_url` | 远程 Selenium 地址（与 `flaresolverr_url` 二选一）                                                                 |
   | `sehuatang_spider.sections`            | 要抓取的分区，默认已配置 `高清中文字幕`，按需修改 `save_path`                                                      |

2. **启动服务**

   ```bash
   docker compose up -d
   ```

   启动后 Telegram Bot 会开始运行，Web UI 默认可通过 `http://<host>:8115` 访问。

3. **本地构建镜像**（可选）

   ```bash
   docker build -t reaper115-bot:latest .
   docker compose up -d
   ```

## 本地开发

不使用 Docker 时，可以设置 `TG115_DEBUG=1`，让项目使用本地目录作为运行路径：

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p config tmp
cp app/config.yaml.example config/config.yaml
# 按上方「必填项」表格填写 config/config.yaml
TG115_DEBUG=1 python app/115bot.py
```

Web UI 开发服务默认将 API 代理到 `http://127.0.0.1:8115`：

```bash
cd web-ui && cp .env.example .env
# 设置 VITE_API_BASE_URL=http://127.0.0.1:8115
npm install && npm run dev
```

Web UI 默认访问地址为 `http://localhost:5173`。

## 配置说明

完整配置项请参考 `app/config.yaml.example`。

### 涩花抓取配置

`config.yaml` 中的 `sehuatang_spider` 是抓取相关配置：

| 配置项               | 默认值  | 说明                                         |
| -------------------- | ------- | -------------------------------------------- |
| `enable`             | `false` | 是否启用涩花抓取                             |
| `sync_time`          | `03:00` | 每日自动抓取时间                             |
| `notify_me`          | `true`  | 成功提交下载后是否发送 Telegram 通知         |
| `notify_with_image`  | `true`  | 通知是否附带封面图，关闭后跳过图片抓取       |
| `sort_by_year_month` | `false` | 是否按年月子目录归档保存                     |
| `rename_by_title`    | `false` | 下载完成后是否按标题自动重命名目录           |
| `sections`           | `[]`    | 要抓取的分区列表，格式为 `{name, save_path}` |

### 广告清理配置

`config.yaml` 中的 `clean_policy` 控制下载后自动清理：

| 配置项              | 说明                                     |
| ------------------- | ---------------------------------------- |
| `switch`            | 是否启用自动清理                         |
| `less_than`         | 小于此大小的文件自动删除（如 `100M`）    |
| `ad_name_patterns`  | 文件名包含这些关键词时删除               |
| `ad_extensions`     | 指定扩展名文件自动删除                   |
| `protect_largest`   | 始终保留目录中最大的文件                 |

### 定时任务

| 任务               | 默认时间          | 说明                   |
| ------------------ | ----------------- | ---------------------- |
| 涩花抓取           | 每天 03:00        | 可在 `sync_time` 中调整 |
| 离线任务重试       | 每天 09:00、18:00 | 重试失败的下载任务     |
| 失败下载重试       | 每 12 小时        | 轮询未完成任务         |
| 请求计数重置       | 每天 00:00        | 重置 API 请求计数      |

### Selenium / FlareSolverr

抓取流程使用 SeleniumBase。绕过 Cloudflare 时可选择：

- **FlareSolverr**：推荐方式，设置 `FLARESOLVERR_URL` 环境变量，并在 `docker-compose.yaml` 中启用 `flaresolverr` 服务
- **Remote Selenium**：设置 `REMOTE_SELENIUM_URL`，并在 `docker-compose.yaml` 中启用 `chrome` 服务

### Web UI 认证

在 `config.yaml` 中配置 `web.auth_key` 可为 Web UI 开启登录保护。未设置时无需登录。

### 代理

如需代理，可在 `docker-compose.yaml` 中设置 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量。

## Bot 命令

| 命令             | 说明                    |
| ---------------- | ----------------------- |
| `/start`         | 显示帮助                |
| `/reload`        | 重新加载配置            |
| `/rl`            | 查看离线失败重试队列    |
| `/csh_yesterday` | 抓取昨天的涩花数据      |
| `/csh_today`     | 抓取今天的涩花数据      |
| `/csh_7days`     | 抓取最近 7 天的涩花数据 |
| `/q`             | 取消当前会话            |

## API 接口

所有接口以 `/api/` 为前缀：

| 路由前缀          | 主要功能                                                         |
| ----------------- | ---------------------------------------------------------------- |
| `/api/dashboard`  | 统计数据（总量、趋势）                                           |
| `/api/sehua`      | 资源列表、单条/批量下载、删除、下载后处理（清理+重命名）         |
| `/api/strategy`   | 策略规则 CRUD、正则测试                                          |
| `/api/crawl`      | 触发抓取、查询状态、SSE 实时日志流                               |
| `/api/tasks`      | 离线任务重试队列列表、重试、删除                                 |
| `/api/system`     | 系统状态、配置读写、重启、Telegram/115 连接测试、扫码登录 115    |
| `/api/auth`       | Web UI 登录状态检查、登录                                        |

## 项目结构

```text
.
├── app/
│   ├── 115bot.py              # 入口文件
│   ├── config.yaml.example    # 配置模板
│   ├── core/
│   │   ├── sehuatang_spider.py   # 涩花爬虫
│   │   ├── open_115.py           # 115 Open API 客户端
│   │   ├── scheduler.py          # APScheduler 定时任务
│   │   ├── offline_task_retry.py # 下载后处理（清理+重命名）
│   │   └── selenium_browser.py   # SeleniumBase 封装
│   ├── handlers/              # Telegram 命令处理
│   ├── init.py                # 全局状态和启动初始化
│   ├── utils/                 # 数据库、消息队列和工具函数
│   └── web/
│       ├── server.py          # FastAPI 应用
│       ├── routers/           # API 路由（dashboard/sehua/strategy/crawl/tasks/system）
│       └── utils.py           # 共享工具函数
├── web-ui/                    # Vite + React 18 + TypeScript 前端
│   └── src/
│       ├── api/               # Axios 客户端、DTO、模型、映射、接口函数
│       ├── components/        # UI 组件库
│       └── pages/             # Dashboard · SehuaData · Strategy · Crawl · Tasks · Config · Login
├── config/                    # 运行时配置，默认被 gitignore
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```

## Web UI 技术栈

Vite · React 18 · TypeScript · Tailwind CSS · TanStack Query v5 · React Router v6 · Recharts · Lucide Icons

## 致谢

感谢原项目 [qiqiandfei/Telegram-115bot](https://github.com/qiqiandfei/Telegram-115bot) 提供的基础实现与思路参考。

## 许可证

MIT License，详见 [LICENSE](LICENSE)。

## 免责声明

本项目仅用于学习和研究。请遵守所在地法律法规以及相关平台服务条款，使用者需自行承担使用风险。
