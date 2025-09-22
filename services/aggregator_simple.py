# -*- coding: utf-8 -*-
"""
Адаптер для совместимости с bot/
Заменяет старую сложную систему сборки отчёта на простой конвейер
"""
import asyncio
import logging
from typing import Dict, Any, List

from services.simple_report import SimpleReportPipeline
from core.logger import setup_logging

log = setup_logging()

class SimpleReportAggregator:
    """Адаптер для совместимости с bot/"""
    
    def __init__(self):
        self.pipeline = SimpleReportPipeline()
    
    async def fetch_company_report_markdown(self, query: str) -> str:
        """
        Адаптер для bot/ - генерирует отчёт в том же формате
        
        Args:
            query: ИНН, ОГРН или название компании
            
        Returns:
            Готовый отчёт в виде строки
        """
        log.info("SimpleReportAggregator: generating report", query=query)
        
        try:
            # Используем простой конвейер
            report = await self.pipeline.generate_report(
                query=query,
                include_sections=['company', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts']
            )
            
            log.info("SimpleReportAggregator: report generated successfully", length=len(report))
            return report
            
        except Exception as e:
            log.error("SimpleReportAggregator: error generating report", error=str(e), query=query)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
    async def fetch_company_profile(self, input_str: str) -> Dict[str, Any]:
        """
        Адаптер для bot/ - возвращает профиль компании в том же формате
        
        Args:
            input_str: ИНН, ОГРН или название компании
            
        Returns:
            Словарь с данными компании (для совместимости)
        """
        log.info("SimpleReportAggregator: fetching company profile", input_str=input_str)
        
        try:
            # Получаем только базовую информацию о компании
            data = await self.pipeline._fetch_data(input_str, ['company'])
            
            # Возвращаем в том же формате, что ожидает bot/
            company_data = data.get('company', {})
            
            return {
                'company': company_data,
                'error': None
            }
            
        except Exception as e:
            log.error("SimpleReportAggregator: error fetching profile", error=str(e), input_str=input_str)
            return {
                'company': {},
                'error': str(e)
            }
    
    async def build_markdown_report(self, profile: Dict[str, Any]) -> str:
        """
        Адаптер для bot/ - строит markdown отчёт
        
        Args:
            profile: Профиль компании
            
        Returns:
            Готовый отчёт в виде строки
        """
        log.info("SimpleReportAggregator: building markdown report")
        
        try:
            # Извлекаем данные из профиля
            company_data = profile.get('company', {})
            if not company_data:
                return "❌ Данные компании не найдены"
            
            # Определяем идентификатор для получения полного отчёта
            inn = company_data.get('ИНН')
            if not inn:
                return "❌ ИНН не найден в данных компании"
            
            # Генерируем полный отчёт
            report = await self.pipeline.generate_report(
                query=inn,
                include_sections=['company', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts']
            )
            
            return report
            
        except Exception as e:
            log.error("SimpleReportAggregator: error building markdown report", error=str(e))
            return f"❌ Ошибка при формировании отчёта: {str(e)}"

