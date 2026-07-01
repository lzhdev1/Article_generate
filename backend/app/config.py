# backend/app/config.py

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 应用配置
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"

    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/article_generator"

    # Redis配置
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery配置
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # 阿里云百炼 API
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_MODEL: str = "qwen-max"
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v3"

    # Google Custom Search API
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_CX: str = ""  # Custom Search Engine ID
    GOOGLE_SEARCH_ENDPOINT: str = "https://www.googleapis.com/customsearch/v1"

    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
