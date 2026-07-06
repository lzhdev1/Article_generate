# backend/app/workflow/nodes/title_generate.py

"""
标题生成主节点：包含 4 个子步骤
1. search - 优化 topic 并联网搜索
2. filter - 筛选内容（过滤博客类文章）
3. analyze - 总结筛选后的搜索结果
4. generate - 生成至少 5 个标题
"""

import re
import json
import httpx
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from bs4 import BeautifulSoup

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


# ===== System Prompts =====

TITLE_SEARCH_SYSTEM_PROMPT = """你是一个专业的内容研究员，擅长通过优化搜索词来获取高质量的信息。

你的任务：
1. 分析用户提供的原始主题，提取核心关键词
2. 优化搜索词，使其更适合获取专业、权威的内容
3. 从多个角度生成搜索关键词（技术、应用、案例、趋势等）

注意：
- 避免过于宽泛的词汇
- 优先选择能获取权威来源的关键词
- 考虑中英文混合搜索"""

TITLE_FILTER_SYSTEM_PROMPT = """你是一个内容审核专家，负责筛选高质量的参考文章。

筛选标准：
1. 排除明显的博客类内容（个人博客、自媒体文章）
2. 优先保留：学术研究、行业报告、权威媒体、官方文档
3. 排除：营销内容、软文、重复内容
4. 确保内容来源可靠、信息准确

判断依据：
- 域名类型（.edu, .gov, 知名媒体优先）
- 内容深度和专业性
- 是否有明确作者和出处"""

TITLE_ANALYZE_SYSTEM_PROMPT = """你是一个知识管理专家，擅长从多篇参考文章中提取和总结关键信息。

你的任务：
1. 从筛选后的文章中提取核心观点和关键信息
2. 识别共同主题和不同视角
3. 总结出结构化的知识要点
4. 为后续的标题生成提供素材

输出要求：
- 使用清晰的层级结构
- 突出关键数据和事实
- 标注信息来源"""


# ===== 子步骤函数 =====

