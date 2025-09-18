# -*- coding: utf-8 -*-
"""
Провайдер для работы с ЕФРСБ (банкротство)
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from pydantic import BaseModel

from domain.models import BankruptcyInfo
from core.logger import setup_logging

log = setup_logging()


class EfrsbConfig(BaseModel):
    """Конфигурация для ЕФРСБ"""
    api_url: str = "https://api-assist.com/efrsb"
    api_key: Optional[str] = None
    timeout: int = 15
    enabled: bool = False


class EfrsbProvider:
    """Провайдер для работы с ЕФРСБ API"""
    
    def __init__(self, config: EfrsbConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        if not self.config.enabled:
            return self
            
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def check_bankruptcy(self, inn: str) -> BankruptcyInfo:
        """Проверяет информацию о банкротстве"""
        if not self.config.enabled or not self._client:
            return BankruptcyInfo(has_bankruptcy_records=False)
        
        try:
            # Ищем по ИНН
            response = await self._client.post(
                f"{self.config.api_url}/search",
                json={"inn": inn, "limit": 10}
            )
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            
            return BankruptcyInfo(
                has_bankruptcy_records=len(records) > 0,
                records=records
            )
            
        except Exception as e:
            log.error("EFRSB check failed", inn=inn, error=str(e))
            return BankruptcyInfo(has_bankruptcy_records=False)


async def check_bankruptcy_status(
    inn: str, 
    api_url: Optional[str] = None, 
    api_key: Optional[str] = None,
    enabled: bool = False
) -> BankruptcyInfo:
    """Проверяет статус банкротства для компании"""
    config = EfrsbConfig(
        api_url=api_url or "https://api-assist.com/efrsb",
        api_key=api_key,
        enabled=enabled
    )
    
    async with EfrsbProvider(config) as provider:
        return await provider.check_bankruptcy(inn)
