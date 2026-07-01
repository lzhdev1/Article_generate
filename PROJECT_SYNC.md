# Article Generate - 项目同步文档

> **最后更新**: 2026-07-01  
> **当前阶段**: MVP 开发完成，前后端联调通过  
> **本文档用途**: 新对话快速同步项目状态

---

## 📋 项目概述

**AI 自动化博客文章生成平台** - 输入一个主题，AI 自动完成「网络检索 → 内容过滤 → 知识提取 → 标题生成 → 大纲生成 → 文章撰写 → 内容验证」全流程。

---

## 🛠️ 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **前端** | Next.js + React + TypeScript | 16.2.9 / 19 / 5.x | App Router, Turbopack |
| **UI** | TailwindCSS + shadcn/ui + Framer Motion | v4 | 简约科技风格 |
| **状态管理** | Zustand | 5.x | 轻量级状态管理 |
| **后端** | FastAPI | 0.115.x | 异步 Web 框架 |
| **AI 编排** | LangGraph + LangChain | 1.0.4 / 0.3.x | 有状态 Agent 工作流 |
| **大模型** | 阿里云百炼 (Qwen) | qwen3.6-flash | OpenAI 兼容接口 |
| **搜索引擎** | Qwen 模型联网搜索 | - | 替代 Google Custom Search |
| **数据库** | PostgreSQL + Redis | 16 / 7 | 主存储 + 缓存 |
| **部署** | Docker Compose | - | 全容器化 |

---

## 📁 项目结构

```
Article_generate/
── frontend/                      # Next.js 前端
│   └── src/
│       ├── app/                   # 页面路由
│       │   ├── page.tsx           # 首页 (Topic 输入)
│       │   └── project/[id]/      # 项目流程页面 (7 个)
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
│       │   └── workflow.py        # 工作流 API (7 个端点)
│       ├── workflow/              # LangGraph 工作流
│       │   ├── graph.py           # 状态图定义 (MemorySaver)
│       │   ├── state.py           # 全局状态定义
│       │   ├── llm.py             # LLM 工厂函数
│       │   └── nodes/             # 工作流节点
│       │       ├── search.py      # 网络搜索节点 (Qwen 联网)
│       │       ├── filter.py      # 内容过滤节点
│       │       ├── extract.py     # 知识提取 (RAG) 节点
│       │       ├── title.py       # 标题生成 + HITL 选择
│       │       ├── outline.py     # 大纲生成 + HITL 选择
│       │       ── article.py     # 文章生成 + 验证
│       └── services/
│           └── workflow_service.py # 工作流编排服务
│
├── docker/                        # Docker 配置
│   ├── Dockerfile.frontend
│   └── Dockerfile.backend
├── spec/                          # 需求规格文档 (15 份)
├── docker-compose.yml             # 开发环境编排
└── .env                           # 环境变量
```

---

## ✅ 已完成功能

### 前端 (8 个页面)

| 页面 | 路径 | 状态 | 说明 |
|------|------|------|------|
| 首页 | `/` | ✅ | Topic 输入，示例主题，Framer Motion 动画 |
| 处理进度 | `/project/[id]/processing` | ✅ | 显示搜索/过滤/提取进度 |
| 标题选择 | `/project/[id]/titles` | ✅ | 展示 5 个候选标题，用户选择 |
| 大纲配置 | `/project/[id]/outline-config` | ✅ | 配置文章长度/风格/可读性 |
| 大纲选择 | `/project/[id]/outlines` | ✅ | 展示 3 种大纲方案 |
| 最终配置 | `/project/[id]/config` | ✅ | 文章配置 (总结/FAQ/字数) |
| 生成进度 | `/project/[id]/generating` | ✅ | 文章生成实时进度 |
| 文章展示 | `/project/[id]/article` | ✅ | 文章渲染 + 总结 + FAQ |

### 后端 (10 个工作流节点)

