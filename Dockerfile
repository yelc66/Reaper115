# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY web-ui/package.json web-ui/package-lock.json ./
RUN npm ci --prefer-offline
COPY web-ui/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
LABEL authors="yelc668"

# 1. 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 2. 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. 安装 Python 依赖
COPY requirements.txt /app/
RUN pip install --upgrade pip --no-cache-dir && \
    pip install -r requirements.txt --no-cache-dir

ADD ./app .

# 3b. 将前端构建产物复制到 web/dist/，FastAPI 会作为静态文件提供服务
COPY --from=frontend-builder /build/dist /app/web/dist

# 4. 设置路径
ENV PYTHONPATH="/app:/app/utils:/app/core:/app/handlers:/app/.."

# 5. 启动命令
CMD ["python", "115bot.py"]
