# -*- coding: utf-8 -*-
"""
Провайдер DaData для получения информации о компаниях
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from pydantic import BaseModel

from domain.models import CompanyBase
from core.logger import setup_logging

log = setup_logging()


class DaDataConfig(BaseModel):
    """Конфигурация DaData"""
    api_key: str
    secret_key: Optional[str] = None
    base_url: str = "https://suggestions.dadata.ru/suggestions/api/4_1/rs"
    timeout: int = 10


class DaDataProvider:
    """Провайдер для работы с DaData API"""
    
    def __init__(self, config: DaDataConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "Authorization": f"Token {self.config.api_key}",
                "Content-Type": "application/json",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def suggest_party(self, query: str) -> List[Dict[str, Any]]:
        """Поиск компаний по названию"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            response = await self._client.post(
                f"{self.config.base_url}/suggest/party",
                json={"query": query, "count": 5}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("suggestions", [])
        except Exception as e:
            log.error("DaData suggest_party failed", error=str(e), query=query)
            raise
    
    async def find_party(self, inn: str) -> Optional[Dict[str, Any]]:
        """Получение полной информации о компании по ИНН"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            response = await self._client.post(
                f"{self.config.base_url}/findById/party",
                json={"query": inn}
            )
            response.raise_for_status()
            data = response.json()
            suggestions = data.get("suggestions", [])
            return suggestions[0] if suggestions else None
        except Exception as e:
            log.error("DaData find_party failed", error=str(e), inn=inn)
            raise
    
    def parse_company_data(self, data: Dict[str, Any]) -> CompanyBase:
        """Парсинг данных компании из ответа DaData"""
        if not data:
            raise ValueError("Empty data provided")
        
        # Извлекаем данные из структуры DaData
        company_data = data.get("data", {})
        
        # Определяем статус компании
        status_map = {
            "ACTIVE": "ACTIVE",
            "LIQUIDATING": "LIQUIDATING", 
            "LIQUIDATED": "LIQUIDATED",
        }
        state = company_data.get("state", {})
        status = status_map.get(state.get("status"), "UNKNOWN")
        
        # Парсим даты
        registration_date = None
        liquidation_date = None
        
        if reg_date := company_data.get("state", {}).get("registration_date"):
            try:
                registration_date = datetime.fromisoformat(reg_date.replace("Z", "+00:00")).date()
            except (ValueError, AttributeError):
                pass
        
        if liq_date := company_data.get("state", {}).get("liquidation_date"):
            try:
                liquidation_date = datetime.fromisoformat(liq_date.replace("Z", "+00:00")).date()
            except (ValueError, AttributeError):
                pass
        
        # Адрес
        address_data = company_data.get("address", {})
        address = address_data.get("value") if address_data else None
        address_qc = str(address_data.get("qc", "")) if address_data else None
        
        # Руководство
        management = company_data.get("management", {})
        management_name = management.get("name") if management else None
        management_post = management.get("post") if management else None
        
        return CompanyBase(
            inn=company_data.get("inn", ""),
            ogrn=company_data.get("ogrn"),
            kpp=company_data.get("kpp"),
            name_full=company_data.get("name", {}).get("full_with_opf", ""),
            name_short=company_data.get("name", {}).get("short_with_opf"),
            registration_date=registration_date,
            liquidation_date=liquidation_date,
            status=status,
            okved=company_data.get("okved"),
            address=address,
            address_qc=address_qc,
            management_name=management_name,
            management_post=management_post,
            authorized_capital=company_data.get("capital"),
        )


async def get_company_by_inn(inn: str, api_key: str, secret_key: Optional[str] = None) -> Optional[CompanyBase]:
    """Получить информацию о компании по ИНН"""
    config = DaDataConfig(api_key=api_key, secret_key=secret_key)
    
    async with DaDataProvider(config) as provider:
        try:
            data = await provider.find_party(inn)
            if data:
                return provider.parse_company_data(data)
            return None
        except Exception as e:
            log.error("Failed to get company data", inn=inn, error=str(e))
            return None


async def search_company_by_name(name: str, api_key: str, secret_key: Optional[str] = None) -> List[CompanyBase]:
    """Поиск компаний по названию"""
    config = DaDataConfig(api_key=api_key, secret_key=secret_key)
    
    async with DaDataProvider(config) as provider:
        try:
            suggestions = await provider.suggest_party(name)
            companies = []
            
            for suggestion in suggestions:
                try:
                    company = provider.parse_company_data(suggestion)
                    companies.append(company)
                except Exception as e:
                    log.warning("Failed to parse company suggestion", error=str(e))
                    continue
            
            return companies
        except Exception as e:
            log.error("Failed to search companies", name=name, error=str(e))
            return []
