# backend/app/workflow/graph.py

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.workflow.state import ArticleState

# 导入新的节点
from app.workflow.nodes.title_generate import (
    title_search_node,
    title_filter_node,
    title_analyze_node,
    title_generate_node,
)
from app.workflow.nodes.title import wait_title_selection_node
from app.workflow.nodes.title import wait_outline_config_node

from app.workflow.nodes.outline_generate import (
    outline_search_node,
    outline_extract_node,
    outline_analyze_node,
    outline_generate_node,
)
from app.workflow.nodes.outline import wait_outline_selection_node

from app.workflow.nodes.final_config import wait_article_config_node

from app.workflow.nodes.article_generate import (
    article_match_evidence_node,
    article_search_node,
    article_generate_node,
)
from app.workflow.nodes.article import verify_article_node, format_output_node


def route_after_verify(state: ArticleState) -> str:
    """验证后的条件路由"""
    if state.get("verification_passed", False):
        return "pass"
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    if retry_count >= max_retries:
        return "fail"
    return "retry"


def build_article_graph() -> StateGraph:
    """构建文章生成工作流图"""
    graph = StateGraph(ArticleState)

    # ===== 标题生成主节点（4 个子步骤）=====
    graph.add_node("title_search", title_search_node)
    graph.add_node("title_filter", title_filter_node)
    graph.add_node("title_analyze", title_analyze_node)
    graph.add_node("title_generate", title_generate_node)
    graph.add_node("wait_title_selection", wait_title_selection_node)
    graph.add_node("wait_outline_config", wait_outline_config_node)

    # ===== 大纲生成主节点（4 个子步骤）=====
    graph.add_node("outline_search", outline_search_node)
    graph.add_node("outline_extract", outline_extract_node)
    graph.add_node("outline_analyze", outline_analyze_node)
    graph.add_node("outline_generate", outline_generate_node)
    graph.add_node("wait_outline_selection", wait_outline_selection_node)

    # ===== 最终配置节点 =====
    graph.add_node("wait_article_config", wait_article_config_node)

    # ===== 文章生成主节点（3 个子步骤）=====
    graph.add_node("article_match_evidence", article_match_evidence_node)
    graph.add_node("article_search", article_search_node)
    graph.add_node("article_generate", article_generate_node)
    graph.add_node("verify_article", verify_article_node)
    graph.add_node("format_output", format_output_node)

    # ===== 添加边 =====

    # 标题生成流程
    graph.add_edge(START, "title_search")
    graph.add_edge("title_search", "title_filter")
    graph.add_edge("title_filter", "title_analyze")
    graph.add_edge("title_analyze", "title_generate")
    graph.add_edge("title_generate", "wait_title_selection")
    graph.add_edge("wait_title_selection", "wait_outline_config")

    # 大纲生成流程
    graph.add_edge("wait_outline_config", "outline_search")
    graph.add_edge("outline_search", "outline_extract")
    graph.add_edge("outline_extract", "outline_analyze")
    graph.add_edge("outline_analyze", "outline_generate")
    graph.add_edge("outline_generate", "wait_outline_selection")

    # 最终配置
    graph.add_edge("wait_outline_selection", "wait_article_config")

    # 文章生成流程
    graph.add_edge("wait_article_config", "article_match_evidence")
    graph.add_edge("article_match_evidence", "article_search")
    graph.add_edge("article_search", "article_generate")
    graph.add_edge("article_generate", "verify_article")

    # 验证后的条件路由
    graph.add_conditional_edges(
        "verify_article",
        route_after_verify,
        {
            "pass": "format_output",
            "retry": "article_generate",  # 重试时从文章生成重新开始
            "fail": END,
        },
    )
    graph.add_edge("format_output", END)

    return graph


# 全局图实例
_workflow_graph = None


def get_workflow_graph():
    """获取编译后的工作流图（使用 MemorySaver）"""
    global _workflow_graph
    if _workflow_graph is None:
        graph = build_article_graph()
        checkpointer = MemorySaver()
        _workflow_graph = graph.compile(checkpointer=checkpointer)
    return _workflow_graph


def reset_workflow_graph():
    """重置图实例（用于测试）"""
    global _workflow_graph
    _workflow_graph = None
