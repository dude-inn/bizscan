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
    
    # DaData
    DADATA_API_KEY: str
    DADATA_SECRET_KEY: Optional[str]
    
    # МСП
    MSME_DATA_URL: str
    MSME_LOCAL_FILE: Optional[str]
    FEATURE_MSME: bool
    
    # ЕФРСБ
    EFRSB_API_URL: str
    EFRSB_API_KEY: Optional[str]
    FEATURE_EFRSB: bool
    
    # КАД
    KAD_API_URL: str
    KAD_API_KEY: Optional[str]
    FEATURE_KAD: bool
    KAD_MAX_CASES: int
    
    # ГИР БО
    GIRBO_BASE_URL: str
    GIRBO_TOKEN: Optional[str]
    FEATURE_GIRBO: bool
    
    # ЕИС (госзакупки)
    ZAKUPKI_MODE: str
    ZAKUPKI_WSDL_URL: Optional[str]
    ZAKUPKI_DATASET_URL: Optional[str]
    FEATURE_ZAKUPKI: bool
    
    # РАР (лицензии алкоголь)
    FSRAR_API_URL: Optional[str]
    FSRAR_DATASET_URL: Optional[str]
    FEATURE_FSRAR: bool
    
    # Прозрачный бизнес
    PB_DATASETS: str  # JSON строка
    FEATURE_PB: bool
    
    # Общие настройки
    REQUEST_TIMEOUT: int
    MAX_RETRIES: int
    CACHE_TTL_HOURS: int
    SQLITE_PATH: str
    
    # Брендирование
    BRAND_NAME: str
    BRAND_LINK: Optional[str]
    
    # Логирование
    LOG_LEVEL: str
    LOG_FORMAT: str


def load_settings() -> Settings:
    """Загружает настройки из settings.py"""
    from core.logger import setup_logging
    log = setup_logging()
    
    try:
        log.info("Loading configuration from settings module")
        cfg = importlib.import_module("settings")
        log.info("Settings module imported successfully")
    except Exception as e:
        log.error("Failed to import settings module", error=str(e))
        raise
    
    try:
        log.info("Creating Settings object")
        settings = Settings(
        # Telegram
        BOT_TOKEN=getattr(cfg, "BOT_TOKEN", ""),
        
        # DaData
        DADATA_API_KEY=getattr(cfg, "DADATA_API_KEY", ""),
        DADATA_SECRET_KEY=getattr(cfg, "DADATA_SECRET_KEY"),
        
        # МСП
        MSME_DATA_URL=getattr(cfg, "MSME_DATA_URL", ""),
        MSME_LOCAL_FILE=getattr(cfg, "MSME_LOCAL_FILE"),
        FEATURE_MSME=getattr(cfg, "FEATURE_MSME", True),
        
        # ЕФРСБ
        EFRSB_API_URL=getattr(cfg, "EFRSB_API_URL", ""),
        EFRSB_API_KEY=getattr(cfg, "EFRSB_API_KEY"),
        FEATURE_EFRSB=getattr(cfg, "FEATURE_EFRSB", False),
        
        # КАД
        KAD_API_URL=getattr(cfg, "KAD_API_URL", ""),
        KAD_API_KEY=getattr(cfg, "KAD_API_KEY"),
        FEATURE_KAD=getattr(cfg, "FEATURE_KAD", False),
        KAD_MAX_CASES=getattr(cfg, "KAD_MAX_CASES", 5),
        
        # ГИР БО
        GIRBO_BASE_URL=getattr(cfg, "GIRBO_BASE_URL", "https://bo.nalog.gov.ru"),
        GIRBO_TOKEN=getattr(cfg, "GIRBO_TOKEN"),
        FEATURE_GIRBO=getattr(cfg, "FEATURE_GIRBO", True),
        
        # ЕИС
        ZAKUPKI_MODE=getattr(cfg, "ZAKUPKI_MODE", "soap"),
        ZAKUPKI_WSDL_URL=getattr(cfg, "ZAKUPKI_WSDL_URL"),
        ZAKUPKI_DATASET_URL=getattr(cfg, "ZAKUPKI_DATASET_URL"),
        FEATURE_ZAKUPKI=getattr(cfg, "FEATURE_ZAKUPKI", False),
        
        # РАР
        FSRAR_API_URL=getattr(cfg, "FSRAR_API_URL"),
        FSRAR_DATASET_URL=getattr(cfg, "FSRAR_DATASET_URL"),
        FEATURE_FSRAR=getattr(cfg, "FEATURE_FSRAR", False),
        
        # Прозрачный бизнес
        PB_DATASETS=getattr(cfg, "PB_DATASETS", "{}"),
        FEATURE_PB=getattr(cfg, "FEATURE_PB", True),
        
        # Общие настройки
        REQUEST_TIMEOUT=getattr(cfg, "REQUEST_TIMEOUT", 10),
        MAX_RETRIES=getattr(cfg, "MAX_RETRIES", 2),
        CACHE_TTL_HOURS=getattr(cfg, "CACHE_TTL_HOURS", 24),
        SQLITE_PATH=getattr(cfg, "SQLITE_PATH", "data/cache.db"),
        
        # Брендирование
        BRAND_NAME=getattr(cfg, "BRAND_NAME", "BizScan"),
        BRAND_LINK=getattr(cfg, "BRAND_LINK"),
        
        # Логирование
        LOG_LEVEL=getattr(cfg, "LOG_LEVEL", "INFO"),
        LOG_FORMAT=getattr(cfg, "LOG_FORMAT", "json"),
    )
        
        log.info("Settings object created successfully", 
                bot_token_present=bool(settings.BOT_TOKEN),
                dadata_key_present=bool(settings.DADATA_API_KEY),
                sqlite_path=settings.SQLITE_PATH,
                msme_enabled=settings.FEATURE_MSME,
                efrsb_enabled=settings.FEATURE_EFRSB,
                kad_enabled=settings.FEATURE_KAD)
        return settings
        
    except Exception as e:
        log.error("Failed to create Settings object", error=str(e))
        raise