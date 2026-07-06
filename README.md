# Article Generate - AI 自动化博客文章生成平台

> 输入一个主题，AI 自动完成「网络检索 → 内容过滤 → 知识提取 → 标题生成 → 大纲生成 → 文章撰写 → 内容验证」全流程，最终交付一篇高质量的博客文章。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Next.js 16 + React 19 + TypeScript | App Router，Turbopack |
| **UI** | TailwindCSS v4 + shadcn/ui + Framer Motion | 简约科技风格设计系统 |
| **状态管理** | Zustand | 轻量级前端状态管理 |
| **后端** | Python FastAPI | 异步 Web 框架 |
| **AI 编排** | LangGraph 1.0 + LangChain 1.0 | 有状态 Agent 工作流 + RAG |
| **大模型** | 阿里云百炼 (Qwen-Max) | OpenAI 兼容接口 |
| **搜索引擎** | Google Custom Search API | 网络内容检索 |
| **数据库** | PostgreSQL 16 + Redis 7 | 主存储 + 缓存/消息队列 |
| **部署** | Docker Compose | 全容器化，一键启动 |

## 项目结构

```
article-generator/
├── frontend/                      # Next.js 前端
│   ── src/
│       ├── app/                   # 页面路由
│       │   ├── page.tsx           # 首页 (Topic 输入)
│       │   └── project/[id]/      # 项目流程页面
│       │       ├── processing/    # 处理进度页
│       │       ├── titles/        # 标题选择页
│       │       ├── outline-config/# 大纲配置页
│       │       ├── outlines/      # 大纲选择页
│       │       ├── config/        # 最终配置页
│       │       ├── generating/    # 文章生成进度页
│       │       └── article/       # 文章展示页
│       ├── components/ui/         # 全局 UI 组件库
│       ├── services/api.ts        # API 客户端
│       └── stores/projectStore.ts # 全局状态
│
├── backend/                       # FastAPI 后端
│   └── app/
│       ├── main.py                # 应用入口
│       ├── config.py              # 配置管理
│       ├── database.py            # 数据库连接
│       ├── api/endpoints/         # API 路由
│       │   ├── project.py         # 项目管理 API
│       │   └── workflow.py        # 工作流 API (7个端点)
│       ├── workflow/              # LangGraph 工作流
│       │   ├── graph.py           # 状态图定义
│       │   ├── state.py           # 全局状态定义
│       │   ├── llm.py             # LLM 工厂函数
│       │   └── nodes/             # 工作流节点
│       │       ├── title_generate.py   # 标题生成 (4个子步骤)
│       │       ├── outline_generate.py # 大纲生成 (4个子步骤)
│       │       ├── article_generate.py # 文章生成 (3个子步骤)
│       │       └── final_config.py     # HITL 配置节点
│       └── services/
│           └── workflow_service.py # 工作流编排服务
│
├── docker/                        # Docker 配置
│   ├── Dockerfile.frontend
│   └── Dockerfile.backend
├── spec/                          # 需求规格文档 (15份)
├── docker-compose.yml             # 开发环境编排
└── .env                           # 环境变量
```

## 快速开始

### 前置条件

- Docker Desktop 已安装并运行
- 项目根目录下已有 `.env` 文件

### 1. 配置环境变量

编辑 `.env` 文件，填入你的 API Key：

```env
# 阿里云百炼（大模型）
DASHSCOPE_API_KEY=sk-xxxxx
DASHSCOPE_MODEL=qwen-max

# Google Custom Search（网络搜索）
GOOGLE_SEARCH_API_KEY=your-google-api-key
GOOGLE_SEARCH_CX=your-search-engine-id
GOOGLE_SEARCH_ENDPOINT=https://www.googleapis.com/customsearch/v1
```

> 获取 DashScope API Key：https://dashscope.console.aliyun.com/
> 获取 Google Custom Search API Key：https://developers.google.com/custom-search/v1/overview
> 创建 Custom Search Engine：https://programmablesearchengine.google.com/

### 2. 一键启动

```bash
docker compose up --build
```

启动后访问：
- 🌐 前端：http://localhost:3000
- 🔌 后端 API：http://localhost:8000
- 📖 API 文档：http://localhost:8000/docs

### 3. 常用命令

