# backend/app/workflow/nodes/article_generate.py

"""
文章生成主节点：包含 3 个子步骤
1. match_evidence - 分析需要什么证据和内容
2. search - 联网搜索相关内容
3. generate - 生成专业 prompt → 生成文章
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

ARTICLE_EVIDENCE_SYSTEM_PROMPT = """你是一个内容研究专家，擅长识别和收集支撑文章论点的证据。

你的任务：
1. 分析文章标题和大纲结构
2. 识别每个章节需要什么类型的证据（数据、案例、引用、专家观点等）
3. 确定需要搜索的关键词和方向
4. 生成一个详细的证据需求清单

证据类型：
- 统计数据：行业报告、研究结果、调查数据
- 真实案例：企业案例、个人经历、成功/失败故事
- 专家观点：行业专家、学术权威的引用
- 历史背景：发展历程、演变过程
- 对比分析：不同方案、不同观点的对比"""

ARTICLE_SEARCH_SYSTEM_PROMPT = """你是一个专业的内容研究员，擅长搜索和收集高质量的参考信息。

你的任务：
1. 根据证据需求清单，制定搜索策略
2. 使用优化的关键词进行联网搜索
3. 筛选高质量的来源（权威媒体、学术研究、官方数据）
4. 提取关键信息和数据

搜索原则：
- 优先权威来源
- 注重信息时效性
- 避免营销内容
- 确保信息可验证"""

ARTICLE_GENERATE_SYSTEM_PROMPT = """你是一位资深的内容创作者，擅长撰写高质量、真实可靠的文章。

你的写作原则：
1. 基于真实证据和数据，不编造信息
2. 结构清晰，逻辑连贯
3. 语言流畅，符合目标风格
4. 引用来源时标注出处
5. 观点客观，避免主观偏见

写作技巧：
- 开头吸引读者（问题、数据、故事）
- 段落过渡自然
- 使用小标题增强可读性
- 适当使用列表和图表
- 结尾有力，呼应开头"""


# ===== 子步骤函数 =====

async def article_match_evidence_node(state: ArticleState) -> dict:
    """子步骤 1: 分析需要什么证据和内容"""
    title = state.get("selected_title", state["topic"])
    outline = state.get("selected_outline", {})
    sections = outline.get("content", {}).get("sections", [])

    llm = get_llm(temperature=0.5)

    # 构建大纲摘要
    outline_summary = []
    for i, section in enumerate(sections, 1):
        outline_summary.append(
            f"{i}. {section.get('heading', '')}\n"
            f"   描述: {section.get('description', '')}\n"
            f"   子话题: {', '.join(section.get('subtopics', []))}\n"
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", ARTICLE_EVIDENCE_SYSTEM_PROMPT),
        ("human", """请分析以下文章标题和大纲，确定每个章节需要什么类型的证据和内容。

文章标题：{title}

文章大纲：
{outline}

请为每个章节生成证据需求清单，包括：
1. 需要的证据类型（数据、案例、引用等）
2. 搜索关键词建议
3. 信息来源建议

