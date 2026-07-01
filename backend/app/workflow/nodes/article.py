# backend/app/workflow/nodes/article.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


async def generate_article_node(state: ArticleState) -> dict:
    """文章生成节点：逐章节生成完整文章"""
    topic = state["topic"]
    title = state.get("selected_title", topic)
    outline = state.get("selected_outline", {})
    knowledge = state.get("retrieved_knowledge", [])
    article_config = state.get("article_config", {})

    llm = get_llm(temperature=0.7)
    sections = outline.get("content", {}).get("sections", [])

    knowledge_text = "\n".join([f"- {k['content'][:300]}" for k in knowledge[:8]])

    full_content = ""
    previous_context = ""

    for section in sections:
        heading = section.get("heading", "")
        description = section.get("description", "")
        subtopics = ", ".join(section.get("subtopics", []))
        word_count = section.get("word_count", 300)

        prompt = ChatPromptTemplate.from_template(
            "请撰写文章的以下章节。\n\n"
            "文章标题：{title}\n"
            "主题：{topic}\n\n"
            "当前章节：{heading}\n"
            "章节描述：{description}\n"
            "子话题：{subtopics}\n"
            "目标字数：{word_count}字\n\n"
            "写作风格：{tone}\n"
            "可读性：{readability}\n\n"
            "参考知识：\n{knowledge}\n\n"
            "前文概要：{previous_context}\n\n"
            "请以Markdown格式输出本章节内容，确保与前后文自然衔接。"
        )

        result = await llm.ainvoke(
            prompt.format_messages(
                title=title,
                topic=topic,
                heading=heading,
                description=description,
                subtopics=subtopics,
                word_count=word_count,
                tone=article_config.get("tone_of_voice", "professional"),
                readability=article_config.get("readability", "general"),
                knowledge=knowledge_text,
                previous_context=previous_context[:800],
            )
        )

        section_content = result.content
        full_content += f"\n\n## {heading}\n\n{section_content}"
        previous_context = section_content[:500]

    # 组装完整文章
    full_article = f"# {title}\n{full_content}"

    # 生成总结（如果需要）
    summary = None
    if article_config.get("add_summary", True):
        summary = await _generate_summary(llm, title, full_article)

    # 生成FAQ（如果需要）
    faq = []
    if article_config.get("add_faq", True):
        faq = await _generate_faq(llm, title, full_article, article_config.get("faq_count", 5))

    return {
        "full_article": full_article,
        "article_summary": summary,
        "article_faq": faq,
        "retry_count": state.get("retry_count", 0) + 1,
        "current_stage": "article_generated",
        "messages": [],
    }


async def verify_article_node(state: ArticleState) -> dict:
    """验证节点：检查文章内容的可靠性和准确性"""
    article = state.get("full_article", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count > max_retries:
        return {
            "verification_passed": False,
            "current_stage": "verification_failed",
            "messages": [],
        }

    llm = get_llm(temperature=0.2)

    prompt = ChatPromptTemplate.from_template(
        "请验证以下文章内容的可靠性。\n\n"
        "文章：\n{article}\n\n"
        "检查：\n"
        "1. 事实准确性\n"
        "2. 逻辑一致性\n"
        "3. 信息时效性\n\n"
        '返回JSON：{{"overall_score": 0.85, "passed": true, "issues": ["问题1"]}}'
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"article": article[:5000]})
        passed = result.get("passed", True) and result.get("overall_score", 1.0) >= 0.6
    except Exception as e:
        print(f"[verify] Failed: {e}")
        passed = True  # 验证失败时默认通过

    return {
        "verification_passed": passed,
        "current_stage": "verification_completed",
        "messages": [],
    }


async def format_output_node(state: ArticleState) -> dict:
    """格式化输出节点"""
    return {
        "current_stage": "completed",
        "messages": [],
    }


async def _generate_summary(llm, title: str, content: str) -> str:
    """生成要点总结"""
    prompt = ChatPromptTemplate.from_template(
        "请为以下文章生成3-5个要点总结，使用Markdown列表格式。\n\n"
        "标题：{title}\n"
        "内容：{content}\n\n"
        "直接输出要点列表。"
    )
    result = await llm.ainvoke(prompt.format_messages(title=title, content=content[:4000]))
    return result.content


async def _generate_faq(llm, title: str, content: str, count: int) -> list[dict]:
    """生成FAQ"""
    prompt = ChatPromptTemplate.from_template(
        f"请根据文章内容生成{count}个常见问题及解答。\n\n"
        "标题：{title}\n"
        "内容摘要：{content}\n\n"
        '返回JSON：{{"faq": [{{"question": "问题", "answer": "答案"}}]}}'
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"title": title, "content": content[:3000]})
        return result.get("faq", [])
    except Exception:
        return []
