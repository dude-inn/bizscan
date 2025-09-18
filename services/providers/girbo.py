# -*- coding: utf-8 -*-
"""
Провайдер ГИР БО (Государственный информационный ресурс бухгалтерской отчетности)
Источник: bo.nalog.gov.ru
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

import httpx
from pydantic import BaseModel

from domain.models import FinanceSnapshot
from core.logger import setup_logging

log = setup_logging()


class ReportMeta(BaseModel):
    """Метаданные отчета"""
    period: str
    form_type: str
    submission_date: Optional[date] = None
    url: Optional[str] = None


class ReportData(BaseModel):
    """Данные отчета"""
    period: str
    revenue: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    assets: Optional[Decimal] = None
    equity: Optional[Decimal] = None
    liabilities_short: Optional[Decimal] = None
    liabilities_long: Optional[Decimal] = None
    source: str = "GIRBO"


class GirboConfig(BaseModel):
    """Конфигурация ГИР БО"""
    base_url: str = "https://bo.nalog.gov.ru"
    token: Optional[str] = None
    timeout: int = 10
    max_retries: int = 2


class GirboProvider:
    """Провайдер для работы с ГИР БО API"""
    
    def __init__(self, config: GirboConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "User-Agent": "BizScan Bot/1.0",
                "Accept": "application/json",
            }
        )
        if self.config.token:
            self._client.headers["Authorization"] = f"Bearer {self.config.token}"
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def list_reports(self, inn_or_ogrn: str) -> List[ReportMeta]:
        """Получает список доступных отчетов для компании"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching reports list from GIRBO", inn_or_ogrn=inn_or_ogrn)
            
            # Поиск компании по ИНН/ОГРН
            search_response = await self._client.get(
                f"{self.config.base_url}/api/v1/search",
                params={"query": inn_or_ogrn, "type": "organization"}
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("organizations"):
                log.warning("No organizations found in GIRBO", inn_or_ogrn=inn_or_ogrn)
                return []
            
            # Получаем ID организации
            org_id = search_data["organizations"][0]["id"]
            log.info("Organization found in GIRBO", org_id=org_id, inn_or_ogrn=inn_or_ogrn)
            
            # Получаем список отчетов
            reports_response = await self._client.get(
                f"{self.config.base_url}/api/v1/organizations/{org_id}/reports"
            )
            reports_response.raise_for_status()
            reports_data = reports_response.json()
            
            reports = []
            for report in reports_data.get("reports", []):
                reports.append(ReportMeta(
                    period=report.get("period", ""),
                    form_type=report.get("form_type", ""),
                    submission_date=datetime.fromisoformat(report["submission_date"]).date() 
                        if report.get("submission_date") else None,
                    url=report.get("url")
                ))
            
            log.info("Reports list fetched successfully", 
                    reports_count=len(reports), 
                    inn_or_ogrn=inn_or_ogrn)
            return reports
            
        except Exception as e:
            log.error("Failed to fetch reports list from GIRBO", 
                     error=str(e), 
                     inn_or_ogrn=inn_or_ogrn)
            return []
    
    async def get_report(self, inn_or_ogrn: str, period: str) -> Optional[ReportData]:
        """Получает данные отчета за указанный период"""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        
        try:
            log.info("Fetching report data from GIRBO", 
                    inn_or_ogrn=inn_or_ogrn, 
                    period=period)
            
            # Получаем список отчетов
            reports = await self.list_reports(inn_or_ogrn)
            target_report = None
            
            for report in reports:
                if report.period == period:
                    target_report = report
                    break
            
            if not target_report:
                log.warning("Report not found for period", 
                           period=period, 
                           inn_or_ogrn=inn_or_ogrn)
                return None
            
            # Получаем данные отчета
            if target_report.url:
                report_response = await self._client.get(target_report.url)
                report_response.raise_for_status()
                report_data = report_response.json()
            else:
                # Альтернативный способ получения данных
                report_response = await self._client.get(
                    f"{self.config.base_url}/api/v1/reports",
                    params={"inn": inn_or_ogrn, "period": period}
                )
                report_response.raise_for_status()
                report_data = report_response.json()
            
            # Парсим финансовые показатели
            financial_data = self._parse_financial_data(report_data)
            
            report_data_obj = ReportData(
                period=period,
                **financial_data
            )
            
            log.info("Report data fetched successfully", 
                    period=period, 
                    inn_or_ogrn=inn_or_ogrn)
            return report_data_obj
            
        except Exception as e:
            log.error("Failed to fetch report data from GIRBO", 
                     error=str(e), 
                     inn_or_ogrn=inn_or_ogrn, 
                     period=period)
            return None
    
    def _parse_financial_data(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсит финансовые данные из отчета"""
        try:
            # Извлекаем данные из форм №1 и №2
            form1_data = report_data.get("form_1", {})
            form2_data = report_data.get("form_2", {})
            
            financial_data = {}
            
            # Выручка (из формы №2)
            if "revenue" in form2_data:
                financial_data["revenue"] = Decimal(str(form2_data["revenue"]))
            
            # Чистая прибыль (из формы №2)
            if "net_profit" in form2_data:
                financial_data["net_profit"] = Decimal(str(form2_data["net_profit"]))
            
            # Активы (из формы №1)
            if "assets" in form1_data:
                financial_data["assets"] = Decimal(str(form1_data["assets"]))
            
            # Капитал (из формы №1)
            if "equity" in form1_data:
                financial_data["equity"] = Decimal(str(form1_data["equity"]))
            
            # Краткосрочные обязательства (из формы №1)
            if "liabilities_short" in form1_data:
                financial_data["liabilities_short"] = Decimal(str(form1_data["liabilities_short"]))
            
            # Долгосрочные обязательства (из формы №1)
            if "liabilities_long" in form1_data:
                financial_data["liabilities_long"] = Decimal(str(form1_data["liabilities_long"]))
            
            return financial_data
            
        except Exception as e:
            log.error("Failed to parse financial data", error=str(e))
            return {}


async def get_company_finances(inn_or_ogrn: str, base_url: str, token: Optional[str] = None) -> List[FinanceSnapshot]:
    """Получает финансовые показатели компании из ГИР БО"""
    config = GirboConfig(base_url=base_url, token=token)
    
    async with GirboProvider(config) as provider:
        try:
            # Получаем список отчетов
            reports = await provider.list_reports(inn_or_ogrn)
            if not reports:
                log.warning("No reports found in GIRBO", inn_or_ogrn=inn_or_ogrn)
                return []
            
            # Получаем данные за последние 3 года
            finances = []
            current_year = datetime.now().year
            
            for year in range(current_year - 2, current_year + 1):
                year_str = str(year)
                report_data = await provider.get_report(inn_or_ogrn, year_str)
                
                if report_data:
                    finances.append(FinanceSnapshot(
                        period=report_data.period,
                        revenue=report_data.revenue,
                        net_profit=report_data.net_profit,
                        assets=report_data.assets,
                        equity=report_data.equity,
                        liabilities_short=report_data.liabilities_short,
                        liabilities_long=report_data.liabilities_long,
                        source="GIRBO"
                    ))
            
            log.info("Company finances fetched successfully", 
                    inn_or_ogrn=inn_or_ogrn, 
                    finances_count=len(finances))
            return finances
            
        except Exception as e:
            log.error("Failed to get company finances from GIRBO", 
                     error=str(e), 
                     inn_or_ogrn=inn_or_ogrn)
            return []
