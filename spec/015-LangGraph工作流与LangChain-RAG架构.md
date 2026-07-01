# Spec-015: LangGraph工作流与LangChain RAG架构

## 1. 功能概述

本模块使用 LangGraph 构建整个文章生成的有状态工作流，使用 LangChain 构建 RAG（检索增强生成）管道。这是系统的核心智能架构层。

核心职责：
- 定义完整的文章生成状态图（StateGraph）
- 实现各节点（搜索、过滤、提取、生成、验证）
- 实现循环验证机制（生成→验证→不合格→重新生成）
- 实现 Human-in-the-Loop（标题选择、大纲选择）
- 实现 RAG 知识管理（Embedding → 向量存储 → 语义检索）
- 实现 Checkpointer 状态持久化（中断恢复）

---

## 2. 技术选型

| 技术 | 版本 | 用途 |
|------|------|------|
| LangGraph | 1.0+ | 工作流编排引擎 |
| LangChain | 1.0+ | AI组件框架 |
| langchain-openai | latest | LLM统一调用接口（兼容百炼） |
| langchain-community | latest | DashScope集成 |
| dashscope | latest | 阿里云百炼SDK |
| langgraph-checkpoint-postgres | latest | LangGraph状态持久化 |
| pgvector | latest | PostgreSQL向量扩展 |
| langchain-postgres | latest | LangChain PGVector集成 |

---

## 3. LangGraph StateGraph 设计

### 3.1 全局状态定义

```python
# backend/app/workflow/state.py

from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class ArticleState(TypedDict):
    """文章生成工作流的全局状态"""
    
    # ===== 项目基础信息 =====
    project_id: str
    topic: str
    
    # ===== 搜索阶段 =====
    search_keywords: list[str]           # 搜索关键词列表
    search_results: list[dict]           # 原始搜索结果
    crawled_documents: list[dict]        # 爬取的文档
    
    # ===== 过滤阶段 =====
    filtered_documents: list[dict]       # 过滤后的相关文档
    relevance_scores: dict[str, float]   # URL -> 相关性评分
    
    # ===== 知识提取（RAG） =====
    knowledge_chunks: list[dict]         # 切分后的知识块
    knowledge_embeddings: list[list[float]]  # 向量嵌入
    retrieved_knowledge: list[dict]      # 检索到的相关知识
    
    # ===== 标题阶段 =====
    generated_titles: list[dict]         # 生成的标题列表
    selected_title: Optional[str]        # 选中的标题
    title_feedback: Optional[str]        # 用户对标题的反馈
    
    # ===== 大纲配置 =====
    outline_config: Optional[dict]       # 大纲生成配置
    
    # ===== 大纲阶段 =====
    generated_outlines: list[dict]       # 生成的大纲列表
    selected_outline: Optional[dict]     # 选中的大纲
    outline_feedback: Optional[str]      # 用户对大纲的反馈
    
    # ===== 文章配置 =====
    article_config: Optional[dict]       # 文章最终配置
    
    # ===== 文章生成 =====
    generated_sections: list[dict]       # 生成的章节内容
    full_article: Optional[str]          # 完整文章
    article_summary: Optional[str]       # 文章总结
    article_faq: list[dict]              # FAQ列表
    
    # ===== 验证 =====
    verification_claims: list[dict]      # 需要验证的声明
    verification_results: list[dict]     # 验证结果
    verification_passed: bool            # 是否通过验证
    retry_count: int                     # 重试次数
    max_retries: int                     # 最大重试次数
    
    # ===== 流程控制 =====
    current_stage: str                   # 当前阶段
    error: Optional[str]                 # 错误信息
    messages: Annotated[list, add_messages]  # 消息历史（LangGraph内置）
```

### 3.2 工作流图定义

