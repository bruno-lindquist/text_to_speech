# core/tts_engine.py
# Wrapper assíncrono do edge-tts. Na Fase 1, só sintetiza texto completo (sem chunking).

import asyncio
import edge_tts
from loguru import logger


class TTSError(Exception):
    # Exceção da camada TTS — UI captura e mostra dialog.
    pass


class NoInternetError(TTSError):
    # Falha por ausência de rede / timeout / DNS.
    pass


async def synthesize(
    text: str,
    voice: str,
    rate: str = "+0%",
    timeout: float = 10.0,
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
