# backend/app/workflow/state.py

from typing import Annotated, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ArticleState(TypedDict):
    """文章生成工作流的全局状态"""

    # ===== 项目基础信息 =====
    project_id: str
    topic: str

    # ===== 搜索阶段 =====
    search_keywords: list[str]
    search_results: list[dict]
    crawled_documents: list[dict]

    # ===== 过滤阶段 =====
    filtered_documents: list[dict]

    # ===== 知识提取(RAG) =====
    retrieved_knowledge: list[dict]

    # ===== 标题阶段 =====
    generated_titles: list[dict]
    selected_title: Optional[str]

    # ===== 大纲阶段 =====
    outline_config: Optional[dict]
    generated_outlines: list[dict]
    selected_outline: Optional[dict]

    # ===== 文章配置 =====
    article_config: Optional[dict]

    # ===== 文章生成 =====
    full_article: Optional[str]
    article_summary: Optional[str]
    article_faq: list[dict]

    # ===== 验证 =====
    verification_passed: bool
    retry_count: int
    max_retries: int

    # ===== 流程控制 =====
    current_stage: str
    error: Optional[str]
    messages: Annotated[list, add_messages]
