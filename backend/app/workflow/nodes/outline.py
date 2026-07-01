# backend/app/workflow/nodes/outline.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


async def generate_outlines_node(state: ArticleState) -> dict:
    """大纲生成节点：基于标题和知识生成至少2个大纲方案"""
    topic = state["topic"]
    title = state.get("selected_title", topic)
    knowledge = state.get("retrieved_knowledge", [])
    outline_config = state.get("outline_config", {})

    llm = get_llm(temperature=0.7)

    knowledge_text = "\n".join([f"- {k['content'][:200]}" for k in knowledge[:8]])
    word_count = outline_config.get("word_count", 2000)
    tone = outline_config.get("tone_of_voice", "professional")
    readability = outline_config.get("readability", "general")

    prompt = ChatPromptTemplate.from_template(
        "你是专业的内容策划师。请根据以下信息生成3个不同风格的文章大纲。\n\n"
        "文章标题：{title}\n"
        "主题：{topic}\n\n"
        "用户配置：\n"
        "- 目标字数: {word_count}字\n"
        "- 可读性: {readability}\n"
        "- 写作风格: {tone}\n\n"
        "参考知识：\n{knowledge}\n\n"
        "请生成3个不同结构的大纲，每个包含4-6个章节。\n"
        "大纲风格参考：\n"
        "1. comprehensive: 全面系统型\n"
        "2. problem_solution: 问题-解决型\n"
        "3. step_by_step: 循序渐进型\n\n"
        '返回JSON：{{"outlines": [{{"content": {{"title": "大纲标题", "sections": [{{"heading": "章节标题", "description": "描述", "subtopics": ["子话题"], "word_count": 300}}]}}, "reasoning": "设计思路", "style": "风格名"}}]}}'
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke(
            {
                "title": title,
                "topic": topic,
                "word_count": word_count,
                "tone": tone,
                "readability": readability,
                "knowledge": knowledge_text,
            }
        )
        outlines = result.get("outlines", [])
    except Exception as e:
        print(f"[outline] Generation failed: {e}")
        outlines = [
            {
                "content": {
                    "title": title,
                    "sections": [
                        {"heading": "引言", "description": "引入主题", "subtopics": [], "word_count": 300},
                        {"heading": "正文", "description": "核心内容", "subtopics": [], "word_count": 1400},
                        {"heading": "总结", "description": "总结观点", "subtopics": [], "word_count": 300},
                    ],
                },
                "reasoning": "基础大纲",
                "style": "general",
            }
        ]

    # 确保 outlines 格式正确
    if not outlines:
        outlines = [
            {
                "content": {
                    "title": title,
                    "sections": [
                        {"heading": "引言", "description": "引入主题", "subtopics": [], "word_count": 300},
                        {"heading": "正文", "description": "核心内容", "subtopics": [], "word_count": 1400},
                        {"heading": "总结", "description": "总结观点", "subtopics": [], "word_count": 300},
                    ],
                },
                "reasoning": "基础大纲",
                "style": "general",
            }
        ]
    elif isinstance(outlines, dict) and "content" in outlines:
        # 如果返回的是单个大纲而不是数组
        outlines = [outlines]

    return {
        "generated_outlines": outlines[:3],
        "current_stage": "outline_generated",
        "messages": [],
    }


async def wait_outline_selection_node(state: ArticleState) -> dict:
    """Human-in-the-Loop: 等待用户选择大纲"""
    from langgraph.types import interrupt

    outlines = state["generated_outlines"]

    human_input = interrupt(
        {
            "action": "select_outline",
            "outlines": outlines,
            "message": "请从以上大纲中选择一个",
        }
    )

    selected_outline = human_input.get("selected_outline")

    return {
        "selected_outline": selected_outline,
        "outline_config": human_input.get("outline_config", state.get("outline_config")),
        "current_stage": "outline_selected",
        "messages": [],
    }
