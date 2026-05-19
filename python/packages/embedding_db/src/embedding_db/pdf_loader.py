from __future__ import annotations
from pathlib import Path

from pypdf import PdfReader


def load_pdf(path: Path | str) -> str:
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)
