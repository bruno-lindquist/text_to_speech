# tests/test_audio_player.py
# Testes das funções puras do audio_player + métodos com mock.
# Métodos reais (com áudio) são validação manual (ver PLANO).

from core.audio_player import format_time, progress_ratio


def test_format_time_zero() -> None:
    assert format_time(0) == "0:00"


def test_format_time_under_minute() -> None:
    assert format_time(45) == "0:45"


def test_format_time_exact_minute() -> None:
    assert format_time(60) == "1:00"


def test_format_time_over_minute() -> None:
    assert format_time(65) == "1:05"
    assert format_time(125) == "2:05"


def test_format_time_negative_clamped() -> None:
    assert format_time(-10) == "0:00"


def test_format_time_float_truncates() -> None:
    # 125.7s -> 2:05 (não arredonda, trunca)
    assert format_time(125.7) == "2:05"


def test_progress_ratio_zero_total() -> None:
    # Edge case: duração 0 → 0.0 sem ZeroDivisionError
    assert progress_ratio(50, 0) == 0.0


def test_progress_ratio_halfway() -> None:
    assert progress_ratio(50, 100) == 0.5


def test_progress_ratio_complete() -> None:
    assert progress_ratio(100, 100) == 1.0


def test_progress_ratio_overflow_clamped() -> None:
    # Se posição passou da duração, retorna 1.0
    assert progress_ratio(150, 100) == 1.0


def test_progress_ratio_negative_clamped() -> None:
    assert progress_ratio(-10, 100) == 0.0