async def title_search_node(state: ArticleState) -> dict:
    """子步骤 1: 优化 topic 并联网搜索"""
    import time
    start_time = time.time()
    print(f"[title_search] Starting at {start_time}")
    topic = state["topic"]

    # 使用支持联网的 LLM
    llm = get_llm(temperature=0.5, enable_search=True)

    # 让 LLM 生成搜索关键词
    keyword_prompt = ChatPromptTemplate.from_template(
        "你是一个专业的内容研究员。请根据以下主题，生成5个搜索关键词。\n\n"
        "主题：{topic}\n\n"
        "请从以下角度生成关键词：\n"
        "1. 技术原理\n"
        "2. 应用场景\n"
        "3. 行业案例\n"
        "4. 发展趋势\n"
        "5. 最佳实践\n\n"
        "返回JSON格式：{{\"keywords\": [\"关键词1\", \"关键词2\", ...]}}\n"
        "只返回JSON，不要其他内容。"
    )

    try:
        print(f"[title_search] Generating keywords at {time.time() - start_time:.2f}s")
        keyword_response = await llm.ainvoke(keyword_prompt.format_messages(topic=topic))
        keyword_data = _parse_json(keyword_response.content)
        keywords = keyword_data.get("keywords", [topic])
        print(f"[title_search] Generated keywords: {keywords}")

        # 使用联网搜索功能搜索第一个关键词（避免多次搜索太慢）
        search_keyword = keywords[0] if keywords else topic
        print(f"[title_search] Searching with keyword: '{search_keyword}' at {time.time() - start_time:.2f}s")

        search_prompt = ChatPromptTemplate.from_template(
            "请使用你的联网搜索功能，搜索以下关键词，并返回真实的搜索结果。\n\n"
            "关键词：{keyword}\n\n"
            "要求：\n"
            "1. 必须使用联网搜索工具获取真实结果\n"
            "2. 返回至少5条真实的搜索结果\n"
            "3. 每条结果必须包含真实的URL、标题和摘要\n"
            "4. 优先选择权威来源（学术、官方、知名媒体）\n\n"
            "返回JSON格式：\n"
            '{{"search_results": [{{"title": "真实标题", "url": "真实URL", "snippet": "真实摘要", "source": "来源"}}]}}\n\n'
            "请确保所有URL都是真实可访问的。"
        )

        print(f"[title_search] Invoking LLM with search at {time.time() - start_time:.2f}s")
        search_response = await llm.ainvoke(search_prompt.format_messages(keyword=search_keyword))
        print(f"[title_search] Search completed at {time.time() - start_time:.2f}s")

        search_data = _parse_json(search_response.content)
        results = search_data.get("search_results", [])
        results = _deduplicate_results(results)

        print(f"[title_search] Got {len(results)} search results")

        # 爬取内容（前 10 条）
        print(f"[title_search] Starting to crawl {len(results[:10])} URLs at {time.time() - start_time:.2f}s")
        crawled_docs = []
        for i, result in enumerate(results[:10], 1):
            url = result.get("url", "")
            if url:
                print(f"[title_search] Crawling [{i}/{len(results[:10])}]: {url}")
                content = await _crawl_page(url)
                if content and len(content) > 200:
                    crawled_docs.append({
                        "title": result.get("title", ""),
                        "url": url,
                        "snippet": result.get("snippet", ""),
                        "content": content[:6000],
                        "source": result.get("source", ""),
                    })
                    print(f"[title_search] Successfully crawled: {len(content)} chars")
                else:
                    print(f"[title_search] Failed to crawl or content too short: {len(content) if content else 0} chars")

        print(f"[title_search] Completed at {time.time() - start_time:.2f}s with {len(crawled_docs)} docs")
        return {
            "optimized_keywords": keywords,
            "search_results": results,
            "crawled_documents": crawled_docs,
            "current_stage": "title_search_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[title_search] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "optimized_keywords": [topic],
            "search_results": [],
            "crawled_documents": [],
            "current_stage": "title_search_completed",
            "error": str(e),
            "messages": [],
        }


async def title_filter_node(state: ArticleState) -> dict:
    """子步骤 2: 筛选内容（过滤博客类文章）"""
    import time
    start_time = time.time()
    print(f"[title_filter] Starting at {start_time}")

    docs = state.get("crawled_documents", [])
    search_results = state.get("search_results", [])
    topic = state.get("topic", "")

    # 即使没有爬取到文档，也使用搜索结果摘要进行筛选
    if not docs and not search_results:
        print(f"[title_filter] No docs or search results, using topic only")
        return {
            "filtered_documents": [],
            "current_stage": "title_filter_completed",
            "messages": [],
        }

    llm = get_llm(temperature=0.3)

    # 构建文档摘要（用于 LLM 判断）
    # 优先使用爬取的文档，否则使用搜索结果
    if docs:
        docs_summary = []
        for i, doc in enumerate(docs[:15], 1):
            docs_summary.append(
                f"{i}. 标题: {doc['title']}\n"
                f"   URL: {doc['url']}\n"
                f"   来源: {doc.get('source', 'unknown')}\n"
                f"   内容前 500 字: {doc['content'][:500]}..."
            )
        docs_text = "\n\n".join(docs_summary)
    else:
        # 使用搜索结果摘要
        results_summary = []
        for i, result in enumerate(search_results[:15], 1):
            results_summary.append(
                f"{i}. 标题: {result.get('title', '')}\n"
                f"   URL: {result.get('url', '')}\n"
                f"   来源: {result.get('source', 'unknown')}\n"
                f"   摘要: {result.get('snippet', '')}"
            )
        docs_text = "\n\n".join(results_summary)
        print(f"[title_filter] Using {len(search_results)} search results instead of crawled docs")

    prompt = ChatPromptTemplate.from_messages([
        ("system", TITLE_FILTER_SYSTEM_PROMPT),
        ("human", """请分析以下搜索结果，筛选出高质量的参考文章。

主题：{topic}

参考文章列表：
{docs}

请筛选出符合标准的文章，返回保留文章的编号列表。

返回 JSON 格式：
{{
  "kept_indices": [1, 3, 5, ...],
  "reasoning": "筛选理由"
}}""")
    ])

    try:
        print(f"[title_filter] Invoking LLM at {time.time() - start_time:.2f}s")
        response = await llm.ainvoke(
            prompt.format_messages(topic=topic, docs=docs_text)
        )
        print(f"[title_filter] LLM response received at {time.time() - start_time:.2f}s")
        filter_result = _parse_json(response.content)
        kept_indices = filter_result.get("kept_indices", list(range(1, len(docs) + 1)))

        # 转换索引（1-based 到 0-based）
        # 如果使用搜索结果，从 search_results 中取；否则从 docs 中取
        source_list = docs if docs else search_results
        filtered_docs = []
        for i in kept_indices:
            if 0 < i <= len(source_list):
                item = source_list[i - 1]
                # 确保每个文档都有必要的字段
                filtered_docs.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "content": item.get("content", item.get("snippet", "")),  # 如果没有 content，使用 snippet
                    "source": item.get("source", ""),
                })

        print(f"[title_filter] Completed at {time.time() - start_time:.2f}s with {len(filtered_docs)} filtered docs")
        return {
            "filtered_documents": filtered_docs,
            "current_stage": "title_filter_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[title_filter] Error: {e}")
        # 出错时保留所有文档
        source_list = docs if docs else search_results
        # 确保字段完整
        safe_docs = []
        for item in source_list:
            safe_docs.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "content": item.get("content", item.get("snippet", "")),
                "source": item.get("source", ""),
            })
        return {
            "filtered_documents": safe_docs,
            "current_stage": "title_filter_completed",
            "messages": [],
        }


