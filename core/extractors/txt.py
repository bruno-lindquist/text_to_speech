# core/extractors/txt.py
# Extrai texto de arquivos .txt. UTF-8 com fallback para latin-1.

from pathlib import Path


def extract(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Arquivo antigo / Windows pode estar em latin-1
        return path.read_text(encoding="latin-1")
