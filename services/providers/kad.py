# -*- coding: utf-8 -*-
"""
Провайдер для работы с КАД (арбитражные дела)
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from pydantic import BaseModel

from domain.models import ArbitrationInfo
from core.logger import setup_logging

log = setup_logging()


class KadConfig(BaseModel):
    """Конфигурация для КАД"""
    api_url: str = "https://api-assist.com/kad"
    api_key: Optional[str] = None
    timeout: int = 15
    enabled: bool = False
    max_cases: int = 5


class KadProvider:
    """Провайдер для работы с КАД API"""
    
    def __init__(self, config: KadConfig):
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
    
    async def get_arbitration_cases(self, inn: str) -> ArbitrationInfo:
        """Получает арбитражные дела по ИНН"""
        if not self.config.enabled or not self._client:
            return ArbitrationInfo(total=0, cases=[])
        
        try:
            # Ищем дела по ИНН
            response = await self._client.post(
                f"{self.config.api_url}/search",
                json={
                    "inn": inn, 
                    "limit": self.config.max_cases,
                    "sort": "date_desc"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            cases = data.get("cases", [])
            total = data.get("total", 0)
            
            # Форматируем дела для вывода
            formatted_cases = []
            for case in cases:
                formatted_case = {
                    "id": case.get("id"),
                    "number": case.get("number"),
                    "date": case.get("date"),
                    "roles": case.get("roles", []),
                    "instance": case.get("instance"),
                    "url": case.get("url")
                }
                formatted_cases.append(formatted_case)
            
            return ArbitrationInfo(
                total=total,
                cases=formatted_cases
            )
            
        except Exception as e:
            log.error("KAD search failed", inn=inn, error=str(e))
            return ArbitrationInfo(total=0, cases=[])


async def get_arbitration_cases(
    inn: str,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    enabled: bool = False,
    max_cases: int = 5
) -> ArbitrationInfo:
    """Получает арбитражные дела для компании"""
    config = KadConfig(
        api_url=api_url or "https://api-assist.com/kad",
        api_key=api_key,
        enabled=enabled,
        max_cases=max_cases
    )
    
    async with KadProvider(config) as provider:
        return await provider.get_arbitration_cases(inn)
