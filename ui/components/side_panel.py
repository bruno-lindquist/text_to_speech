# ui/components/side_panel.py
# Painel lateral à esquerda com lista de leituras anteriores (Fase 4).
# Cartão = snippet + voz + data; clique = restaura texto/voz/rate na main.
# Botão "Limpar histórico" no rodapé com diálogo de confirmação.

from collections.abc import Callable
from datetime import datetime
from dataclasses import dataclass

import flet as ft

from core.storage import HistoryEntry

PANEL_WIDTH = 280


def _format_timestamp(iso_ts: str) -> str:
    # "2026-05-14T22:13:45+00:00" -> "14/05 22:13"
    # Falha graciosamente se o timestamp não for parseável.
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return iso_ts


def _short_voice(voice: str) -> str:
    # "pt-BR-FranciscaNeural" -> "Francisca"
    name = voice.split("-")[-1]
    if name.endswith("Neural"):
        name = name[: -len("Neural")]
    return name


@dataclass
class SidePanel:
    container: ft.Control
    refresh: Callable[[list[HistoryEntry]], None]


def build_side_panel(
    page: ft.Page,
    initial_history: list[HistoryEntry],
    on_card_click: Callable[[HistoryEntry], None],
    on_clear: Callable[[], None],
) -> SidePanel:
    # Monta o painel completo. `refresh(history)` re-renderiza os cartões
    # depois que a main grava uma entrada nova ou limpa tudo.

    cards_column = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=8,
        expand=True,
    )

    empty_state = ft.Container(
        content=ft.Text(
            "Nenhuma leitura ainda.\nUse ▶ para começar.",
            size=12,
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        padding=20,
    )

    def _build_card(entry: HistoryEntry) -> ft.Control:
        # Cartão clicável: snippet em destaque + linha pequena com voz e data
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        entry.snippet,
                        size=12,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Row(
                        [
                            ft.Text(
                                _short_voice(entry.voice),
                                size=10,
                                color=ft.Colors.AMBER_400,
                            ),
                            ft.Text(
                                _format_timestamp(entry.timestamp),
                                size=10,
                                color=ft.Colors.GREY_500,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=4,
            ),
            padding=10,
            border_radius=6,
            bgcolor=ft.Colors.GREY_800,
            ink=True,
            on_click=lambda _e: on_card_click(entry),
        )

    def refresh(history: list[HistoryEntry]) -> None:
        if not history:
            cards_column.controls = [empty_state]
        else:
            cards_column.controls = [_build_card(e) for e in history]
        cards_column.update()

    # --- Diálogo de confirmação para "Limpar histórico" ---
    def _confirm_clear(_e: ft.Event) -> None:
        def _do_clear(_evt: ft.Event) -> None:
            page.pop_dialog()
            on_clear()

        dlg = ft.AlertDialog(
            title=ft.Text("Limpar histórico?"),
            content=ft.Text("Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Limpar", on_click=_do_clear),
            ],
        )
        page.show_dialog(dlg)

    clear_button = ft.TextButton(
        "🗑 Limpar histórico",
        on_click=_confirm_clear,
        style=ft.ButtonStyle(color=ft.Colors.GREY_400),
    )

    # --- Layout final do painel ---
    container = ft.Container(
        content=ft.Column(
            [
                ft.Text("📜 Histórico", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                cards_column,
                ft.Divider(),
                clear_button,
            ],
            spacing=8,
            expand=True,
        ),
        width=PANEL_WIDTH,
        padding=10,
        bgcolor=ft.Colors.GREY_900,
        border_radius=8,
    )

    # Render inicial
    if not initial_history:
        cards_column.controls = [empty_state]
    else:
        cards_column.controls = [_build_card(e) for e in initial_history]

    return SidePanel(container=container, refresh=refresh)