| 节点 | 功能 | 状态 | 说明 |
|------|------|------|------|
| `search_node` | 生成关键词 + 联网搜索 | ✅ | 使用 Qwen 模型联网能力 |
| `filter_node` | 内容相关性评分过滤 | ✅ | LLM 评分 0-1，过滤<0.5 |
| `extract_knowledge_node` | 知识提取 (RAG) | ✅ | 文本切分 + 向量存储 + 语义检索 |
| `generate_titles_node` | 生成 5 个候选标题 | ✅ | 5 种不同风格 |
| `wait_title_selection_node` | 等待用户选择标题 | ✅ | Human-in-the-Loop (interrupt) |
| `generate_outlines_node` | 生成 3 种大纲方案 | ✅ | 全面型/问题 - 解决型/循序渐进型 |
| `wait_outline_selection_node` | 等待用户选择大纲 | ✅ | Human-in-the-Loop (interrupt) |
| `generate_article_node` | 逐章节生成文章 | ✅ | 每章节检索相关知识 |
| `verify_article_node` | 验证文章质量 | ✅ | 事实准确性/逻辑一致性 |
| `format_output_node` | 生成总结+FAQ | ✅ | 要点总结 + 5 个 FAQ |

### API 端点 (7 个)

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/projects` | POST | 创建项目 | ✅ |
| `/api/projects/{id}/workflow/start` | POST | 启动工作流 (Phase 1) | ✅ |
| `/api/projects/{id}/workflow/select-title` | POST | 选择标题 (Phase 2) | ✅ |
| `/api/projects/{id}/workflow/save-outline-config` | POST | 保存大纲配置 | ✅ |
| `/api/projects/{id}/workflow/select-outline` | POST | 选择大纲 (Phase 3) | ✅ |
| `/api/projects/{id}/workflow/save-article-config` | POST | 保存文章配置 | ✅ |
| `/api/projects/{id}/workflow/state` | GET | 获取工作流状态 | ✅ |

---

## 🔑 关键配置

### .env 文件

```env
# ===== 阿里云百炼 =====
DASHSCOPE_API_KEY=sk-76ea62005c3a47fdba93092872b5dfbf
DASHSCOPE_MODEL=qwen3.6-flash
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4

# ===== Google Custom Search (已弃用，改用 Qwen 联网) =====
# GOOGLE_SEARCH_API_KEY=
# GOOGLE_SEARCH_CX=
# GOOGLE_SEARCH_ENDPOINT=