async def title_analyze_node(state: ArticleState) -> dict:
    """子步骤 3: 总结筛选后的搜索结果"""
    import time
    start_time = time.time()
    print(f"[title_analyze] Starting at {start_time}")

    docs = state.get("filtered_documents", [])
    topic = state.get("topic", "")

    # 即使没有筛选后的文档，也基于 topic 和搜索结果生成总结
    if not docs:
        print(f"[title_analyze] No filtered docs, generating summary from topic only")
        llm = get_llm(temperature=0.4)
        prompt = ChatPromptTemplate.from_messages([
            ("system", TITLE_ANALYZE_SYSTEM_PROMPT),
            ("human", """请基于以下主题，总结该领域的关键信息和核心观点。

主题：{topic}

请总结：
1. 主要观点和论据
2. 关键数据和事实
3. 不同视角和观点
4. 值得引用的内容

返回结构化的总结（Markdown 格式）：""")
        ])

        try:
            print(f"[title_analyze] Invoking LLM (topic-only mode) at {time.time() - start_time:.2f}s")
            response = await llm.ainvoke(prompt.format_messages(topic=topic))
            print(f"[title_analyze] LLM response received at {time.time() - start_time:.2f}s")
            summary = response.content
            print(f"[title_analyze] Completed at {time.time() - start_time:.2f}s")
            return {
                "knowledge_summary": summary,
                "current_stage": "title_analyze_completed",
                "messages": [],
            }
        except Exception as e:
            print(f"[title_analyze] Error in topic-only mode: {e}")
            return {
                "knowledge_summary": "",
                "current_stage": "title_analyze_completed",
                "messages": [],
            }

    llm = get_llm(temperature=0.4)

    # 构建文档内容
    docs_content = []
    for i, doc in enumerate(docs[:10], 1):
        docs_content.append(
            f"文章 {i}:\n"
            f"标题: {doc['title']}\n"
            f"内容: {doc['content'][:1500]}...\n"
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", TITLE_ANALYZE_SYSTEM_PROMPT),
        ("human", """请分析以下参考文章，总结关键信息和核心观点。

参考文章：
{docs}

请总结：
1. 主要观点和论据
2. 关键数据和事实
3. 不同视角和观点
4. 值得引用的内容

返回结构化的总结（Markdown 格式）：""")
    ])

    try:
        print(f"[title_analyze] Invoking LLM at {time.time() - start_time:.2f}s")
        response = await llm.ainvoke(
            prompt.format_messages(docs="\n\n".join(docs_content))
        )
        print(f"[title_analyze] LLM response received at {time.time() - start_time:.2f}s")
        summary = response.content
        print(f"[title_analyze] Completed at {time.time() - start_time:.2f}s")

        return {
            "knowledge_summary": summary,
            "current_stage": "title_analyze_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[title_analyze] Error: {e}")
        # 简单拼接作为后备
        simple_summary = "\n\n".join([f"- {d['title']}: {d['snippet']}" for d in docs[:10]])
        return {
            "knowledge_summary": simple_summary,
            "current_stage": "title_analyze_completed",
            "messages": [],
        }


