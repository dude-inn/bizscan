# -*- coding: utf-8 -*-
"""Все ключевые настройки проекта BizScan Telegram Bot."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv


# Загрузка переменных окружения из .env в корне проекта
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

# === Rusprofile (авторизованная сессия подписчика) ===
# Используем куки из .env: RUSPROFILE_SESSID и RUSPROFILE_CSRF
_RUSPROFILE_SESSID = os.getenv("RUSPROFILE_SESSID")
_RUSPROFILE_CSRF = os.getenv("RUSPROFILE_CSRF")

RUSPROFILE_COOKIES = {}
if _RUSPROFILE_SESSID:
    RUSPROFILE_COOKIES["sessionid"] = _RUSPROFILE_SESSID
if _RUSPROFILE_CSRF:
    RUSPROFILE_COOKIES["csrftoken"] = _RUSPROFILE_CSRF

# Заголовки для запросов к rusprofile
_default_ua = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
_headers_raw = {
    "User-Agent": os.getenv("RUSPROFILE_UA", _default_ua),
    "Referer": os.getenv("RUSPROFILE_REFERER", "https://www.rusprofile.ru/"),
}
if _RUSPROFILE_CSRF:
    _headers_raw["X-CSRFToken"] = _RUSPROFILE_CSRF
RUSPROFILE_HEADERS = {k: str(v) for k, v in _headers_raw.items() if v is not None}

# Лимиты и поведение сети
REQUESTS_RPS = _get_float("REQUESTS_RPS", 0.5)            # запросов в секунду (глобально)
REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 30)          # секунды
SEARCH_PAGE_SIZE = _get_int("SEARCH_PAGE_SIZE", 10)        # кол-во результатов на страницу в боте (локальная пагинация)
CACHE_TTL_MIN = _get_int("CACHE_TTL_MIN", 30)              # TTL кэша (минуты)
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/cache.db")    # путь к SQLite

# === Payments (ЮKassa) ===
PAYMENTS_ENABLED = _get_bool("PAYMENTS_ENABLED", False)
PAYMENT_AMOUNT_RUB = _get_int("PAYMENT_AMOUNT_RUB", 70)
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_API_KEY = os.getenv("YOOKASSA_API_KEY", "")

# Брендирование
BRAND_NAME = os.getenv("BRAND_NAME", "BizScan")
BRAND_LINK = os.getenv("BRAND_LINK")  # по ТЗ из памяти проекта

# Локаль / форматирование
DATE_FORMAT = os.getenv("DATE_FORMAT", "%d.%m.%Y")

# PDF генерация
GENERATE_PDF_FREE = _get_bool("GENERATE_PDF_FREE", True)
