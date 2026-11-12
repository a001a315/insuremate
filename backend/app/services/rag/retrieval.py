import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document, DocumentChunk
from app.services.embeddings import get_embedding_provider
from app.services.rag import vectorstore


@dataclass
class Retrieved:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    policy_id: uuid.UUID | None
    document_name: str
    page_number: int | None
    text: str
    score: float


def retrieve(db: Session, user_id: uuid.UUID, question: str, policy_ids: list[uuid.UUID] | None,
             k: int | None = None, min_score: float | None = None) -> list[Retrieved]:
    s = get_settings()
    k = k or s.retrieval_top_k
    min_score = s.retrieval_min_score if min_score is None else min_score
    qvec = get_embedding_provider().embed_query(question)
    hits = vectorstore.query(user_id, qvec, k * 2, policy_ids)
    out: list[Retrieved] = []
    seen_hashes: set[str] = set()
    for chunk_id, score in sorted(hits, key=lambda h: -h[1]):
        if score < min_score:
            continue
        chunk = db.get(DocumentChunk, uuid.UUID(chunk_id))
        # Defense in depth: re-verify ownership and liveness against PostgreSQL.
        if chunk is None or chunk.user_id != user_id or chunk.content_hash in seen_hashes:
            continue
        doc = db.get(Document, chunk.document_id)
        if doc is None or doc.user_id != user_id or doc.deleted_at is not None:
            continue
        if policy_ids is not None and doc.policy_id not in policy_ids:
            continue
        seen_hashes.add(chunk.content_hash)
        out.append(Retrieved(chunk.id, doc.id, doc.policy_id, doc.original_name, chunk.page_number, chunk.text, score))
        if len(out) >= k:
            break
    return out
