# backend/app/workflow/nodes/search.py

import httpx
import json
import re
from langchain_core.prompts import ChatPromptTemplate
from bs4 import BeautifulSoup

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


async def search_node(state: ArticleState) -> dict:
    """搜索节点：LLM 生成关键词 -> 联网搜索 -> 爬取内容"""
    topic = state["topic"]

    # 1. 用支持联网的模型生成关键词并搜索
    search_llm = get_llm(temperature=0.5, enable_search=True)

    search_prompt = ChatPromptTemplate.from_template(
        "请根据以下主题，从不同角度生成5个搜索关键词，然后对每个关键词进行联网搜索，"
        "最后以JSON格式返回搜索结果。每个结果包含：title（标题）、url（链接）、snippet（摘要）。\n\n"
        "主题：{topic}\n\n"
        "返回格式：\n"
        '{{"keywords": ["关键词1", "关键词2"], "results": [{{"title": "...", "url": "...", "snippet": "..."}}]}}\n\n'
        "请直接返回JSON，不要其他内容。"
    )

    response = await search_llm.ainvoke(
        search_prompt.format_messages(topic=topic)
    )

    # 解析搜索结果
    search_data = _parse_json_object(response.content)
    keywords = search_data.get("keywords", [topic])
    results = search_data.get("results", [])

    # 如果模型返回的结果不够，用关键词补充搜索
    if len(results) < 5:
        all_results = list(results)
        for kw in keywords[:5]:
            try:
                kw_results = await _search_with_llm(search_llm, kw)
                all_results.extend(kw_results)
            except Exception as e:
                print(f"[search] LLM search failed for '{kw}': {e}")

        # 去重
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        results = unique_results

    # 2. 爬取内容（取前20条）
    documents = []
    for result in results[:20]:
        url = result.get("url", "")
        if not url:
            continue
        content = await _crawl_page(url)
        if content and len(content) > 200:
            documents.append(
                {
                    "title": result.get("title", ""),
                    "url": url,
                    "snippet": result.get("snippet", ""),
                    "content": content[:8000],
                    "source": _extract_domain(url),
                }
            )

    return {
        "search_keywords": keywords,
        "search_results": results,
        "crawled_documents": documents,
        "current_stage": "search_completed",
        "messages": [],
    }


async def _search_with_llm(llm, query: str, count: int = 5) -> list[dict]:
    """用联网模型搜索单个关键词"""
    prompt = ChatPromptTemplate.from_template(
        "请搜索以下关键词，返回最相关的{count}条结果。\n\n"
        "关键词：{query}\n\n"
        "以JSON数组格式返回，每条结果包含：title（标题）、url（链接）、snippet（摘要）。\n"
        '例如：[{{"title": "...", "url": "...", "snippet": "..."}}]\n\n'
        "请直接返回JSON数组，不要其他内容。"
    )

    response = await llm.ainvoke(
        prompt.format_messages(query=query, count=count)
    )

    # 解析JSON数组
    match = re.search(r"\[.*?\]", response.content, re.DOTALL)
    if match:
        try:
            results = json.loads(match.group())
            if isinstance(results, list):
                return results
        except json.JSONDecodeError:
            pass

    return []


async def _crawl_page(url: str) -> str | None:
    """爬取网页正文"""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                url,
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ArticleGenerator/1.0)"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 移除script/style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # 清理空行
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines)
    except Exception:
        return None


def _extract_domain(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc.replace("www.", "")


def _parse_json_object(text: str) -> dict:
    """从LLM输出中解析JSON对象"""
    # 尝试提取JSON对象
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return {}


def _parse_json_array(text: str) -> list[str]:
    """从LLM输出中解析JSON数组"""
    # 尝试提取JSON数组
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            arr = json.loads(match.group())
            if isinstance(arr, list):
                return [str(item) for item in arr]
        except json.JSONDecodeError:
            pass

    # 回退：按行分割
    lines = [line.strip().strip("-").strip("*").strip('"').strip("'").strip(",")
             for line in text.split("\n") if line.strip()]
    return [line for line in lines if len(line) > 2][:5]
