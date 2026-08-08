"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe, environment-driven defaults."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "TraceCommerce RAG Agent"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    database_url: str = "sqlite+aiosqlite:///./tracecommerce.db"
    jwt_secret_key: str = "development-only-secret-change-before-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_collection: str = "tracecommerce_chunks"
    vector_store_provider: str = "milvus"

    llm_provider: str = "openai_compatible"
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 60.0

    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 16

    reranker_provider: str = "cross_encoder"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"

    retrieval_top_k: int = 12
    rerank_top_k: int = 5
    min_retrieval_score: float = 0.35
    min_evidence_score: float = 0.45

    shopify_allowed_prefixes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "https://help.shopify.com/zh-CN/manual/international",
            "https://help.shopify.com/zh-CN/manual/markets",
            "https://help.shopify.com/zh-CN/manual/shipping-and-delivery",
            "https://help.shopify.com/zh-CN/manual/taxes",
            "https://help.shopify.com/zh-CN/manual/fulfillment/managing-orders/returns",
            "https://help.shopify.com/zh-CN/manual/fulfillment/managing-orders/refunding-orders",
            "https://help.shopify.com/zh-CN/manual/fulfillment/setup/order-status-page",
            "https://help.shopify.com/zh-CN/manual/fulfillment/managing-orders/order-status",
        ]
    )
    crawler_user_agent: str = (
        "Mozilla/5.0 (compatible; TraceCommerceKnowledgeBot/1.0; +local educational RAG project)"
    )
    crawler_timeout_seconds: float = 20.0
    crawler_delay_seconds: float = 1.0
    crawler_max_pages: int = 30
    crawler_max_depth: int = 2
    max_upload_bytes: int = 10 * 1024 * 1024

    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-before-running"

    @field_validator("cors_origins", "shopify_allowed_prefixes", mode="before")
    @classmethod
    def parse_csv_list(cls, value: object) -> object:
        """Allow comma-separated lists in environment variables."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        """Normalize API prefix to a single leading slash."""
        return "/" + value.strip("/")


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""
    return Settings()
