# -*- coding: utf-8 -*-
"""
Пример конфигурации для BizScan Bot
Скопируйте этот файл в settings.py и заполните реальными значениями
"""

# === Telegram ===
BOT_TOKEN = "your_bot_token_here"

# === Data Source Configuration (OFData only) ===
DATASOURCE = "ofdata"

# DataNewton removed

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

# === ГИР БО (финансы) ===
GIRBO_BASE_URL = "https://bo.nalog.gov.ru"
GIRBO_TOKEN = "your_girbo_token_here"
FEATURE_GIRBO = True

# === ЕИС (госзакупки) ===
ZAKUPKI_MODE = "soap"  # soap | dataset
ZAKUPKI_WSDL_URL = "your_zakupki_wsdl_url_here"
ZAKUPKI_DATASET_URL = "your_zakupki_dataset_url_here"
FEATURE_ZAKUPKI = False

# === РАР (лицензии алкоголь) ===
FSRAR_API_URL = "your_fsrar_api_url_here"
FSRAR_DATASET_URL = "your_fsrar_dataset_url_here"
FEATURE_FSRAR = False

# === Прозрачный бизнес ===
PB_DATASETS = '{"addresses": "https://www.nalog.ru/opendata/...", "disqualification": "https://www.nalog.ru/opendata/..."}'
FEATURE_PB = True

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
OPENAI_API_KEY = "your_openai_api_key_here"
OPENAI_MODEL_GAMMA = "gpt-4o-mini"

# === TTL Settings (в часах) ===
TTL_COUNTERPARTY_H = 72
TTL_FINANCE_H = 168
TTL_PAIDTAX_H = 168
TTL_ARBITRAGE_H = 12

# === Логирование ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "json"
