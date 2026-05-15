# tests/test_tts_engine.py
# Teste do tts_engine com mock do edge-tts (sem rede em CI).
# Teste real está marcado com @pytest.mark.network — excluído do CI por padrão.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tts_engine import NoInternetError, TTSError, synthesize


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