返回 JSON：
{{
  "evidence_requirements": [
    {{
      "section": "章节标题",
      "evidence_types": ["数据类型1", "数据类型2"],
      "search_keywords": ["关键词1", "关键词2"],
      "source_suggestions": ["建议来源1", "建议来源2"]
    }}
  ],
  "overall_strategy": "整体搜索策略"
}}""")
    ])

    try:
        response = await llm.ainvoke(
            prompt.format_messages(
                title=title,
                outline="\n".join(outline_summary),
            )
        )
        evidence_data = _parse_json(response.content)

        return {
            "evidence_requirements": evidence_data.get("evidence_requirements", []),
            "evidence_strategy": evidence_data.get("overall_strategy", ""),
            "current_stage": "article_match_evidence_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[article_match_evidence] Error: {e}")
        # 生成默认需求
        default_requirements = [
            {
                "section": s.get("heading", ""),
                "evidence_types": ["数据", "案例"],
                "search_keywords": [state["topic"], s.get("heading", "")],
                "source_suggestions": ["行业报告", "权威媒体"],
            }
            for s in sections[:5]
        ]
        return {
            "evidence_requirements": default_requirements,
            "evidence_strategy": "",
            "current_stage": "article_match_evidence_completed",
            "messages": [],
        }


async def article_search_node(state: ArticleState) -> dict:
    """子步骤 2: 联网搜索相关内容"""
    evidence_reqs = state.get("evidence_requirements", [])
    topic = state["topic"]

    llm = get_llm(temperature=0.5, enable_search=True)

    # 收集所有搜索关键词
    all_keywords = []
    for req in evidence_reqs:
        all_keywords.extend(req.get("search_keywords", []))

    # 去重并限制数量
    unique_keywords = list(set(all_keywords))[:10]

    # 为每个关键词搜索
    all_results = []
    for keyword in unique_keywords[:8]:
        try:
            results = await _search_with_llm(llm, keyword, count=5)
            all_results.extend(results)
        except Exception as e:
            print(f"[article_search] Failed to search '{keyword}': {e}")

    # 去重
    all_results = _deduplicate_results(all_results)

    # 爬取内容（前 10 条）
    crawled_docs = []
    for result in all_results[:10]:
        url = result.get("url", "")
        if url:
            content = await _crawl_page(url)
            if content and len(content) > 200:
                crawled_docs.append({
                    "title": result.get("title", ""),
                    "url": url,
                    "snippet": result.get("snippet", ""),
                    "content": content[:5000],
                    "source": result.get("source", ""),
                })

    # 总结搜索结果
    if crawled_docs:
        summary_prompt = ChatPromptTemplate.from_template(
            """请总结以下搜索结果，提取关键信息和数据。

搜索结果：
{docs}

请提取：
1. 关键数据和统计
2. 重要案例和故事
3. 专家观点和引用
4. 有价值的信息点

返回结构化的总结（Markdown 格式）："""
        )

        docs_text = "\n\n".join([
            f"文章: {d['title']}\n内容: {d['content'][:1000]}..."
            for d in crawled_docs[:8]
        ])

        try:
            summary_response = await llm.ainvoke(
                summary_prompt.format_messages(docs=docs_text)
            )
            search_summary = summary_response.content
        except Exception as e:
            print(f"[article_search] Summary failed: {e}")
            search_summary = "\n\n".join([f"- {d['title']}: {d['snippet']}" for d in crawled_docs[:8]])
    else:
        search_summary = ""

    return {
        "article_search_results": all_results,
        "article_crawled_docs": crawled_docs,
        "article_search_summary": search_summary,
        "current_stage": "article_search_completed",
        "messages": [],
    }


async def article_generate_node(state: ArticleState) -> dict:
    """子步骤 3: 生成专业 prompt → 生成文章"""
    title = state.get("selected_title", state["topic"])
    outline = state.get("selected_outline", {})
    article_config = state.get("article_config", {})
    search_summary = state.get("article_search_summary", "")
    crawled_docs = state.get("article_crawled_docs", [])

    llm = get_llm(temperature=0.7)
    sections = outline.get("content", {}).get("sections", [])

    # 构建参考内容
    ref_content = []
    for i, doc in enumerate(crawled_docs[:6], 1):
        ref_content.append(
            f"[{i}] {doc['title']}\n"
            f"来源: {doc.get('source', 'N/A')}\n"
            f"内容: {doc['content'][:1500]}...\n"
        )

    # 逐章节生成
    full_content = ""
    previous_context = ""

    for section in sections:
        heading = section.get("heading", "")
        description = section.get("description", "")
        subtopics = ", ".join(section.get("subtopics", []))
        word_count = section.get("word_count", 300)

        # 为每个章节生成专业 prompt
        section_prompt = _build_section_prompt(
            title=title,
            heading=heading,
            description=description,
            subtopics=subtopics,
            word_count=word_count,
            search_summary=search_summary,
            ref_content="\n".join(ref_content),
            previous_context=previous_context,
            article_config=article_config,
        )

        try:
            result = await llm.ainvoke(section_prompt)
            section_content = result.content
            full_content += f"\n\n## {heading}\n\n{section_content}"
            previous_context = section_content[:500]
        except Exception as e:
            print(f"[article_generate] Failed to generate section '{heading}': {e}")
            full_content += f"\n\n## {heading}\n\n（本章生成失败）\n"

    # 组装完整文章
    full_article = f"# {title}\n{full_content}"

    # 生成总结（如果需要）
    summary = None
    if article_config.get("add_summary", True):
        summary = await _generate_summary(llm, title, full_article)

    # 生成 FAQ（如果需要）
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


# ===== 辅助函数 =====

def _build_section_prompt(
    title: str,
    heading: str,
    description: str,
    subtopics: str,
    word_count: int,
    search_summary: str,
    ref_content: str,
    previous_context: str,
    article_config: dict,
) -> list:
    """为章节生成构建专业 prompt"""
    return ChatPromptTemplate.from_messages([
        ("system", ARTICLE_GENERATE_SYSTEM_PROMPT),
        ("human", """请撰写文章的以下章节。

