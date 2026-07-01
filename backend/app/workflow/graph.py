# backend/app/workflow/graph.py

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.workflow.state import ArticleState
from app.workflow.nodes.search import search_node
from app.workflow.nodes.filter import filter_node
from app.workflow.nodes.extract import extract_knowledge_node
from app.workflow.nodes.title import generate_titles_node, wait_title_selection_node
from app.workflow.nodes.outline import generate_outlines_node, wait_outline_selection_node
from app.workflow.nodes.article import (
    generate_article_node,
    verify_article_node,
    format_output_node,
)


def route_after_verify(state: ArticleState) -> str:
    """验证后的条件路由"""
    if state.get("verification_passed", False):
        return "pass"
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    if retry_count >= max_retries:
        return "fail"
    return "retry"


async def wait_article_config_node(state: ArticleState) -> dict:
    """等待用户填写文章配置"""
    from langgraph.types import interrupt

    # 暂停，等待用户输入文章配置
    article_config = interrupt(
        {
            "action": "set_article_config",
            "message": "请填写文章配置（图片、视频、总结、FAQ 等）",
        }
    )

    return {
        "article_config": article_config,
        "current_stage": "article_config_set",
        "messages": [],
    }


def build_article_graph() -> StateGraph:
    """构建文章生成工作流图"""
    graph = StateGraph(ArticleState)

    # ===== 添加节点 =====
    graph.add_node("search", search_node)
    graph.add_node("filter", filter_node)
    graph.add_node("extract_knowledge", extract_knowledge_node)
    graph.add_node("generate_titles", generate_titles_node)
    graph.add_node("wait_title_selection", wait_title_selection_node)
    graph.add_node("generate_outlines", generate_outlines_node)
    graph.add_node("wait_outline_selection", wait_outline_selection_node)
    graph.add_node("wait_article_config", wait_article_config_node)
    graph.add_node("generate_article", generate_article_node)
    graph.add_node("verify_article", verify_article_node)
    graph.add_node("format_output", format_output_node)

    # ===== 添加边 =====
    # 阶段 1: 搜索→过滤→提取→标题生成→等待选择
    graph.add_edge(START, "search")
    graph.add_edge("search", "filter")
    graph.add_edge("filter", "extract_knowledge")
    graph.add_edge("extract_knowledge", "generate_titles")
    graph.add_edge("generate_titles", "wait_title_selection")

    # 阶段 2: 选择标题后→生成大纲→等待选择
    graph.add_edge("wait_title_selection", "generate_outlines")
    graph.add_edge("generate_outlines", "wait_outline_selection")

    # 阶段 3: 选择大纲后→等待文章配置→生成文章→验证→完成
    graph.add_edge("wait_outline_selection", "wait_article_config")
    graph.add_edge("wait_article_config", "generate_article")
    graph.add_edge("generate_article", "verify_article")
    graph.add_conditional_edges(
        "verify_article",
        route_after_verify,
        {
            "pass": "format_output",
            "retry": "generate_article",
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
