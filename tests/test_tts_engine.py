# tests/test_tts_engine.py
# Teste do tts_engine com mock do edge-tts (sem rede em CI).
# Teste real está marcado com @pytest.mark.network — excluído do CI por padrão.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import asyncio

from core.tts_engine import (
    NoInternetError,
    TTSError,
    Voice,
    _extract_friendly_name,
    _reset_voices_cache,
    list_voices,
    stream_to_queue,
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


# ---------- stream_to_queue (Fase 5a) ----------


@pytest.mark.asyncio
async def test_stream_to_queue_puts_each_chunk_then_sentinel() -> None:
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    fake_audios = [b"audio1", b"audio2", b"audio3"]

    async def fake_synthesize_chunks(*_a, **_kw):
        for a in fake_audios:
            yield a

    with patch("core.tts_engine.synthesize_chunks", fake_synthesize_chunks):
        await stream_to_queue(["t1", "t2", "t3"], "pt-BR-FranciscaNeural", queue)

    # 3 chunks + sentinela None
    assert queue.qsize() == 4
    items = [await queue.get() for _ in range(4)]
    assert items == [b"audio1", b"audio2", b"audio3", None]


@pytest.mark.asyncio
async def test_stream_to_queue_sentinel_on_synthesis_error() -> None:
    # Mesmo se synthesize_chunks levantar, sentinela DEVE ir pra fila
    # para não deixar o consumidor bloqueado em queue.get()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def boom(*_a, **_kw):
        yield b"primeiro_ok"
        raise NoInternetError("Simulated connection drop")

    with patch("core.tts_engine.synthesize_chunks", boom):
        with pytest.raises(NoInternetError):
            await stream_to_queue(["t1", "t2"], "pt-BR-FranciscaNeural", queue)

    # Fila tem o chunk que deu certo + sentinela (mesmo após exceção)
    items = []
    while not queue.empty():
        items.append(await queue.get())
    assert items == [b"primeiro_ok", None]


@pytest.mark.asyncio
async def test_stream_to_queue_empty_chunks_only_sentinel() -> None:
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def empty_gen(*_a, **_kw):
        return
        yield  # pragma: no cover  # marca a função como generator

    with patch("core.tts_engine.synthesize_chunks", empty_gen):
        await stream_to_queue([], "pt-BR-FranciscaNeural", queue)

    assert queue.qsize() == 1
    assert await queue.get() is None


@pytest.mark.asyncio
async def test_stream_to_queue_sentinel_on_cancel() -> None:
    # Se a task for cancelada no meio, sentinela ainda vai pra fila (graças ao finally)
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def slow_gen(*_a, **_kw):
        yield b"first"
        await asyncio.sleep(10)  # vai ser cancelado aqui
        yield b"never_reached"  # pragma: no cover

    with patch("core.tts_engine.synthesize_chunks", slow_gen):
        task = asyncio.create_task(
            stream_to_queue(["t1", "t2"], "pt-BR-FranciscaNeural", queue)
        )
        # Espera primeiro chunk chegar na fila
        first = await queue.get()
        assert first == b"first"
        # Cancela
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    # Sentinela foi colocada no finally mesmo após cancel
    assert await queue.get() is None
