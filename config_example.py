# -*- coding: utf-8 -*-
"""
Пример конфигурации для BizScan Bot
Скопируйте этот файл в settings.py и заполните реальными значениями
"""

# === Telegram ===
BOT_TOKEN = "your_bot_token_here"

# === Data Source Configuration (OFData only) ===
DATASOURCE = "ofdata"


# === OFData API (для поиска по названию) ===
OFDATA_API = "https://ofdata.ru/api"
OFDATA_KEY = "your_ofdata_api_key_here"
OFDATA_RATE_LIMIT_QPM = 70

# OFData endpoint paths
OFDATA_PATH_SEARCH = "/v2/search"
OFDATA_PATH_COMPANY = "/v2/company"
OFDATA_PATH_FINANCES = "/v2/finances"
OFDATA_PATH_LEGAL_CASES = "/v2/legal-cases"
OFDATA_PATH_CONTRACTS = "/v2/contracts"
OFDATA_PATH_ENFORCEMENTS = "/v2/enforcements"


# === Removed: МСП, ЕФРСБ, КАД ===

# === Removed: ГИР БО, ЕИС, РАР, Прозрачный бизнес ===

# === Общие настройки ===
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

# === Кэширование ===
CACHE_TTL_HOURS = 24
SQLITE_PATH = "data/cache.db"

# === Брендирование ===
BRAND_NAME = "BizScan"
BRAND_LINK = None

# Web search providers removed

# === OpenAI для ИИ-обогащения ===
# OpenAI disabled; keep placeholders for compatibility
OPENAI_API_KEY = ""
OPENAI_MODEL_GAMMA = ""

# === TTL Settings (в часах) ===
TTL_COUNTERPARTY_H = 72
TTL_FINANCE_H = 168
TTL_PAIDTAX_H = 168
TTL_ARBITRAGE_H = 12

# === Логирование ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "json"
