# -*- coding: utf-8 -*-
import logging
import logging.handlers
import structlog
import os
from pathlib import Path

_logger_initialized = False
_configured_level = None
_configured_format = None

from typing import Optional

def setup_logging(log_level: Optional[str] = None, log_format: Optional[str] = None):
    global _logger_initialized
    global _configured_level, _configured_format
    
    # Idempotent with possibility to upgrade level/format once
    if not _logger_initialized:
        _configured_level = (log_level or os.getenv("LOG_LEVEL") or "INFO").upper()
        _configured_format = (log_format or os.getenv("LOG_FORMAT") or "text").lower()
        level_value = getattr(logging, _configured_level, logging.INFO)
        # Создаем папку logs если её нет
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Удаляем старый лог-файл при запуске (если не заблокирован)
        log_file = logs_dir / "bot.log"
        if log_file.exists():
            try:
                log_file.unlink()
            except PermissionError:
                # Файл заблокирован другим процессом, пропускаем удаление
                pass
        
        # Настраиваем логирование в файл с ротацией по размеру (5MB)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=1,         # только 1 backup файл
            encoding='utf-8'
        )
        
        console_handler = logging.StreamHandler()
        
        # Console format readable, file structured
        console_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        file_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        logging.basicConfig(level=level_value, handlers=[file_handler, console_handler])
        
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(level_value),
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.KeyValueRenderer(key_order=["event", "logger", "level"]),
            ],
        )
        _logger_initialized = True
    
    return structlog.get_logger("bizscan")


def get_logger(name: str = "bizscan"):
    """Получить логгер по имени"""
    return structlog.get_logger(name)
