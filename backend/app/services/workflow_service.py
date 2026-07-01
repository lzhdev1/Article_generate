# backend/app/services/workflow_service.py

"""
分阶段工作流服务：
  Phase 1: start()       → 运行到标题选择（interrupt）
  Phase 2: resume_title() → 恢复，运行到大纲选择（interrupt）
  Phase 3: resume_outline() → 恢复，运行到文章完成
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow.graph import get_workflow_graph
from app.models.project import Project


def _initial_state(project_id: str, topic: str) -> dict:
    return {
        "project_id": project_id,
        "topic": topic,
        "search_keywords": [],
        "search_results": [],
        "crawled_documents": [],
        "filtered_documents": [],
        "retrieved_knowledge": [],
        "generated_titles": [],
        "selected_title": None,
        "outline_config": {},
        "generated_outlines": [],
        "selected_outline": None,
        "article_config": {},
        "full_article": None,
        "article_summary": None,
        "article_faq": [],
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
                # 检查是否是 interrupt
                if '__interrupt__' in chunk:
                    break
                # 累积状态更新
                for key, value in chunk.items():
                    if isinstance(value, dict):
                        result.update(value)
        except Exception as e:
            # interrupt 会抛异常，这是正常的
            pass

        # 获取最新状态
        state = await graph.aget_state(config)
        if state and state.values:
            result = state.values

        return self._format_response(result)

    async def resume_with_title(self, db: AsyncSession, project_id: str, title: str) -> dict:
        """
        Phase 2: 用户选择标题
        恢复工作流，运行到 wait_outline_selection (interrupt)，返回大纲
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 把标题传给 wait_title_selection 节点
        try:
            result = await graph.ainvoke(
                Command(resume={"selected_title": title}),
                config,
            )
        except Exception:
            result = (await graph.aget_state(config)).values

        return self._format_response(result)

    async def generate_outlines_with_config(
        self, db: AsyncSession, project_id: str, outline_config: dict
    ) -> dict:
        """
        Phase 2.5: 注入大纲配置后继续
        实际上Phase 2已经运行到wait_outline_selection，
        这里是为了在generate_outlines之前注入配置
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        # 获取当前状态，更新outline_config
        state = await graph.aget_state(config)
        if state and state.values:
            current = dict(state.values)
            current["outline_config"] = outline_config
            await graph.aupdate_state(config, current)

        return self._format_response(current if state and state.values else {})

    async def resume_with_outline(self, db: AsyncSession, project_id: str, outline: dict) -> dict:
        """
        Phase 3: 用户选择大纲
        恢复工作流，运行到文章生成完成
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 传递包含selected_outline的字典给interrupt
        try:
            result = await graph.ainvoke(
                Command(resume={"selected_outline": outline}),
                config,
            )
        except Exception:
            result = (await graph.aget_state(config)).values

        return self._format_response(result)

    async def generate_article_with_config(
        self, db: AsyncSession, project_id: str, article_config: dict
    ) -> dict:
        """
        Phase 3.5: 恢复工作流，传入文章配置，运行到完成
        """
        graph = get_workflow_graph()
        config = {"configurable": {"thread_id": project_id}}

        from langgraph.types import Command

        # resume: 把文章配置传给 wait_article_config 节点
        try:
            result = await graph.ainvoke(
                Command(resume=article_config),
                config,
            )
        except Exception:
            result = (await graph.aget_state(config)).values

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
