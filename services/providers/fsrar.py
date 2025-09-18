# -*- coding: utf-8 -*-
"""
Провайдер РАР (Росалкогольрегулирование) - лицензии алкоголь
Источник: fsrar.gov.ru
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, date

import httpx
from pydantic import BaseModel

from domain.models import License
from core.logger import setup_logging

log = setup_logging()


class FsrarConfig(BaseModel):
    """Конфигурация РАР"""
    base_url: str = "https://fsrar.gov.ru"
    api_url: Optional[str] = None
    dataset_url: Optional[str] = None
    timeout: int = 10
    max_retries: int = 2


class FsrarProvider:
    """Провайдер для работы с РАР"""
    
    def __init__(self, config: FsrarConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "User-Agent": "BizScan Bot/1.0",
                "Accept": "application/json, text/csv",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get_fsrar_licenses_api(self, inn: str) -> List[License]:
        """Получает лицензии через API РАР"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching FSRAR licenses via API", inn=inn)
            
            # Поиск лицензий по ИНН
            response = await self._client.get(
                f"{self.config.api_url}/licenses",
                params={"inn": inn}
            )
            response.raise_for_status()
            
            licenses_data = response.json()
            licenses = []
            
            for license_data in licenses_data.get("licenses", []):
                license_obj = License(
                    registry="FSRAR",
                    number=license_data.get("number", ""),
                    activity=license_data.get("activity"),
                    issued_at=datetime.fromisoformat(license_data["issued_at"]).date()
                        if license_data.get("issued_at") else None,
                    valid_to=datetime.fromisoformat(license_data["valid_to"]).date()
                        if license_data.get("valid_to") else None,
                    status=license_data.get("status")
                )
                licenses.append(license_obj)
            
            log.info("FSRAR licenses fetched via API", 
                    inn=inn, 
                    licenses_count=len(licenses))
            return licenses
            
        except Exception as e:
            log.error("Failed to fetch FSRAR licenses via API", 
                     error=str(e), 
                     inn=inn)
            return []
    
    async def get_fsrar_licenses_dataset(self, inn: str) -> List[License]:
        """Получает лицензии из открытых датасетов РАР"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching FSRAR licenses from dataset", inn=inn)
            
            # Загружаем открытые данные по лицензиям
            response = await self._client.get(self.config.dataset_url)
            response.raise_for_status()
            
            # Парсим CSV данные
            import pandas as pd
            import io
            
            df = pd.read_csv(io.StringIO(response.text), encoding='utf-8')
            
            # Фильтруем по ИНН
            company_licenses = df[df['inn'] == inn] if 'inn' in df.columns else pd.DataFrame()
            
            if company_licenses.empty:
                log.warning("No licenses found in dataset", inn=inn)
                return []
            
            licenses = []
            for _, row in company_licenses.iterrows():
                license_obj = License(
                    registry="FSRAR",
                    number=row.get('license_number', ''),
                    activity=row.get('activity'),
                    issued_at=pd.to_datetime(row['issued_at']).date()
                        if pd.notna(row.get('issued_at')) else None,
                    valid_to=pd.to_datetime(row['valid_to']).date()
                        if pd.notna(row.get('valid_to')) else None,
                    status=row.get('status')
                )
                licenses.append(license_obj)
            
            log.info("FSRAR licenses fetched from dataset", 
                    inn=inn, 
                    licenses_count=len(licenses))
            return licenses
            
        except Exception as e:
            log.error("Failed to fetch FSRAR licenses from dataset", 
                     error=str(e), 
                     inn=inn)
            return []
    
    async def get_fsrar_licenses_direct(self, inn: str) -> List[License]:
        """Получает лицензии напрямую с сайта РАР"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching FSRAR licenses directly", inn=inn)
            
            # Поиск на сайте РАР
            search_response = await self._client.get(
                f"{self.config.base_url}/search",
                params={"query": inn, "type": "license"}
            )
            search_response.raise_for_status()
            
            # Парсим HTML ответ (упрощенный)
            licenses = self._parse_licenses_from_html(search_response.text, inn)
            
            log.info("FSRAR licenses fetched directly", 
                    inn=inn, 
                    licenses_count=len(licenses))
            return licenses
            
        except Exception as e:
            log.error("Failed to fetch FSRAR licenses directly", 
                     error=str(e), 
                     inn=inn)
            return []
    
    def _parse_licenses_from_html(self, html_content: str, inn: str) -> List[License]:
        """Парсит лицензии из HTML (упрощенная версия)"""
        try:
            # В реальной реализации здесь был бы парсинг HTML
            # Для демонстрации возвращаем пустой список
            log.info("Parsing licenses from HTML", inn=inn)
            return []
            
        except Exception as e:
            log.error("Failed to parse licenses from HTML", error=str(e))
            return []


async def get_fsrar_licenses(inn: str, api_url: Optional[str] = None, 
                           dataset_url: Optional[str] = None) -> List[License]:
    """Получает лицензии РАР для компании"""
    config = FsrarConfig(
        api_url=api_url,
        dataset_url=dataset_url
    )
    
    async with FsrarProvider(config) as provider:
        try:
            # Пробуем разные способы получения данных
            if api_url:
                licenses = await provider.get_fsrar_licenses_api(inn)
                if licenses:
                    return licenses
            
            if dataset_url:
                licenses = await provider.get_fsrar_licenses_dataset(inn)
                if licenses:
                    return licenses
            
            # Fallback - прямой поиск
            licenses = await provider.get_fsrar_licenses_direct(inn)
            return licenses
                
        except Exception as e:
            log.error("Failed to get FSRAR licenses", 
                     error=str(e), 
                     inn=inn)
            return []