# ===== 数据库 =====
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@postgres:5432/article_generator
REDIS_URL=redis://redis:6379/0
```

### 关键设计决策

1. **搜索方案**: 从 Google Custom Search API 改为 Qwen 模型联网搜索
   - 原因：Google API 403 权限问题 + 阿里云百炼免费额度用完
   - 方案：使用 `qwen3.6-flash` 的 `enable_search=True` 参数

2. **工作流执行**: 使用 `astream` 而非 `ainvoke`
   - 原因：`ainvoke` 不会正确触发 LangGraph interrupt
   - 方案：`async for chunk in graph.astream(...)` 检测 `__interrupt__`

3. **状态持久化**: 使用 MemorySaver (内存)
   - 原因：PostgresSaver 需要异步版本但不可用
   - 影响：容器重启后工作流状态丢失 (项目数据仍在数据库)

---

##  已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Google Search 403 | API Key 与项目不匹配 | 改用 Qwen 模型联网搜索 |
| 免费额度用完 | 阿里云百炼付费未配置 | 改用 `qwen3.6-flash` (免费) |
| `ainvoke` 不触发 interrupt | LangGraph 机制问题 | 改用 `astream` + 检测 `__interrupt__` |
| PostgresSaver 不可用 | 需要异步版本 | 使用 MemorySaver + 数据库存储项目数据 |
| 大纲 JSON 解析失败 | LLM 返回 markdown 格式 | 添加回退解析逻辑 |
| 前端容器未启动 | docker compose up 时未包含 | `docker compose up -d frontend` |

---

## 🚀 部署命令

### 启动所有服务
```bash
docker compose up -d
```

### 查看状态
```bash
docker compose ps
```

### 查看日志
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### 重启后端 (修改代码后)
```bash
docker compose restart backend
```

### 停止所有服务
```bash
docker compose down
```

### 停止并清除数据
```bash
docker compose down -v
```

---

## 📊 测试结果 (2026-07-01)

### 完整工作流测试

| 步骤 | 操作 | 状态 | 结果 |
|------|------|------|------|
| 1 | 创建项目 | ✅ | 项目 ID 生成 |
| 2 | 启动工作流 Phase 1 | ✅ | 5 个标题生成 (~60s) |
| 3 | 选择标题 | ✅ | 3 个大纲生成 (~30s) |
| 4 | 保存大纲配置 | ✅ | 配置已保存 |
| 5 | 选择大纲 | ✅ | 进入文章生成 |
| 6 | 保存文章配置 | ✅ | 文章生成完成 (~90s) |
| 7 | 查看最终状态 | ✅ | 文章 + 总结+FAQ |

### 生成示例

- **文章长度**: 2619 字符
- **要点总结**: 2 条核心要点
- **FAQ**: 5 个问答
- **生成标题**: 2024 AI 教育实战指南：掌握这 5 个核心落地策略，让教学提质增效

---

##  下一步计划

### Phase 6: Docker 部署与联调 (Spec-014)

- [ ] 前端容器健康检查配置
- [ ] 后端容器优雅重启
- [ ] 环境变量管理优化
- [ ] 生产环境部署文档

---

## 📝 Spec 文档清单 (15 份)

| 编号 | 文档 | 状态 |
|------|------|------|
| 001 | 项目基础设施与架构 | ✅ |
| 002 | 全局 UI 设计系统 | ✅ |
| 003 | 首页与 Topic 输入 | ✅ |
| 004 | 网络搜索模块 | ✅ |
| 005 | 内容过滤模块 | ✅ |
| 006 | 知识提取模块 | ✅ |
| 007 | 标题生成与选择 | ✅ |
| 008 | 大纲配置页面 | ✅ |
| 009 | 大纲生成与选择 | ✅ |
| 010 | 最终配置页面 | ✅ |
| 011 | 文章生成模块 | ✅ |
| 012 | 文章展示页面 | ✅ |
| 013 | 任务流程编排 | ✅ |
| 014 | Docker 部署方案 | ✅ |
| 015 | LangGraph 工作流与 LangChain RAG 架构 | ✅ |

---

## 📊 项目进度总结

| 指标 | 状态 |
|------|------|
| Spec 文档 | ✅ 15/15 完成 |
| 前端页面 | ✅ 8/8 完成 |
| 工作流节点 | ✅ 10/10 完成 |
| API 端点 | ✅ 7/7 完成 |
| 容器部署 | ✅ 4/4 运行 |
| 完整测试 | ✅ 通过 |

**MVP 阶段已完成！** Phase 6 是最后的部署优化阶段。

### 优化项

- [ ] 工作流状态持久化 (PostgreSQL)
- [ ] 文章生成进度实时推送 (WebSocket)
- [ ] 前端错误边界处理
- [ ] 后端 API 限流
- [ ] 搜索节点结果质量优化

### 功能扩展

- [ ] 多语言支持
- [ ] 文章模板系统
- [ ] 用户认证/授权
- [ ] 项目历史记录
- [ ] 文章导出 (PDF/Markdown)

---

## 🔗 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 需求规格 | `spec/` | 15 份详细需求文档 |
| 项目 README | `README.md` | 完整项目说明 |
| 简历项目描述 | `RESUME_PROJECT.md` | 简历用项目经历 |
| 测试脚本 | `test_google_search.py` | Google Search 测试 |
| 测试脚本 | `test_search_with_llm.py` | Qwen 联网搜索测试 |

---

## 💡 新对话快速开始

如果你在新对话中需要继续开发，请：

1. **读取本文档** 了解项目状态
2. **检查容器状态**: `docker compose ps`
3. **检查 .env 配置**: 确保 API Key 正确
4. **测试后端 API**: `curl http://localhost:8000/health`
5. **测试前端**: 打开 http://localhost:3000

### 常见问题

**Q: 前端容器未启动？**  
A: `docker compose up -d frontend`

**Q: 后端 API 返回 500？**  
A: 检查日志 `docker compose logs backend`，通常是 API Key 问题

**Q: 工作流卡在 starting？**  
A: 使用 `astream` 而非 `ainvoke`，增加超时时间到 120s+

**Q: 如何修改模型？**  
A: 编辑 `.env` 中的 `DASHSCOPE_MODEL`，然后 `docker compose restart backend`

---

**文档版本**: v1.0  
**维护者**: lzhdev1  
**最后验证**: 2026-07-01