```python
# backend/app/workflow/graph.py

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command

from app.workflow.state import ArticleState
from app.workflow.nodes import (
    search_node,
    filter_node,
    extract_knowledge_node,
    generate_titles_node,
    wait_title_selection_node,
    generate_outlines_node,
    wait_outline_selection_node,
    generate_article_node,
    verify_article_node,
    format_output_node,
)
from app.workflow.edges import (
    route_after_verify,
    route_after_search,
)

def build_article_graph():
    """构建文章生成工作流图"""
    
    graph = StateGraph(ArticleState)
    
    # ========== 添加节点 ==========
    
    # 自动化节点
    graph.add_node("search", search_node)
    graph.add_node("filter", filter_node)
    graph.add_node("extract_knowledge", extract_knowledge_node)
    graph.add_node("generate_titles", generate_titles_node)
    graph.add_node("generate_outlines", generate_outlines_node)
    graph.add_node("generate_article", generate_article_node)
    graph.add_node("verify_article", verify_article_node)
    graph.add_node("format_output", format_output_node)
    
    # Human-in-the-Loop 节点
    graph.add_node("wait_title_selection", wait_title_selection_node)
    graph.add_node("wait_outline_selection", wait_outline_selection_node)
    
    # ========== 添加边 ==========
    
    # 起始 → 搜索
    graph.add_edge(START, "search")
    
    # 搜索 → 过滤
    graph.add_edge("search", "filter")
    
    # 过滤 → 知识提取
    graph.add_edge("filter", "extract_knowledge")
    
    # 知识提取 → 生成标题
    graph.add_edge("extract_knowledge", "generate_titles")
    
    # 生成标题 → 等待用户选择标题（HITL）
    graph.add_edge("generate_titles", "wait_title_selection")
    
    # 用户选择标题后 → 生成大纲
    graph.add_edge("wait_title_selection", "generate_outlines")
    
    # 生成大纲 → 等待用户选择大纲（HITL）
    graph.add_edge("generate_outlines", "wait_outline_selection")
    
    # 用户选择大纲后 → 生成文章
    graph.add_edge("wait_outline_selection", "generate_article")
    
    # 生成文章 → 验证文章
    graph.add_edge("generate_article", "verify_article")
    
    # 验证文章 → 条件路由（通过→格式化 / 不通过→重新生成）
    graph.add_conditional_edges(
        "verify_article",
        route_after_verify,
        {
            "pass": "format_output",        # 验证通过 → 格式化输出
            "retry": "generate_article",     # 验证不通过 → 重新生成
            "fail": END,                     # 超过重试次数 → 结束
        }
    )
    
    # 格式化输出 → 结束
    graph.add_edge("format_output", END)
    
    return graph


def create_compiled_graph():
    """创建可执行的工作流图（带Checkpointer）"""
    
    graph = build_article_graph()
    
    # PostgreSQL Checkpointer（持久化状态）
    checkpointer = PostgresSaver.from_conn_string(
        settings.DATABASE_URL.replace("+asyncpg", "")
    )
    
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["wait_title_selection", "wait_outline_selection"],
    )
    
    return compiled
```

### 3.3 工作流可视化

```
                        ┌─────────────────────────────────────┐
                        │           START                      │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │         search                      │
                        │  (LangChain: 搜索 + 爬取文档)        │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │         filter                      │
                        │  (LangChain: LLM评分 + 过滤)         │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │     extract_knowledge               │
                        │  (LangChain RAG: 切分→Embedding     │
                        │   → PGVector存储 → 语义检索)         │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │     generate_titles                 │
                        │  (LangChain: PromptTemplate + LLM)  │
                        └──────────────┬──────────────────────┘
                                       │
                   ┌────────────────────▼────────────────────┐
                   │  ⏸️ wait_title_selection (HITL)         │
                   │  暂停，等待用户选择标题                    │
                   │  Command(resume={"title_id": "xxx"})    │
                   └────────────────────┬────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │     generate_outlines               │
                        │  (LangChain: RAG检索 + LLM)         │
                        └──────────────┬──────────────────────┘
                                       │
                   ┌────────────────────▼────────────────────┐
                   │  ⏸️ wait_outline_selection (HITL)       │
                   │  暂停，等待用户选择大纲                    │
                   └────────────────────┬────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │     generate_article                │
                        │  (LangChain: 逐章节生成 + RAG参考)   │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │     verify_article                  │
                        │  (LangChain: 事实验证 + 网络搜索)    │
                        └──────────────┬──────────────────────┘
                                       │
                              ┌────────┴────────┐
                              │ 条件路由         │
                              └───┬────┬────┬───┘
                         pass ────┘    │    └──── retry
                        ┌──────────┐   │   ┌──────────────┐
                        │ format   │   │   │ 回到 generate │
                        │ output   │   │   │ (循环)        │
                        └────┬─────┘   │   └──────────────┘
                             │         │ fail → END
                        ┌────▼────┐    │
                        │  END    │◀───┘ (超过max_retries)
                        └─────────┘
```

