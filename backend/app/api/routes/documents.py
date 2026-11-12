import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.document import INDEXED_CATEGORIES, DocumentOut
from app.services.documents.service import DocumentService
from app.services.rag.ingestion import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DocumentService:
    return DocumentService(db, user.id)


@router.get("", response_model=list[DocumentOut])
def list_documents(q: str | None = None, category: str | None = None, policy_id: uuid.UUID | None = None,
                   patient_id: uuid.UUID | None = None, svc: DocumentService = Depends(_svc)):
    return svc.repo.list_filtered(q, category, policy_id, patient_id)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(background: BackgroundTasks, file: UploadFile = File(...), category: str = Form("other"),
                          policy_id: uuid.UUID | None = Form(None),
                          patient_id: uuid.UUID | None = Form(None), svc: DocumentService = Depends(_svc)):
    doc = await svc.upload(file, category, policy_id, patient_id)
    if category in INDEXED_CATEGORIES:  # insurance policy documents go through the RAG pipeline
        background.add_task(ingest_document, doc.id, svc.user_id)
    return doc


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: uuid.UUID, svc: DocumentService = Depends(_svc)):
    return svc.get(doc_id)


def _file(svc: DocumentService, doc_id: uuid.UUID, disposition: str) -> FileResponse:
    doc = svc.get(doc_id)
    return FileResponse(svc.path_for(doc), media_type=doc.mime_type, filename=doc.original_name,
                        content_disposition_type=disposition)


@router.get("/{doc_id}/download")
def download(doc_id: uuid.UUID, svc: DocumentService = Depends(_svc)):
    return _file(svc, doc_id, "attachment")


@router.get("/{doc_id}/preview")
def preview(doc_id: uuid.UUID, svc: DocumentService = Depends(_svc)):
    return _file(svc, doc_id, "inline")


@router.post("/{doc_id}/reindex", response_model=DocumentOut)
def reindex(doc_id: uuid.UUID, background: BackgroundTasks, svc: DocumentService = Depends(_svc)):
    doc = svc.get(doc_id)
    doc.index_status, doc.index_error = "uploaded", None
    svc.db.commit()
    background.add_task(ingest_document, doc.id, svc.user_id)
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: uuid.UUID, svc: DocumentService = Depends(_svc)):
    svc.delete(doc_id)
    return Response(status_code=204)
