# core/storage.py
# Persistência JSON e função utilitária de pasta do usuário.
# Fase 1: config.json com defaults de voz/rate.
# Fase 4: history.json com FIFO de 50 entradas + salvamento incremental.

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Snippet exibido no painel — chars iniciais do texto, sem quebras de linha.
SNIPPET_LENGTH = 80

# Limite máximo de entradas no histórico (FIFO).
MAX_HISTORY = 50

# Defaults usados quando ainda não há config salva (ou para preencher campos faltantes).
# - default_voice: short_name no formato edge-tts (ex: "pt-BR-FranciscaNeural")
# - default_locale: usado pelo dropdown de idioma para abrir já filtrado
# - default_rate: string no formato edge-tts ("+0%", "-25%", "+50%")
# - default_volume: float 0.0 - 1.0 (aplicado no AudioPlayer, NÃO no edge-tts)
DEFAULT_CONFIG: dict[str, Any] = {
    "default_voice": "pt-BR-FranciscaNeural",
    "default_locale": "pt-BR",
    "default_rate": "+0%",
    "default_volume": 1.0,
}


def ensure_user_dir() -> Path:
    # Devolve ~/FizzyBee/, criando se ainda não existe.
    # Usada por logger.py e por toda persistência.
    user_dir = Path.home() / "FizzyBee"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _config_path() -> Path:
    return ensure_user_dir() / "config.json"


def load_config() -> dict[str, Any]:
    # Lê config.json; se não existir ou estiver corrompido, devolve defaults.
    path = _config_path()
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Garante que campos faltantes recebam defaults (forward-compat)
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    # Escreve config.json com indentação (legível pra debug manual).
    path = _config_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ---------- Histórico ----------


@dataclass
class HistoryEntry:
    # Uma leitura registrada — guarda contexto suficiente para reabrir igual.
    snippet: str       # primeiros 80 chars (sem quebras), exibido no painel
    text: str          # texto completo, restaurado ao clicar no cartão
    voice: str         # short_name no formato edge-tts
    rate: str          # "+0%", "-25%", etc
    timestamp: str     # ISO 8601 UTC


def _history_path() -> Path:
    return ensure_user_dir() / "history.json"


def _make_snippet(text: str) -> str:
    # Quebra de linha vira espaço; trunca em SNIPPET_LENGTH; adiciona "…" se cortou.
    flat = " ".join(text.split())
    if len(flat) <= SNIPPET_LENGTH:
        return flat
    return flat[:SNIPPET_LENGTH].rstrip() + "…"


def load_history() -> list[HistoryEntry]:
    # Lê history.json (lista de dicts); se não existir/corromper, devolve [].
    # Ordem preservada do disco: mais recente primeiro (mantida por save_history_entry).
    path = _history_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return [HistoryEntry(**entry) for entry in data]
    except (json.JSONDecodeError, OSError, TypeError):
        return []


def save_history_entry(text: str, voice: str, rate: str) -> HistoryEntry:
    # Adiciona uma nova entrada no topo do histórico, aplica FIFO (MAX_HISTORY)
    # e persiste em disco. Devolve a entrada criada (útil pro caller atualizar UI).
    entry = HistoryEntry(
        snippet=_make_snippet(text),
        text=text,
        voice=voice,
        rate=rate,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    history = load_history()
    history.insert(0, entry)
    history = history[:MAX_HISTORY]  # FIFO: descarta os mais antigos
    _write_history(history)
    return entry


def clear_history() -> None:
    # Zera o histórico (escreve lista vazia em disco).
    _write_history([])


def _write_history(entries: list[HistoryEntry]) -> None:
    path = _history_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in entries], f, indent=2, ensure_ascii=False)
