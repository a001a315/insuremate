import io

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

from app.services.rag.chunking import chunk_pages
from app.services.rag.extraction import ExtractionError, Page, extract_pages
from tests.conftest import make_pdf, new_policy, upload


def test_upload_validation(client, auth_headers):
    assert upload(client, auth_headers, b"hello", name="x.exe").status_code == 422
    assert upload(client, auth_headers, b"not a pdf at all", name="x.pdf").status_code == 422   # content/extension mismatch
    assert upload(client, auth_headers, b"", name="x.pdf").status_code == 422
    assert upload(client, auth_headers, make_pdf(), category="weird").status_code == 422


def test_upload_size_limit(client, auth_headers, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert upload(client, auth_headers, make_pdf()).status_code == 422


def test_pdf_indexing_status_and_download(client, auth_headers):
    p = new_policy(client, auth_headers)
    r = upload(client, auth_headers, make_pdf(), policy_id=p["id"])
    assert r.status_code == 201
    d = client.get(f"/api/documents/{r.json()['id']}", headers=auth_headers).json()
    assert d["index_status"] == "indexed" and d["page_count"] == 3   # background task ran
    dl = client.get(f"/api/documents/{d['id']}/download", headers=auth_headers)
    assert dl.status_code == 200 and dl.content.startswith(b"%PDF")
    assert "inline" in client.get(f"/api/documents/{d['id']}/preview", headers=auth_headers).headers["content-disposition"]


def test_non_policy_documents_are_not_indexed(client, auth_headers):
    d = upload(client, auth_headers, make_pdf(), category="hospital_bill").json()
    assert d["index_status"] == "uploaded"


def test_failed_extraction_has_meaningful_message(client, auth_headers):
    blank = fitz.open()
    blank.new_page()
    r = upload(client, auth_headers, blank.tobytes()).json()
    d = client.get(f"/api/documents/{r['id']}", headers=auth_headers).json()
    assert d["index_status"] == "failed" and "No readable text" in d["index_error"]


def test_delete_removes_chunks_vectors_and_file(client, auth_headers):
    from app.database.session import SessionLocal
    from app.models import DocumentChunk
    from app.services.rag import vectorstore
    p = new_policy(client, auth_headers)
    d = upload(client, auth_headers, make_pdf(), policy_id=p["id"]).json()
    assert vectorstore.stats()["vectors"] > 0
    assert client.delete(f"/api/documents/{d['id']}", headers=auth_headers).status_code == 204
    assert vectorstore.stats()["vectors"] == 0
    with SessionLocal() as db:
        assert db.query(DocumentChunk).count() == 0
    assert client.get(f"/api/documents/{d['id']}/download", headers=auth_headers).status_code == 404


def test_reindex_replaces_not_duplicates(client, auth_headers):
    from app.services.rag import vectorstore
    p = new_policy(client, auth_headers)
    d = upload(client, auth_headers, make_pdf(), policy_id=p["id"]).json()
    n = vectorstore.stats()["vectors"]
    r = client.post(f"/api/documents/{d['id']}/reindex", headers=auth_headers)
    assert r.status_code == 200
    assert vectorstore.stats()["vectors"] == n
    assert client.get(f"/api/documents/{d['id']}", headers=auth_headers).json()["index_status"] == "indexed"


def test_extract_docx_and_ocr_scanned_pdf(tmp_path):
    import docx
    f = tmp_path / "a.docx"
    d = docx.Document()
    d.add_paragraph("Co-payment of 20 percent applies to all claims.")
    d.save(f)
    pages = extract_pages(f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "20 percent" in pages[0].text

    # image-only PDF forces the OCR fallback
    img = Image.new("RGB", (1200, 300), "white")
    ImageDraw.Draw(img).text((40, 100), "Room rent limit is five thousand rupees per day", fill="black",
                             font=ImageFont.load_default(size=40))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    pdf = fitz.open()
    page = pdf.new_page(width=700, height=200)
    page.insert_image(page.rect, stream=buf.getvalue())
    path = tmp_path / "scan.pdf"
    pdf.save(str(path))
    text = extract_pages(path, "application/pdf")[0].text.lower()
    assert "room rent" in text


def test_chunking_keeps_pages_overlap_and_dedupes():
    s1 = "Alpha clause one is long enough. " * 30
    pages = [Page(1, s1), Page(2, "Second page content that is unique and long enough to keep."),
             Page(3, "Second page content that is unique and long enough to keep.")]
    chunks = chunk_pages(pages, size=300, overlap=60)
    assert {c.page_number for c in chunks} >= {1, 2}
    assert [c.page_number for c in chunks].count(3) == 0   # duplicate dropped
    assert all(len(c.text) <= 300 + 60 for c in chunks)
    assert len({c.content_hash for c in chunks}) == len(chunks)
    try:
        chunk_pages(pages, 100, 100)
        assert False
    except ValueError:
        pass
