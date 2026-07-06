# backend/app/workflow/state.py

from typing import Annotated, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ArticleState(TypedDict):
    """文章生成工作流的全局状态"""

    # ===== 项目基础信息 =====
    project_id: str
    topic: str

    # ===== 标题生成阶段 =====
    # 子步骤 1: search
    optimized_keywords: list[str]
    search_keywords: list[str]
    search_results: list[dict]
    crawled_documents: list[dict]
    # 子步骤 2: filter
    filtered_documents: list[dict]
    # 子步骤 3: analyze
    knowledge_summary: Optional[str]
    # 子步骤 4: generate
    generated_titles: list[dict]
    selected_title: Optional[str]

    # ===== 大纲生成阶段 =====
    outline_config: Optional[dict]
    # 子步骤 1: search (分析)
    outline_search_analysis: Optional[dict]
    # 子步骤 2: extract (提取风格)
    article_style_analysis: Optional[str]
    # 子步骤 3: analyze (生成 prompt)
    outline_generation_prompt: Optional[str]
    # 子步骤 4: generate
    generated_outlines: list[dict]
    selected_outline: Optional[dict]

    # ===== 文章配置 =====
    article_config: Optional[dict]

    # ===== 文章生成阶段 =====
    # 子步骤 1: match_evidence
    evidence_requirements: list[dict]
    evidence_strategy: Optional[str]
    # 子步骤 2: search
    article_search_results: list[dict]
    article_crawled_docs: list[dict]
    article_search_summary: Optional[str]
    # 子步骤 3: generate
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
