# core/logger.py
# Configuração centralizada do loguru. Importar antes de qualquer logger.info().

import os
import sys
from loguru import logger

from core.storage import ensure_user_dir

# Flag para evitar configurar duas vezes se o módulo for re-importado
_configured = False


def setup_logger() -> None:
    # Configura loguru uma única vez:
    # - console: INFO em dev, WARNING em produção (frozen pelo PyInstaller)
    # - arquivo: ~/FizzyBee/logs/fizzy_bee.log com rotação diária, retenção 7 dias
    # - env var FIZZYBEE_LOG_LEVEL sobrescreve o nível detectado automaticamente
    global _configured
    if _configured:
        return

    # Detecta dev vs produção
    is_frozen = getattr(sys, "frozen", False)
    default_level = "WARNING" if is_frozen else "INFO"
    level = os.environ.get("FIZZYBEE_LOG_LEVEL", default_level).upper()

    # Garante que ~/FizzyBee/logs/ existe
    logs_dir = ensure_user_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Remove sinks default do loguru (que vão pro stderr sem formatação custom)
    logger.remove()

    # Console
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Arquivo
    logger.add(
        logs_dir / "fizzy_bee.log",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="00:00",  # rotaciona à meia-noite
        retention="7 days",
        encoding="utf-8",
    )

    _configured = True
    logger.info(f"Logger configurado (level={level}, frozen={is_frozen})")
