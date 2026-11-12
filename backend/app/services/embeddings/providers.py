import hashlib
import math
import re

from app.services.embeddings.base import EmbeddingProvider

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str):
        self.name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._load().encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        prefix = BGE_QUERY_PREFIX if "bge" in self.name.lower() else ""
        return self._load().encode([prefix + text], normalize_embeddings=True, show_progress_bar=False)[0].tolist()


class HashingProvider(EmbeddingProvider):
    """Deterministic bag-of-words embedder for automated tests only (EMBEDDING_PROVIDER=hash).
    Not semantic; never used unless explicitly configured."""
    name = "hashing-test-embedder"
    DIM = 512

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.DIM
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            if len(tok) < 3:
                continue
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)
