# -*- coding: utf-8 -*-
"""Настройки проекта BizScan - агрегация данных о компаниях"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Загрузка переменных окружения
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# === Telegram ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === DaData API ===
DADATA_API_KEY = os.getenv("DADATA_API_KEY")
DADATA_SECRET_KEY = os.getenv("DADATA_SECRET_KEY")

# === Реестр МСП ===
MSME_DATA_URL = os.getenv(
    "MSME_DATA_URL", 
    "https://ofd.nalog.ru/opendata/7707329152-rsmp/data-20250101-structure-20141120.csv"
)
MSME_LOCAL_FILE = os.getenv("MSME_LOCAL_FILE")  # Путь к локальному файлу МСП
FEATURE_MSME = _get_bool("FEATURE_MSME", True)

# === ЕФРСБ (банкротство) ===
EFRSB_API_URL = os.getenv("EFRSB_API_URL", "https://api-assist.com/efrsb")
EFRSB_API_KEY = os.getenv("EFRSB_API_KEY")
FEATURE_EFRSB = _get_bool("FEATURE_EFRSB", False)

# === КАД (арбитраж) ===
KAD_API_URL = os.getenv("KAD_API_URL", "https://api-assist.com/kad")
KAD_API_KEY = os.getenv("KAD_API_KEY")
FEATURE_KAD = _get_bool("FEATURE_KAD", False)
KAD_MAX_CASES = _get_int("KAD_MAX_CASES", 5)

# === Общие настройки ===
REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 10)
MAX_RETRIES = _get_int("MAX_RETRIES", 2)

# === Кэширование ===
CACHE_TTL_HOURS = _get_int("CACHE_TTL_HOURS", 24)
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/cache.db")

# === Брендирование ===
BRAND_NAME = os.getenv("BRAND_NAME", "BizScan")
BRAND_LINK = os.getenv("BRAND_LINK")

# === Логирование ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")