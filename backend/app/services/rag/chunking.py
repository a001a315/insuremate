import hashlib
import re
from dataclasses import dataclass

from app.services.rag.extraction import Page


@dataclass
class Chunk:
    index: int
    page_number: int
    text: str
    content_hash: str


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n(?=[a-z])", "", text)          # de-hyphenate line wraps
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_units(text: str) -> list[str]:
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        units.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", para) if s.strip())
    return units


def chunk_pages(pages: list[Page], size: int, overlap: int) -> list[Chunk]:
    """Sentence-aware chunks that never cross page boundaries, so page citations stay exact."""
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
    chunks: list[Chunk] = []
    seen: set[str] = set()

    def emit(page: int, text: str):
        text = text.strip()
        if len(text) < 20:
            return
        h = hashlib.sha256(re.sub(r"\s+", " ", text.lower()).encode()).hexdigest()
        if h in seen:  # avoid duplicate chunks (repeated headers/footers)
            return
        seen.add(h)
        chunks.append(Chunk(len(chunks), page, text, h))

    for page in pages:
        text = clean_text(page.text)
        if not text:
            continue
        current = ""
        for unit in _split_units(text):
            while len(unit) > size:  # hard-split very long unit
                head, unit = unit[:size], unit[size - overlap:]
                if current:
                    emit(page.number, current)
                    current = ""
                emit(page.number, head)
            if current and len(current) + len(unit) + 1 > size:
                emit(page.number, current)
                tail = current[-overlap:] if overlap else ""
                tail = tail[tail.find(" ") + 1:] if " " in tail else tail
                current = tail
            current = f"{current} {unit}".strip()
        emit(page.number, current)
    return chunks
