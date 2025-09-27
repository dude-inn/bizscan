# -*- coding: utf-8 -*-
"""
Конфигурация приложения
"""
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
import importlib


@dataclass
class Settings:
    """Настройки приложения"""
    # Telegram
    BOT_TOKEN: str
    # OFData
    OFDATA_KEY: str
    # Database
    DATABASE_TYPE: str
    SQLITE_PATH: str
    # Общие настройки
    REQUEST_TIMEOUT: int
    MAX_RETRIES: int
    CACHE_TTL_HOURS: int
    # Брендирование
    BRAND_NAME: str
    BRAND_LINK: Optional[str]
    # Логирование
    LOG_LEVEL: str
    LOG_FORMAT: str
    # Стоимость и эквайринг
    REPORT_PRICE: int
    ENABLE_PAYMENTS: bool
    ROBOKASSA_MERCHANT_LOGIN: str
    ROBOKASSA_PASSWORD1: str
    ROBOKASSA_PASSWORD2: str
    ROBOKASSA_IS_TEST: bool
    ROBOKASSA_BASE_URL: str
    RESULT_URL: str
    SUCCESS_URL: str
    FAIL_URL: str
    ROBOKASSA_REFUND_URL: str
    ROBOKASSA_PARTNER_ID: Optional[str]


def load_settings() -> Settings:
    """Загружает настройки из settings.py"""
    try:
        cfg = importlib.import_module("settings")
    except Exception as e:
        raise
    try:
        settings = Settings(
            # Telegram
            BOT_TOKEN=getattr(cfg, "BOT_TOKEN", ""),
            # OFData
            OFDATA_KEY=getattr(cfg, "OFDATA_KEY", ""),
            # Database
            DATABASE_TYPE=getattr(cfg, "DATABASE_TYPE", "sqlite"),
            SQLITE_PATH=getattr(cfg, "SQLITE_PATH", "data/cache.db"),
            # Общие настройки
            REQUEST_TIMEOUT=getattr(cfg, "REQUEST_TIMEOUT", 10),
            MAX_RETRIES=getattr(cfg, "MAX_RETRIES", 2),
            CACHE_TTL_HOURS=getattr(cfg, "CACHE_TTL_HOURS", 24),
            # Брендирование
            BRAND_NAME=getattr(cfg, "BRAND_NAME", "BizScan"),
            BRAND_LINK=getattr(cfg, "BRAND_LINK"),
            # Логирование
            LOG_LEVEL=getattr(cfg, "LOG_LEVEL", "INFO"),
            LOG_FORMAT=getattr(cfg, "LOG_FORMAT", "json"),
            # Стоимость и эквайринг
            REPORT_PRICE=getattr(cfg, "REPORT_PRICE", 0),
            ENABLE_PAYMENTS=bool(getattr(cfg, "ENABLE_PAYMENTS", True)),
            ROBOKASSA_MERCHANT_LOGIN=getattr(cfg, "ROBOKASSA_MERCHANT_LOGIN", ""),
            ROBOKASSA_PASSWORD1=getattr(cfg, "ROBOKASSA_PASSWORD1", ""),
            ROBOKASSA_PASSWORD2=getattr(cfg, "ROBOKASSA_PASSWORD2", ""),
            ROBOKASSA_IS_TEST=bool(getattr(cfg, "ROBOKASSA_IS_TEST", True)),
            ROBOKASSA_BASE_URL=getattr(cfg, "ROBOKASSA_BASE_URL", ""),
            RESULT_URL=getattr(cfg, "RESULT_URL", ""),
            SUCCESS_URL=getattr(cfg, "SUCCESS_URL", ""),
            FAIL_URL=getattr(cfg, "FAIL_URL", ""),
            ROBOKASSA_REFUND_URL=getattr(cfg, "ROBOKASSA_REFUND_URL", ""),
            ROBOKASSA_PARTNER_ID=getattr(cfg, "ROBOKASSA_PARTNER_ID", None),
        )
        return settings
    except Exception as e:
        raise
