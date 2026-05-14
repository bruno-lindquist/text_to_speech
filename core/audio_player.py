# core/audio_player.py
# Player de áudio com play/pause/stop/seek/volume.
# Wraps just_playback (síncrono) em métodos async com asyncio.Lock para evitar race.

import asyncio
import tempfile
from pathlib import Path

from just_playback import Playback
from loguru import logger


def format_time(seconds: float) -> str:
    # Formata segundos como mm:ss (ex: 0 -> "0:00", 65 -> "1:05").
    # Função pura — fácil de testar.
    if seconds < 0:
        seconds = 0
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def progress_ratio(current: float, total: float) -> float:
    # Devolve 0.0..1.0 dado posição atual e duração total.
    # Trata edge cases (total=0, current>total). Função pura.
    if total <= 0:
        return 0.0
    ratio = current / total
    return max(0.0, min(1.0, ratio))


class AudioPlayer:
    # Wrapper async sobre just_playback.
    # Estado interno protegido por asyncio.Lock — qualquer mutação passa pelo lock.

    def __init__(self) -> None:
        self._playback = Playback()
        self._lock = asyncio.Lock()
        self._temp_file: Path | None = None
        self._volume = 1.0  # 0.0..1.0
        self._playback.set_volume(self._volume)

    async def play(self, mp3_bytes: bytes) -> None:
        # Carrega o MP3 (via arquivo temporário, pois just_playback exige path) e toca.
        async with self._lock:
            # Para qualquer reprodução anterior
            self._playback.stop()
            # Limpa temp file anterior
            self._cleanup_temp_file()
            # Cria novo temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.write(mp3_bytes)
            tmp.close()
            self._temp_file = Path(tmp.name)
            logger.debug(f"Tocando MP3 temp em {self._temp_file}")
            # load_file e play são síncronos — rodam no executor pra não bloquear o loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._playback.load_file, str(self._temp_file))
            await loop.run_in_executor(None, self._playback.play)
            self._playback.set_volume(self._volume)

    async def pause(self) -> None:
        async with self._lock:
            self._playback.pause()

    async def resume(self) -> None:
        async with self._lock:
            self._playback.resume()

    async def stop(self) -> None:
        # Stop síncrono do just_playback (interrompe o thread interno na hora).
        # Importante: chamar ANTES de cancelar tasks de síntese — ver Concorrência no PLANO.
        async with self._lock:
            self._playback.stop()
            self._cleanup_temp_file()

    async def seek(self, position_seconds: float) -> None:
        async with self._lock:
            self._playback.seek(position_seconds)

    async def set_volume(self, volume: float) -> None:
        # Volume do player (não do edge-tts) — mudança em tempo real, sem resintetizar.
        volume = max(0.0, min(1.0, volume))
        async with self._lock:
            self._volume = volume
            self._playback.set_volume(volume)

    @property
    def is_playing(self) -> bool:
        return self._playback.playing

    @property
    def is_paused(self) -> bool:
        return self._playback.paused

    @property
    def position(self) -> float:
        # Posição atual em segundos.
        return self._playback.curr_pos

    @property
    def duration(self) -> float:
        # Duração total do arquivo em segundos (só disponível depois de load_file).
        return self._playback.duration

    def _cleanup_temp_file(self) -> None:
        # Remove o MP3 temporário. Silencioso se já tiver sido removido.
        if self._temp_file and self._temp_file.exists():
            try:
                self._temp_file.unlink()
            except OSError as e:
                logger.warning(f"Falha ao remover temp file: {e}")
        self._temp_file = None

    def __del__(self) -> None:
        self._cleanup_temp_file()
