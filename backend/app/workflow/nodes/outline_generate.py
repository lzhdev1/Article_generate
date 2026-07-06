# backend/app/workflow/nodes/outline_generate.py

"""
大纲生成主节点：包含 4 个子步骤
1. search - 分析标题 + 配置 + 之前内容
2. extract - 提取参考文章的结构和风格
3. analyze - 生成专业 prompt
4. generate - 生成大纲
"""

import re
import json
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.workflow.state import ArticleState
from app.workflow.llm import get_llm


# ===== System Prompts =====

OUTLINE_SEARCH_SYSTEM_PROMPT = """你是一个内容策划专家，擅长分析文章结构和规划内容。

你的任务：
1. 分析选定的标题，理解其核心意图
2. 结合用户的配置要求（字数、风格、可读性）
3. 整合之前的搜索内容，识别可用的素材
4. 为大纲生成提供清晰的方向"""

OUTLINE_EXTRACT_SYSTEM_PROMPT = """你是一个文章结构分析专家，擅长解构优秀文章的组织和风格。

你的任务：
1. 分析参考文章的目录结构（章节划分）
2. 识别文章的写作风格和语调
3. 提取内容组织模式（如何引入、展开、总结）
4. 总结出可借鉴的结构模板

分析维度：
- 章节数量和层级
- 每章节的内容类型（理论、案例、数据、观点）
- 过渡和衔接方式
- 开头和结尾的技巧"""

OUTLINE_ANALYZE_SYSTEM_PROMPT = """你是一个提示工程专家，擅长构建高质量的 LLM 提示词。

你的任务：
1. 基于前面的分析结果，生成一个专业的大纲生成提示词
2. 确保提示词包含：
   - 明确的角色定义
   - 清晰的任务描述
   - 具体的约束条件
   - 期望的输出格式
3. 优化提示词以获得最佳的大纲生成效果"""


# ===== 子步骤函数 =====

async def outline_search_node(state: ArticleState) -> dict:
    """子步骤 1: 分析标题 + 配置 + 之前内容"""
    title = state.get("selected_title", state["topic"])
    outline_config = state.get("outline_config", {})
    knowledge_summary = state.get("knowledge_summary", "")

    llm = get_llm(temperature=0.5)

    prompt = ChatPromptTemplate.from_messages([
        ("system", OUTLINE_SEARCH_SYSTEM_PROMPT),
        ("human", """请分析以下信息，为大纲生成做准备。

选定标题：{title}

用户配置：
- 目标字数: {word_count} 字
- 写作风格: {tone}
- 可读性: {readability}
- 目标受众: {audience}

之前的知识总结：
{knowledge}

请分析并总结：
1. 标题的核心意图和预期内容方向
2. 用户配置的关键要求
3. 可用的素材和知识点
4. 建议的内容组织方向

返回 JSON：
{{
  "title_analysis": "标题分析",
  "config_requirements": "配置要求总结",
  "available_materials": "可用素材",
  "suggested_direction": "建议方向"
}}""")
    ])

    try:
        response = await llm.ainvoke(
            prompt.format_messages(
                title=title,
                word_count=outline_config.get("word_count", 2000),
                tone=outline_config.get("tone_of_voice", "professional"),
                readability=outline_config.get("readability", "general"),
                audience=outline_config.get("target_audience", "general"),
                knowledge=knowledge_summary[:1500],
            )
        )
        analysis = _parse_json(response.content)

        return {
            "outline_search_analysis": analysis,
            "current_stage": "outline_search_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[outline_search] Error: {e}")
        return {
            "outline_search_analysis": {},
            "current_stage": "outline_search_completed",
            "messages": [],
        }


async def outline_extract_node(state: ArticleState) -> dict:
    """子步骤 2: 提取参考文章的结构和风格"""
    docs = state.get("filtered_documents", [])

    if not docs:
        return {
            "article_style_analysis": "",
            "current_stage": "outline_extract_completed",
            "messages": [],
        }

    llm = get_llm(temperature=0.4)

    # 选择 3-5 篇代表性文章进行分析
    sample_docs = docs[:5]
    docs_content = []
    for i, doc in enumerate(sample_docs, 1):
        docs_content.append(
            f"文章 {i}:\n"
            f"标题: {doc.get('title', 'N/A')}\n"
            f"内容片段:\n{doc.get('content', '')[:1200]}...\n"
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", OUTLINE_EXTRACT_SYSTEM_PROMPT),
        ("human", """请分析以下参考文章的结构和写作风格。

参考文章：
{docs}

请分析并总结：
1. 每篇文章的章节结构（章节数量、层级关系）
2. 内容组织模式（如何引入、展开、总结）
3. 写作风格和语调特点
4. 值得借鉴的结构技巧

返回结构化的分析报告（Markdown 格式）：""")
    ])

    try:
        response = await llm.ainvoke(
            prompt.format_messages(docs="\n\n".join(docs_content))
        )
        style_analysis = response.content

        return {
            "article_style_analysis": style_analysis,
            "current_stage": "outline_extract_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[outline_extract] Error: {e}")
        return {
            "article_style_analysis": "",
            "current_stage": "outline_extract_completed",
            "messages": [],
        }


