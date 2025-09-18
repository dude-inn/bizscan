# -*- coding: utf-8 -*-
"""
Провайдер для работы с Реестром МСП
"""
import asyncio
import csv
import io
from typing import Optional, Dict, Any
from datetime import datetime, date
from pathlib import Path

import httpx
import pandas as pd
from pydantic import BaseModel

from domain.models import MsmeInfo
from core.logger import setup_logging

log = setup_logging()


class MsmeConfig(BaseModel):
    """Конфигурация для МСП"""
    data_url: str = "https://ofd.nalog.ru/opendata/7707329152-rsmp/data-20241201-structure-20141120.csv"
    local_file: Optional[str] = None
    cache_ttl_days: int = 30
    timeout: int = 30


class MsmeProvider:
    """Провайдер для работы с Реестром МСП"""
    
    def __init__(self, config: MsmeConfig):
        self.config = config
        self._data: Optional[pd.DataFrame] = None
        self._last_update: Optional[datetime] = None
    
    async def _load_data(self) -> pd.DataFrame:
        """Загружает данные МСП"""
        if self._data is not None and self._last_update:
            # Проверяем, не устарели ли данные
            if (datetime.now() - self._last_update).days < self.config.cache_ttl_days:
                return self._data
        
        try:
            if self.config.local_file and Path(self.config.local_file).exists():
                # Загружаем из локального файла
                log.info("Loading MSME data from local file", file=self.config.local_file)
                self._data = pd.read_csv(self.config.local_file, encoding='utf-8')
            else:
                # Загружаем из интернета
                log.info("Loading MSME data from URL", url=self.config.data_url)
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    response = await client.get(self.config.data_url)
                    response.raise_for_status()
                    
                    # Парсим CSV
                    csv_content = response.text
                    self._data = pd.read_csv(io.StringIO(csv_content), encoding='utf-8')
            
            self._last_update = datetime.now()
            log.info("MSME data loaded successfully", rows=len(self._data))
            return self._data
            
        except Exception as e:
            log.error("Failed to load MSME data", error=str(e))
            raise
    
    async def get_msme_status(self, inn: str) -> MsmeInfo:
        """Получает статус МСП для компании"""
        try:
            data = await self._load_data()
            
            # Ищем компанию по ИНН
            company_row = data[data['ИНН'] == inn]
            
            if company_row.empty:
                return MsmeInfo(is_msme=False)
            
            # Берем первую найденную запись
            row = company_row.iloc[0]
            
            # Определяем категорию
            category_map = {
                'микропредприятие': 'micro',
                'малое предприятие': 'small', 
                'среднее предприятие': 'medium'
            }
            
            category = None
            if 'Категория' in row and pd.notna(row['Категория']):
                category = category_map.get(row['Категория'].lower())
            
            # Определяем период данных
            period = None
            if 'Период' in row and pd.notna(row['Период']):
                period = str(row['Период'])
            
            return MsmeInfo(
                is_msme=True,
                category=category,
                period=period
            )
            
        except Exception as e:
            log.error("Failed to get MSME status", inn=inn, error=str(e))
            return MsmeInfo(is_msme=False)


async def check_msme_status(inn: str, data_url: Optional[str] = None, local_file: Optional[str] = None) -> MsmeInfo:
    """Проверяет статус МСП для компании"""
    config = MsmeConfig(
        data_url=data_url or "https://ofd.nalog.ru/opendata/7707329152-rsmp/data-20241201-structure-20141120.csv",
        local_file=local_file
    )
    
    provider = MsmeProvider(config)
    return await provider.get_msme_status(inn)
