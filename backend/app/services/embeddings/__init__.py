from functools import lru_cache

from app.core.config import get_settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.providers import HashingProvider, SentenceTransformerProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    s = get_settings()
    if s.embedding_provider == "hash":
        return HashingProvider()
    return SentenceTransformerProvider(s.embedding_model)
