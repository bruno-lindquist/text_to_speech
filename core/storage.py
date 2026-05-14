# core/storage.py
# Persistência JSON e função utilitária de pasta do usuário.

import json
from pathlib import Path
from typing import Any

# Voz e taxa padrão usadas quando ainda não há config salva
DEFAULT_CONFIG: dict[str, Any] = {
    "default_voice": "pt-BR-FranciscaNeural",
    "default_rate": "+0%",
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