---

## 4. 各节点实现

### 4.1 搜索节点

```python
# backend/app/workflow/nodes/search.py

from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.workflow.state import ArticleState
from app.services.search_service import search_service

async def search_node(state: ArticleState) -> dict:
    """搜索节点：生成关键词 → 搜索 → 爬取文档"""
    
    topic = state["topic"]
    
    # 1. 使用LLM生成搜索关键词
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    keyword_prompt = ChatPromptTemplate.from_template("""
    请根据以下主题生成5个搜索关键词：
    主题：{topic}
    请以JSON数组格式返回：["关键词1", "关键词2", ...]
    """)
    
    keyword_chain = keyword_prompt | llm
    keyword_response = await keyword_chain.ainvoke({"topic": topic})
    keywords = parse_json_array(keyword_response.content)
    
    # 2. 执行搜索
    all_results = []
    for keyword in keywords:
        results = await search_service.search(keyword)
        all_results.extend(results)
    
    # 去重
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique_results.append(r)
    
    # 3. 使用LangChain WebBaseLoader爬取内容
    documents = []
    for result in unique_results[:30]:
        try:
            loader = WebBaseLoader(result["url"])
            docs = await loader.aload()
            if docs:
                doc = docs[0]
                doc.metadata["source_url"] = result["url"]
                doc.metadata["title"] = result["title"]
                doc.metadata["snippet"] = result.get("snippet", "")
                documents.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                })
        except Exception as e:
            print(f"Failed to load {result['url']}: {e}")
    
    return {
        "search_keywords": keywords,
        "search_results": unique_results,
        "crawled_documents": documents,
        "current_stage": "search_completed",
    }
```

### 4.2 过滤节点

```python
# backend/app/workflow/nodes/filter.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.workflow.state import ArticleState

async def filter_node(state: ArticleState) -> dict:
    """过滤节点：LLM评估相关性"""
    
    topic = state["topic"]
    documents = state["crawled_documents"]
    
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    filter_prompt = ChatPromptTemplate.from_template("""
    请评估以下搜索结果与主题的相关性。
    
    主题：{topic}
    
    搜索结果：
    {documents}
    
    请对每篇文章评分(0-1)并说明原因。
    以JSON格式返回：
    [{{"index": 0, "score": 0.85, "reason": "..."}}]
    """)
    
    parser = JsonOutputParser()
    chain = filter_prompt | llm | parser
    
    # 分批处理
    filtered = []
    batch_size = 5
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        docs_text = "\n".join([
            f"[{j}] 标题: {d['metadata']['title']}\n内容: {d['content'][:1000]}"
            for j, d in enumerate(batch)
        ])
        
        result = await chain.ainvoke({
            "topic": topic,
            "documents": docs_text
        })
        
        for item in result:
            idx = item["index"]
            score = item["score"]
            if score >= 0.6 and idx < len(batch):
                doc = batch[idx]
                doc["relevance_score"] = score
                doc["filter_reason"] = item.get("reason", "")
                filtered.append(doc)
    
    # 按评分排序，取top 15
    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    filtered = filtered[:15]
    
    return {
        "filtered_documents": filtered,
        "current_stage": "filter_completed",
    }
```

### 4.3 知识提取节点（RAG核心）

