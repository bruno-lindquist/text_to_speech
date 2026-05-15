# core/tts_engine.py
# Wrapper assíncrono do edge-tts.
# Fase 1: synthesize() para texto completo.
# Fase 2: synthesize_chunks() para uma lista de chunks (sem streaming progressivo ainda — Fase 5).
# Fase 3: list_voices() com cache em memória + fallback offline.

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

import edge_tts
from loguru import logger


class TTSError(Exception):
    # Exceção da camada TTS — UI captura e mostra dialog.
    pass


class NoInternetError(TTSError):
    # Falha por ausência de rede / timeout / DNS.
    pass


@dataclass(frozen=True)
class Voice:
    # Representação simples de uma voz do edge-tts.
    short_name: str  # ex: "pt-BR-FranciscaNeural" — é o que vai pro Communicate
    locale: str      # ex: "pt-BR"
    gender: str      # "Female" | "Male"
    friendly_name: str  # ex: "Francisca"


# Voz hardcoded usada como fallback quando list_voices() falha (offline).
# Validada no catálogo edge-tts na Fase 1.
_FALLBACK_VOICE = Voice(
    short_name="pt-BR-FranciscaNeural",
    locale="pt-BR",
    gender="Female",
    friendly_name="Francisca",
)

# Cache em memória da lista de vozes (carrega 1x por sessão).
_voices_cache: list[Voice] | None = None


def _extract_friendly_name(short_name: str) -> str:
    # "pt-BR-FranciscaNeural" -> "Francisca"
    # "pt-BR-ThalitaMultilingualNeural" -> "Thalita Multilingual"
    name_part = short_name.split("-")[-1]
    if name_part.endswith("Neural"):
        name_part = name_part[: -len("Neural")]
    # Quebra CamelCase: "ThalitaMultilingual" -> "Thalita Multilingual"
    result = []
    for i, ch in enumerate(name_part):
        if i > 0 and ch.isupper():
            result.append(" ")
        result.append(ch)
    return "".join(result)


async def list_voices(timeout: float = 10.0) -> list[Voice]:
    # Devolve a lista completa de vozes do edge-tts, ordenada por (locale, friendly_name).
    # Cacheia em memória durante a sessão — chamadas seguintes não vão à rede.
    # Se a chamada falhar (sem internet), devolve uma lista mínima com a voz fallback
    # (Francisca pt-BR) para o app continuar funcional.
    global _voices_cache
    if _voices_cache is not None:
        return _voices_cache

    try:
        async with asyncio.timeout(timeout):
            raw = await edge_tts.list_voices()
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Falha ao listar vozes do edge-tts: {e} — usando fallback offline")
        _voices_cache = [_FALLBACK_VOICE]
        return _voices_cache

    voices = [
        Voice(
            short_name=v["ShortName"],
            locale=v["Locale"],
            gender=v["Gender"],
            friendly_name=_extract_friendly_name(v["ShortName"]),
        )
        for v in raw
    ]
    voices.sort(key=lambda v: (v.locale, v.friendly_name))
    _voices_cache = voices
    logger.info(f"Carregadas {len(voices)} vozes do edge-tts")
    return voices


def _reset_voices_cache() -> None:
    # Apenas para testes — força recarregar na próxima chamada.
    global _voices_cache
    _voices_cache = None


async def synthesize(
    text: str,
    voice: str,
    rate: str = "+0%",
    timeout: float = 20.0,
) -> bytes:
    # Sintetiza o texto completo e devolve o MP3 em bytes.
    # rate vai como string no formato exigido pelo edge-tts: "+10%", "-25%".
    # Levanta NoInternetError se não conseguir conectar dentro de `timeout`.
    if not text.strip():
        raise TTSError("Texto vazio — nada a sintetizar.")

    logger.info(f"Sintetizando {len(text)} chars com voz={voice} rate={rate}")
    communicate = edge_tts.Communicate(text, voice, rate=rate)

    try:
        # Coleta o áudio aguardando todos os chunks do stream do edge-tts
        chunks: list[bytes] = []
        async with asyncio.timeout(timeout):
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
    except asyncio.TimeoutError as e:
        logger.warning(f"Timeout ({timeout}s) ao sintetizar — possível falta de rede")
        raise NoInternetError("Sem conexão — tempo esgotado ao falar com edge-tts.") from e
    except Exception as e:
        # edge-tts pode levantar várias exceções (DNS, SSL, etc) — tratamos como sem internet
        msg = str(e).lower()
        if any(t in msg for t in ("connection", "dns", "ssl", "timed out", "network")):
            logger.warning(f"Erro de rede em edge-tts: {e}")
            raise NoInternetError("Sem conexão — não foi possível sintetizar a voz.") from e
        logger.error(f"Falha inesperada no edge-tts: {e}")
        raise TTSError(f"Falha na síntese: {e}") from e

    audio = b"".join(chunks)
    logger.info(f"Síntese concluída ({len(audio)} bytes)")
    return audio


async def synthesize_chunks(
    text_chunks: list[str],
    voice: str,
    rate: str = "+0%",
    timeout: float = 20.0,
) -> AsyncIterator[bytes]:
    # Sintetiza cada chunk em sequência e devolve seus MP3s como AsyncIterator.
    # Fase 2: o caller acumula tudo antes de tocar (sem streaming progressivo).
    # Fase 5: vira streaming progressivo via asyncio.Queue (ver stream_to_queue abaixo).
    for i, chunk_text in enumerate(text_chunks):
        logger.info(f"Sintetizando chunk {i + 1}/{len(text_chunks)} ({len(chunk_text)} chars)")
        audio = await synthesize(chunk_text, voice, rate=rate, timeout=timeout)
        yield audio


async def stream_to_queue(
    text_chunks: list[str],
    voice: str,
    queue: "asyncio.Queue[bytes | None]",
    rate: str = "+0%",
    timeout: float = 20.0,
) -> None:
    # Produtor para o streaming progressivo da Fase 5a:
    # sintetiza cada chunk e coloca na fila assim que pronto. O consumidor
    # (AudioPlayer.play_queue) começa a tocar o primeiro chunk enquanto
    # os próximos ainda estão sendo sintetizados.
    #
    # Sempre coloca o sentinela QUEUE_END (None) na fila no `finally`, para
    # garantir que o consumidor não fique bloqueado em await queue.get() se:
    #   - a síntese falhou (TTSError / NoInternetError)
    #   - a task foi cancelada (Stop)
    # A exceção em si é re-levantada para o caller via task.exception().
    try:
        async for audio in synthesize_chunks(
            text_chunks, voice, rate=rate, timeout=timeout
        ):
            await queue.put(audio)
    finally:
        # QUEUE_END = None — definido em audio_player.py mas usamos None
        # diretamente aqui para evitar dependência circular.
        await queue.put(None)
