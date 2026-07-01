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
│       │       ├── search.py      # 网络搜索节点
│       │       ├── filter.py      # 内容过滤节点
│       │       ├── extract.py     # 知识提取(RAG)节点
│       │       ├── title.py       # 标题生成 + HITL 选择
│       │       ├── outline.py     # 大纲生成 + HITL 选择
│       │       └── article.py     # 文章生成 + 验证
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
                           │ REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + LangGraph)              │
│                                                              │
│  StateGraph: search → filter → extract → title_gen           │
│              → [HITL: 选标题] → outline_gen                  │
│              → [HITL: 选大纲] → article_gen → verify         │
│              → [pass/retry/fail] → output                    │
│                                                              │
│  RAG: WebBaseLoader → TextSplitter → PGVector → Retriever    │
└──────────┬─────────────────────────────┬────────────────────
           │                             │
     ┌─────▼──────┐              ┌──────▼──────┐
     │ PostgreSQL  │              │    Redis    │
     │  主数据库   │              │ 缓存/状态   │
     └────────────┘              └─────────────┘
```

### 工作流节点说明

| 节点 | 功能 | 技术 |
|------|------|------|
| `search` | LLM生成关键词 → Google 搜索 → 爬取全文 | httpx + BeautifulSoup4 |
| `filter` | LLM对每篇文章评分(0-1)，过滤不相关内容 | LangChain PromptTemplate |
| `extract_knowledge` | 文本切分 → Embedding → PGVector存储 → 语义检索 | LangChain RAG |
| `generate_titles` | 基于知识生成5个不同风格的标题 | Qwen-Max |
| `wait_title_selection` | **Human-in-the-Loop**：暂停等待用户选择 | LangGraph interrupt |
| `generate_outlines` | 分析文章风格，生成3种不同结构的大纲 | Qwen-Max |
| `wait_outline_selection` | **Human-in-the-Loop**：暂停等待用户选择 | LangGraph interrupt |
| `generate_article` | 逐章节生成文章，每章节检索相关知识 | Qwen-Max + RAG |
| `verify_article` | 验证事实准确性、逻辑一致性、信息时效性 | Qwen-Max |
| `format_output` | 生成要点总结和FAQ，格式化输出 | Qwen-Max |

### 关键设计决策

1. **LangGraph interrupt/resume 机制**：标题和大纲选择时暂停工作流，等待用户输入后继续，避免全自动化导致质量不可控
2. **RAG 知识管理**：不把所有参考文章塞入 Prompt，而是通过向量检索精准注入每章节最相关的知识片段
3. **条件路由验证循环**：文章生成后自动验证，不通过则重新生成（最多3次）
4. **分阶段 API**：每个用户交互点对应一个独立 API 端点，前端按需调用

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
