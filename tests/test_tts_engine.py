# tests/test_tts_engine.py
# Teste do tts_engine com mock do edge-tts (sem rede em CI).
# Teste real está marcado com @pytest.mark.network — excluído do CI por padrão.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tts_engine import (
    NoInternetError,
    TTSError,
    Voice,
    _extract_friendly_name,
    _reset_voices_cache,
    list_voices,
    synthesize,
)


@pytest.mark.asyncio
async def test_synthesize_empty_text_raises() -> None:
    with pytest.raises(TTSError):
        await synthesize("", "pt-BR-FranciscaNeural")


@pytest.mark.asyncio
async def test_synthesize_whitespace_only_raises() -> None:
    with pytest.raises(TTSError):
        await synthesize("   \n\t  ", "pt-BR-FranciscaNeural")


@pytest.mark.asyncio
async def test_synthesize_returns_bytes_with_mock() -> None:
    # Mock do edge-tts.Communicate.stream() para devolver chunks fake
    fake_chunks = [
        {"type": "audio", "data": b"\xff\xfb"},
        {"type": "audio", "data": b"\x00\x00fake_mp3_data"},
        {"type": "WordBoundary", "offset": 0, "duration": 100, "text": "olá"},
    ]

    async def fake_stream():
        for c in fake_chunks:
            yield c

    mock_comm = MagicMock()
    mock_comm.stream = fake_stream

    with patch("core.tts_engine.edge_tts.Communicate", return_value=mock_comm):
        audio = await synthesize("olá", "pt-BR-FranciscaNeural")

    assert audio == b"\xff\xfb\x00\x00fake_mp3_data"
    assert isinstance(audio, bytes)


@pytest.mark.asyncio
async def test_synthesize_network_error_becomes_no_internet_error() -> None:
    # Quando edge-tts levanta erro de conexão, devolve NoInternetError
    mock_comm = MagicMock()

    async def boom():
        raise ConnectionError("Connection refused")
        yield  # pragma: no cover

    mock_comm.stream = boom

    with patch("core.tts_engine.edge_tts.Communicate", return_value=mock_comm):
        with pytest.raises(NoInternetError):
            await synthesize("olá", "pt-BR-FranciscaNeural")


@pytest.mark.network
@pytest.mark.asyncio
async def test_synthesize_real_edge_tts() -> None:
    # Teste com rede real — só roda quando explicitamente pedido com -m network.
    audio = await synthesize("Olá teste.", "pt-BR-FranciscaNeural")
    assert len(audio) > 1000
    # MP3 começa com sync word 0xFFFB ou tem ID3
    assert audio[:2] in (b"\xff\xfb", b"\xff\xf3", b"ID3")


# ---------- list_voices ----------

def test_extract_friendly_name_simples() -> None:
    assert _extract_friendly_name("pt-BR-FranciscaNeural") == "Francisca"
    assert _extract_friendly_name("en-US-AriaNeural") == "Aria"


def test_extract_friendly_name_camelcase() -> None:
    assert _extract_friendly_name("pt-BR-ThalitaMultilingualNeural") == "Thalita Multilingual"


@pytest.mark.asyncio
async def test_list_voices_returns_voice_objects() -> None:
    _reset_voices_cache()
    fake_raw = [
        {"ShortName": "pt-BR-FranciscaNeural", "Locale": "pt-BR", "Gender": "Female"},
        {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female"},
    ]
    with patch("core.tts_engine.edge_tts.list_voices", AsyncMock(return_value=fake_raw)):
        voices = await list_voices()

    assert len(voices) == 2
    assert all(isinstance(v, Voice) for v in voices)
    short_names = {v.short_name for v in voices}
    assert "pt-BR-FranciscaNeural" in short_names
    assert "en-US-AriaNeural" in short_names


@pytest.mark.asyncio
async def test_list_voices_sorted_by_locale_then_name() -> None:
    _reset_voices_cache()
    fake_raw = [
        {"ShortName": "en-US-GuyNeural", "Locale": "en-US", "Gender": "Male"},
        {"ShortName": "pt-BR-FranciscaNeural", "Locale": "pt-BR", "Gender": "Female"},
        {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female"},
    ]
    with patch("core.tts_engine.edge_tts.list_voices", AsyncMock(return_value=fake_raw)):
        voices = await list_voices()

    locales_in_order = [v.locale for v in voices]
    assert locales_in_order == ["en-US", "en-US", "pt-BR"]
    en_names = [v.friendly_name for v in voices if v.locale == "en-US"]
    assert en_names == sorted(en_names)


@pytest.mark.asyncio
async def test_list_voices_caches_result() -> None:
    _reset_voices_cache()
    fake_raw = [{"ShortName": "pt-BR-FranciscaNeural", "Locale": "pt-BR", "Gender": "Female"}]
    mock = AsyncMock(return_value=fake_raw)
    with patch("core.tts_engine.edge_tts.list_voices", mock):
        await list_voices()
        await list_voices()
        await list_voices()

    # Só foi à rede uma vez — duas chamadas seguintes vieram do cache
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_list_voices_falls_back_when_offline() -> None:
    _reset_voices_cache()
    # Simula falha de rede no edge-tts
    with patch(
        "core.tts_engine.edge_tts.list_voices",
        AsyncMock(side_effect=ConnectionError("DNS lookup failed")),
    ):
        voices = await list_voices()

    assert len(voices) == 1
    assert voices[0].short_name == "pt-BR-FranciscaNeural"
    assert voices[0].locale == "pt-BR"
