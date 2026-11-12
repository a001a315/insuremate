from abc import ABC, abstractmethod
from collections.abc import Iterator

Message = dict[str, str]  # {"role": "system"|"user"|"assistant", "content": "..."}


class LLMUnavailable(Exception):
    """The configured model server cannot be reached or the model is missing."""


class LLMProvider(ABC):
    """Swap in another local model server by implementing this interface; RAG code only sees this."""

    model: str

    @abstractmethod
    def generate(self, messages: list[Message]) -> str: ...

    @abstractmethod
    def stream(self, messages: list[Message]) -> Iterator[str]: ...

    @abstractmethod
    def health(self) -> dict: ...
