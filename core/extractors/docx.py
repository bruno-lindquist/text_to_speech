# core/extractors/docx.py
# Extrai texto de arquivos .docx (Microsoft Word) usando python-docx.

from pathlib import Path

from docx import Document


def extract(path: Path) -> str:
    doc = Document(str(path))
    # Concatena parágrafos com quebra de linha, ignora linhas em branco
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
