# backend/app/workflow/nodes/final_config.py

"""
最终配置节点：用户填写文章生成配置
这是一个 Human-in-the-Loop 节点
"""

from app.workflow.state import ArticleState


async def wait_article_config_node(state: ArticleState) -> dict:
    """等待用户填写文章配置"""
    from langgraph.types import interrupt

    # 暂停，等待用户输入
    article_config = interrupt(
        {
            "action": "set_article_config",
            "message": "请填写文章生成配置（图片、视频、总结、FAQ 等）",
        }
    )

    return {
        "article_config": article_config,
        "current_stage": "article_config_set",
        "messages": [],
    }
