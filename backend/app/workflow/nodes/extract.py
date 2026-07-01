# backend/app/workflow/nodes/extract.py

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.workflow.state import ArticleState
from app.workflow.llm import get_embeddings


async def extract_knowledge_node(state: ArticleState) -> dict:
    """知识提取节点：将过滤后的文档切分为chunks，存入向量库，然后检索"""
    project_id = state["project_id"]
    documents = state["filtered_documents"]

    if not documents:
        return {
            "retrieved_knowledge": [],
            "current_stage": "extract_completed",
            "messages": [],
        }

    # 1. 文本切分
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", "！", "？", ". "],
    )

    all_chunks: list[Document] = []
    for doc in documents:
        chunks = splitter.split_text(doc.get("content", ""))
        for i, chunk in enumerate(chunks):
            all_chunks.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source_url": doc.get("url", ""),
                        "title": doc.get("title", ""),
                        "chunk_index": i,
                        "project_id": project_id,
                    },
                )
            )

    # 2. 存入PGVector
    try:
        from langchain_postgres import PGVector

        embeddings = get_embeddings()
        collection_name = f"knowledge_{project_id.replace('-', '_')}"

        vectorstore = PGVector(
            embeddings,
            collection_name=collection_name,
            connection=state.get("_db_url", ""),
            use_jsonb=True,
        )

        await vectorstore.aadd_documents(all_chunks)

        # 3. 检索
        retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
        retrieved_docs = await retriever.ainvoke(state["topic"])

        retrieved_knowledge = [
            {
                "content": doc.page_content,
                "source_url": doc.metadata.get("source_url", ""),
                "title": doc.metadata.get("title", ""),
            }
            for doc in retrieved_docs
        ]
    except Exception as e:
        print(f"[extract] PGVector failed, falling back to simple extraction: {e}")
        # 回退：直接用文档内容作为知识
        retrieved_knowledge = [
            {"content": doc.get("content", "")[:1500], "source_url": doc.get("url", ""), "title": doc.get("title", "")}
            for doc in documents[:10]
        ]

    return {
        "retrieved_knowledge": retrieved_knowledge,
        "current_stage": "extract_completed",
        "messages": [],
    }
