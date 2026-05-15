# tests/test_extractors.py
# Testa os 4 extractors com fixtures em tests/fixtures/docs/.
# As fixtures são geradas por script (não versionadas como binários grandes).

from pathlib import Path

import pytest

from core.extractors import (
    SUPPORTED_EXTENSIONS,
    ExtractorError,
    UnsupportedFormatError,
    extract,
)

FIXTURES = Path(__file__).parent / "fixtures" / "docs"


def test_extract_txt() -> None:
    if not (FIXTURES / "sample.txt").exists():
        pytest.skip("Fixture sample.txt não existe — gerar antes")
    text = extract(FIXTURES / "sample.txt")
    assert "Olá" in text or "TXT" in text  # fixtures de teste contêm essas palavras
    assert len(text) > 10


def test_extract_pdf() -> None:
    if not (FIXTURES / "sample.pdf").exists():
        pytest.skip("Fixture sample.pdf não existe")
    text = extract(FIXTURES / "sample.pdf")
    assert "Pagina" in text or "PDF" in text
    assert len(text) > 10


def test_extract_docx() -> None:
    if not (FIXTURES / "sample.docx").exists():
        pytest.skip("Fixture sample.docx não existe")
    text = extract(FIXTURES / "sample.docx")
    assert "parágrafo" in text.lower() or "DOCX" in text
    assert len(text) > 10


def test_extract_epub() -> None:
    if not (FIXTURES / "sample.epub").exists():
        pytest.skip("Fixture sample.epub não existe")
    text = extract(FIXTURES / "sample.epub")
    assert "Capitulo" in text or "capítulo" in text.lower()
    assert len(text) > 10


def test_extract_nonexistent_raises() -> None:
    with pytest.raises(ExtractorError):
        extract("/nao/existe.txt")


def test_extract_unsupported_format_raises(tmp_path: Path) -> None:
    fake = tmp_path / "fake.xyz"
    fake.write_text("conteudo")
    with pytest.raises(UnsupportedFormatError):
        extract(fake)


def test_supported_extensions() -> None:
    # As 4 extensões esperadas
    assert ".txt" in SUPPORTED_EXTENSIONS
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".epub" in SUPPORTED_EXTENSIONS


def test_extract_string_path_also_works(tmp_path: Path) -> None:
    # extract() aceita Path ou str
    fake = tmp_path / "ex.txt"
    fake.write_text("teste curto")
    assert extract(str(fake)) == "teste curto"
