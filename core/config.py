# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass
from typing import Dict, Any
import importlib

@dataclass
class Settings:
    BOT_TOKEN: str
    RUSPROFILE_COOKIES: Dict[str, str]
    RUSPROFILE_HEADERS: Dict[str, str]
    REQUESTS_RPS: float
    REQUEST_TIMEOUT: int
    SEARCH_PAGE_SIZE: int
    CACHE_TTL_MIN: int
    SQLITE_PATH: str
    PAYMENTS_ENABLED: bool
    PAYMENT_AMOUNT_RUB: int
    YOOKASSA_SHOP_ID: str
    YOOKASSA_API_KEY: str
    BRAND_NAME: str
    BRAND_LINK: str
    DATE_FORMAT: str

def load_settings() -> Settings:
    cfg = importlib.import_module("settings")
    return Settings(
        BOT_TOKEN=getattr(cfg, "BOT_TOKEN", ""),
        RUSPROFILE_COOKIES=getattr(cfg, "RUSPROFILE_COOKIES", {}),
        RUSPROFILE_HEADERS=getattr(cfg, "RUSPROFILE_HEADERS", {}),
        REQUESTS_RPS=getattr(cfg, "REQUESTS_RPS", 0.5),
        REQUEST_TIMEOUT=getattr(cfg, "REQUEST_TIMEOUT", 30),
        SEARCH_PAGE_SIZE=getattr(cfg, "SEARCH_PAGE_SIZE", 10),
        CACHE_TTL_MIN=getattr(cfg, "CACHE_TTL_MIN", 30),
        SQLITE_PATH=getattr(cfg, "SQLITE_PATH", "data/cache.db"),
        PAYMENTS_ENABLED=getattr(cfg, "PAYMENTS_ENABLED", False),
        PAYMENT_AMOUNT_RUB=getattr(cfg, "PAYMENT_AMOUNT_RUB", 70),
        YOOKASSA_SHOP_ID=getattr(cfg, "YOOKASSA_SHOP_ID", ""),
        YOOKASSA_API_KEY=getattr(cfg, "YOOKASSA_API_KEY", ""),
        BRAND_NAME=getattr(cfg, "BRAND_NAME", "BizScan"),
        BRAND_LINK=getattr(cfg, "BRAND_LINK", ""),
        DATE_FORMAT=getattr(cfg, "DATE_FORMAT", "%d.%m.%Y"),
    )
