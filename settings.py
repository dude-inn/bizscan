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

# === DaData API (REMOVED - using OFData only) ===
# DADATA_API_KEY = os.getenv("DADATA_API_KEY")
# DADATA_SECRET_KEY = os.getenv("DADATA_SECRET_KEY")

# === Data Source Configuration === (OFData only)
DATASOURCE = "ofdata"
OFDATA_API = os.getenv("OFDATA_API", "https://api.ofdata.ru/v2")
OFDATA_KEY = os.getenv("OFDATA_KEY")
FEATURE_OFDATA = _get_bool("FEATURE_OFDATA", True)

# === Реестр МСП ===
MSME_DATA_URL = os.getenv(
    "MSME_DATA_URL", 
    "https://www.nalog.gov.ru/opendata/7707329152-rsmp/data-latest.csv"
)
MSME_LOCAL_FILE = os.getenv("MSME_LOCAL_FILE")  # Путь к локальному файлу МСП
FEATURE_MSME = _get_bool("FEATURE_MSME", False)

# === ЕФРСБ (банкротство) ===
EFRSB_API_URL = os.getenv("EFRSB_API_URL", "https://api-assist.com/efrsb")
EFRSB_API_KEY = os.getenv("EFRSB_API_KEY")
FEATURE_EFRSB = _get_bool("FEATURE_EFRSB", False)

# === КАД (арбитраж) ===
KAD_API_URL = os.getenv("KAD_API_URL", "https://api-assist.com/kad")
KAD_API_KEY = os.getenv("KAD_API_KEY")
FEATURE_KAD = _get_bool("FEATURE_KAD", False)
KAD_MAX_CASES = _get_int("KAD_MAX_CASES", 5)

# === ГИР БО (финансы) ===
GIRBO_BASE_URL = os.getenv("GIRBO_BASE_URL", "https://bo.nalog.gov.ru")
GIRBO_TOKEN = os.getenv("GIRBO_TOKEN")
FEATURE_GIRBO = _get_bool("FEATURE_GIRBO", False)

# === ЕИС (госзакупки) ===
ZAKUPKI_MODE = os.getenv("ZAKUPKI_MODE", "soap")
ZAKUPKI_WSDL_URL = os.getenv("ZAKUPKI_WSDL_URL")
ZAKUPKI_DATASET_URL = os.getenv("ZAKUPKI_DATASET_URL")
FEATURE_ZAKUPKI = _get_bool("FEATURE_ZAKUPKI", False)

# === РАР (лицензии алкоголь) ===
FSRAR_API_URL = os.getenv("FSRAR_API_URL")
FSRAR_DATASET_URL = os.getenv("FSRAR_DATASET_URL")
FEATURE_FSRAR = _get_bool("FEATURE_FSRAR", False)

# === Прозрачный бизнес ===
PB_DATASETS = os.getenv("PB_DATASETS", "{}")
FEATURE_PB = _get_bool("FEATURE_PB", False)

# === Общие настройки ===
REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 10)
MAX_RETRIES = _get_int("MAX_RETRIES", 2)

# === Кэширование ===
CACHE_TTL_HOURS = _get_int("CACHE_TTL_HOURS", 24)
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/cache.db")

# === TTL Settings ===
TTL_COUNTERPARTY_H = _get_int("TTL_COUNTERPARTY_H", 72)
TTL_FINANCE_H = _get_int("TTL_FINANCE_H", 168)
TTL_PAIDTAX_H = _get_int("TTL_PAIDTAX_H", 168)
TTL_ARBITRAGE_H = _get_int("TTL_ARBITRAGE_H", 12)

# === Брендирование ===
BRAND_NAME = os.getenv("BRAND_NAME", "BizScan")
BRAND_LINK = os.getenv("BRAND_LINK")

# Web search providers removed

# === OpenAI для Gamma.app ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_GAMMA = os.getenv("OPENAI_MODEL_GAMMA", "gpt-4o-mini")

# === Логирование ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")