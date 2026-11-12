from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import LLMProvider, LLMUnavailable
from app.services.llm.ollama import OllamaProvider

__all__ = ["LLMProvider", "LLMUnavailable", "get_llm_provider"]


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    return OllamaProvider(s.ollama_base_url, s.llm_model)
