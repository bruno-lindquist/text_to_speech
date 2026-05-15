# core/extractors/epub.py
# Extrai texto de arquivos .epub usando ebooklib + BeautifulSoup.

from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub


def extract(path: Path) -> str:
    book = epub.read_epub(str(path))
    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        # Cada item é um capítulo (HTML). Extraímos só o texto visível.
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if text:
            parts.append(text)
    return "\n\n".join(parts)
