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
FEEDBACK_CHAT_ID = os.getenv("FEEDBACK_CHAT_ID", "")


# === Data Source Configuration === (OFData only)
DATASOURCE = "ofdata"
OFDATA_API = os.getenv("OFDATA_API", "https://api.ofdata.ru/v2")
OFDATA_KEY = os.getenv("OFDATA_KEY")
FEATURE_OFDATA = _get_bool("FEATURE_OFDATA", True)

# === Removed: МСП, ЕФРСБ, КАД ===

# === Removed: ГИР БО, ЕИС, РАР, Прозрачный бизнес ===

# === Общие настройки ===
REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 10)
MAX_RETRIES = _get_int("MAX_RETRIES", 2)

# === Database Configuration ===
# Database type: sqlite or postgresql
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")

# SQLite settings (legacy)
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/cache.db")

# PostgreSQL settings
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = _get_int("POSTGRES_PORT", 5432)
POSTGRES_DB = os.getenv("POSTGRES_DB", "bizscan")
POSTGRES_USER = os.getenv("POSTGRES_USER", "bizscan")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Database URL for SQLAlchemy
if DATABASE_TYPE == "postgresql":
    DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
else:
    DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"

# === Кэширование ===
CACHE_TTL_HOURS = _get_int("CACHE_TTL_HOURS", 24)

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
# OpenAI отключён — переменные оставлены для совместимости, но не используются
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_GAMMA = os.getenv("OPENAI_MODEL_GAMMA", "")

# === Gamma Generate API (beta) ===
ENABLE_GAMMA_PDF = _get_bool("ENABLE_GAMMA_PDF", False)
GAMMA_API_KEY = os.getenv("GAMMA_API_KEY", "")
GAMMA_API_BASE = os.getenv("GAMMA_API_BASE", "https://public-api.gamma.app/v0.2")
GAMMA_THEME = os.getenv("GAMMA_THEME", "")
GAMMA_NUM_CARDS = _get_int("GAMMA_NUM_CARDS", 40)  # 0 = не ограничивать
# Режим обработки текста для Gamma (preserve|auto|raw) — по умолчанию preserve
GAMMA_TEXT_MODE = os.getenv("GAMMA_TEXT_MODE", "preserve")
GAMMA_LONG_INSTRUCTIONS = (
    "Сделай структурированный аналитический отчёт по данным. Сохраняй весь объём, при избытке — разбивай на секции/страницы. "
    "Ссылки (ЕГРЮЛ/ФНС/ФИПС и др.) — кликабельные. "
    "Финансы: только рубли (₽); никогда не используй символ '$' (заменяй на '₽' или 'руб.') и англ. сокращения (в т.ч. 'B' для миллиардов). "
    "Все подписи осей и графиков должны использовать '₽' или 'руб.' вместо '$'. "
    "Числа показывай полностью без сокращений и многоточий, используй пробел как разделитель тысяч (например, 1 234 567). "
    "Без вводящих в заблуждение сокращений. "
    "Структура: 1) Общие сведения (название, ИНН/ОГРН, дата регистрации, статус, форма, управление, ОКВЭД). "
    "2) Финансы: таблицы по выручке, прибыли, активам, обязательствам, капиталу за 3–5 лет; графики с подписями осей/единиц/валюты; "
    "график активов и график выручки формируй раздельно. Добавь комментарии (тренды, аномалии, факторы) и вывод. "
    "3) Налоги/задолженности. 4) Суды (крупные — подробно, прочие — списком). 5) Связи (диаграмма, роли/доли). 6) Риски и рекомендация. "
    "Стиль: русский язык; избегай декоративных изображений; визуализации — осмысленные графики/диаграммы/таблицы; "
    "графики информативные (подписи, легенда, периоды). Каждый раздел самодостаточен."
)

# Короткая англоязычная инструкция для additionalInstructions (<=500 chars)
GAMMA_COMPACT_INSTRUCTIONS = os.getenv(
    "GAMMA_COMPACT_INSTRUCTIONS",
    (
        "Produce a super-detailed analytical report in Russian. "
        "Keep all facts, split into multiple pages, make links clickable. "
        "Use ₽ only and never output \"$\" (replace it with ₽ or the word 'руб.'); avoid English short forms. "
        "Axis labels must use ₽ instead of $. Show full numbers without ellipses or abbreviations, use a space as the thousands separator (e.g. 1 234 567), and never truncate numbers with dots. "
        "Separate charts for Assets and Revenue."
    ),
)

# Тайминги ожидания Gamma (секунды)
GAMMA_POLL_TIMEOUT_SEC = _get_int("GAMMA_POLL_TIMEOUT_SEC", 1200)   # 15 минут по умолчанию
GAMMA_POLL_INTERVAL_SEC = _get_int("GAMMA_POLL_INTERVAL_SEC", 20)   # опрос каждые 5 сек

# === Цены ===
# Стоимость формирования отчёта (руб.) — настраивается через переменную окружения REPORT_PRICE
REPORT_PRICE = _get_int("REPORT_PRICE", 390)
# Возможность отключить оплату, чтобы тестировать генерацию
ENABLE_PAYMENTS = _get_bool("ENABLE_PAYMENTS", False)

# === Robokassa ===
ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN", "")
ROBOKASSA_PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1", "")
ROBOKASSA_PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2", "")
ROBOKASSA_IS_TEST = _get_bool("ROBOKASSA_IS_TEST", True)
ROBOKASSA_BASE_URL = os.getenv("ROBOKASSA_BASE_URL", "https://auth.robokassa.ru/Merchant/Index.aspx")
RESULT_URL = os.getenv("RESULT_URL", "https://your.domain/robokassa/result")
SUCCESS_URL = os.getenv("SUCCESS_URL", "https://your.domain/robokassa/success")
FAIL_URL = os.getenv("FAIL_URL", "https://your.domain/robokassa/fail")
ROBOKASSA_REFUND_URL = os.getenv("ROBOKASSA_REFUND_URL", "https://services.robokassa.ru/PartnerRegisterService/api/Operation/RefundOperation")
ROBOKASSA_PARTNER_ID = os.getenv("ROBOKASSA_PARTNER_ID", "")

# === Логирование ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

# === Queue System Configuration ===
# Gamma API queue settings
GAMMA_QUEUE_MAX_WORKERS = _get_int("GAMMA_QUEUE_MAX_WORKERS", 2)  # Max concurrent Gamma requests
GAMMA_DAILY_LIMIT = _get_int("GAMMA_DAILY_LIMIT", 50)  # Daily limit for Gamma generations
GAMMA_RATE_LIMIT_PER_MINUTE = _get_int("GAMMA_RATE_LIMIT_PER_MINUTE", 5)  # Requests per minute

# OFData API queue settings  
OFDATA_QUEUE_MAX_WORKERS = _get_int("OFDATA_QUEUE_MAX_WORKERS", 5)  # Max concurrent OFData requests
OFDATA_RATE_LIMIT_PER_MINUTE = _get_int("OFDATA_RATE_LIMIT_PER_MINUTE", 30)  # Requests per minute
OFDATA_RATE_LIMIT_PER_HOUR = _get_int("OFDATA_RATE_LIMIT_PER_HOUR", 1000)  # Requests per hour

# Queue processing intervals (seconds)
QUEUE_PROCESS_INTERVAL = _get_int("QUEUE_PROCESS_INTERVAL", 1)  # How often to process queue
QUEUE_CLEANUP_INTERVAL = _get_int("QUEUE_CLEANUP_INTERVAL", 300)  # Cleanup old tasks every 5 minutes

