<div align="center">
    <h1>Reaper115</h1>
    <p>涩花资源抓取 + 115 离线下载 + Web 管理后台</p>
</div>

Reaper115 是一个基于 Python 的 Telegram Bot 项目，聚焦涩花资源自动抓取、策略过滤、115 网盘离线下载和失败任务重试，并提供 FastAPI + React 构建的 Web 管理后台。

## 功能特性

- **涩花资源抓取**
  - 支持按计划自动抓取 sehuatang.net
  - 支持配置不同分区和保存路径
  - 支持通过 Web UI 管理标题过滤规则和正则测试
  - 支持通过 Telegram 发送下载通知，可选附带封面图

- **Web 管理后台**
  - 仪表盘展示抓取统计和趋势
  - 浏览、检索和下载已抓取资源
  - 管理分区策略规则，支持规则增删改查和正则验证
  - 手动触发抓取任务，并通过 SSE 查看实时日志
  - 管理 115 离线任务失败重试队列
  - 查看和编辑系统配置，执行连接检查

- **115 离线下载**
  - 支持将资源提交到 115 网盘离线下载
  - 基于 115 Open Platform API
  - 支持失败任务进入重试队列

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

   | 配置项 | 说明 |
   | --- | --- |
   | `bot_token` | Telegram Bot Token |
   | `allowed_user` | 允许使用 Bot 的 Telegram 用户 ID |
   | `115_app_id` | 115 Open Platform App ID |
   | `access_token` / `refresh_token` | 115 授权令牌（与 `115_app_id` 二选一填写：直接粘贴已有 Token，或填写 `115_app_id` 后通过 Web UI 扫码登录自动获取）|
   | `sehuatang_spider.flaresolverr_url` | FlareSolverr 服务地址（与 `remote_selenium_url` 二选一，推荐使用此方式）|
   | `sehuatang_spider.remote_selenium_url` | 远程 Selenium 地址（与 `flaresolverr_url` 二选一）|
   | `sehuatang_spider.sections` | 要抓取的分区，默认已配置 `高清中文字幕`，按需修改 `save_path` |

2. **启动服务**

   ```bash
   docker compose up -d
   ```

   启动后 Telegram Bot 会开始运行，Web UI 默认可通过 `http://<host>:8000` 访问。

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

Web UI 开发服务默认将 API 代理到 `http://127.0.0.1:8000`：

```bash
cd web-ui && cp .env.example .env
# 设置 VITE_API_BASE_URL=http://127.0.0.1:8000
npm install && npm run dev
```

Web UI 默认访问地址为 `http://localhost:5173`。

## 配置说明

完整配置项请参考 `app/config.yaml.example`。

### 涩花抓取配置

`config.yaml` 中的 `sehuatang_spider` 是抓取相关配置：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `enable` | `false` | 是否启用涩花抓取 |
| `notify_me` | `true` | 成功提交下载后是否发送 Telegram 通知 |
| `notify_with_image` | `true` | 通知是否附带封面图，关闭后跳过图片抓取 |
| `sort_by_year_month` | `false` | 是否按年月创建保存目录 |
| `sections` | `[]` | 要抓取的分区列表，格式为 `{name, save_path}` |

### 定时任务

默认每天 **03:00** 执行抓取任务，可在 `config.yaml` 的 `scheduler` 中调整。

### Selenium / FlareSolverr

抓取流程使用 SeleniumBase。绕过 Cloudflare 时可选择：

- **FlareSolverr**：推荐方式，设置 `FLARESOLVERR_URL` 环境变量，并在 `docker-compose.yaml` 中启用 `flaresolverr` 服务
- **Remote Selenium**：设置 `REMOTE_SELENIUM_URL`，并在 `docker-compose.yaml` 中启用 `chrome` 服务

### 代理

如需代理，可在 `docker-compose.yaml` 中设置 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量。

## Bot 命令

| 命令 | 说明 |
| --- | --- |
| `/start` | 显示帮助 |
| `/reload` | 重新加载配置 |
| `/rl` | 查看离线失败重试队列 |
| `/csh_yesterday` | 抓取昨天的涩花数据 |
| `/csh_today` | 抓取今天的涩花数据 |
| `/csh_7days` | 抓取最近 7 天的涩花数据 |
| `/q` | 取消当前会话 |

也可以手动发送 `/csh YYYYMMDD` 抓取指定日期的数据。

## 项目结构

```text
.
├── app/
│   ├── 115bot.py              # 入口文件
│   ├── config.yaml.example    # 配置模板
│   ├── core/                  # 抓取、调度、115 API 客户端
│   ├── handlers/              # Telegram 命令处理
│   ├── init.py                # 全局状态和启动初始化
│   ├── utils/                 # 数据库、消息队列和工具函数
│   └── web/                   # FastAPI 服务和路由
├── web-ui/                    # Vite + React 18 + TypeScript 前端
├── config/                    # 运行时配置，默认被 gitignore
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```

## Web UI 技术栈

Vite · React 18 · TypeScript · Tailwind CSS · TanStack Query v5 · React Router v6 · Recharts

主要页面：Dashboard · Sehua Data · Strategy · Crawl · Tasks · Config · System

## 致谢

感谢原项目 [qiqiandfei/Telegram-115bot](https://github.com/qiqiandfei/Telegram-115bot) 提供的基础实现与思路参考。

## 许可证

MIT License，详见 [LICENSE](LICENSE)。

## 免责声明

本项目仅用于学习和研究。请遵守所在地法律法规以及相关平台服务条款，使用者需自行承担使用风险。
