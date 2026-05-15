# core/storage.py
# Persistência JSON e função utilitária de pasta do usuário.

import json
from pathlib import Path
from typing import Any

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