async def outline_analyze_node(state: ArticleState) -> dict:
    """子步骤 3: 生成专业 prompt"""
    title = state.get("selected_title", state["topic"])
    outline_config = state.get("outline_config", {})
    search_analysis = state.get("outline_search_analysis", {})
    style_analysis = state.get("article_style_analysis", "")

    llm = get_llm(temperature=0.5)

    prompt = ChatPromptTemplate.from_messages([
        ("system", OUTLINE_ANALYZE_SYSTEM_PROMPT),
        ("human", """请基于以下分析结果，生成一个专业的大纲生成提示词。

选定标题：{title}

标题分析：{title_analysis}

配置要求：{config_requirements}

文章风格分析：
{style_analysis}

请生成一个完整的大纲生成提示词，包含：
1. 角色定义（你是一位...）
2. 任务描述（请生成...）
3. 约束条件（要求...）
4. 输出格式（返回 JSON...）

直接输出提示词内容：""")
    ])

    try:
        response = await llm.ainvoke(
            prompt.format_messages(
                title=title,
                title_analysis=search_analysis.get("title_analysis", ""),
                config_requirements=search_analysis.get("config_requirements", ""),
                style_analysis=style_analysis[:1500],
            )
        )
        outline_prompt = response.content

        return {
            "outline_generation_prompt": outline_prompt,
            "current_stage": "outline_analyze_completed",
            "messages": [],
        }
    except Exception as e:
        print(f"[outline_analyze] Error: {e}")
        # 使用默认 prompt
        default_prompt = _get_default_outline_prompt(title, outline_config)
        return {
            "outline_generation_prompt": default_prompt,
            "current_stage": "outline_analyze_completed",
            "messages": [],
        }


async def outline_generate_node(state: ArticleState) -> dict:
    """子步骤 4: 生成大纲"""
    title = state.get("selected_title", state["topic"])
    outline_config = state.get("outline_config", {})
    outline_prompt = state.get("outline_generation_prompt", "")

    llm = get_llm(temperature=0.7)

    # 如果没有生成 prompt，使用默认的
    if not outline_prompt:
        outline_prompt = _get_default_outline_prompt(title, outline_config)

    # 构建完整的生成请求
    full_prompt = ChatPromptTemplate.from_template(
        outline_prompt + "\n\n" +
        """文章标题：{title}

目标字数：{word_count} 字
写作风格：{tone}
可读性：{readability}

请生成至少 2 个不同风格的大纲方案。

返回 JSON：
{{"outlines": [{{"content": {{"title": "大纲标题", "sections": [{{"heading": "章节标题", "description": "描述", "subtopics": ["子话题"], "word_count": 300}}]}}, "reasoning": "设计思路", "style": "风格名"}}]}}"""
    )

    parser = JsonOutputParser()
    chain = full_prompt | llm | parser

    try:
        result = await chain.ainvoke({
            "title": title,
            "word_count": outline_config.get("word_count", 2000),
            "tone": outline_config.get("tone_of_voice", "professional"),
            "readability": outline_config.get("readability", "general"),
        })
        outlines = result.get("outlines", [])
    except Exception as e:
        print(f"[outline_generate] Error: {e}")
        outlines = []

    # 确保至少 2 个大纲
    if len(outlines) < 2:
        outlines.append({
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
        })

    return {
        "generated_outlines": outlines[:3],  # 最多 3 个
        "current_stage": "outline_generated",
        "messages": [],
    }


# ===== 辅助函数 =====

def _get_default_outline_prompt(title: str, config: dict) -> str:
    """获取默认的大纲生成 prompt"""
    return f"""你是一位专业的内容策划师，擅长设计清晰、有吸引力的文章结构。

请根据以下信息生成文章大纲：

文章标题：{title}

要求：
1. 生成至少 2 个不同风格的大纲方案
2. 每个大纲包含 4-6 个章节
3. 每个章节包含：标题、描述、子话题、预估字数
4. 风格参考：全面系统型、问题-解决型、循序渐进型

返回 JSON 格式：
{{"outlines": [{{"content": {{"title": "大纲标题", "sections": [{{"heading": "章节标题", "description": "描述", "subtopics": ["子话题"], "word_count": 300}}]}}, "reasoning": "设计思路", "style": "风格名"}}]}}"""


def _parse_json(text: str) -> dict:
    """从 LLM 输出中解析 JSON"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}
