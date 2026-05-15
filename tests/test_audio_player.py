# tests/test_audio_player.py
# Testes das funções puras do audio_player + métodos com mock.
# Métodos reais (com áudio) são validação manual (ver PLANO).

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from core.audio_player import QUEUE_END, AudioPlayer, format_time, progress_ratio


def test_format_time_zero() -> None:
    assert format_time(0) == "0:00"


def test_format_time_under_minute() -> None:
    assert format_time(45) == "0:45"


def test_format_time_exact_minute() -> None:
    assert format_time(60) == "1:00"


def test_format_time_over_minute() -> None:
    assert format_time(65) == "1:05"
    assert format_time(125) == "2:05"


def test_format_time_negative_clamped() -> None:
    assert format_time(-10) == "0:00"


def test_format_time_float_truncates() -> None:
    # 125.7s -> 2:05 (não arredonda, trunca)
    assert format_time(125.7) == "2:05"


def test_progress_ratio_zero_total() -> None:
    # Edge case: duração 0 → 0.0 sem ZeroDivisionError
    assert progress_ratio(50, 0) == 0.0


def test_progress_ratio_halfway() -> None:
    assert progress_ratio(50, 100) == 0.5


def test_progress_ratio_complete() -> None:
    assert progress_ratio(100, 100) == 1.0


def test_progress_ratio_overflow_clamped() -> None:
    # Se posição passou da duração, retorna 1.0
    assert progress_ratio(150, 100) == 1.0


def test_progress_ratio_negative_clamped() -> None:
    assert progress_ratio(-10, 100) == 0.0


# ---------- play_queue (Fase 5a) ----------


class FakePlayback:
    # Substitui just_playback.Playback nos testes.
    # Simula um chunk como "ativo" por N ticks de polling.
    def __init__(self, ticks_per_chunk: int = 2, fake_duration: float = 1.5) -> None:
        self.playing = False
        self.paused = False
        self.curr_pos = 0.0
        self.duration = fake_duration
        self._ticks_per_chunk = ticks_per_chunk
        self._ticks_remaining = 0
        self.set_volume_calls: list[float] = []
        self.stop_calls = 0

    def set_volume(self, v: float) -> None:
        self.set_volume_calls.append(v)

    def load_file(self, _path: str) -> None:
        self._ticks_remaining = self._ticks_per_chunk

    def play(self) -> None:
        self.playing = True

    def stop(self) -> None:
        self.stop_calls += 1
        self.playing = False
        self._ticks_remaining = 0

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def seek(self, _pos: float) -> None:
        pass

    @property
    def active(self) -> bool:
        # Cada acesso a .active consome um tick. Quando zera, simula fim do chunk.
        if self._ticks_remaining > 0:
            self._ticks_remaining -= 1
            return True
        self.playing = False
        return False


def _make_player_with_fake() -> tuple[AudioPlayer, FakePlayback]:
    fake = FakePlayback()
    with patch("core.audio_player.Playback", return_value=fake):
        player = AudioPlayer()
    return player, fake


@pytest.mark.asyncio
async def test_play_queue_consumes_until_sentinel() -> None:
    player, fake = _make_player_with_fake()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    await queue.put(b"\xff\xfb_chunk1")
    await queue.put(b"\xff\xfb_chunk2")
    await queue.put(QUEUE_END)

    await player.play_queue(queue)

    assert player.chunks_done == 2
    # Cada chunk gera uma duração registrada
    assert len(player.chunk_durations) == 2


@pytest.mark.asyncio
async def test_play_queue_resets_progress_at_start() -> None:
    player, _ = _make_player_with_fake()
    # Suja o estado pra simular uma fila anterior
    player._chunks_done = 99
    player._chunk_durations = [10.0, 20.0]

    queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    await queue.put(QUEUE_END)
    await player.play_queue(queue)

    # Reset feito antes de processar a fila — fica zerado mesmo que vazia
    assert player.chunks_done == 0
    assert player.chunk_durations == []


@pytest.mark.asyncio
async def test_play_queue_stops_when_stop_requested_mid_queue() -> None:
    player, fake = _make_player_with_fake()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    for i in range(5):
        await queue.put(f"chunk{i}".encode())
    await queue.put(QUEUE_END)

    async def stop_after_first_chunk() -> None:
        # Espera tempo suficiente pro primeiro chunk começar a tocar
        await asyncio.sleep(0.08)
        await player.stop()

    await asyncio.gather(
        player.play_queue(queue),
        stop_after_first_chunk(),
    )

    # Stop deve ter interrompido antes de processar todos os 5 chunks
    assert player.chunks_done < 5
    assert fake.stop_calls >= 1


@pytest.mark.asyncio
async def test_reset_progress_clears_state() -> None:
    player, _ = _make_player_with_fake()
    player._chunks_done = 7
    player._chunk_durations = [1.0, 2.0, 3.0]
    player._stop_requested = True

    player.reset_progress()

    assert player.chunks_done == 0
    assert player.chunk_durations == []
    assert player._stop_requested is False


@pytest.mark.asyncio
async def test_chunk_durations_returns_copy() -> None:
    # chunk_durations devolve cópia — mutar a lista de fora não afeta o player
    player, _ = _make_player_with_fake()
    player._chunk_durations = [1.0, 2.0]

    durations = player.chunk_durations
    durations.append(99.0)

    assert player.chunk_durations == [1.0, 2.0]
