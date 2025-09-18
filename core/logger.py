# -*- coding: utf-8 -*-
import logging
import logging.handlers
import structlog
import os
from pathlib import Path

_logger_initialized = False

def setup_logging():
    global _logger_initialized
    
    if not _logger_initialized:
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
        
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[file_handler, console_handler]
        )
        
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
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
