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
  - 手动触发抓取任务（今日/昨日/近 7 天），通过 SSE 实时查看日志
  - 管理 115 离线任务失败重试队列，支持单条/全部重试
  - 下载后处理：自动清理广告文件、按标题重命名、按年月归档
  - 系统配置编辑、Telegram / 115 连接测试、扫码登录 115

- **115 离线下载**
  - 基于 115 Open Platform API，支持 OAuth2 PKCE 扫码授权
  - 提交 magnet/ed2k 离线下载，自动重试失败任务
  - 下载完成后自动执行清理（广告文件/小文件）和目录重命名

## 按番号整理（可选）

在 `config.yaml` 中开启 `organize.enabled`，涩花离线任务完成、广告清理和标题重命名之后，会把目录里的正片按番号移动到 `{root}/{分类}/{番号}/`，并命名为 Emby 可识别的多版本格式：

```
/涩花/整理/日本有码/MIDA-752/MIDA-752 - C.mp4
/涩花/整理/日本有码/MIDA-752/MIDA-752 - UC.mp4
```

- 后缀：`-C` 中文字幕，`-UC` 无码破解+中文字幕，`-U` 无码破解；`-CD1` 等分段追加为 `cd1`
- 分类与 MDC-NG 一致：日本有码 / 日本无码 / 素人 / FC2 / 国产 / 欧美；未识别（未知）保留原位
- 同番号已有目录时合并进去；目标文件已存在则跳过
- `dry_run: true`（默认）只输出日志不改动 115；所有 API 调用按 `api_interval_sec` 串行间隔
- 源目录无剩余正片时才删除（仅非 dry-run）
- 解析逻辑见 `app/core/organize.py`，测试：`pytest tests/test_organize.py`

### Emby 热门合集（可选，默认关闭）

开启 `emby.enabled` 后，每天 `emby.sync_time` 抓取 missav 今日/本周/本月热门榜单（只读榜单页，不下载），按番号在 Emby 中查找已有影片，同步为合集「今日热门 / 本周热门 / 本月热门」：新上榜的加入、掉榜的移除。TG 发送 `/embyhot` 可手动触发。

- 配置项：`url`、`api_key`、`user_id`（可选）、`sync_time`、`max_items`、`collections`（榜单→合集名）、`list_paths`（可选）
- 番号匹配复用 `organize` 的解析规则（文件名/路径/名称）；同一番号多版本都会加入合集
- 榜单自动翻页（`?page=N`），直到凑满 `max_items`（默认 48）或 `max_pages`
- `auto_download: true` 时，上榜但库中没有的番号会自动补全：按 `download_source_order`（默认 `[sehuatang, missav]`）先在涩花站内搜索番号（「高清中文字幕」版块/中文字幕帖优先），找不到再取 missav 详情页 magnet；提交 115 离线后写入 `sehua_data`/`missav_data`，走正常后处理（广告清理 → 重命名 → `organize` 整理）。每个番号 `retry_days` 天内只尝试一次，单次最多 `max_downloads_per_run` 个，每个提交都会 TG 通知
- 测试：`pytest tests/test_emby_hot.py tests/test_emby_hot_download.py`

## 快速开始

### 环境要求