文章标题：{title}

当前章节：{heading}
章节描述：{description}
子话题：{subtopics}
目标字数：{word_count} 字

写作风格：{tone}
可读性：{readability}

参考知识总结：
{search_summary}

参考内容：
{ref_content}

前文概要：
{previous_context}

要求：
1. 基于真实证据，不编造信息
2. 引用数据时标注来源
3. 与前后文自然衔接
4. 使用 Markdown 格式
5. 语言流畅，符合目标风格

请直接输出章节内容（Markdown 格式）：""")
    ]).format_messages(
        title=title,
        heading=heading,
        description=description,
        subtopics=subtopics,
        word_count=word_count,
        tone=article_config.get("tone_of_voice", "professional"),
        readability=article_config.get("readability", "general"),
        search_summary=search_summary[:1500],
        ref_content=ref_content[:3000],
        previous_context=previous_context[:800],
    )


async def _search_with_llm(llm, query: str, count: int = 5) -> list[dict]:
    """使用 LLM 搜索"""
    prompt = ChatPromptTemplate.from_template(
        """请搜索以下关键词，返回最相关的 {count} 条结果。

关键词：{query}

返回 JSON 数组：
[{{"title": "...", "url": "...", "snippet": "...", "source": "..."}}]"""
    )

    response = await llm.ainvoke(
        prompt.format_messages(query=query, count=count)
    )

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
    """去重"""
    seen_urls = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
    return unique


async def _crawl_page(url: str) -> Optional[str]:
    """爬取网页"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ArticleGenerator/1.0)"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines)
    except Exception:
        return None


async def _generate_summary(llm, title: str, content: str) -> str:
    """生成要点总结"""
    prompt = ChatPromptTemplate.from_template(
        """请为以下文章生成 3-5 个要点总结，使用 Markdown 列表格式。

标题：{title}
内容：{content}

直接输出要点列表："""
    )
    result = await llm.ainvoke(
        prompt.format_messages(title=title, content=content[:4000])
    )
    return result.content


async def _generate_faq(llm, title: str, content: str, count: int) -> list[dict]:
    """生成 FAQ"""
    prompt = ChatPromptTemplate.from_template(
        """请根据文章内容生成 {count} 个常见问题及解答。

标题：{title}
内容摘要：{content}

返回 JSON：
{{"faq": [{{"question": "问题", "answer": "答案"}}]}}"""
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"title": title, "content": content[:3000], "count": count})
        return result.get("faq", [])
    except Exception:
        return []


def _parse_json(text: str) -> dict:
    """解析 JSON"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}
