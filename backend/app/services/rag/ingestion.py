"""Document ingestion: extract → clean/chunk → embed → store in Chroma. Runs in a background task."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models import Document, DocumentChunk
from app.services.embeddings import get_embedding_provider
from app.services.rag import vectorstore
from app.services.rag.chunking import chunk_pages
from app.services.rag.extraction import ExtractionError, extract_pages

log = logging.getLogger("insuremate.ingestion")  # never log document text


def _set(db: Session, doc: Document, status: str, error: str | None = None) -> None:
    doc.index_status = status
    doc.index_error = error
    db.commit()


def ingest_document(document_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """(Re)index one document. Safe to call repeatedly: old chunks and vectors are replaced."""
    s = get_settings()
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if doc is None or doc.user_id != user_id or doc.deleted_at is not None:
            return
        try:
            from pathlib import Path
            path = Path(s.upload_dir) / str(doc.user_id) / doc.stored_name
            if not path.exists():
                raise ExtractionError("The stored file is missing.")
            _set(db, doc, "extracting_text")
            pages = extract_pages(path, doc.mime_type)
            doc.page_count = len(pages)

            _set(db, doc, "processing")
            chunks = chunk_pages(pages, s.chunk_size, s.chunk_overlap)
            if not chunks:
                raise ExtractionError("The document contained too little text to index.")

            _set(db, doc, "generating_embeddings")
            # replace any previous index for this document (re-indexing)
            vectorstore.delete_document(doc.user_id, doc.id)
            for old in db.query(DocumentChunk).filter_by(document_id=doc.id, user_id=doc.user_id):
                db.delete(old)
            db.commit()

            vectors = get_embedding_provider().embed_documents([c.text for c in chunks])
            rows = [DocumentChunk(user_id=doc.user_id, document_id=doc.id, chunk_index=c.index,
                                  page_number=c.page_number, text=c.text, content_hash=c.content_hash)
                    for c in chunks]
            db.add_all(rows)
            db.flush()
            meta = [{"user_id": str(doc.user_id), "policy_id": str(doc.policy_id) if doc.policy_id else "",
                     "document_id": str(doc.id), "document_name": doc.original_name,
                     "page_number": c.page_number, "chunk_number": c.index, "category": doc.category}
                    for c in chunks]
            vectorstore.add_chunks([str(r.id) for r in rows], vectors, meta)
            doc.indexed_at = datetime.now(timezone.utc)
            _set(db, doc, "indexed")
        except ExtractionError as e:
            db.rollback()
            _set(db, doc, "failed", str(e))
        except Exception as e:  # unexpected: record a safe message, keep details out of user-facing text
            db.rollback()
            log.exception("ingestion failed for document %s", document_id)
            msg = "Indexing failed. Check that the embedding model is available and try re-indexing."
            _set(db, doc, "failed", f"{msg} ({type(e).__name__})")
