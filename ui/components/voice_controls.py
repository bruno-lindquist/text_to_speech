# ui/components/voice_controls.py
# Componente Flet com 2 dropdowns (idioma → voz) + slider de velocidade.
# Volume NÃO está aqui — fica no player_controls (volume é do player, não do edge-tts).

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from core.tts_engine import Voice

# Limites de rate aceitos pelo edge-tts (validados na Fase 3 — fora desse range,
# o serviço aceita mas a qualidade degrada).
RATE_MIN = -50
RATE_MAX = 100
RATE_STEP = 5


def rate_to_string(rate_pct: int) -> str:
    # Converte int (-25) para o formato string exigido pelo edge-tts ("-25%" ou "+25%")
    sign = "+" if rate_pct >= 0 else ""
    return f"{sign}{rate_pct}%"


def rate_from_string(rate_str: str) -> int:
    # "+10%" -> 10 ; "-25%" -> -25
    return int(rate_str.rstrip("%"))


@dataclass
class VoiceControls:
    # Bundle dos controles para o app principal acessar.
    locale_dropdown: ft.Dropdown
    voice_dropdown: ft.Dropdown
    rate_slider: ft.Slider
    container: ft.Control  # o que vai no layout


def build_voice_controls(
    voices: list[Voice],
    initial_locale: str,
    initial_voice: str,
    initial_rate: str,
    on_voice_change: Callable[[str, str], None],  # (locale, voice_short_name)
    on_rate_change: Callable[[str], None],         # rate como "+10%"
) -> VoiceControls:
    # Monta os 3 controles e devolve um bundle pronto pra ser colocado na página.
    # Os callbacks são chamados quando o usuário muda algo (responsabilidade do caller persistir).

    # Locales únicos, ordenados
    locales = sorted({v.locale for v in voices})

    # Se o locale salvo não está mais disponível, cai no primeiro
    if initial_locale not in locales:
        initial_locale = locales[0] if locales else "pt-BR"

    def voices_for(locale: str) -> list[Voice]:
        return [v for v in voices if v.locale == locale]

    def voice_options_for(locale: str) -> list[ft.DropdownOption]:
        return [
            ft.DropdownOption(
                key=v.short_name,
                text=f"{v.friendly_name} ({v.gender[0]})",  # "Francisca (F)"
            )
            for v in voices_for(locale)
        ]

    locale_dropdown = ft.Dropdown(
        label="Idioma",
        width=180,
        options=[ft.DropdownOption(key=loc, text=loc) for loc in locales],
        value=initial_locale,
    )

    initial_voice_options = voice_options_for(initial_locale)
    voice_value = (
        initial_voice
        if any(opt.key == initial_voice for opt in initial_voice_options)
        else (initial_voice_options[0].key if initial_voice_options else None)
    )

    voice_dropdown = ft.Dropdown(
        label="Voz",
        width=280,
        options=initial_voice_options,
        value=voice_value,
    )

    rate_slider = ft.Slider(
        min=RATE_MIN,
        max=RATE_MAX,
        value=rate_from_string(initial_rate),
        divisions=(RATE_MAX - RATE_MIN) // RATE_STEP,
        label="Velocidade: {value}%",
        width=300,
    )

    # --- Handlers internos ---
    def _on_locale_change(_e: ft.Event) -> None:
        new_locale = locale_dropdown.value or locales[0]
        new_options = voice_options_for(new_locale)
        voice_dropdown.options = new_options
        # Mantém a voz se ainda estiver disponível, senão pega a primeira
        if not any(opt.key == voice_dropdown.value for opt in new_options):
            voice_dropdown.value = new_options[0].key if new_options else None
        voice_dropdown.update()
        on_voice_change(new_locale, voice_dropdown.value or "")

    def _on_voice_change(_e: ft.Event) -> None:
        on_voice_change(locale_dropdown.value or locales[0], voice_dropdown.value or "")

    def _on_rate_change(_e: ft.Event) -> None:
        on_rate_change(rate_to_string(int(rate_slider.value)))

    locale_dropdown.on_change = _on_locale_change
    voice_dropdown.on_change = _on_voice_change
    rate_slider.on_change = _on_rate_change

    container = ft.Row(
        [locale_dropdown, voice_dropdown, rate_slider],
        spacing=15,
        wrap=True,
    )

    return VoiceControls(
        locale_dropdown=locale_dropdown,
        voice_dropdown=voice_dropdown,
        rate_slider=rate_slider,
        container=container,
    )
