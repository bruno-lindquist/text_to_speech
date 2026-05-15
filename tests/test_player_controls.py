# tests/test_player_controls.py
# Testes das funções puras do player_controls (componente visual).
# A renderização Flet em si é validada manualmente.

from unittest.mock import MagicMock

from ui.components.player_controls import _elapsed_seconds, _estimate_total_seconds


def test_estimate_no_chunks_ready_returns_none() -> None:
    # Antes de qualquer chunk ser sintetizado, exibimos "calculando…"
    assert _estimate_total_seconds([], total_chunks=5) is None


def test_estimate_zero_total_chunks_returns_none() -> None:
    # Caso degenerado — não deve dividir por zero
    assert _estimate_total_seconds([], total_chunks=0) is None
    assert _estimate_total_seconds([1.0], total_chunks=0) is None


def test_estimate_all_chunks_ready_returns_real_sum() -> None:
    # Todos sintetizados → estimativa = soma exata, sem extrapolação
    durations = [2.0, 3.0, 1.5]
    assert _estimate_total_seconds(durations, total_chunks=3) == 6.5


def test_estimate_extrapolates_with_average() -> None:
    # 2 chunks reais (média 5s) + 3 pendentes → 10 + 15 = 25
    durations = [4.0, 6.0]
    result = _estimate_total_seconds(durations, total_chunks=5)
    assert result == 25.0


def test_estimate_single_chunk_extrapolates() -> None:
    # 1 chunk real de 4s + 4 pendentes → 4 + 4*4 = 20
    assert _estimate_total_seconds([4.0], total_chunks=5) == 20.0


def test_elapsed_zero_when_nothing_played() -> None:
    player = MagicMock()
    player.chunk_durations = []
    player.chunks_done = 0
    player.position = 0.0
    assert _elapsed_seconds(player) == 0.0


def test_elapsed_includes_finished_chunks_plus_current_position() -> None:
    # 2 chunks de 3s já tocados + 1.5s no atual = 7.5s
    player = MagicMock()
    player.chunk_durations = [3.0, 3.0, 3.0]  # 3 chunks carregados (atual incluído)
    player.chunks_done = 2                     # mas só 2 já terminaram
    player.position = 1.5                      # posição dentro do chunk atual

    assert _elapsed_seconds(player) == 7.5


def test_elapsed_only_first_chunk_in_progress() -> None:
    # Tocando o primeiro chunk; nada terminou ainda
    player = MagicMock()
    player.chunk_durations = [4.0]
    player.chunks_done = 0
    player.position = 1.2

    assert _elapsed_seconds(player) == 1.2