```python
# backend/app/workflow/nodes/extract_knowledge.py

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_core.documents import Document
from app.workflow.state import ArticleState

async def extract_knowledge_node(state: ArticleState) -> dict:
    """知识提取节点：使用RAG管道处理知识"""
    
    project_id = state["project_id"]
    documents = state["filtered_documents"]
    
    # 1. 文本切分
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", "！", "？", "."],
    )
    
    all_chunks = []
    for doc in documents:
        chunks = text_splitter.split_text(doc["content"])
        for i, chunk in enumerate(chunks):
            all_chunks.append(Document(
                page_content=chunk,
                metadata={
                    "source_url": doc["metadata"]["source_url"],
                    "title": doc["metadata"]["title"],
                    "chunk_index": i,
                    "project_id": project_id,
                }
            ))
    
    # 2. 创建Embedding并存入PGVector
    embeddings = OpenAIEmbeddings(
        model="text-embedding-v3",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    # 使用项目ID作为collection名称，实现数据隔离
    collection_name = f"knowledge_{project_id.replace('-', '_')}"
    
    vectorstore = PGVector(
        embeddings,
        collection_name=collection_name,
        connection=settings.DATABASE_URL,
        use_jsonb=True,
    )
    
    # 清空旧数据（如果有）
    vectorstore.delete(collection_name=collection_name)
    
    # 批量添加文档
    await vectorstore.aadd_documents(all_chunks)
    
    # 3. 创建Retriever用于后续知识检索
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10},
    )
    
    # 4. 基于Topic检索相关知识
    retrieved_docs = await retriever.ainvoke(state["topic"])
    
    retrieved_knowledge = [
        {
            "content": doc.page_content,
            "source_url": doc.metadata.get("source_url", ""),
            "title": doc.metadata.get("title", ""),
        }
        for doc in retrieved_docs
    ]
    
    return {
        "knowledge_chunks": [{"content": c.page_content, "metadata": c.metadata} for c in all_chunks],
        "retrieved_knowledge": retrieved_knowledge,
        "current_stage": "extract_completed",
    }
```

### 4.4 标题生成节点

```python
# backend/app/workflow/nodes/generate_titles.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.workflow.state import ArticleState

async def generate_titles_node(state: ArticleState) -> dict:
    """标题生成节点"""
    
    topic = state["topic"]
    knowledge = state["retrieved_knowledge"]
    
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.8,  # 标题需要创造性
    )
    
    # 构建参考知识文本
    knowledge_text = "\n".join([
        f"- {k['content'][:200]}" for k in knowledge[:10]
    ])
    
    title_prompt = ChatPromptTemplate.from_template("""
    你是专业的内容编辑。请根据以下信息生成5个不同风格的文章标题。
    
    主题：{topic}
    
    参考知识：
    {knowledge}
    
    请生成5个标题，每个使用不同风格：
    1. 数字列表型（包含具体数字）
    2. 问题引导型（以问题开头）
    3. 权威专业型（体现深度）
    4. 情感共鸣型（引发共鸣）
    5. 对比冲突型（制造冲突）
    
    返回JSON：
    {{"titles": [{{"content": "标题", "style": "风格名", "reasoning": "理由"}}]}}
    """)
    
    parser = JsonOutputParser()
    chain = title_prompt | llm | parser
    
    result = await chain.ainvoke({
        "topic": topic,
        "knowledge": knowledge_text,
    })
    
    titles = result.get("titles", [])
    
    return {
        "generated_titles": titles,
        "current_stage": "title_generated",
    }
```

### 4.5 Human-in-the-Loop: 等待标题选择

```python
# backend/app/workflow/nodes/hitl.py

from langgraph.types import interrupt, Command
from app.workflow.state import ArticleState

async def wait_title_selection_node(state: ArticleState) -> dict:
    """暂停等待用户选择标题"""
    
    titles = state["generated_titles"]
    
    # 暂停工作流，等待用户输入
    human_input = interrupt({
        "action": "select_title",
        "titles": titles,
        "message": "请从以上标题中选择一个",
    })
    
    # 用户恢复时传入选择结果
    selected = human_input.get("selected_title")
    title_id = human_input.get("title_id")
    
    return {
        "selected_title": selected,
        "current_stage": "title_selected",
    }


async def wait_outline_selection_node(state: ArticleState) -> dict:
    """暂停等待用户选择大纲"""
    
    outlines = state["generated_outlines"]
    
    human_input = interrupt({
        "action": "select_outline",
        "outlines": outlines,
        "message": "请从以上大纲中选择一个",
    })
    
    selected = human_input.get("selected_outline")
    
    return {
        "selected_outline": selected,
        "outline_config": human_input.get("outline_config"),
        "current_stage": "outline_selected",
    }
```

