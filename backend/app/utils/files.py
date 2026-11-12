import io
import zipfile

MIME_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def sniff_mime(head: bytes, full: bytes | None = None) -> str | None:
    """Detect the real type from content, not from the client-supplied name or content-type."""
    if head.startswith(b"%PDF"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"PK\x03\x04") and full is not None:
        try:
            with zipfile.ZipFile(io.BytesIO(full)) as z:
                if "word/document.xml" in z.namelist():
                    return MIME_BY_EXT["docx"]
        except zipfile.BadZipFile:
            return None
    return None


def safe_display_name(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    cleaned = "".join(c for c in name if c.isprintable() and c not in '<>:"|?*')
    return (cleaned or "document")[:200]
