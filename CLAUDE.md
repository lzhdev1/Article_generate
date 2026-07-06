# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

AI-powered blog article generation platform. User enters a topic; the system runs a pipeline of LLM-driven stages — web search → content filtering → RAG knowledge extraction → title generation → outline generation → article writing → verification — delivering a final blog post. Human-in-the-loop interrupts pause the workflow at three decision points (title, outline, article config) so the user can steer output.

## Commands

Everything runs through Docker Compose in the repo root. There is no local venv / `npm install` workflow — the containers mount `./backend` and `./frontend/src` as volumes.

```bash
# Start all services (frontend :3000, backend :8000, postgres :5432, redis :6379, celery worker)
docker compose up --build

# Tail logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart backend after editing .env or requirements
docker compose restart backend

# Frontend lint (run inside the container or after `cd frontend && npm install` locally)
docker compose exec frontend npm run lint
```

API docs live at http://localhost:8000/docs once the backend is up.

## Architecture

### Backend — LangGraph StateGraph with phased resume

The heart of the backend is `backend/app/workflow/`:

- `state.py` — `ArticleState` TypedDict, the single mutable state threaded through every node.
- `graph.py` — `build_article_graph()` builds a `StateGraph(ArticleState)` and compiles it with a `MemorySaver` checkpointer. The graph is a singleton accessed via `get_workflow_graph()`.
- `nodes/*.py` — one file per major stage. Each major node contains multiple sub-steps that execute sequentially:
  - `title_generate.py` — 4 sub-steps as separate nodes: `title_search` (LLM联网搜索) → `title_filter` (LLM筛选内容) → `title_analyze` (LLM分析总结) → `title_generate` (LLM生成标题)
  - `outline_generate.py` — 4 sub-steps: `outline_search` → `outline_extract` → `outline_analyze` → `outline_generate`
  - `article_generate.py` — 3 sub-steps: `match_evidence` → `article_search` → `article_generate`
  - `final_config.py` — Human-in-the-loop configuration node with `interrupt()`

The graph has **four `interrupt()` points** for human-in-the-loop interaction:
- `wait_title_selection` — 用户选择标题
- `wait_outline_config` — 用户配置大纲生成参数
- `wait_outline_selection` — 用户选择大纲
- `wait_article_config` — 用户配置文章生成参数

Each `interrupt()` pauses the graph and yields control to the API layer.

`services/workflow_service.py` exposes the resume protocol — this is the single most important file to understand before modifying workflow behavior:

| Phase | Method | API endpoint | Runs until |
|---|---|---|---|
| 1 | `start_with_progress()` | `GET /workflow/start-stream` (SSE) | `wait_title_selection` interrupt |
| 2 | `resume_with_title(title)` | `POST /workflow/select-title` | `wait_outline_config` interrupt |
| 2.5 | `resume_with_outline_config(cfg)` | `POST /workflow/save-outline-config` | `wait_outline_selection` interrupt |
| 3 | `resume_with_outline(outline)` | `POST /workflow/select-outline` | `wait_article_config` interrupt |
| 3.5 | `resume_with_article_config(cfg)` | `POST /workflow/save-article-config` | graph END |

Each resume uses `graph.astream(Command(resume=<payload>), config)` and breaks on the next `__interrupt__` chunk. State is keyed by `thread_id = project_id`.

**SSE Progress Events**: The `start_with_progress()` method uses `graph.astream()` to stream execution results. As each sub-step node completes, a progress event is yielded via Server-Sent Events, enabling real-time progress updates on the frontend.

Event format:
```json
{"event": "progress", "data": {"main_node": "title_generate", "sub_step": "search", "message": "搜索相关内容完成"}}
```

The frontend receives these events via EventSource and updates the UI to show which sub-step is currently running.

### Backend — other pieces

- `api/endpoints/project.py` — CRUD for projects (PostgreSQL via async SQLAlchemy + asyncpg).
- `api/endpoints/workflow.py` — the seven workflow endpoints; each is a thin wrapper over `workflow_service`.
- `api/router.py` — where new routers must be registered.
- `models/project.py` — SQLAlchemy project model.
- `tasks/` — Celery app (broker/result backend on Redis); currently a stub for future async work.
- LLM access goes through `workflow/llm.py` (Qwen-Max via DashScope, OpenAI-compatible).

### Frontend — Next.js 16 + React 19

App Router with pages under `frontend/src/app/project/[id]/...` mirroring the workflow phases: `processing` → `titles` → `outline-config` → `outlines` → `config` → `generating` → `article`.

- `services/api.ts` — thin `fetch` wrapper reading `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api`).
- `stores/projectStore.ts` — Zustand store with `persist` middleware (key: `article-generator-project`), holds `currentProject`.
- UI components under `components/ui/` follow the shadcn/ui pattern: `class-variance-authority` for variants, `clsx` + `tailwind-merge` via a `cn()` helper.
- Tailwind v4, configured via `postcss.config.mjs` (no `tailwind.config.js` — v4 uses CSS-based config).

**Important:** per `frontend/AGENTS.md`, Next.js 16 has breaking API changes from earlier versions. Before writing page/layout/routing code, consult the relevant guide in `frontend/node_modules/next/dist/docs/` rather than relying on training-data conventions.

## Spec documents

`spec/` contains 15 Chinese-language requirement documents (`001-项目基础设施与架构.md` through `015-LangGraph工作流与LangChain-RAG架构.md`) covering the full system design. Read these when you need authoritative answers about intended behavior, UI flow, or module boundaries — they take precedence over ad-hoc conventions.

## Environment variables

`.env` at the repo root (not committed) supplies:

- `DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL` — LLM provider (Alibaba DashScope / Qwen).
- `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CX`, `GOOGLE_SEARCH_ENDPOINT` — Google Custom Search.
- `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — injected by docker-compose; normally not touched.
- `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL` — injected into the frontend container.

## Adding a new workflow stage

1. Create `backend/app/workflow/nodes/my_node.py` with `async def my_node(state: ArticleState) -> dict`.
2. Register in `graph.py`: `graph.add_node("my_node", my_node)` and wire edges.
3. If the user must interact, call `langgraph.types.interrupt()` inside the node and add a matching `resume_with_*` method on `WorkflowService` plus a new endpoint in `api/endpoints/workflow.py`.
4. Add any new state fields to `ArticleState` in `state.py` and to `_initial_state()` in `workflow_service.py`.