async def title_generate_node(state: ArticleState) -> dict:
    """子步骤 4: 生成至少 5 个标题"""
    topic = state["topic"]
    summary = state.get("knowledge_summary", "")
    docs = state.get("filtered_documents", [])

    llm = get_llm(temperature=0.85)

    # 提取参考文章的标题
    ref_titles = [doc.get("title", "") for doc in docs[:10]]
    ref_titles_text = "\n".join([f"- {t}" for t in ref_titles if t])

    prompt = ChatPromptTemplate.from_template(
        """你是专业的内容编辑。请根据以下信息生成至少 5 个不同风格的文章标题。

主题：{topic}

知识总结：
{summary}

参考文章标题：
{ref_titles}

请生成至少 5 个标题，使用不同风格：
1. 数字列表型（包含具体数字，如"X 个方法"）
2. 问题引导型（以问句吸引读者）
3. 权威专业型（体现深度和权威性）
4. 情感共鸣型（引发读者情感共鸣）
5. 对比冲突型（制造认知冲突）
6. 趋势洞察型（展望未来趋势）
7. 实战指南型（强调实用性）

返回 JSON：
{{"titles": [{{"content": "标题内容", "style": "风格名称", "reasoning": "生成理由"}}]}}"""
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({
            "topic": topic,
            "summary": summary[:2000],
            "ref_titles": ref_titles_text,
        })
        titles = result.get("titles", [])
    except Exception as e:
        print(f"[title_generate] Error: {e}")
        titles = []

    # 确保至少 5 个标题
    while len(titles) < 5:
        titles.append({
            "content": f"深度解析：{topic} 的第 {len(titles) + 1} 个视角",
            "style": "general",
            "reasoning": "补充标题",
        })

    return {
        "generated_titles": titles[:7],  # 最多返回 7 个
        "current_stage": "title_generated",
        "messages": [],
    }


# ===== 辅助函数 =====

async def _search_single_keyword(llm, keyword: str, count: int = 5) -> list[dict]:
    """使用单个关键词搜索"""
    prompt = ChatPromptTemplate.from_template(
        """请搜索以下关键词，返回最相关的 {count} 条结果。

关键词：{keyword}

返回 JSON 数组：
[{{"title": "...", "url": "...", "snippet": "...", "source": "..."}}]"""
    )

    response = await llm.ainvoke(
        prompt.format_messages(keyword=keyword, count=count)
    )

    # 解析 JSON 数组
    match = re.search(r"\[.*?\]", response.content, re.DOTALL)
    if match:
        try:
            results = json.loads(match.group())
            if isinstance(results, list):
                return results
        except json.JSONDecodeError:
            pass

    return []


def _deduplicate_results(results: list[dict]) -> list[dict]:
    """去重搜索结果"""
    seen_urls = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
    return unique


async def _crawl_page(url: str) -> Optional[str]:
    """爬取网页正文"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ArticleGenerator/1.0)"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 移除无关标签
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines)
    except Exception:
        return None


def _parse_json(text: str) -> dict:
    """从 LLM 输出中解析 JSON"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}
