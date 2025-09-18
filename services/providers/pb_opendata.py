# -*- coding: utf-8 -*-
"""
Провайдер Прозрачный бизнес - открытые данные ФНС
Источник: pb.nalog.ru, nalog.gov.ru/opendata
"""
import asyncio
import json
import csv
import zipfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import tempfile

import httpx
import pandas as pd
from pydantic import BaseModel

from core.logger import setup_logging

log = setup_logging()


class PbOpenDataConfig(BaseModel):
    """Конфигурация Прозрачный бизнес"""
    datasets: Dict[str, str]  # вид -> URL
    cache_dir: str = "data/pb_cache"
    timeout: int = 30
    max_retries: int = 2


class PbOpenDataProvider:
    """Провайдер для работы с открытыми данными ФНС"""
    
    def __init__(self, config: PbOpenDataConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._cache_dir = Path(config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "User-Agent": "BizScan Bot/1.0",
                "Accept": "application/json, text/csv, application/zip",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def load_dataset(self, kind: str, url: str) -> Optional[Path]:
        """Скачивает и распаковывает датасет"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Loading dataset", kind=kind, url=url)
            
            # Проверяем кэш
            cache_file = self._cache_dir / f"{kind}.csv"
            if cache_file.exists():
                log.info("Dataset found in cache", kind=kind)
                return cache_file
            
            # Скачиваем файл
            response = await self._client.get(url)
            response.raise_for_status()
            
            # Определяем тип файла
            content_type = response.headers.get("content-type", "")
            if "zip" in content_type or url.endswith(".zip"):
                # Обрабатываем ZIP архив
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = Path(tmp_file.name)
                
                # Распаковываем ZIP
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    # Ищем CSV файл в архиве
                    csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                    if not csv_files:
                        log.error("No CSV files found in ZIP archive", kind=kind)
                        return None
                    
                    # Извлекаем первый CSV файл
                    csv_file = csv_files[0]
                    zip_ref.extract(csv_file, self._cache_dir)
                    
                    # Переименовываем в стандартное имя
                    extracted_path = self._cache_dir / csv_file
                    extracted_path.rename(cache_file)
                
                # Удаляем временный файл
                tmp_path.unlink()
                
            elif "csv" in content_type or url.endswith(".csv"):
                # Прямо сохраняем CSV
                cache_file.write_bytes(response.content)
            else:
                log.error("Unsupported file type", 
                         content_type=content_type, 
                         kind=kind)
                return None
            
            log.info("Dataset loaded successfully", kind=kind, file_path=str(cache_file))
            return cache_file
            
        except Exception as e:
            log.error("Failed to load dataset", 
                     error=str(e), 
                     kind=kind, 
                     url=url)
            return None
    
    async def query_company_by_inn(self, inn: str) -> Dict[str, Any]:
        """Ищет информацию о компании в открытых данных"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Querying company in open data", inn=inn)
            
            result = {
                "inn": inn,
                "addresses": [],
                "disqualification": False,
                "other_flags": [],
                "datasets_checked": []
            }
            
            # Проверяем каждый датасет
            for kind, url in self.config.datasets.items():
                try:
                    log.info("Checking dataset", kind=kind, inn=inn)
                    
                    # Загружаем датасет
                    dataset_path = await self.load_dataset(kind, url)
                    if not dataset_path:
                        continue
                    
                    # Читаем CSV
                    df = pd.read_csv(dataset_path, encoding='utf-8')
                    
                    # Ищем компанию по ИНН
                    company_rows = df[df['inn'] == inn] if 'inn' in df.columns else pd.DataFrame()
                    
                    if not company_rows.empty:
                        log.info("Company found in dataset", kind=kind, inn=inn)
                        result["datasets_checked"].append(kind)
                        
                        # Извлекаем адреса
                        if 'address' in df.columns:
                            addresses = company_rows['address'].dropna().unique().tolist()
                            result["addresses"].extend(addresses)
                        
                        # Проверяем дисквалификацию
                        if 'disqualification' in df.columns:
                            has_disqualification = company_rows['disqualification'].any()
                            if has_disqualification:
                                result["disqualification"] = True
                        
                        # Другие флаги
                        flag_columns = [col for col in df.columns 
                                      if col not in ['inn', 'address', 'disqualification']]
                        for col in flag_columns:
                            if company_rows[col].any():
                                result["other_flags"].append({
                                    "flag": col,
                                    "value": company_rows[col].iloc[0]
                                })
                    
                except Exception as e:
                    log.warning("Failed to process dataset", 
                               error=str(e), 
                               kind=kind, 
                               inn=inn)
                    continue
            
            log.info("Company query completed", 
                    inn=inn, 
                    datasets_checked=len(result["datasets_checked"]),
                    addresses_count=len(result["addresses"]))
            return result
            
        except Exception as e:
            log.error("Failed to query company in open data", 
                     error=str(e), 
                     inn=inn)
            return {"inn": inn, "error": str(e)}


async def get_company_open_data(inn: str, datasets: Dict[str, str]) -> Dict[str, Any]:
    """Получает открытые данные о компании"""
    config = PbOpenDataConfig(datasets=datasets)
    
    async with PbOpenDataProvider(config) as provider:
        try:
            result = await provider.query_company_by_inn(inn)
            return result
        except Exception as e:
            log.error("Failed to get company open data", 
                     error=str(e), 
                     inn=inn)
            return {"inn": inn, "error": str(e)}
