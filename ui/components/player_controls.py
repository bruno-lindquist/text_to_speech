# ui/components/player_controls.py
# Barra de progresso + tempos (decorrido / total estimado).
# Fase 5a: lê posição do AudioPlayer e durações dos chunks já sintetizados.
# Estimativa do total: durações reais dos chunks prontos + média × pendentes.

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from core.audio_player import AudioPlayer, format_time, progress_ratio


@dataclass
class PlayerControls:
    container: ft.Control
    update: Callable[[int], None]    # (total_chunks) -> None — chamar a cada tick
    reset: Callable[[], None]        # zera barra e tempos para nova reprodução


def _estimate_total_seconds(
    chunk_durations: list[float],
    total_chunks: int,
) -> float | None:
    # Estimativa do tempo total da fila (em segundos).
    # Critério (do PLANO):
    #   - 0 chunks prontos: None ("calculando…")
    #   - N chunks prontos: soma_real + média × (total_chunks - N)
    if not chunk_durations or total_chunks <= 0:
        return None
    real_sum = sum(chunk_durations)
    avg = real_sum / len(chunk_durations)
    pending = max(0, total_chunks - len(chunk_durations))
    return real_sum + avg * pending


def _elapsed_seconds(player: AudioPlayer) -> float:
    # Tempo decorrido = soma das durações dos chunks já tocados + posição no atual.
    # chunk_durations inclui o chunk atual (load_file já registrou); chunks_done não.
    durations = player.chunk_durations
    done = player.chunks_done
    elapsed_done = sum(durations[:done])
    return elapsed_done + player.position


def build_player_controls(player: AudioPlayer) -> PlayerControls:
    # Componente puramente visual: lê estado do player e renderiza.
    # O caller chama update(total_chunks) periodicamente (loop de tick na UI).

    progress_bar = ft.ProgressBar(
        value=0.0,
        bar_height=8,
        color=ft.Colors.AMBER_400,
        bgcolor=ft.Colors.GREY_800,
        expand=True,
    )

    elapsed_text = ft.Text("0:00", size=12, color=ft.Colors.GREY_400)
    total_text = ft.Text("calculando…", size=12, color=ft.Colors.GREY_400)

    def update(total_chunks: int) -> None:
        elapsed = _elapsed_seconds(player)
        total = _estimate_total_seconds(player.chunk_durations, total_chunks)

        elapsed_text.value = format_time(elapsed)
        if total is None:
            total_text.value = "calculando…"
            progress_bar.value = 0.0
        else:
            total_text.value = format_time(total)
            progress_bar.value = progress_ratio(elapsed, total)

        progress_bar.update()
        elapsed_text.update()
        total_text.update()

    def reset() -> None:
        progress_bar.value = 0.0
        elapsed_text.value = "0:00"
        total_text.value = "calculando…"
        progress_bar.update()
        elapsed_text.update()
        total_text.update()

    container = ft.Column(
        [
            progress_bar,
            ft.Row(
                [elapsed_text, total_text],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ],
        spacing=4,
    )

    return PlayerControls(container=container, update=update, reset=reset)
