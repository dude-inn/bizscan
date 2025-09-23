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

# === Gamma Generate API (beta) ===
ENABLE_GAMMA_PDF = _get_bool("ENABLE_GAMMA_PDF", False)
GAMMA_API_KEY = os.getenv("GAMMA_API_KEY", "")
GAMMA_API_BASE = os.getenv("GAMMA_API_BASE", "https://public-api.gamma.app/v0.2")
GAMMA_THEME = os.getenv("GAMMA_THEME", "")
GAMMA_NUM_CARDS = _get_int("GAMMA_NUM_CARDS", 0)  # 0 = не ограничивать
GAMMA_ADDITIONAL_INSTRUCTIONS = (
    "Составь подробный аналитический отчёт о компании на основе данных. "
    "Структура отчёта: "
    "1) Общие сведения: название компании, ИНН/ОГРН, дата регистрации, статус (действующая/ликвидирована), "
    "форма собственности, структура управления (директор, учредители, владельцы долей/акций), "
    "основной вид деятельности (ОКВЭД). Все ссылки на госисточники (ЕГРЮЛ, ФНС, ФИПС и др.) должны быть кликабельными. "
    "2) Финансы: сводные таблицы по ключевым показателям (выручка, прибыль, активы, обязательства, капитал), "
    "динамика за последние 3–5 лет, графики роста/падения и сравнения по годам, краткий вывод о финансовом состоянии. "
    "3) Налоги и задолженности: налоговые платежи, недоимки, штрафы, проблемы (банкротство, арбитражные дела, санкции, блокировки). "
    "4) Суды: подробно выдели крупные дела (суммы, стадии, стороны), остальные перечисли списком. "
    "5) Связи: построй диаграмму связей в формате фамильного дерева, включая учредителей, бенефициаров, связанные компании и дочерние общества. "
    "Сверху — владельцы, ниже — компания, ещё ниже — дочерние/аффилированные компании. "
    "6) Риски и вывод: итоговая оценка надёжности компании, основные риски (финансовые, налоговые, судебные, управленческие), "
    "заключение — стоит или не стоит сотрудничать. "
    "Формат и стиль: язык русский, использовать уменьшенный шрифт, чтобы на одной странице помещалось много информации, "
    "избегать крупных заголовков и пустого пространства, делать подачу плотной и насыщенной в стиле аналитического отчёта. "
    "Добавлять графики, таблицы и диаграммы. Все ссылки должны быть кликабельными."
)


# === Логирование ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")