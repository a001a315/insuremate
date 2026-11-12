"""ChromaDB wrapper. Vectors only; chunk text and all structured data live in PostgreSQL."""
import threading
import uuid

from app.core.config import get_settings

COLLECTION = "policy_chunks"


_client_lock = threading.Lock()
_client_instance = None


def _client():
    """Create the Chroma client once. Chroma's client initialisation is not thread-safe, so concurrent
    first requests (e.g. indexing in a background task while the settings page loads) must be serialised."""
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                import chromadb
                path = get_settings().chroma_path
                _client_instance = chromadb.EphemeralClient() if path == ":memory:" else chromadb.PersistentClient(path=path)
    return _client_instance


def _collection():
    return _client().get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def reset_vector_store() -> None:
    try:
        _client().delete_collection(COLLECTION)
    except Exception:
        pass


def add_chunks(ids: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
    if ids:
        _collection().upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)


def delete_document(user_id: uuid.UUID, document_id: uuid.UUID) -> None:
    _collection().delete(where={"$and": [{"user_id": str(user_id)}, {"document_id": str(document_id)}]})


def query(user_id: uuid.UUID, embedding: list[float], k: int, policy_ids: list[uuid.UUID] | None) -> list[tuple[str, float]]:
    """Returns (chunk_id, similarity). The user filter is mandatory and applied inside the vector query."""
    conds: list[dict] = [{"user_id": str(user_id)}]
    if policy_ids is not None:
        if not policy_ids:
            return []
        conds.append({"policy_id": {"$in": [str(p) for p in policy_ids]}} if len(policy_ids) > 1
                     else {"policy_id": str(policy_ids[0])})
    col = _collection()
    if col.count() == 0:
        return []
    where = conds[0] if len(conds) == 1 else {"$and": conds}
    res = col.query(query_embeddings=[embedding], n_results=k, where=where)
    ids, dists = res["ids"][0], res["distances"][0]
    return [(i, 1.0 - d) for i, d in zip(ids, dists)]


def stats() -> dict:
    try:
        return {"ok": True, "vectors": _collection().count()}
    except Exception as e:
        return {"ok": False, "vectors": 0, "detail": f"{type(e).__name__}"}
