# tests/test_storage.py
# Testes do core/storage.py — função utilitária, load/save com defaults.

import json
from pathlib import Path
from unittest.mock import patch

from core.storage import DEFAULT_CONFIG, ensure_user_dir, load_config, save_config


def test_ensure_user_dir_creates_folder(tmp_path: Path, monkeypatch) -> None:
    # Garante que a pasta é criada se não existir.
    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    result = ensure_user_dir()

    assert result == fake_home / "FizzyBee"
    assert result.exists()
    assert result.is_dir()


def test_ensure_user_dir_idempotent(tmp_path: Path, monkeypatch) -> None:
    # Chamar duas vezes não dá erro.
    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    ensure_user_dir()
    ensure_user_dir()  # não deve levantar


def test_load_config_returns_defaults_when_missing(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    config = load_config()

    assert config == DEFAULT_CONFIG
    # Garante que devolve uma cópia (mutar não afeta defaults)
    config["default_voice"] = "outra"
    assert DEFAULT_CONFIG["default_voice"] != "outra"


def test_save_and_load_round_trip(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    new_config = {"default_voice": "pt-BR-AntonioNeural", "default_rate": "+10%"}
    save_config(new_config)
    loaded = load_config()

    assert loaded["default_voice"] == "pt-BR-AntonioNeural"
    assert loaded["default_rate"] == "+10%"


def test_load_config_corrupted_json_returns_defaults(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    user_dir = ensure_user_dir()
    (user_dir / "config.json").write_text("isso não é JSON {{{")

    config = load_config()

    assert config == DEFAULT_CONFIG


def test_load_config_merges_missing_fields(tmp_path: Path, monkeypatch) -> None:
    # Forward-compat: config antigo com campos faltantes recebe defaults nos novos.
    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    user_dir = ensure_user_dir()
    (user_dir / "config.json").write_text(json.dumps({"default_voice": "pt-BR-AntonioNeural"}))

    config = load_config()

    assert config["default_voice"] == "pt-BR-AntonioNeural"
    assert config["default_rate"] == DEFAULT_CONFIG["default_rate"]
    # Forward-compat: campos novos (Fase 3) também recebem defaults quando ausentes
    assert config["default_locale"] == DEFAULT_CONFIG["default_locale"]
    assert config["default_volume"] == DEFAULT_CONFIG["default_volume"]


def test_default_config_has_phase3_fields() -> None:
    # Garante que Fase 3 adicionou todos os campos esperados (locale, rate, volume)
    assert DEFAULT_CONFIG["default_locale"] == "pt-BR"
    assert DEFAULT_CONFIG["default_rate"] == "+0%"
    assert DEFAULT_CONFIG["default_volume"] == 1.0
    assert 0.0 <= DEFAULT_CONFIG["default_volume"] <= 1.0
