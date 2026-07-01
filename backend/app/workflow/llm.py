# backend/app/workflow/llm.py

from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(temperature: float = 0.7, enable_search: bool = False) -> ChatOpenAI:
    """获取LLM实例（使用阿里云百炼兼容OpenAI接口）"""
    # 阿里云百炼的联网搜索通过 extra_body 传递
    client_kwargs = {}
    if enable_search:
        client_kwargs["extra_body"] = {"enable_search": True}

    return ChatOpenAI(
        model=settings.DASHSCOPE_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=temperature,
        **client_kwargs,
    )


def get_embeddings():
    """获取 Embedding 实例"""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.DASHSCOPE_EMBEDDING_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
