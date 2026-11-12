"""Text extraction: PyMuPDF for PDFs (OCR fallback per page), python-docx for DOCX, Tesseract for images."""
import io
from dataclasses import dataclass
from pathlib import Path

MIN_TEXT_CHARS = 40  # below this a PDF page is treated as scanned


class ExtractionError(Exception):
    """Carries a message safe to show the user."""


@dataclass
class Page:
    number: int
    text: str


def _ocr_image(img) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(img)
    except Exception as e:  # tesseract binary missing, corrupt image, ...
        raise ExtractionError(f"OCR failed ({type(e).__name__}). Is Tesseract installed?") from e


def extract_pdf(path: Path) -> list[Page]:
    import pymupdf as fitz
    try:
        doc = fitz.open(path)
    except Exception as e:
        raise ExtractionError("This PDF could not be opened. It may be corrupted or password-protected.") from e
    if doc.needs_pass:
        raise ExtractionError("This PDF is password-protected. Remove the password and upload it again.")
    pages: list[Page] = []
    from PIL import Image
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if len(text) < MIN_TEXT_CHARS:
            pix = page.get_pixmap(dpi=200)
            text = _ocr_image(Image.open(io.BytesIO(pix.tobytes("png")))).strip()
        pages.append(Page(i, text))
    return pages


def extract_docx(path: Path) -> list[Page]:
    import docx
    try:
        d = docx.Document(str(path))
    except Exception as e:
        raise ExtractionError("This Word document could not be read. It may be corrupted.") from e
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return [Page(1, "\n".join(parts))]  # DOCX has no fixed pagination


def extract_image(path: Path) -> list[Page]:
    from PIL import Image
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        raise ExtractionError("This image could not be read.") from e
    return [Page(1, _ocr_image(img).strip())]


def extract_pages(path: Path, mime_type: str) -> list[Page]:
    if mime_type == "application/pdf":
        pages = extract_pdf(path)
    elif mime_type.endswith("wordprocessingml.document"):
        pages = extract_docx(path)
    elif mime_type.startswith("image/"):
        pages = extract_image(path)
    else:
        raise ExtractionError(f"Unsupported file type: {mime_type}")
    if not any(p.text.strip() for p in pages):
        raise ExtractionError("No readable text was found in this document, even after OCR.")
    return pages
