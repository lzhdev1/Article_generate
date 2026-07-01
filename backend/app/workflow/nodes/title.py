# backend/app/workflow/nodes/title.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


async def generate_titles_node(state: ArticleState) -> dict:
    """标题生成节点：基于Topic和知识生成5个不同风格的标题"""
    topic = state["topic"]
    knowledge = state.get("retrieved_knowledge", [])

    llm = get_llm(temperature=0.85)

    knowledge_text = "\n".join([f"- {k['content'][:200]}" for k in knowledge[:10]])

    prompt = ChatPromptTemplate.from_template(
        "你是专业的内容编辑。请根据以下信息生成5个不同风格的文章标题。\n\n"
        "主题：{topic}\n\n"
        "参考知识：\n{knowledge}\n\n"
        "请生成5个标题，使用不同风格：\n"
        "1. 数字列表型（包含具体数字，如'X个方法'）\n"
        "2. 问题引导型（以问句吸引读者）\n"
        "3. 权威专业型（体现深度和权威性）\n"
        "4. 情感共鸣型（引发读者情感共鸣）\n"
        "5. 对比冲突型（制造认知冲突）\n\n"
        '返回JSON：{{"titles": [{{"content": "标题内容", "style": "风格名称", "reasoning": "生成理由"}}]}}'
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"topic": topic, "knowledge": knowledge_text})
        titles = result.get("titles", [])
    except Exception as e:
        print(f"[title] Generation failed: {e}")
        titles = [
            {"content": f"深度解析：{topic}", "style": "authority", "reasoning": "权威专业型"},
            {"content": f"{topic}：你需要知道的一切", "style": "comprehensive", "reasoning": "全面解析型"},
        ]

    # 确保至少5个
    while len(titles) < 5:
        titles.append(
            {
                "content": f"关于{topic}的第{len(titles)+1}个视角",
                "style": "general",
                "reasoning": "补充标题",
            }
        )

    return {
        "generated_titles": titles[:5],
        "current_stage": "title_generated",
        "messages": [],
    }


async def wait_title_selection_node(state: ArticleState) -> dict:
    """Human-in-the-Loop: 等待用户选择标题"""
    from langgraph.types import interrupt

    titles = state["generated_titles"]

    # 暂停，等待用户输入
    human_input = interrupt(
        {
            "action": "select_title",
            "titles": titles,
            "message": "请从以上标题中选择一个",
        }
    )

    selected_title = human_input.get("selected_title", "")

    return {
        "selected_title": selected_title,
        "current_stage": "title_selected",
        "messages": [],
    }
