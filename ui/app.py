# ui/app.py
# UI mínima do MVP — Flet 0.85.

import asyncio
from pathlib import Path

import flet as ft
from loguru import logger

from core.audio_player import AudioPlayer
from core.extractors import ExtractorError, SUPPORTED_EXTENSIONS, extract
from core.storage import load_config, save_config
from core.text_chunker import chunk
from core.tts_engine import NoInternetError, TTSError, list_voices, synthesize_chunks
from ui.components.voice_controls import build_voice_controls


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

    # Carrega vozes do edge-tts (cache em memória; fallback offline se sem rede)
    voices = await list_voices()

    # --- Componentes ---
    text_area = ft.TextField(
        label="Cole ou digite o texto aqui",
        multiline=True,
        min_lines=10,
        max_lines=20,
        expand=True,
        autofocus=True,
    )

    def _on_voice_or_locale_change(locale: str, voice_short_name: str) -> None:
        config["default_locale"] = locale
        config["default_voice"] = voice_short_name
        save_config(config)

    def _on_rate_change(rate_str: str) -> None:
        config["default_rate"] = rate_str
        save_config(config)

    voice_controls = build_voice_controls(
        voices=voices,
        initial_locale=config.get("default_locale", "pt-BR"),
        initial_voice=config.get("default_voice", "pt-BR-FranciscaNeural"),
        initial_rate=config.get("default_rate", "+0%"),
        on_voice_change=_on_voice_or_locale_change,
        on_rate_change=_on_rate_change,
    )

    volume_slider = ft.Slider(
        min=0,
        max=100,
        value=int(config.get("default_volume", 1.0) * 100),
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
        config["default_volume"] = volume
        save_config(config)

    async def do_synthesize_and_play() -> None:
        text = text_area.value or ""
        voice = voice_controls.voice_dropdown.value or "pt-BR-FranciscaNeural"
        rate = config.get("default_rate", "+0%")
        if not text.strip():
            return

        play_button.disabled = True
        page.update()

        try:
            # Quebra em chunks (todo texto passa pelo chunker — KISS)
            chunks_text = chunk(text, language="pt")
            total = len(chunks_text)
            audios: list[bytes] = []

            i = 0
            async for audio in synthesize_chunks(chunks_text, voice, rate=rate):
                i += 1
                audios.append(audio)
                status_text.value = f"Sintetizando… ({i}/{total})"
                status_text.color = ft.Colors.AMBER_400
                page.update()

            # Concatenação binária dos MP3s (validada na Fase 1: parâmetros consistentes)
            full_audio = b"".join(audios)
            last_audio["bytes"] = full_audio

            status_text.value = "Tocando…"
            status_text.color = ft.Colors.GREEN_400
            page.update()
            await player.play(full_audio)
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

    async def on_open_file(e: ft.Event) -> None:
        # Abre o file picker pra escolher um arquivo, extrai texto e coloca no text_area.
        # Em Flet 0.85, pick_files retorna lista de FilePickerFile com .path
        result = await file_picker.pick_files(
            dialog_title="Abrir arquivo",
            allowed_extensions=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
            allow_multiple=False,
        )
        if not result:
            return

        # Pega o primeiro (e único) arquivo
        file_path = Path(result[0].path)
        status_text.value = f"Lendo {file_path.name}…"
        status_text.color = ft.Colors.AMBER_400
        page.update()

        try:
            # Extração pode ser pesada (PDF grande) — roda em executor para não travar
            loop = asyncio.get_running_loop()
            extracted_text = await loop.run_in_executor(None, extract, file_path)
            text_area.value = extracted_text
            on_text_change(None)  # atualiza estado do botão play
            status_text.value = f"Carregado {file_path.name} ({len(extracted_text)} chars)"
            status_text.color = ft.Colors.GREEN_400
            page.update()
        except ExtractorError as exc:
            show_error(str(exc))
            status_text.value = "Erro ao ler arquivo."
            status_text.color = ft.Colors.RED_400
            page.update()

    def on_text_change(e: ft.Event | None) -> None:
        has_text = bool((text_area.value or "").strip())
        play_button.disabled = not has_text
        page.update()

    text_area.on_change = on_text_change
    volume_slider.on_change = on_volume_change

    # --- Botões ---
    open_button = ft.ElevatedButton(
        "📁 Abrir arquivo",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=on_open_file,
    )
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
                voice_controls.container,
                ft.Row([volume_slider], spacing=20),
                ft.Row([open_button, play_button, stop_button, save_button], spacing=10),
                status_text,
            ],
            spacing=15,
            expand=True,
        )
    )

    # Aplica volume inicial salvo (default 1.0)
    await player.set_volume(float(config.get("default_volume", 1.0)))

    # Shutdown limpo
    async def on_close_handler() -> None:
        logger.info("Fechando app — limpando estado")
        await player.stop()
        task = current_task["synth"]
        if task and not task.done():
            task.cancel()

    page.on_close = lambda e: asyncio.create_task(on_close_handler())
