# ui/app.py
# UI mínima do MVP — Flet 0.85.

import asyncio
from pathlib import Path

import flet as ft
from loguru import logger

from core.audio_player import QUEUE_END, AudioPlayer
from core.extractors import ExtractorError, SUPPORTED_EXTENSIONS, extract
from core.storage import (
    HistoryEntry,
    clear_history,
    load_config,
    load_history,
    save_config,
    save_history_entry,
)
from core.text_chunker import chunk
from core.tts_engine import (
    NoInternetError,
    TTSError,
    list_voices,
    synthesize_chunks,
)
from ui.components.player_controls import build_player_controls
from ui.components.side_panel import build_side_panel
from ui.components.voice_controls import build_voice_controls


async def main(page: ft.Page) -> None:
    page.title = "Fizzy Bee 🐝"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Estado da app
    player = AudioPlayer()
    config = load_config()
    # Acumula os MP3s sintetizados durante o streaming — usado pelo "Salvar MP3"
    # (concatenação binária validada na Fase 1).
    last_audio_chunks: list[bytes] = []
    # Tasks ativas: producer (síntese), consumer (player), tick (UI). Cada um pode
    # ser cancelado individualmente por on_stop / on_play (que dispara nova leitura).
    current_tasks: dict[str, asyncio.Task | None] = {
        "producer": None,
        "consumer": None,
        "tick": None,
    }

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

    # Barra de progresso da Fase 5a — atualizada por um tick loop durante a reprodução
    player_controls = build_player_controls(player)

    status_text = ft.Text("Pronto.", size=12, color=ft.Colors.GREY_400)

    # --- Painel lateral de histórico (Fase 4) ---
    def _restore_from_entry(entry: HistoryEntry) -> None:
        # Clique no cartão: restaura texto + voz + locale + rate na main.
        # Não dispara play automático — usuário decide quando reproduzir.
        text_area.value = entry.text
        on_text_change(None)  # habilita o botão Play
        # Restaura locale e voz nos dropdowns (se a voz ainda existir no catálogo)
        locale = entry.voice.rsplit("-", 1)[0]  # "pt-BR-FranciscaNeural" -> "pt-BR"
        voice_controls.locale_dropdown.value = locale
        # Repopula opções do dropdown de voz para o locale e seleciona a voz
        voice_options = [
            opt for opt in voice_controls.voice_dropdown.options or []
        ]
        # Se o locale mudou, precisa repopular — dispara o handler do dropdown
        if voice_controls.locale_dropdown.value != locale:
            voice_controls.locale_dropdown.value = locale
        voice_controls.voice_dropdown.value = entry.voice
        voice_controls.rate_slider.value = int(entry.rate.rstrip("%"))
        # Persiste como nova preferência
        config["default_locale"] = locale
        config["default_voice"] = entry.voice
        config["default_rate"] = entry.rate
        save_config(config)
        status_text.value = f"Restaurado: {entry.snippet[:40]}…"
        status_text.color = ft.Colors.AMBER_400
        page.update()

    def _on_clear_history() -> None:
        clear_history()
        side_panel.refresh([])
        status_text.value = "Histórico limpo."
        status_text.color = ft.Colors.GREY_400
        page.update()

    side_panel = build_side_panel(
        page=page,
        initial_history=load_history(),
        on_card_click=_restore_from_entry,
        on_clear=_on_clear_history,
    )

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

    async def _tick_loop(total_chunks: int, consumer_task: asyncio.Task) -> None:
        # Atualiza a barra a cada 100ms enquanto o consumer (player_queue) está vivo.
        # Para automaticamente quando o consumer termina — assim o tick não fica
        # rodando à toa quando nada está sendo reproduzido (checkpoint do PLANO).
        try:
            while not consumer_task.done():
                player_controls.update(total_chunks)
                await asyncio.sleep(0.1)
            # Atualização final para refletir o estado do último chunk
            player_controls.update(total_chunks)
        except asyncio.CancelledError:
            return

    async def _producer_wrapper(
        chunks_text: list[str],
        voice: str,
        rate: str,
        queue: asyncio.Queue,
    ) -> None:
        # Wrapper local do stream_to_queue: duplica cada chunk para last_audio_chunks
        # (necessário para o "Salvar MP3", já que a fila só guarda chunks consumidos).
        # Mantém a mesma garantia do stream_to_queue: QUEUE_END no finally.
        try:
            async for audio in synthesize_chunks(chunks_text, voice, rate=rate):
                last_audio_chunks.append(audio)
                await queue.put(audio)
        finally:
            await queue.put(QUEUE_END)

    async def do_synthesize_and_play() -> None:
        text = text_area.value or ""
        voice = voice_controls.voice_dropdown.value or "pt-BR-FranciscaNeural"
        rate = config.get("default_rate", "+0%")
        if not text.strip():
            return

        play_button.disabled = True
        last_audio_chunks.clear()
        player_controls.reset()
        page.update()

        try:
            chunks_text = chunk(text, language="pt")
            total = len(chunks_text)

            status_text.value = f"Sintetizando… (0/{total})"
            status_text.color = ft.Colors.AMBER_400
            page.update()

            # Salvamento incremental: histórico gravado ANTES do play começar,
            # para sobreviver a crashes (mesma garantia da Fase 4).
            save_history_entry(text=text, voice=voice, rate=rate)
            side_panel.refresh(load_history())

            # Streaming progressivo: producer sintetiza e enfileira;
            # consumer (player.play_queue) toca enquanto producer continua.
            queue: asyncio.Queue[bytes | None] = asyncio.Queue()

            producer = asyncio.create_task(
                _producer_wrapper(chunks_text, voice, rate, queue)
            )
            consumer = asyncio.create_task(player.play_queue(queue))
            tick = asyncio.create_task(_tick_loop(total, consumer))

            current_tasks["producer"] = producer
            current_tasks["consumer"] = consumer
            current_tasks["tick"] = tick

            status_text.value = "Tocando…"
            status_text.color = ft.Colors.GREEN_400
            page.update()

            # Espera ambos terminarem. return_exceptions=True para que uma falha
            # do producer não cancele o consumer antes dele tocar o que já chegou.
            results = await asyncio.gather(producer, consumer, return_exceptions=True)
            tick.cancel()

            # Se o producer falhou, propaga a exceção
            for r in results:
                if isinstance(r, BaseException) and not isinstance(r, asyncio.CancelledError):
                    raise r

            status_text.value = f"Concluído ({total} chunks)."
            status_text.color = ft.Colors.GREY_400
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
        # Cancela qualquer reprodução anterior antes de começar a nova
        await _cancel_all_tasks()
        await player.stop()
        current_tasks["consumer"] = asyncio.create_task(do_synthesize_and_play())

    async def on_stop(e: ft.Event) -> None:
        # Ordem do PLANO: para player primeiro (síncrono), depois cancela tasks
        await player.stop()
        await _cancel_all_tasks()
        status_text.value = "Parado."
        status_text.color = ft.Colors.GREY_400
        page.update()

    async def _cancel_all_tasks() -> None:
        # Cancela producer, consumer e tick — ordem não importa porque o player
        # já foi parado (ou está prestes a ser).
        for key in ("producer", "consumer", "tick"):
            task = current_tasks[key]
            if task and not task.done():
                task.cancel()

    async def on_save(e: ft.Event) -> None:
        if not last_audio_chunks:
            show_error("Nada para salvar. Clique em Reproduzir antes.")
            return

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
        # Concatenação binária dos chunks acumulados durante o streaming
        # (parâmetros consistentes — validado na Fase 1)
        path.write_bytes(b"".join(last_audio_chunks))
        status_text.value = f"Salvo em {path.name}"
        status_text.color = ft.Colors.GREEN_400
        page.update()

    async def _load_file_into_textarea(file_path: Path) -> None:
        # Lógica compartilhada entre clique no botão "Abrir arquivo" e drop nativo.
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            show_error(f"Formato não suportado: {file_path.suffix}")
            return

        status_text.value = f"Lendo {file_path.name}…"
        status_text.color = ft.Colors.AMBER_400
        page.update()

        try:
            # Extração pode ser pesada (PDF grande) — roda em executor para não travar
            loop = asyncio.get_running_loop()
            extracted_text = await loop.run_in_executor(None, extract, file_path)
            text_area.value = extracted_text
            on_text_change(None)
            status_text.value = f"Carregado {file_path.name} ({len(extracted_text)} chars)"
            status_text.color = ft.Colors.GREEN_400
            page.update()
        except ExtractorError as exc:
            show_error(str(exc))
            status_text.value = "Erro ao ler arquivo."
            status_text.color = ft.Colors.RED_400
            page.update()

    async def on_open_file(e: ft.Event) -> None:
        # Abre o file picker pra escolher um arquivo.
        result = await file_picker.pick_files(
            dialog_title="Abrir arquivo",
            allowed_extensions=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
            allow_multiple=False,
        )
        if not result:
            return
        await _load_file_into_textarea(Path(result[0].path))

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
    # Row de duas colunas: painel lateral à esquerda (largura fixa) + main expandida
    main_column = ft.Column(
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
            player_controls.container,
            status_text,
        ],
        spacing=15,
        expand=True,
    )

    page.add(
        ft.Row(
            [side_panel.container, main_column],
            spacing=15,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )

    # Aplica volume inicial salvo (default 1.0)
    await player.set_volume(float(config.get("default_volume", 1.0)))

    # Shutdown limpo
    async def on_close_handler() -> None:
        logger.info("Fechando app — limpando estado")
        await player.stop()
        await _cancel_all_tasks()

    page.on_close = lambda e: asyncio.create_task(on_close_handler())