### 4.6 文章生成节点

```python
# backend/app/workflow/nodes/generate_article.py

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.prompts import ChatPromptTemplate
from app.workflow.state import ArticleState

async def generate_article_node(state: ArticleState) -> dict:
    """文章生成节点：逐章节生成，每章节通过RAG检索相关知识"""
    
    topic = state["topic"]
    title = state["selected_title"]
    outline = state["selected_outline"]
    article_config = state.get("article_config", {})
    
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.7,
    )
    
    embeddings = OpenAIEmbeddings(
        model="text-embedding-v3",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    # 从向量库检索相关知识
    collection_name = f"knowledge_{state['project_id'].replace('-', '_')}"
    vectorstore = PGVector(
        embeddings,
        collection_name=collection_name,
        connection=settings.DATABASE_URL,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # 逐章节生成
    sections_content = []
    previous_context = ""
    
    for section in outline.get("sections", []):
        # 根据章节标题检索相关知识
        section_query = f"{title} {section['heading']} {section.get('description', '')}"
        relevant_docs = await retriever.ainvoke(section_query)
        
        knowledge_text = "\n".join([doc.page_content[:500] for doc in relevant_docs])
        
        section_prompt = ChatPromptTemplate.from_template("""
        请撰写文章的以下章节。
        
        文章标题：{title}
        主题：{topic}
        
        当前章节：{heading}
        章节描述：{description}
        子话题：{subtopics}
        目标字数：{word_count}字
        
        写作要求：
        - 可读性：{readability}
        - 风格：{tone}
        - 视角：{pov}
        
        参考知识：
        {knowledge}
        
        前文概要：{previous_context}
        
        请以Markdown格式输出本章节内容。
        """)
        
        chain = section_prompt | llm
        
        content = await chain.ainvoke({
            "title": title if isinstance(title, str) else title.get("content", ""),
            "topic": topic,
            "heading": section["heading"],
            "description": section.get("description", ""),
            "subtopics": ", ".join(section.get("subtopics", [])),
            "word_count": section.get("word_count", 300),
            "readability": article_config.get("readability", "general"),
            "tone": article_config.get("tone_of_voice", "professional"),
            "pov": article_config.get("point_of_view", "third_person"),
            "knowledge": knowledge_text,
            "previous_context": previous_context[:1000],
        })
        
        sections_content.append({
            "heading": section["heading"],
            "content": content.content,
        })
        previous_context = content.content[:500]
    
    # 组装完整文章
    title_text = title if isinstance(title, str) else title.get("content", "")
    full_article = f"# {title_text}\n\n"
    for section in sections_content:
        full_article += f"## {section['heading']}\n\n{section['content']}\n\n"
    
    return {
        "generated_sections": sections_content,
        "full_article": full_article,
        "retry_count": state.get("retry_count", 0) + 1,
        "current_stage": "article_generated",
    }
```

### 4.7 验证节点（循环关键）

```python
# backend/app/workflow/nodes/verify_article.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.workflow.state import ArticleState

async def verify_article_node(state: ArticleState) -> dict:
    """验证节点：检查文章可靠性、时效性、真实性"""
    
    article = state["full_article"]
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count > max_retries:
        return {
            "verification_passed": False,
            "error": "超过最大重试次数",
            "current_stage": "verification_failed",
        }
    
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    verify_prompt = ChatPromptTemplate.from_template("""
    请验证以下文章内容的可靠性和准确性。
    
    文章内容：
    {article}
    
    请检查：
    1. 事实准确性：数据和事实是否正确
    2. 时效性：信息是否过时
    3. 逻辑性：论证是否合理
    
    返回JSON：
    {{
        "claims": [
            {{"claim": "声明", "is_verified": true, "confidence": 0.9, "issue": "问题描述或null"}}
        ],
        "overall_score": 0.85,
        "passed": true,
        "issues": ["需要修正的问题列表"]
    }}
    """)
    
    parser = JsonOutputParser()
    chain = verify_prompt | llm | parser
    
    result = await chain.ainvoke({"article": article[:5000]})
    
    passed = result.get("passed", False) and result.get("overall_score", 0) >= 0.7
    
    return {
        "verification_claims": result.get("claims", []),
        "verification_results": result,
        "verification_passed": passed,
        "current_stage": "verification_completed",
    }


def route_after_verify(state: ArticleState) -> str:
    """验证后的路由逻辑"""
    if state.get("verification_passed"):
        return "pass"
    
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count >= max_retries:
        return "fail"
    
    return "retry"
```