```bash
# 查看容器状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 查看前端日志
docker compose logs -f frontend

# 重启后端（修改 .env 后）
docker compose restart backend

# 停止所有服务
docker compose down

# 停止并清除数据卷（彻底重置）
docker compose down -v
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                     │
│  首页 → 处理进度 → 标题选择 → 大纲配置 → 大纲选择              │
│  → 最终配置 → 生成进度 → 文章展示                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API + SSE
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + LangGraph)              │
│                                                              │
│  StateGraph: title_search → title_filter → title_analyze     │
│              → title_generate → [HITL: 选标题]               │
│              → outline_search → outline_extract              │
│              → outline_analyze → outline_generate            │
│              → [HITL: 选大纲] → article_match_evidence       │
│              → article_search → article_generate             │
│              → [HITL: 文章配置] → END                        │
│                                                              │
└──────────┬─────────────────────────────┬────────────────────
           │                             │
     ┌─────▼──────┐              ┌──────▼──────┐
     │ PostgreSQL  │              │    Redis    │
     │  主数据库   │              │ 缓存/消息   │
     └────────────┘              └─────────────┘
```

### 工作流节点说明

| 主节点 | 子步骤 | 功能 | 技术 |
|------|------|------|------|
| **title_generate** | search | LLM生成关键词 → 联网搜索（DashScope enable_search） → 爬取全文 | httpx + BeautifulSoup4 |
| | filter | LLM分析内容，过滤低质量文章 | LangChain PromptTemplate |
| | analyze | 总结筛选后的搜索结果，提取关键信息 | Qwen-Max |
| | generate | 基于总结内容生成至少5个不同风格的标题 | Qwen-Max |
| **outline_generate** | search | 分析标题+配置，搜索相关内容 | Qwen-Max |
| | extract | 提取参考文章的结构和风格 | Qwen-Max |
| | analyze | 生成专业的大纲生成 prompt | Qwen-Max |
| | generate | 根据prompt生成至少2个大纲方案 | Qwen-Max |
| **final_config** | config | 用户填写文章生成配置（图片、视频、总结、FAQ等） | Human-in-the-Loop |
| **article_generate** | match_evidence | 分析标题和大纲，确定需要什么类型的证据 | Qwen-Max |
| | search | 根据证据需求联网搜索相关内容 | httpx + BeautifulSoup4 |
| | generate | 基于大纲和搜索内容生成文章 | Qwen-Max |

### 关键设计决策

1. **子步骤进度显示**：每个主节点的子步骤作为独立的 LangGraph 节点执行，通过 SSE（Server-Sent Events）实时推送进度到前端，用户可以看到每个子步骤的执行状态
2. **LangGraph interrupt/resume 机制**：标题和大纲选择时暂停工作流，等待用户输入后继续，避免全自动化导致质量不可控
3. **分阶段 API**：每个用户交互点对应一个独立 API 端点，前端按需调用
4. **SSE 实时进度**：使用 `StreamingResponse` 和 `text/event-stream` 实现 Server-Sent Events，前端通过 `EventSource` 接收进度更新

## 开发指南

### 新增一个工作流节点

1. 在 `backend/app/workflow/nodes/` 创建 `my_node.py`
2. 实现异步函数，接收 `ArticleState`，返回 `dict`（状态更新）
3. 在 `graph.py` 中 `add_node` 和 `add_edge`
4. 如果前端需要交互，在节点内调用 `interrupt()`

```python
# 节点模板
async def my_node(state: ArticleState) -> dict:
    # 读取状态
    topic = state["topic"]
    
    # 执行逻辑
    result = await some_llm_call(topic)
    
    # 返回状态更新
    return {
        "my_field": result,
        "current_stage": "my_stage_completed",
        "messages": [],
    }
```

### 修改 UI 组件

全局 UI 组件位于 `frontend/src/components/ui/`，遵循 shadcn/ui 模式：
- 使用 `class-variance-authority` 管理变体
- 使用 `clsx` + `tailwind-merge` 合并 className
- 通过 `cn()` 工具函数统一样式

### 添加新的 API 端点

1. 在 `backend/app/api/endpoints/` 创建文件
2. 使用 FastAPI `APIRouter` 定义路由
3. 在 `api/router.py` 中注册

### 测试工作流

```bash
# 1. 启动所有服务
docker compose up

# 2. 测试创建项目
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"topic":"AI在教育领域的应用"}'

# 3. 启动工作流（会运行到标题选择）
curl -X POST http://localhost:8000/api/projects/{project_id}/workflow/start

# 4. 查看工作流状态
curl http://localhost:8000/api/projects/{project_id}/workflow/state
```

## 目录说明

| 目录 | 说明 |
|------|------|
| `spec/` | 15份详细需求规格文档，覆盖从基础设施到部署的完整方案 |
| `docker/` | Docker 配置文件（Dockerfile、Nginx 配置） |
| `frontend/` | Next.js 前端项目 |
| `backend/` | FastAPI 后端项目 |
| `docker-compose.yml` | Docker Compose 开发环境编排 |
| `.env` | 环境变量（API Keys 等，不提交到 Git） |
| `.gitignore` | Git 忽略配置 |

## 许可证

MIT