- Docker + Docker Compose
- 115 Open Platform App ID（扫码授权时需要；已有 Token 可不填；[申请入口](https://open.115.com/)）
- Telegram Bot Token（使用 Telegram Bot 时需要）

### 使用 Docker Compose 部署

1. **克隆并初始化配置**

   ```bash
   git clone https://github.com/yelc66/Reaper115.git
   cd Reaper115
   mkdir -p config tmp
   cp app/config.yaml.example config/config.yaml
   ```

   编辑 `config/config.yaml`，以下字段按使用方式填写：

   | 配置项                                 | 说明                                                                                                               |
   | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
   | `bot_token`                            | Telegram Bot Token；使用 Bot 时填写                                                                                |
   | `allowed_user`                         | 允许使用 Bot 的 Telegram 用户 ID；使用 Bot 时填写                                                                  |
   | `115_app_id`                           | 115 Open Platform App ID；扫码授权时填写                                                                           |
   | `access_token` / `refresh_token`       | 115 授权令牌；可直接粘贴已有 Token，或填写 `115_app_id` 后通过 Web UI / Bot 扫码登录自动获取                       |
   | `remote_selenium_url`                  | 远程 Selenium 地址；启用涩花抓取时必填，Docker Compose 默认 `http://chrome:4444`                                   |
   | `flaresolverr_url`                     | FlareSolverr 服务地址；可选，遇到 Cloudflare 验证时自动调用，Docker Compose 默认走环境变量 `FLARESOLVERR_URL`     |
   | `sehuatang_spider.sections`            | 要抓取的分区，默认已配置 `高清中文字幕`，按需修改 `save_path`                                                      |

2. **启动服务**

   ```bash
   docker compose -f docker/docker-compose.yaml up -d
   ```

   启动后 Web UI 默认可通过 `http://<host>:8115` 访问；如果已配置 Telegram Bot，Bot 会同时开始运行。

3. **本地构建镜像**（可选）

   ```bash
   docker build -f docker/Dockerfile -t reaper115-bot:latest .
   BOT_IMAGE=reaper115-bot:latest docker compose -f docker/docker-compose.yaml up -d
   ```

## 本地开发

不使用 Docker 时，可以设置 `TG115_DEBUG=1`，让项目使用本地目录作为运行路径：

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p config tmp
cp app/config.yaml.example config/config.yaml
# 按上方「关键配置」表格填写 config/config.yaml
./scripts/dev.sh
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

### 涩花抓取（`sehuatang_spider`）

| 配置项               | 默认值  | 说明                                   |
| -------------------- | ------- | -------------------------------------- |
| `enable`             | `false` | 主开关                                 |
| `sync_time`          | `03:00` | 每日自动抓取时间                       |
| `notify_me`          | `true`  | 提交下载后发 Telegram 通知             |
| `notify_with_image`  | `false` | 通知是否附带封面图                     |
| `sort_by_year_month` | `false` | 按年月子目录归档                       |
| `rename_by_title`    | `true`  | 下载完成后按标题重命名目录             |
| `sections`           | —       | 抓取分区列表，每项含 `name`、`save_path`、可选 `rules` |

`sections.rules` 为空时该分区所有标题均下载。规则支持 `include`/`exclude` 两种 `kind`，通过 Web UI 策略页管理。

### 广告清理（`clean_policy`）

下载完成后自动对目录执行清理，规则按优先级依次生效：

1. `ad_extensions` — 扩展名匹配（`.html`、`.txt`、`.url` 等）直接删除，不受大小和保护限制
2. `ad_name_patterns` — 文件名含关键词直接删除，不受大小限制
3. `less_than` — 小于指定大小（默认 `100M`）的文件删除
4. `protect_largest: true` — 目录中体积最大的文件始终保留（1、2 步骤除外）

`switch: "off"` 可完全关闭清理。

### 浏览器服务

抓取使用 Remote Selenium 作为主浏览器，FlareSolverr 在遇到 Cloudflare 验证时自动介入。`docker/docker-compose.yaml` 默认包含 `chrome` 和 `flaresolverr` 两个服务，并通过环境变量提供默认地址。

### 其他

- **Web UI 认证**：`web.auth_key` 不为空时启用登录保护
- **代理**：在 `docker/docker-compose.yaml` 中设置 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量

## Bot 命令

| 命令             | 说明                    |
| ---------------- | ----------------------- |
| `/start`         | 显示帮助                |
| `/reload`        | 重新加载配置            |
| `/rl`            | 查看离线失败重试队列    |
| `/auth`          | 重新扫码授权 115        |
| `/csh`           | 抓取昨天或预设范围数据  |
| `/csh_yesterday` | 抓取昨天的涩花数据      |
| `/csh_today`     | 抓取今天的涩花数据      |
| `/csh_7days`     | 抓取最近 7 天的涩花数据 |
| `/q`             | 取消当前会话            |

`/csh` 支持 `today`、`yesterday` 或 `7days`，例如 `/csh today`。

## API 接口

所有接口以 `/api/` 为前缀：

| 路由前缀          | 主要功能                                                         |
| ----------------- | ---------------------------------------------------------------- |
| `/api/dashboard`  | 统计数据（总量、趋势）                                           |
| `/api/sehua`      | 资源列表、单条/批量下载、删除、下载后处理（清理+重命名）         |
| `/api/strategy`   | 正则测试；策略规则增删改由 Web UI 通过 `/api/system/config` 写入配置 |
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
│   │   └── selenium_browser.py   # Selenium WebDriver 封装
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
├── docker/                    # Dockerfile、docker-compose.yaml
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