---

## 5. LangChain RAG 管道详解

### 5.1 RAG 流程

```
文档加载 → 文本切分 → Embedding → 向量存储 → 语义检索 → 注入Prompt
(WebBaseLoader) (Splitter)  (DashScope)  (PGVector)   (Retriever)  (LLM)
```

### 5.2 知识库管理

```python
# backend/app/services/knowledge_service.py

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

class KnowledgeService:
    """RAG知识管理服务"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-v3",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    def get_vectorstore(self, project_id: str) -> PGVector:
        """获取项目的向量存储"""
        collection_name = f"knowledge_{project_id.replace('-', '_')}"
        return PGVector(
            self.embeddings,
            collection_name=collection_name,
            connection=settings.DATABASE_URL,
            use_jsonb=True,
        )
    
    async def add_documents(self, project_id: str, documents: list[Document]):
        """添加文档到知识库"""
        vectorstore = self.get_vectorstore(project_id)
        await vectorstore.aadd_documents(documents)
    
    async def search(self, project_id: str, query: str, k: int = 10) -> list[Document]:
        """语义检索"""
        vectorstore = self.get_vectorstore(project_id)
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return await retriever.ainvoke(query)
    
    async def cleanup(self, project_id: str):
        """清理项目知识数据"""
        vectorstore = self.get_vectorstore(project_id)
        collection_name = f"knowledge_{project_id.replace('-', '_')}"
        vectorstore.delete(collection_name=collection_name)

knowledge_service = KnowledgeService()
```

### 5.3 为什么要用RAG而不是直接塞全文？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **直接塞全文**（当前方案） | 简单直接 | 超出上下文限制、信息噪声大、成本高 |
| **RAG检索**（新方案） | 精准召回相关知识、成本可控、可扩展 | 需要额外基础设施 |

对于我们的项目，参考文章可能有15篇，每篇5000字，总计7.5万字。直接塞入Prompt：
- 超出大多数模型的有效注意力范围
- Token成本极高
- 关键信息可能被淹没

RAG方案只在生成每个章节时检索最相关的5-10个段落（约5000字），大幅降低成本并提高质量。

---

## 6. FastAPI 集成

### 6.1 API端点

```python
# backend/app/api/endpoints/workflow.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from app.workflow.graph import create_compiled_graph

router = APIRouter()

# 全局图实例
workflow_graph = None

def get_graph():
    global workflow_graph
    if workflow_graph is None:
        workflow_graph = create_compiled_graph()
    return workflow_graph

@router.post("/projects/{project_id}/workflow/start")
async def start_workflow(project_id: str, topic: str):
    """启动工作流"""
    graph = get_graph()
    
    config = {"configurable": {"thread_id": project_id}}
    
    initial_state = {
        "project_id": project_id,
        "topic": topic,
        "max_retries": 3,
        "retry_count": 0,
        "messages": [],
    }
    
    # 运行到第一个interrupt点
    result = await graph.ainvoke(initial_state, config)
    
    return {
        "project_id": project_id,
        "status": result.get("current_stage"),
        "data": {
            "titles": result.get("generated_titles", []),
        }
    }

@router.post("/projects/{project_id}/workflow/resume")
async def resume_workflow(
    project_id: str,
    action: str,        # "select_title" | "select_outline" | "save_config"
    payload: dict,
):
    """恢复工作流（用户交互后）"""
    graph = get_graph()
    config = {"configurable": {"thread_id": project_id}}
    
    # 构建恢复命令
    resume_data = Command(resume=payload)
    
    result = await graph.ainvoke(resume_data, config)
    
    return {
        "project_id": project_id,
        "status": result.get("current_stage"),
        "data": _extract_response_data(result),
    }

@router.get("/projects/{project_id}/workflow/state")
async def get_workflow_state(project_id: str):
    """获取工作流当前状态"""
    graph = get_graph()
    config = {"configurable": {"thread_id": project_id}}
    
    state = await graph.aget_state(config)
    
    return {
        "project_id": project_id,
        "current_stage": state.values.get("current_stage"),
        "values": _extract_response_data(state.values),
        "next": state.next,  # 下一个要执行的节点
    }

def _extract_response_data(state_values: dict) -> dict:
    """提取返回给前端的数据"""
    return {
        "topic": state_values.get("topic"),
        "titles": state_values.get("generated_titles"),
        "selected_title": state_values.get("selected_title"),
        "outlines": state_values.get("generated_outlines"),
        "selected_outline": state_values.get("selected_outline"),
        "article": state_values.get("full_article"),
        "verification": state_values.get("verification_results"),
        "current_stage": state_values.get("current_stage"),
    }
```

