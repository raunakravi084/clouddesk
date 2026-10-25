"""Application settings (CLAUDE.md §10.1).

Every value comes from the environment or `.env`. `get_settings()` is cached,
so restart the server after changing `.env`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Runtime
    demo_mode: bool = True
    environment: str = "local"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"

    # Auth
    jwt_secret: SecretStr = SecretStr("dev-only-change-me")
    supabase_jwt_secret: SecretStr | None = None

    # Persistence
    database_url: str = "sqlite+aiosqlite:///./data/support.db"
    checkpoint_db_path: str = "./data/checkpoints.db"

    # Redis
    redis_url: str = ""
    use_fake_redis: bool = False

    # LLM
    llm_provider: str = "fake"
    llm_api_key: SecretStr | None = None
    llm_model: str = ""

    # Embeddings and vector store
    embedding_provider: str = "fake"
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=384, gt=0)
    vector_store: Literal["memory", "qdrant"] = "memory"
    qdrant_url: str = ""
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "clouddesk_knowledge"

    # Policy
    approval_required_for_refunds: bool = True
    max_refund_without_approval: float = Field(default=0, ge=0)
    tool_timeout_seconds: float = Field(default=30, gt=0)
    rate_limit_per_minute: int = Field(default=120, gt=0)
    sample_data_dir: str = "./sample_data"

    # Observability
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None
    langchain_project: str = "clouddesk-support"

    @property
    def effective_jwt_secret(self) -> str:
        """Supabase JWT secret when set, otherwise the local JWT secret (CLAUDE.md §9)."""
        if self.supabase_jwt_secret and self.supabase_jwt_secret.get_secret_value():
            return self.supabase_jwt_secret.get_secret_value()
        return self.jwt_secret.get_secret_value()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_fakeredis(self) -> bool:
        """Empty `REDIS_URL` means fakeredis (CLAUDE.md §10.1)."""
        return self.use_fake_redis or not self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
