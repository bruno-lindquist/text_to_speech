# tests/test_storage.py
# Testes do core/storage.py — função utilitária, load/save com defaults.

import json
from pathlib import Path
from unittest.mock import patch

from core.storage import (
    DEFAULT_CONFIG,
    MAX_HISTORY,
    SNIPPET_LENGTH,
    clear_history,
    ensure_user_dir,
    load_config,
    load_history,
    save_config,
    save_history_entry,
)


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


# ---------- Histórico (Fase 4) ----------


def test_load_history_returns_empty_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")
    assert load_history() == []


def test_save_and_load_history_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    entry = save_history_entry("texto curto", "pt-BR-FranciscaNeural", "+0%")

    loaded = load_history()
    assert len(loaded) == 1
    assert loaded[0].text == "texto curto"
    assert loaded[0].voice == "pt-BR-FranciscaNeural"
    assert loaded[0].rate == "+0%"
    assert loaded[0].snippet == entry.snippet
    assert loaded[0].timestamp == entry.timestamp


def test_history_order_most_recent_first(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    save_history_entry("primeiro", "pt-BR-FranciscaNeural", "+0%")
    save_history_entry("segundo", "pt-BR-AntonioNeural", "+10%")
    save_history_entry("terceiro", "en-US-AriaNeural", "-25%")

    history = load_history()
    assert [e.text for e in history] == ["terceiro", "segundo", "primeiro"]


def test_history_fifo_caps_at_max(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    # Adiciona MAX_HISTORY + 5 entradas
    for i in range(MAX_HISTORY + 5):
        save_history_entry(f"entrada {i}", "pt-BR-FranciscaNeural", "+0%")

    history = load_history()
    assert len(history) == MAX_HISTORY
    # As 5 mais antigas (0, 1, 2, 3, 4) foram descartadas; a mais nova é a primeira
    assert history[0].text == f"entrada {MAX_HISTORY + 4}"
    assert history[-1].text == "entrada 5"


def test_snippet_truncates_long_text(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    long_text = "a" * 200
    entry = save_history_entry(long_text, "pt-BR-FranciscaNeural", "+0%")

    assert len(entry.snippet) <= SNIPPET_LENGTH + 1  # +1 do "…"
    assert entry.snippet.endswith("…")


def test_snippet_flattens_newlines(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    text_with_newlines = "linha um\n\nlinha dois\nlinha três"
    entry = save_history_entry(text_with_newlines, "pt-BR-FranciscaNeural", "+0%")

    assert "\n" not in entry.snippet
    assert entry.snippet == "linha um linha dois linha três"


def test_clear_history_empties_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    save_history_entry("a", "pt-BR-FranciscaNeural", "+0%")
    save_history_entry("b", "pt-BR-FranciscaNeural", "+0%")
    assert len(load_history()) == 2

    clear_history()
    assert load_history() == []


def test_load_history_corrupted_json_returns_empty(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    user_dir = ensure_user_dir()
    (user_dir / "history.json").write_text("{invalid json")

    assert load_history() == []


def test_load_history_wrong_type_returns_empty(tmp_path: Path, monkeypatch) -> None:
    # Se o JSON for válido mas não for uma lista, devolve [] (não crasha)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    user_dir = ensure_user_dir()
    (user_dir / "history.json").write_text(json.dumps({"not": "a list"}))

    assert load_history() == []


def test_max_history_is_fifty() -> None:
    # Checkpoint do PLANO pede explicitamente FIFO de 50
    assert MAX_HISTORY == 50
