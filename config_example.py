# -*- coding: utf-8 -*-
"""
Пример конфигурации для BizScan Bot
Скопируйте этот файл в settings.py и заполните реальными значениями
"""

# === Telegram ===
BOT_TOKEN = "your_bot_token_here"

# === DaData API ===
DADATA_API_KEY = "your_dadata_api_key_here"
DADATA_SECRET_KEY = "your_dadata_secret_key_here"

# === Реестр МСП ===
MSME_DATA_URL = "https://ofd.nalog.ru/opendata/7707329152-rsmp/data-20241201-structure-20141120.csv"
MSME_LOCAL_FILE = None  # Путь к локальному файлу МСП
FEATURE_MSME = True

# === ЕФРСБ (банкротство) ===
EFRSB_API_URL = "https://api-assist.com/efrsb"
EFRSB_API_KEY = "your_efrsb_api_key_here"
FEATURE_EFRSB = False

# === КАД (арбитраж) ===
KAD_API_URL = "https://api-assist.com/kad"
KAD_API_KEY = "your_kad_api_key_here"
FEATURE_KAD = False
KAD_MAX_CASES = 5

# === Общие настройки ===
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

# === Кэширование ===
CACHE_TTL_HOURS = 24
SQLITE_PATH = "data/cache.db"

# === Брендирование ===
BRAND_NAME = "BizScan"
BRAND_LINK = None

# === Логирование ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "json"
