# Spec-014: Docker部署方案

## 1. 功能概述

本模块负责项目的容器化部署方案，实现：
- 全部服务Docker容器化（前端、后端、PostgreSQL、Redis、Celery Worker）
- Docker Compose 一键部署
- 阿里云服务器适配
- 生产环境配置（Nginx反向代理、HTTPS、日志、监控）
- 一键部署脚本
- 数据持久化与备份

---

## 2. 技术选型

| 技术 | 用途 |
|------|------|
| Docker | 容器化 |
| Docker Compose | 多容器编排 |
| Nginx | 反向代理 + 静态资源 |
| Let's Encrypt | HTTPS证书 |
| Certbot | 证书自动续期 |

---

## 3. 服务架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         阿里云 ECS                               │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Docker Compose                           │  │
│  │                                                            │  │
│  │  ┌──────────┐     ┌──────────────────────────────────┐    │  │
│  │  │  Nginx   │────▶│         Frontend                 │    │  │
│  │  │  :80/443 │     │    (Next.js :3000)               │    │  │
│  │  └──────────┘     └──────────────────────────────────┘    │  │
│  │       │                                                    │  │
│  │       │ /api/*                                             │  │
│  │       ▼                                                    │  │
│  │  ┌──────────────────────────────────────────────────┐      │  │
│  │  │              Backend (FastAPI :8000)              │      │  │
│  │  └──────────────────────────────────────────────────┘      │  │
│  │       │                                                    │  │
│  │       ├────────────────────────┐                           │  │
│  │       ▼                        ▼                           │  │
│  │  ┌──────────┐          ┌──────────────┐                   │  │
│  │  │PostgreSQL│          │    Redis      │                   │  │
│  │  │  :5432   │          │    :6379      │                   │  │
│  │  └──────────┘          └──────────────┘                   │  │
│  │                           │                                │  │
│  │                           ▼                                │  │
│  │                    ┌──────────────┐                        │  │
│  │                    │Celery Worker │                        │  │
│  │                    │  (异步任务)   │                        │  │
│  │                    └──────────────┘                        │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │
│  │  /data/pgdata  │  │  /data/redis  │  │   /data/uploads   │    │
│  │  (数据卷)      │  │  (数据卷)     │  │   (上传文件)       │    │
│  └───────────────┘  └───────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| nginx | nginx:alpine | 80, 443 | 反向代理 + 静态资源 |
| frontend | 自建 (Node 20) | 3000 | Next.js 应用 |
| backend | 自建 (Python 3.11) | 8000 | FastAPI 应用 |
| celery_worker | 同 backend | - | 异步任务处理 |
| celery_beat | 同 backend | - | 定时任务调度 |
| postgres | postgres:16-alpine | 5432 | 主数据库 |
| redis | redis:7-alpine | 6379 | 缓存 + 消息队列 |

---

## 4. 目录结构

```
article-generator/
├── docker/
│   ├── nginx/
│   │   ├── nginx.conf              # Nginx主配置
│   │   ├── conf.d/
│   │   │   ├── default.conf        # 开发环境
│   │   │   └── production.conf     # 生产环境(HTTPS)
│   │   └── ssl/                    # SSL证书目录
│   ├── Dockerfile.frontend         # 前端镜像
│   ├── Dockerfile.backend          # 后端镜像
│   ├── docker-compose.yml          # 开发环境
│   ├── docker-compose.prod.yml     # 生产环境
│   └── .env.example                # 环境变量模板
├── scripts/
│   ├── deploy.sh                   # 一键部署脚本
│   ├── backup.sh                   # 备份脚本
│   ├── restore.sh                  # 恢复脚本
│   └── health-check.sh             # 健康检查脚本
└── ...
```

---

## 5. Dockerfile

### 5.1 前端 Dockerfile

```dockerfile
# docker/Dockerfile.frontend

# ===== 构建阶段 =====
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --registry=https://registry.npmmirror.com

# 复制源码并构建
COPY frontend/ .

# 构建参数（环境变量）
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}

RUN npm run build

# ===== 运行阶段 =====
FROM node:20-alpine AS runner

WORKDIR /app

# 安全：不使用root运行
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制构建产物
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
```

### 5.2 后端 Dockerfile

```dockerfile
# docker/Dockerfile.backend

FROM python:3.11-slim AS base

# 系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装Python依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# 复制源码
COPY backend/ .

# 创建非root用户
RUN adduser --system --uid 1001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 默认启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 6. Docker Compose 配置

### 6.1 开发环境

```yaml
# docker/docker-compose.yml

version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    container_name: ag-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: article_generator
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres123}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: ag-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend (FastAPI)
  backend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: ag-backend
    restart: unless-stopped
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - APP_ENV=development
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD:-postgres123}@postgres:5432/article_generator
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DASHSCOPE_MODEL=${DASHSCOPE_MODEL:-qwen-max}
      - BING_SEARCH_API_KEY=${BING_SEARCH_API_KEY}
      - BING_SEARCH_ENDPOINT=${BING_SEARCH_ENDPOINT:-https://api.bing.microsoft.com/v7.0/search}
      - CORS_ORIGINS=["http://localhost:3000","http://localhost"]
    ports:
      - "8000:8000"
    volumes:
      - ../backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Celery Worker
  celery_worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: ag-celery-worker
    restart: unless-stopped
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD:-postgres123}@postgres:5432/article_generator
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DASHSCOPE_MODEL=${DASHSCOPE_MODEL:-qwen-max}
      - BING_SEARCH_API_KEY=${BING_SEARCH_API_KEY}
    volumes:
      - ../backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Frontend (Next.js)
  frontend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8000/api
        NEXT_PUBLIC_WS_URL: ws://localhost:8000/ws
    container_name: ag-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local
```

### 6.2 生产环境

```yaml
# docker/docker-compose.prod.yml

version: '3.8'

services:
  # Nginx - 反向代理
  nginx:
    image: nginx:alpine
    container_name: ag-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d/production.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - nginx_logs:/var/log/nginx
    depends_on:
      - frontend
      - backend
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    container_name: ag-postgres
    restart: always
    environment:
      POSTGRES_DB: ${DB_NAME:-article_generator}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # 生产环境不暴露端口到宿主机
    expose:
      - "5432"

  # Redis
  redis:
    image: redis:7-alpine
    container_name: ag-redis
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD:-redis123} --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-redis123}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    expose:
      - "6379"

  # Backend
  backend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: ag-backend
    restart: always
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-postgres}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-article_generator}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/2
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DASHSCOPE_MODEL=${DASHSCOPE_MODEL:-qwen-max}
      - BING_SEARCH_API_KEY=${BING_SEARCH_API_KEY}
      - CORS_ORIGINS=["https://${DOMAIN}","https://www.${DOMAIN}"]
    expose:
      - "8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Celery Worker
  celery_worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: ag-celery-worker
    restart: always
    command: celery -A app.tasks.celery_app worker --loglevel=warning --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-postgres}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-article_generator}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/2
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DASHSCOPE_MODEL=${DASHSCOPE_MODEL:-qwen-max}
      - BING_SEARCH_API_KEY=${BING_SEARCH_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Celery Beat (定时任务)
  celery_beat:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: ag-celery-beat
    restart: always
    command: celery -A app.tasks.celery_app beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/2
    depends_on:
      redis:
        condition: service_healthy

  # Frontend
  frontend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
      args:
        NEXT_PUBLIC_API_URL: https://${DOMAIN}/api
        NEXT_PUBLIC_WS_URL: wss://${DOMAIN}/ws
    container_name: ag-frontend
    restart: always
    expose:
      - "3000"
    depends_on:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local
  nginx_logs:
    driver: local
```

---

## 7. Nginx配置

### 7.1 生产环境配置

```nginx
# docker/nginx/conf.d/production.conf

# 上游服务
upstream frontend {
    server frontend:3000;
}

upstream backend {
    server backend:8000;
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    # Let's Encrypt 验证
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};

    # SSL证书
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 日志
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # 请求体大小限制
    client_max_body_size 10M;

    # 前端页面 + 静态资源
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Next.js 静态资源
    location /_next/static {
        proxy_pass http://frontend;
        proxy_cache_valid 60m;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # API 代理
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置（LLM调用可能较慢）
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 超时
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # FastAPI 文档 (可选，生产环境可关闭)
    location /docs {
        proxy_pass http://backend;
        # 生产环境建议限制访问
        # allow 10.0.0.0/8;
        # deny all;
    }

    location /openapi.json {
        proxy_pass http://backend;
    }

    # 健康检查
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

### 7.2 开发环境配置

```nginx
# docker/nginx/conf.d/default.conf

upstream frontend {
    server frontend:3000;
}

upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name localhost;

    client_max_body_size 10M;

    # 前端
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # API
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    # WebSocket
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

---

## 8. 环境变量

```bash
# docker/.env.example

# ===== 域名 =====
DOMAIN=your-domain.com

# ===== 数据库 =====
DB_NAME=article_generator
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

# ===== Redis =====
REDIS_PASSWORD=your_redis_password_here

# ===== 阿里云百炼 =====
DASHSCOPE_API_KEY=sk-xxxx
DASHSCOPE_MODEL=qwen-max

# ===== Bing Search =====
BING_SEARCH_API_KEY=your_bing_api_key
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search
```

---

## 9. 一键部署脚本

### 9.1 部署脚本

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===== 检查环境 =====
check_requirements() {
    log_info "检查环境依赖..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，正在安装..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        log_info "Docker 安装完成"
    fi
    
    # Docker Compose
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose 未安装，正在安装..."
        apt-get update && apt-get install -y docker-compose-plugin
        log_info "Docker Compose 安装完成"
    fi
    
    log_info "环境检查通过 ✓"
}

# ===== 初始化配置 =====
init_config() {
    log_info "初始化配置..."
    
    if [ ! -f docker/.env ]; then
        cp docker/.env.example docker/.env
        log_warn "已创建 .env 文件，请编辑 docker/.env 填入你的 API Key"
        log_warn "必填项: DASHSCOPE_API_KEY, BING_SEARCH_API_KEY, DB_PASSWORD"
        
        # 生成随机密码
        DB_PASS=$(openssl rand -base64 16 | tr -d '=/+' | head -c 16)
        REDIS_PASS=$(openssl rand -base64 16 | tr -d '=/+' | head -c 16)
        sed -i "s/your_secure_password_here/$DB_PASS/g" docker/.env
        sed -i "s/your_redis_password_here/$REDIS_PASS/g" docker/.env
        
        log_info "已生成随机数据库密码"
    fi
    
    # 检查API Key
    source docker/.env
    if [ -z "$DASHSCOPE_API_KEY" ] || [ "$DASHSCOPE_API_KEY" = "sk-xxxx" ]; then
        log_error "请在 docker/.env 中填入 DASHSCOPE_API_KEY"
        exit 1
    fi
    if [ -z "$BING_SEARCH_API_KEY" ] || [ "$BING_SEARCH_API_KEY" = "your_bing_api_key" ]; then
        log_error "请在 docker/.env 中填入 BING_SEARCH_API_KEY"
        exit 1
    fi
    
    log_info "配置初始化完成 ✓"
}

# ===== 构建镜像 =====
build_images() {
    log_info "构建Docker镜像..."
    
    cd docker
    docker compose -f docker-compose.prod.yml build --no-cache
    cd ..
    
    log_info "镜像构建完成 ✓"
}

# ===== 启动服务 =====
start_services() {
    log_info "启动所有服务..."
    
    cd docker
    docker compose -f docker-compose.prod.yml up -d
    cd ..
    
    log_info "等待服务就绪..."
    sleep 10
    
    # 检查服务状态
    log_info "服务状态:"
    cd docker
    docker compose -f docker-compose.prod.yml ps
    cd ..
    
    log_info "服务启动完成 ✓"
}

# ===== HTTPS配置（可选） =====
setup_https() {
    source docker/.env
    
    if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "your-domain.com" ]; then
        log_warn "未配置域名，跳过HTTPS设置"
        log_warn "如需配置HTTPS，请设置 DOMAIN 后重新运行: ./scripts/deploy.sh --https"
        return
    fi
    
    log_info "配置HTTPS证书..."
    
    # 安装certbot
    apt-get update && apt-get install -y certbot
    
    # 先停止nginx以释放80端口
    cd docker
    docker compose -f docker-compose.prod.yml stop nginx
    cd ..
    
    # 获取证书
    certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN \
        --email admin@$DOMAIN --agree-tos --no-eff-email
    
    # 复制证书到nginx目录
    mkdir -p docker/nginx/ssl
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem docker/nginx/ssl/
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem docker/nginx/ssl/
    
    # 重启nginx
    cd docker
    docker compose -f docker-compose.prod.yml start nginx
    cd ..
    
    log_info "HTTPS配置完成 ✓"
}

# ===== 数据库初始化 =====
init_database() {
    log_info "初始化数据库..."
    
    cd docker
    docker compose -f docker-compose.prod.yml exec backend \
        python -c "from app.database import engine, Base; import asyncio; asyncio.run(engine.dispose())"
    
    # 运行数据库迁移
    docker compose -f docker-compose.prod.yml exec backend \
        alembic upgrade head
    cd ..
    
    log_info "数据库初始化完成 ✓"
}

# ===== 主流程 =====
main() {
    echo ""
    echo "============================================"
    echo "  Article Generate - 一键部署脚本"
    echo "============================================"
    echo ""
    
    check_requirements
    init_config
    build_images
    start_services
    init_database
    
    if [ "$1" = "--https" ]; then
        setup_https
    fi
    
    echo ""
    echo "============================================"
    log_info "🎉 部署完成！"
    echo ""
    source docker/.env
    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "your-domain.com" ]; then
        log_info "🌐 访问地址: https://$DOMAIN"
    else
        log_info "🌐 访问地址: http://$(curl -s ifconfig.me)"
    fi
    echo ""
    log_info "📋 常用命令:"
    echo "   查看日志:  cd docker && docker compose -f docker-compose.prod.yml logs -f"
    echo "   重启服务:  cd docker && docker compose -f docker-compose.prod.yml restart"
    echo "   停止服务:  cd docker && docker compose -f docker-compose.prod.yml down"
    echo "   备份数据:  ./scripts/backup.sh"
    echo "============================================"
}

main "$@"
```

### 9.2 备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p $BACKUP_DIR

source docker/.env

echo "[INFO] 开始备份... ($TIMESTAMP)"

# 备份PostgreSQL
cd docker
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U ${DB_USER:-postgres} ${DB_NAME:-article_generator} | \
    gzip > "$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"
cd ..

echo "[INFO] 数据库备份完成: db_${TIMESTAMP}.sql.gz"

# 备份Redis
cd docker
docker compose -f docker-compose.prod.yml exec -T redis \
    redis-cli -a ${REDIS_PASSWORD:-redis123} BGSAVE
sleep 2
docker cp $(docker compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb \
    "$BACKUP_DIR/redis_${TIMESTAMP}.rdb"
cd ..

echo "[INFO] Redis备份完成: redis_${TIMESTAMP}.rdb"

# 清理旧备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "redis_*.rdb" -mtime +$RETENTION_DAYS -delete
echo "[INFO] 已清理 $RETENTION_DAYS 天前的备份"

# 备份文件信息
echo ""
echo "备份完成:"
ls -lh $BACKUP_DIR/*_${TIMESTAMP}*
```

### 9.3 恢复脚本

```bash
#!/bin/bash
# scripts/restore.sh

set -e

if [ -z "$1" ]; then
    echo "用法: ./scripts/restore.sh <备份文件>"
    echo "示例: ./scripts/restore.sh db_20240101_120000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1
source docker/.env

echo "[INFO] 从备份恢复: $BACKUP_FILE"

if [[ $BACKUP_FILE == *.sql.gz ]]; then
    echo "[INFO] 恢复数据库..."
    cd docker
    gunzip -c "../$BACKUP_FILE" | docker compose -f docker-compose.prod.yml exec -T postgres \
        psql -U ${DB_USER:-postgres} ${DB_NAME:-article_generator}
    cd ..
    echo "[INFO] 数据库恢复完成 ✓"
else
    echo "[ERROR] 不支持的备份文件格式"
    exit 1
fi
```

---

## 10. Next.js standalone 输出配置

```javascript
// frontend/next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',  // 关键：启用standalone输出
  reactStrictMode: true,
  
  // 图片域名白名单
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
}

module.exports = nextConfig
```

---

## 11. 服务器要求

### 11.1 最低配置

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 2核 | 4核 |
| 内存 | 4GB | 8GB |
| 磁盘 | 40GB | 100GB SSD |
| 带宽 | 3Mbps | 5Mbps |
| 系统 | Ubuntu 22.04 | Ubuntu 22.04 |

### 11.2 阿里云ECS推荐

| 方案 | 规格 | 适用场景 |
|------|------|----------|
| 轻量应用 | 2核4G, 60G SSD | MVP测试，日活<100 |
| 标准方案 | 4核8G, 100G ESSD | 正式运营，日活<1000 |
| 高性能 | 8核16G, 200G ESSD | 高并发，日活>1000 |

---

## 12. 部署步骤

### 12.1 完整部署流程

```bash
# 1. 在阿里云购买ECS (推荐Ubuntu 22.04)

# 2. SSH连接到服务器
ssh root@your-server-ip

# 3. 安装Git并拉取代码
apt update && apt install -y git
git clone https://github.com/your-repo/article-generator.git
cd article-generator

# 4. 编辑环境变量
vi docker/.env
# 填入: DASHSCOPE_API_KEY, BING_SEARCH_API_KEY, DOMAIN

# 5. 一键部署
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# 6. (可选) 配置HTTPS
./scripts/deploy.sh --https

# 7. 验证
curl http://localhost/health
```

### 12.2 更新部署

```bash
# 拉取最新代码
cd article-generator
git pull origin main

# 重新构建并启动
cd docker
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 数据库迁移（如有）
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## 13. 监控与日志

### 13.1 日志查看

```bash
# 查看所有服务日志
cd docker && docker compose -f docker-compose.prod.yml logs -f

# 查看特定服务
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx

# 最近100行
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

### 13.2 健康检查

```bash
#!/bin/bash
# scripts/health-check.sh

echo "=== 服务健康检查 ==="

# Docker 容器状态
echo ""
echo "--- 容器状态 ---"
cd docker
docker compose -f docker-compose.prod.yml ps

# API 健康检查
echo ""
echo "--- API 健康检查 ---"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "API 不可达"

# 数据库连接
echo ""
echo "--- 数据库连接 ---"
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Redis 连接
echo ""
echo "--- Redis 连接 ---"
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# 磁盘使用
echo ""
echo "--- 磁盘使用 ---"
df -h / /data

cd ..
```

---

## 14. 验收标准

### 14.1 部署验收

- [ ] `./scripts/deploy.sh` 一键启动所有服务
- [ ] 前端可通过浏览器访问
- [ ] API接口可正常响应
- [ ] WebSocket连接正常
- [ ] Celery Worker正常运行
- [ ] 数据库表正确创建

### 14.2 生产环境验收

- [ ] HTTPS正确配置（如有域名）
- [ ] HTTP自动跳转HTTPS
- [ ] Nginx日志正常记录
- [ ] 容器自动重启策略生效
- [ ] 资源限制正确配置
- [ ] 健康检查端点可用

### 14.3 运维验收

- [ ] 备份脚本可正确执行
- [ ] 恢复脚本可正确恢复
- [ ] 日志查看方便
- [ ] 服务更新流程简单

### 14.4 性能验收

- [ ] 首页加载时间 < 3秒
- [ ] API响应时间 < 2秒（不含LLM）
- [ ] 内存使用 < 3GB（空闲状态）
- [ ] 磁盘使用增长合理
