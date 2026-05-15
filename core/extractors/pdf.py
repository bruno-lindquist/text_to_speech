# core/extractors/pdf.py
# Extrai texto de PDFs usando pypdf.

from pathlib import Path

from pypdf import PdfReader


def extract(path: Path) -> str:
    reader = PdfReader(str(path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    # Junta páginas com 2 quebras de linha (parágrafo) para preservar separação visual
    return "\n\n".join(pages_text).strip()
