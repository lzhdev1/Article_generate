# backend/app/services/workflow_service.py

"""
分阶段工作流服务：
  Phase 1: start()                    → 运行到标题选择（interrupt）
  Phase 2: resume_with_title()        → 恢复，运行到大纲配置（interrupt）
  Phase 2.5: resume_with_outline_config() → 恢复，运行到大纲选择（interrupt）
  Phase 3: resume_with_outline()      → 恢复，运行到文章配置（interrupt）
  Phase 3.5: resume_with_article_config() → 恢复，运行到文章完成
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow.graph import get_workflow_graph
from app.models.project import Project


def _initial_state(project_id: str, topic: str) -> dict:
    return {
        "project_id": project_id,
        "topic": topic,
        # 标题生成阶段
        "optimized_keywords": [],
        "search_keywords": [],
        "search_results": [],
        "crawled_documents": [],
        "filtered_documents": [],
        "knowledge_summary": None,
        "generated_titles": [],
        "selected_title": None,
        # 大纲生成阶段
        "outline_config": {},
        "outline_search_analysis": {},
        "article_style_analysis": None,
        "outline_generation_prompt": None,
        "generated_outlines": [],
        "selected_outline": None,
        # 文章配置
        "article_config": {},
        # 文章生成阶段
        "evidence_requirements": [],
        "evidence_strategy": None,
        "article_search_results": [],
        "article_crawled_docs": [],
        "article_search_summary": None,
        "full_article": None,
        "article_summary": None,
        "article_faq": [],
        # 验证
        "verification_passed": False,
        "retry_count": 0,
        "max_retries": 3,
        "current_stage": "starting",
        "error": None,
    }


class WorkflowService:

    async def start(self, db: AsyncSession, project_id: str) -> dict:
        """
        Phase 1: 搜索→过滤→提取→生成标题
        运行到 wait_title_selection (interrupt)，返回5个标题
        """
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        # 检查是否已有状态
        state = await graph.aget_state(config)
        if state and state.values and state.values.get("generated_titles"):
            # 已生成标题，直接返回
            return self._format_response(state.values)

        # 初始化并使用 astream 运行到第一个 interrupt
        initial = _initial_state(project_id, project.topic)
        result = initial
        try:
            async for chunk in graph.astream(initial, config):
                if '__interrupt__' in chunk:
                    break
                for key, value in chunk.items():
                    if isinstance(value, dict):
                        result.update(value)
        except Exception:
            pass

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        return self._format_response(result)

    async def start_with_progress(self, project_id: str):
        """
        Phase 1 with SSE progress events.
        Yields progress events as each sub-step completes.
        """
        from app.database import async_session_factory

        # 获取项目信息
        async with async_session_factory() as db:
            project = await db.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            topic = project.topic

        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        # 检查是否已有状态
        state = await graph.aget_state(config)
        if state and state.values and state.values.get("generated_titles"):
            # 已生成标题，直接返回完成事件
            yield {"event": "progress", "data": {"main_node": "title_generate", "sub_step": "generate", "message": "标题已生成"}}
            yield {"event": "completed", "data": self._format_response(state.values)}
            return

        # 发送开始事件，标记第一个子步骤为运行中
        yield {"event": "progress", "data": {"main_node": "title_generate", "sub_step": "search", "message": "正在搜索相关内容..."}}

        # 初始化并使用 astream 运行到第一个 interrupt
        initial = _initial_state(project_id, topic)
        result = initial

        # 节点到主节点/子步骤的映射
        node_mapping = {
            "title_search": ("title_generate", "search", "搜索相关内容完成"),
            "title_filter": ("title_generate", "filter", "筛选文章内容完成"),
            "title_analyze": ("title_generate", "analyze", "分析搜索结果完成"),
            "title_generate": ("title_generate", "generate", "生成候选标题完成"),
        }

        try:
            import time
            start_time = time.time()
            print(f"[SSE] Starting graph.astream at {start_time}")

            async for chunk in graph.astream(initial, config):
                chunk_time = time.time()
                elapsed = chunk_time - start_time
                print(f"[SSE] Received chunk after {elapsed:.2f}s: {list(chunk.keys())}")

                if '__interrupt__' in chunk:
                    print(f"[SSE] Received interrupt after {elapsed:.2f}s")
                    break

                # 每个 chunk 的 key 是完成的节点名
                for node_name, node_output in chunk.items():
                    node_time = time.time()
                    node_elapsed = node_time - start_time
                    print(f"[SSE] Node '{node_name}' completed after {node_elapsed:.2f}s")

                    if node_name in node_mapping:
                        main_node, sub_step, message = node_mapping[node_name]
                        event_time = time.time()
                        event_elapsed = event_time - start_time
                        print(f"[SSE] >>> Yielding progress event at {event_elapsed:.2f}s for {main_node}/{sub_step}: {message}")
                        yield {
                            "event": "progress",
                            "data": {
                                "main_node": main_node,
                                "sub_step": sub_step,
                                "message": message,
                                "timestamp": event_elapsed,
                            }
                        }
                        print(f"[SSE] <<< Progress event yielded at {event_elapsed:.2f}s")

                    if isinstance(node_output, dict):
                        result.update(node_output)
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": {"message": str(e)}}
            return

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        yield {"event": "completed", "data": self._format_response(result)}

    async def resume_with_title(self, db: AsyncSession, project_id: str, title: str) -> dict:
        """
        Phase 2: 用户选择标题
        恢复工作流，运行到 wait_outline_config (interrupt)，暂停等待用户填写配置
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 把标题传给 wait_title_selection 节点
        # 使用 astream 运行到下一个 interrupt (wait_outline_config)
        result = {}
        try:
            async for chunk in graph.astream(
                Command(resume={"selected_title": title}),
                config,
            ):
                if '__interrupt__' in chunk:
                    break
                for key, value in chunk.items():
                    if isinstance(value, dict):
                        result.update(value)
        except Exception:
            pass

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        return self._format_response(result)

    async def resume_with_outline_config(
        self, db: AsyncSession, project_id: str, outline_config: dict
    ) -> dict:
        """
        Phase 2.5: 用户填写大纲配置
        恢复工作流，运行到 wait_outline_selection (interrupt)，返回生成的大纲
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 把配置传给 wait_outline_config 节点
        # 运行 generate_outlines → 到 wait_outline_selection (interrupt)
        result = {}
        try:
            async for chunk in graph.astream(
                Command(resume=outline_config),
                config,
            ):
                if '__interrupt__' in chunk:
                    break
                for key, value in chunk.items():
                    if isinstance(value, dict):
                        result.update(value)
        except Exception:
            pass

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        return self._format_response(result)

    async def resume_with_outline(self, db: AsyncSession, project_id: str, outline: dict) -> dict:
        """
        Phase 3: 用户选择大纲
        恢复工作流，运行到 wait_article_config (interrupt)
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 传递包含selected_outline的字典给interrupt
        # 运行到 wait_article_config (interrupt)
        result = {}
        try:
            async for chunk in graph.astream(
                Command(resume={"selected_outline": outline}),
                config,
            ):
                if '__interrupt__' in chunk:
                    break
                for key, value in chunk.items():
                    if isinstance(value, dict):
                        result.update(value)
        except Exception:
            pass

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        return self._format_response(result)

    async def resume_with_article_config(
        self, db: AsyncSession, project_id: str, article_config: dict
    ) -> dict:
        """
        Phase 3.5: 恢复工作流，传入文章配置，运行到完成
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 把文章配置传给 wait_article_config 节点
        result = {}
        try:
            async for chunk in graph.astream(
                Command(resume=article_config),
                config,
            ):
                if '__interrupt__' in chunk:
                    break
                for key, value in chunk.items():
                    if isinstance(value, dict):
                        result.update(value)
        except Exception:
            pass

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        return self._format_response(result)

    async def get_state(self, project_id: str) -> Optional[dict]:
        """获取工作流当前状态"""
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}
        state = await graph.aget_state(config)

        if not state or not state.values:
            return None
        return state.values

    def _format_response(self, values: dict) -> dict:
        """格式化返回数据"""
        return {
            "status": values.get("current_stage", "unknown"),
            "titles": values.get("generated_titles", []),
            "selected_title": values.get("selected_title"),
            "outlines": values.get("generated_outlines", []),
            "selected_outline": values.get("selected_outline"),
            "article": values.get("full_article"),
            "summary": values.get("article_summary"),
            "faq": values.get("article_faq", []),
            "verification_passed": values.get("verification_passed"),
            "error": values.get("error"),
            "full_state": values,
        }


workflow_service = WorkflowService()