---

## 7. 数据库变更

### 7.1 添加PGVector扩展

```sql
-- 在PostgreSQL中启用pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- LangGraph Checkpointer需要的表（由langgraph-checkpoint-postgres自动创建）
-- 不需要手动创建
```

### 7.2 更新requirements.txt

```txt
# backend/requirements.txt (新增)

# LangChain生态
langchain>=1.0.0
langchain-core>=1.0.0
langchain-community>=0.3.0
langchain-openai>=0.3.0
langchain-postgres>=0.0.0
langchain-text-splitters>=0.3.0

# LangGraph
langgraph>=1.0.0
langgraph-checkpoint-postgres>=0.1.0

# 向量数据库
pgvector>=0.3.0

# DashScope（备用，主要用OpenAI兼容接口）
dashscope>=1.20.0
```

---

## 8. 优势对比

### 8.1 与Spec-004~013原方案的对比

| 维度 | 原方案（手动编排） | 新方案（LangGraph + RAG） |
|------|-------------------|--------------------------|
| **知识利用** | 全文塞入Prompt | RAG精准检索，每次只注入相关知识 |
| **内容验证** | 一次性验证，不通过也输出 | 循环验证，不通过自动重新生成 |
| **状态管理** | 手动存数据库+Redis | LangGraph Checkpointer自动持久化 |
| **中断恢复** | 自定义恢复逻辑 | Checkpoint自动恢复，零代码 |
| **用户交互** | 暂停API+轮询 | interrupt()原生支持 |
| **Prompt管理** | 字符串散落各处 | PromptTemplate统一管理 |
| **代码量** | 大量胶水代码 | 图定义清晰，节点独立 |
| **可观测性** | 需要自建 | 可接入LangSmith追踪全链路 |
| **Token成本** | 高（全文塞入） | 低（RAG按需检索） |
| **文章质量** | 一般 | 更高（精准知识 + 循环验证） |

---

## 9. 验收标准

### 9.1 工作流验收

- [ ] StateGraph 可正确编译和运行
- [ ] 各节点按顺序执行
- [ ] 条件边正确路由（验证通过/重试/失败）
- [ ] interrupt() 正确暂停工作流
- [ ] Command(resume=...) 正确恢复工作流
- [ ] Checkpointer 正确持久化和恢复状态

### 9.2 RAG 验收

- [ ] 文档正确切分为chunks
- [ ] Embedding正确生成并存储到PGVector
- [ ] 语义检索返回相关结果
- [ ] 不同项目的知识库数据隔离
- [ ] 项目结束后可清理知识数据

### 9.3 质量验收

- [ ] 生成的文章引用了知识库中的相关信息
- [ ] 验证不通过时可自动重新生成
- [ ] 重试次数限制生效
- [ ] Token消耗比原方案降低30%+

### 9.4 API 验收

- [ ] /workflow/start 可启动工作流
- [ ] /workflow/resume 可恢复工作流
- [ ] /workflow/state 可查询状态
- [ ] WebSocket实时推送进度
