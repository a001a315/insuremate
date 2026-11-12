"""Environment-based configuration. Model names are never hardcoded elsewhere."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "InsureMate AI"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://insuremate:insuremate@localhost:5432/insuremate"

    # Auth
    secret_key: str = Field(default="change-me-in-production-please-32+chars")
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:5173"

    # Storage / uploads
    upload_dir: str = "./storage/uploads"
    max_upload_mb: int = 25
    allowed_extensions: str = "pdf,docx,png,jpg,jpeg"

    scheduler_enabled: bool = True

    # AI
    embedding_provider: str = "sentence-transformers"  # or "hash" (tests only)
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b-instruct"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chroma_path: str = "./storage/chroma"
    chunk_size: int = 900
    chunk_overlap: int = 150
    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extension_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",")}


@lru_cache
def get_settings() -> Settings:
    return Settings()
