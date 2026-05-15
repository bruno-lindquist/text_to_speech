# ui/app.py
# UI mínima do MVP — Flet 0.85.

import asyncio
from pathlib import Path

import flet as ft
from loguru import logger

from core.audio_player import AudioPlayer
from core.storage import load_config, save_config
from core.tts_engine import NoInternetError, TTSError, synthesize

# 3 vozes pt-BR confirmadas no catálogo edge-tts (validadas na Fase 1)
HARDCODED_VOICES = [
    ("pt-BR-FranciscaNeural", "Francisca (feminina)"),
    ("pt-BR-AntonioNeural", "Antonio (masculino)"),
    ("pt-BR-ThalitaMultilingualNeural", "Thalita (feminina, multilíngue)"),
]


async def main(page: ft.Page) -> None:
    page.title = "Fizzy Bee 🐝"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Estado da app
    player = AudioPlayer()
    config = load_config()
    last_audio: dict[str, bytes] = {}
    current_task: dict[str, asyncio.Task | None] = {"synth": None}

    # FilePicker é Service em Flet 0.85 — vai em page.services, não em page.overlay
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # --- Componentes ---
    text_area = ft.TextField(
        label="Cole ou digite o texto aqui",
        multiline=True,
        min_lines=10,
        max_lines=20,
        expand=True,
        autofocus=True,
    )

    voice_dropdown = ft.Dropdown(
        label="Voz",
        width=300,
        options=[ft.DropdownOption(key=v, text=label) for v, label in HARDCODED_VOICES],
        value=config.get("default_voice", HARDCODED_VOICES[0][0]),
    )

    volume_slider = ft.Slider(
        min=0,
        max=100,
        value=100,
        divisions=20,
        label="Volume: {value}%",
        width=300,
    )

    status_text = ft.Text("Pronto.", size=12, color=ft.Colors.GREY_400)

    # --- Helpers ---
    def show_error(message: str) -> None:
        # AlertDialog via show_dialog/pop_dialog (Flet 0.85)
        dlg = ft.AlertDialog(
            title=ft.Text("Erro"),
            content=ft.Text(message),
        )
        dlg.actions = [
            ft.TextButton("OK", on_click=lambda _: page.pop_dialog()),
        ]
        page.show_dialog(dlg)

    # --- Handlers ---
    async def on_volume_change(e: ft.Event) -> None:
        volume = float(volume_slider.value) / 100.0
        await player.set_volume(volume)

    async def on_voice_change(e: ft.Event) -> None:
        config["default_voice"] = voice_dropdown.value
        save_config(config)

    async def do_synthesize_and_play() -> None:
        text = text_area.value or ""
        voice = voice_dropdown.value or HARDCODED_VOICES[0][0]
        if not text.strip():
            return

        play_button.disabled = True
        status_text.value = "Sintetizando…"
        status_text.color = ft.Colors.AMBER_400
        page.update()

        try:
            audio = await synthesize(text, voice, rate=config.get("default_rate", "+0%"))
            last_audio["bytes"] = audio
            status_text.value = "Tocando…"
            status_text.color = ft.Colors.GREEN_400
            page.update()
            await player.play(audio)
        except NoInternetError:
            show_error("Sem conexão — não foi possível sintetizar a voz.")
            status_text.value = "Erro de conexão."
            status_text.color = ft.Colors.RED_400
        except TTSError as exc:
            show_error(f"Falha na síntese: {exc}")
            status_text.value = "Falha na síntese."
            status_text.color = ft.Colors.RED_400
        except asyncio.CancelledError:
            logger.info("Síntese cancelada pelo usuário")
            status_text.value = "Cancelado."
            status_text.color = ft.Colors.GREY_400
            raise
        finally:
            play_button.disabled = False
            page.update()

    async def on_play(e: ft.Event) -> None:
        prev = current_task["synth"]
        if prev and not prev.done():
            prev.cancel()
        current_task["synth"] = asyncio.create_task(do_synthesize_and_play())

    async def on_stop(e: ft.Event) -> None:
        # Ordem do PLANO: para player primeiro (síncrono), depois cancela task
        await player.stop()
        task = current_task["synth"]
        if task and not task.done():
            task.cancel()
        status_text.value = "Parado."
        status_text.color = ft.Colors.GREY_400
        page.update()

    async def on_save(e: ft.Event) -> None:
        if "bytes" not in last_audio:
            show_error("Nada para salvar. Clique em Reproduzir antes.")
            return

        # Em Flet 0.85, save_file é sync e retorna o path direto
        result_path = await file_picker.save_file(
            dialog_title="Salvar MP3",
            file_name="fizzy_bee.mp3",
            allowed_extensions=["mp3"],
        )
        if not result_path:
            return  # usuário cancelou

        path = Path(result_path)
        if path.suffix.lower() != ".mp3":
            path = path.with_suffix(".mp3")
        path.write_bytes(last_audio["bytes"])
        status_text.value = f"Salvo em {path.name}"
        status_text.color = ft.Colors.GREEN_400
        page.update()

    def on_text_change(e: ft.Event) -> None:
        has_text = bool((text_area.value or "").strip())
        play_button.disabled = not has_text
        page.update()

    text_area.on_change = on_text_change
    voice_dropdown.on_change = on_voice_change
    volume_slider.on_change = on_volume_change

    # --- Botões ---
    play_button = ft.ElevatedButton(
        "▶ Reproduzir",
        icon=ft.Icons.PLAY_ARROW,
        on_click=on_play,
        disabled=True,
        bgcolor=ft.Colors.AMBER_700,
        color=ft.Colors.WHITE,
    )
    stop_button = ft.ElevatedButton(
        "⏹ Parar", icon=ft.Icons.STOP, on_click=on_stop
    )
    save_button = ft.ElevatedButton(
        "💾 Salvar MP3", icon=ft.Icons.SAVE, on_click=on_save
    )

    # --- Layout ---
    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("🐝 Fizzy Bee", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Leitor de texto com vozes neurais",
                            size=12,
                            color=ft.Colors.GREY_400,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    spacing=10,
                ),
                ft.Divider(),
                text_area,
                ft.Row([voice_dropdown, volume_slider], spacing=20),
                ft.Row([play_button, stop_button, save_button], spacing=10),
                status_text,
            ],
            spacing=15,
            expand=True,
        )
    )

    # Aplica volume inicial
    await player.set_volume(1.0)

    # Shutdown limpo
    async def on_close_handler() -> None:
        logger.info("Fechando app — limpando estado")
        await player.stop()
        task = current_task["synth"]
        if task and not task.done():
            task.cancel()

    page.on_close = lambda e: asyncio.create_task(on_close_handler())
