import json
from collections.abc import Iterator

import httpx

from app.services.llm.base import LLMProvider, LLMUnavailable, Message


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _payload(self, messages: list[Message], stream: bool) -> dict:
        return {"model": self.model, "messages": messages, "stream": stream,
                "options": {"temperature": 0.1}}

    def _unavailable(self, e: Exception) -> LLMUnavailable:
        return LLMUnavailable(
            f"The local AI model server (Ollama at {self.base_url}) is not reachable. "
            f"Start Ollama and make sure the model '{self.model}' is pulled.")

    def generate(self, messages: list[Message]) -> str:
        try:
            r = httpx.post(f"{self.base_url}/api/chat", json=self._payload(messages, False), timeout=self.timeout)
        except httpx.HTTPError as e:
            raise self._unavailable(e) from e
        if r.status_code == 404:
            raise LLMUnavailable(f"Model '{self.model}' is not installed. Run: ollama pull {self.model}")
        r.raise_for_status()
        return r.json()["message"]["content"]

    def stream(self, messages: list[Message]) -> Iterator[str]:
        try:
            with httpx.stream("POST", f"{self.base_url}/api/chat", json=self._payload(messages, True),
                              timeout=self.timeout) as r:
                if r.status_code == 404:
                    raise LLMUnavailable(f"Model '{self.model}' is not installed. Run: ollama pull {self.model}")
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if tok := chunk.get("message", {}).get("content"):
                        yield tok
                    if chunk.get("done"):
                        break
        except httpx.HTTPError as e:
            raise self._unavailable(e) from e

    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            r.raise_for_status()
        except httpx.HTTPError:
            return {"reachable": False, "model": self.model, "model_available": False,
                    "detail": f"Cannot reach Ollama at {self.base_url}"}
        names = {m.get("name", "") for m in r.json().get("models", [])}
        available = self.model in names or f"{self.model}:latest" in names
        return {"reachable": True, "model": self.model, "model_available": available,
                "detail": "ok" if available else f"Model not pulled. Run: ollama pull {self.model}"}
