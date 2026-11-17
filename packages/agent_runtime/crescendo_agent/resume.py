"""Read a resume's text locally (JOB-F02). Nothing here sends the resume anywhere.

PDF (via pypdf), .txt, or .md. Bounded: at most 10 MB and 10 pages, 50,000
characters of text. A scanned (image-only) PDF yields no text; that is reported
rather than guessed.
"""
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10
MAX_CHARS = 50_000


class ResumeError(Exception):
    """The resume could not be read; the message is safe to show."""


def read_resume_text(path) -> str:
    path = Path(path)
    if not path.is_file():
        raise ResumeError(f"No file at {path}.")
    if path.stat().st_size > MAX_BYTES:
        raise ResumeError("The resume file is larger than 10 MB.")
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(errors="replace")
    elif suffix == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise ResumeError("The PDF is password-protected.")
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:MAX_PAGES])
        except PdfReadError:
            raise ResumeError("The PDF could not be read.") from None
    else:
        raise ResumeError("Use a .pdf, .txt, or .md resume.")
    text = "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()
    if not text:
        raise ResumeError("No text found in the resume (a scanned image PDF needs OCR first).")
    return text[:MAX_CHARS]
