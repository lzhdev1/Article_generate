# backend/app/workflow/nodes/filter.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


async def filter_node(state: ArticleState) -> dict:
    """过滤节点：LLM评估每条搜索结果与Topic的相关性"""
    topic = state["topic"]
    documents = state["crawled_documents"]

    if not documents:
        return {
            "filtered_documents": [],
            "current_stage": "filter_completed",
            "messages": [],
        }

    llm = get_llm(temperature=0.3)
    parser = JsonOutputParser()

    filtered = []
    batch_size = 5

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]

        docs_text = ""
        for j, doc in enumerate(batch):
            preview = doc["content"][:800]
            docs_text += f"\n[{j}] 标题: {doc['title']}\n内容摘要: {preview}\n"

        prompt = ChatPromptTemplate.from_template(
            "请评估以下搜索结果与主题的相关性。\n\n"
            "主题：{topic}\n\n"
            "搜索结果：\n{documents}\n\n"
            "对每篇文章评分(0-1)并简要说明。\n"
            '返回JSON数组：[{{"index": 0, "score": 0.85, "reason": "原因"}}]'
        )

        chain = prompt | llm | parser
        try:
            result = await chain.ainvoke({"topic": topic, "documents": docs_text})
            for item in result:
                idx = item.get("index", 0)
                score = float(item.get("score", 0))
                if 0 <= idx < len(batch) and score >= 0.5:
                    doc = batch[idx].copy()
                    doc["relevance_score"] = score
                    doc["filter_reason"] = item.get("reason", "")
                    filtered.append(doc)
        except Exception as e:
            print(f"[filter] Batch evaluation failed: {e}")
            # 回退：全部保留
            for doc in batch:
                doc_copy = doc.copy()
                doc_copy["relevance_score"] = 0.5
                filtered.append(doc_copy)

    # 按评分排序，取top 15
    filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    filtered = filtered[:15]

    return {
        "filtered_documents": filtered,
        "current_stage": "filter_completed",
        "messages": [],
    }
