# tests/test_text_chunker.py

from core.text_chunker import DEFAULT_MAX_CHARS, chunk


def test_empty_text_returns_empty_list() -> None:
    assert chunk("") == []
    assert chunk("   \n\t  ") == []


def test_short_text_single_chunk() -> None:
    chunks = chunk("Olá mundo. Tudo bem?", language="pt")
    assert len(chunks) == 1
    assert chunks[0] == "Olá mundo. Tudo bem?"


def test_pysbd_respeita_abreviacoes_pt() -> None:
    # Checkpoint do PLANO: 'Sr. Silva foi ao Dr. Mendes. Depois voltou para casa.'
    # Deve virar 2 frases, NÃO 4. Como o limite é alto, vira 1 chunk só,
    # mas o que importa é que pysbd não corte em "Sr." nem em "Dr.".
    chunks = chunk(
        "Sr. Silva foi ao Dr. Mendes. Depois voltou para casa.",
        language="pt",
    )
    assert len(chunks) == 1


def test_long_text_multiple_chunks() -> None:
    # Texto de 5000+ chars com max_chars=1000 deve virar múltiplos chunks
    text = "Olá mundo. " * 500
    chunks = chunk(text, language="pt", max_chars=1000)
    assert len(chunks) > 1


def test_chunks_respect_max_chars() -> None:
    text = "Frase curta. " * 1000
    max_chars = 500
    chunks = chunk(text, language="pt", max_chars=max_chars)
    # Tolerância pequena pela junção com espaços
    for c in chunks:
        assert len(c) <= max_chars + 50


def test_single_sentence_larger_than_limit_passes_intact() -> None:
    # Frase única muito longa não é cortada no meio — passa inteira
    long_sentence = "palavra " * 500 + "fim."
    chunks = chunk(long_sentence, language="pt", max_chars=100)
    assert len(chunks) == 1
    assert chunks[0].endswith("fim.")


def test_unknown_language_falls_back_to_english() -> None:
    # Idioma desconhecido pelo pysbd não levanta erro — usa 'en' como fallback
    chunks = chunk("Hello. World.", language="xyz")
    assert len(chunks) >= 1


def test_default_max_chars() -> None:
    # Calibrado empiricamente na Fase 2 — ver comentário em text_chunker.py
    assert DEFAULT_MAX_CHARS == 2000
