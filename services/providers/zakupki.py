# -*- coding: utf-8 -*-
"""
Провайдер ЕИС (Единая информационная система в сфере закупок)
Источник: zakupki.gov.ru
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

import httpx
from pydantic import BaseModel

from domain.models import ProcurementStats
from core.logger import setup_logging

log = setup_logging()


class ZakupkiConfig(BaseModel):
    """Конфигурация ЕИС"""
    mode: str = "soap"  # soap | dataset
    wsdl_url: Optional[str] = None
    dataset_url: Optional[str] = None
    timeout: int = 10
    max_retries: int = 2


class ZakupkiProvider:
    """Провайдер для работы с ЕИС"""
    
    def __init__(self, config: ZakupkiConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "User-Agent": "BizScan Bot/1.0",
                "Accept": "application/json, text/xml",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get_procurement_stats_soap(self, inn: str) -> Optional[ProcurementStats]:
        """Получает статистику по госзакупкам через SOAP API"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching procurement stats via SOAP", inn=inn)
            
            # SOAP запрос для получения статистики по ИНН
            soap_body = f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <getProcurementStats xmlns="http://zakupki.gov.ru/">
                        <inn>{inn}</inn>
                    </getProcurementStats>
                </soap:Body>
            </soap:Envelope>
            """
            
            response = await self._client.post(
                self.config.wsdl_url,
                data=soap_body,
                headers={"Content-Type": "text/xml; charset=utf-8"}
            )
            response.raise_for_status()
            
            # Парсим XML ответ
            stats_data = self._parse_soap_response(response.text)
            
            if stats_data:
                stats = ProcurementStats(
                    total_contracts=stats_data.get("total_contracts", 0),
                    total_amount=Decimal(str(stats_data.get("total_amount", 0))) 
                        if stats_data.get("total_amount") else None,
                    last_contract_date=datetime.fromisoformat(stats_data["last_contract_date"]).date()
                        if stats_data.get("last_contract_date") else None,
                    source="ZAKUPKI_SOAP"
                )
                
                log.info("Procurement stats fetched via SOAP", 
                        inn=inn, 
                        total_contracts=stats.total_contracts)
                return stats
            
            return None
            
        except Exception as e:
            log.error("Failed to fetch procurement stats via SOAP", 
                     error=str(e), 
                     inn=inn)
            return None
    
    async def get_procurement_stats_dataset(self, inn: str) -> Optional[ProcurementStats]:
        """Получает статистику по госзакупкам из открытых датасетов"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching procurement stats from dataset", inn=inn)
            
            # Загружаем открытые данные по госзакупкам
            response = await self._client.get(self.config.dataset_url)
            response.raise_for_status()
            
            # Парсим CSV данные
            import pandas as pd
            import io
            
            df = pd.read_csv(io.StringIO(response.text), encoding='utf-8')
            
            # Фильтруем по ИНН
            company_contracts = df[df['inn'] == inn] if 'inn' in df.columns else pd.DataFrame()
            
            if company_contracts.empty:
                log.warning("No contracts found in dataset", inn=inn)
                return None
            
            # Агрегируем статистику
            total_contracts = len(company_contracts)
            total_amount = company_contracts['amount'].sum() if 'amount' in company_contracts.columns else None
            last_contract_date = None
            
            if 'contract_date' in company_contracts.columns:
                last_contract_date = pd.to_datetime(company_contracts['contract_date']).max().date()
            
            stats = ProcurementStats(
                total_contracts=total_contracts,
                total_amount=Decimal(str(total_amount)) if total_amount else None,
                last_contract_date=last_contract_date,
                source="ZAKUPKI_DATASET"
            )
            
            log.info("Procurement stats fetched from dataset", 
                    inn=inn, 
                    total_contracts=stats.total_contracts)
            return stats
            
        except Exception as e:
            log.error("Failed to fetch procurement stats from dataset", 
                     error=str(e), 
                     inn=inn)
            return None
    
    def _parse_soap_response(self, xml_text: str) -> Optional[Dict[str, Any]]:
        """Парсит SOAP ответ"""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_text)
            
            # Извлекаем данные из XML
            stats_data = {}
            
            # Ищем элементы в SOAP ответе
            for elem in root.iter():
                if elem.tag.endswith('totalContracts'):
                    stats_data['total_contracts'] = int(elem.text)
                elif elem.tag.endswith('totalAmount'):
                    stats_data['total_amount'] = float(elem.text)
                elif elem.tag.endswith('lastContractDate'):
                    stats_data['last_contract_date'] = elem.text
            
            return stats_data if stats_data else None
            
        except Exception as e:
            log.error("Failed to parse SOAP response", error=str(e))
            return None


async def get_procurement_stats(inn: str, mode: str, wsdl_url: Optional[str] = None, 
                               dataset_url: Optional[str] = None) -> Optional[ProcurementStats]:
    """Получает статистику по госзакупкам для компании"""
    config = ZakupkiConfig(
        mode=mode,
        wsdl_url=wsdl_url,
        dataset_url=dataset_url
    )
    
    async with ZakupkiProvider(config) as provider:
        try:
            if mode == "soap" and wsdl_url:
                return await provider.get_procurement_stats_soap(inn)
            elif mode == "dataset" and dataset_url:
                return await provider.get_procurement_stats_dataset(inn)
            else:
                log.error("Invalid configuration for procurement stats", 
                         mode=mode, 
                         wsdl_url=wsdl_url, 
                         dataset_url=dataset_url)
                return None
                
        except Exception as e:
            log.error("Failed to get procurement stats", 
                     error=str(e), 
                     inn=inn)
            return None
