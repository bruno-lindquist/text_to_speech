# core/audio_player.py
# Player de áudio com play/pause/stop/seek/volume.
# Wraps just_playback (síncrono) em métodos async com asyncio.Lock para evitar race.
# Fase 5a: play_queue() consome uma asyncio.Queue de MP3s e toca em sequência
# (streaming progressivo — chunk N+1 chega na fila enquanto chunk N toca).

import asyncio
import tempfile
from pathlib import Path

from just_playback import Playback
from loguru import logger

# Sentinela enviada na fila para sinalizar fim do streaming.
# (None é semanticamente claro e evita confusão com bytes vazios.)
QUEUE_END = None


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
        # Temp files acumulados durante play_queue() — limpos no stop ou no fim da fila.
        self._queue_temp_files: list[Path] = []
        self._volume = 1.0  # 0.0..1.0
        self._playback.set_volume(self._volume)
        # Tracking para a barra de progresso (Fase 5a):
        # quantos chunks já terminaram E duração de cada um (em segundos).
        self._chunks_done = 0
        self._chunk_durations: list[float] = []
        # Flag para play_queue interromper o loop quando stop() é chamado.
        self._stop_requested = False

    # ---------- Tracking de progresso (Fase 5a) ----------

    @property
    def chunks_done(self) -> int:
        # Quantos chunks da fila já terminaram de tocar (não inclui o atual).
        return self._chunks_done

    @property
    def chunk_durations(self) -> list[float]:
        # Duração (segundos) de cada chunk já carregado — copy para evitar mutação externa.
        return self._chunk_durations.copy()

    def reset_progress(self) -> None:
        # Zera contadores antes de iniciar uma nova fila.
        self._chunks_done = 0
        self._chunk_durations = []
        self._stop_requested = False

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

    async def play_queue(self, queue: "asyncio.Queue[bytes | None]") -> None:
        # Consome chunks MP3 da fila e toca em sequência.
        # Termina quando recebe QUEUE_END (None) ou quando stop() é chamado.
        # O caller (UI) lê chunks_done e chunk_durations para a barra de progresso.
        self.reset_progress()

        while True:
            if self._stop_requested:
                logger.debug("play_queue: stop requisitado, encerrando loop")
                return

            chunk_bytes = await queue.get()
            if chunk_bytes is QUEUE_END:
                logger.debug("play_queue: sentinela de fim recebida")
                return

            await self._play_one_chunk(chunk_bytes)

            if self._stop_requested:
                # Stop pode ter chegado durante o playback do chunk
                return

            self._chunks_done += 1

    async def _play_one_chunk(self, mp3_bytes: bytes) -> None:
        # Toca um chunk e bloqueia até o just_playback indicar que terminou.
        # Polling a cada 50ms (mesma cadência prevista para o tick loop da Fase 5b).
        async with self._lock:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.write(mp3_bytes)
            tmp.close()
            tmp_path = Path(tmp.name)
            self._queue_temp_files.append(tmp_path)

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._playback.load_file, str(tmp_path))
            # Já temos a duração agora — registrar para a barra de progresso
            self._chunk_durations.append(self._playback.duration)
            await loop.run_in_executor(None, self._playback.play)
            self._playback.set_volume(self._volume)

        # Espera fora do lock — outros métodos (set_volume, stop) precisam pegar o lock.
        # just_playback expõe .active = True enquanto está tocando E não foi parado.
        while self._playback.active and not self._stop_requested:
            await asyncio.sleep(0.05)

    def _cleanup_queue_temp_files(self) -> None:
        # Remove todos os temp files acumulados durante uma play_queue.
        for path in self._queue_temp_files:
            if path.exists():
                try:
                    path.unlink()
                except OSError as e:
                    logger.warning(f"Falha ao remover temp da fila: {e}")
        self._queue_temp_files = []

    async def pause(self) -> None:
        async with self._lock:
            self._playback.pause()

    async def resume(self) -> None:
        async with self._lock:
            self._playback.resume()

    async def stop(self) -> None:
        # Stop síncrono do just_playback (interrompe o thread interno na hora).
        # Importante: chamar ANTES de cancelar tasks de síntese — ver Concorrência no PLANO.
        # Também sinaliza para play_queue() interromper seu loop interno.
        async with self._lock:
            self._stop_requested = True
            self._playback.stop()
            self._cleanup_temp_file()
            self._cleanup_queue_temp_files()

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
        self._cleanup_queue_temp_files()
