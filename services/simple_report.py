# -*- coding: utf-8 -*-
"""
Простой конвейер формирования отчёта
Заменяет сложную систему сборки отчёта, но сохраняет интерфейс для bot/
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.providers.ofdata import OFDataProvider
from services.providers.openai import OpenAIProvider
from core.logger import setup_logging

log = setup_logging()

class SimpleReportPipeline:
    """Простой конвейер формирования отчёта"""
    
    def __init__(self):
        self.ofdata = OFDataProvider()
        self.openai = OpenAIProvider()
        
        # Алиасы для русских подписей ключей
        self.aliases = {
            # Основные реквизиты
            'ИНН': 'ИНН',
            'ОГРН': 'ОГРН', 
            'КПП': 'КПП',
            'ОКПО': 'ОКПО',
            'НаимПолн': 'Полное наименование',
            'НаимСокр': 'Сокращённое наименование',
            'Статус': 'Статус',
            'ДатаРег': 'Дата регистрации',
            'ДатаЛикв': 'Дата ликвидации',
            'ЮрАдрес': 'Юридический адрес',
            'Руководитель': 'Руководитель',
            'УстКап': 'Уставный капитал',
            'СЧР': 'Численность работников',
            
            # Финансы
            'Выручка': 'Выручка',
            'Прибыль': 'Прибыль',
            'Активы': 'Активы',
            'Капитал': 'Капитал',
            
            # Налоги
            'ОсобРежим': 'Налоговые режимы',
            'СумУпл': 'Уплачено налогов',
            'СумНедоим': 'Недоимка',
            
            # Арбитраж
            'ЗапВсего': 'Всего дел',
            'ОбщСуммИск': 'Общая сумма исков',
            'Номер': 'Номер дела',
            'Суд': 'Суд',
            'Дата': 'Дата дела',
            'СуммИск': 'Сумма иска',
            'Ист': 'Истцы',
            'Ответ': 'Ответчики',
            
            # Исполнительные производства
            'ИспПрНомер': 'Номер производства',
            'ДолжНаим': 'Должник',
            'СумДолг': 'Сумма долга',
            'ОстЗадолж': 'Остаток задолженности',
            'СудПристНаим': 'Пристав',
            
            # Проверки
            'Тип': 'Тип проверки',
            'Нарушения': 'Нарушения',
            'Штраф': 'Штраф',
            
            # Госзакупки
            'РегНомер': 'Номер контракта',
            'Цена': 'Цена контракта',
            'Заказ': 'Заказчик',
            'Постав': 'Поставщик',
            'Объекты': 'Объекты закупки'
        }
    
    async def generate_report(self, query: str, include_sections: List[str] = None) -> str:
        """
        Генерирует простой отчёт по запросу
        
        Args:
            query: ИНН, ОГРН или название компании
            include_sections: Список секций для включения
            
        Returns:
            Готовый отчёт в виде строки
        """
        if include_sections is None:
            include_sections = ['company', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts']
        
        log.info("SimpleReportPipeline: starting report generation", query=query, sections=include_sections)
        
        try:
            # 1. Получаем данные из OFData
            data = await self._fetch_data(query, include_sections)
            
            # 2. Форматируем в человекочитаемый текст
            report_text = self._format_to_text(data, include_sections)
            
            # 3. Добавляем OpenAI блоки
            full_report = await self._add_openai_sections(report_text)
            
            log.info("SimpleReportPipeline: report generated successfully", length=len(full_report))
            return full_report
            
        except Exception as e:
            log.error("SimpleReportPipeline: error generating report", error=str(e), query=query)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
    async def _fetch_data(self, query: str, include_sections: List[str]) -> Dict[str, Any]:
        """Получает данные из OFData API"""
        data = {}
        
        # Определяем тип запроса и получаем базовую информацию
        if query.isdigit() and len(query) in [10, 12]:
            # ИНН или ОГРН
            if len(query) == 10:
                data['company'] = await self.ofdata.get_company(inn=query)
            else:
                data['company'] = await self.ofdata.get_company(ogrn=query)
        else:
            # Поиск по названию
            search_results = await self.ofdata.search_companies(query)
            if search_results and len(search_results) > 0:
                first_result = search_results[0]
                inn = first_result.get('ИНН')
                if inn:
                    data['company'] = await self.ofdata.get_company(inn=inn)
            else:
                raise ValueError("Компания не найдена")
        
        # Получаем дополнительные данные
        if 'finances' in include_sections:
            try:
                data['finances'] = await self.ofdata.get_finances(inn=query)
            except Exception as e:
                log.warning("Could not fetch finances", error=str(e))
                data['finances'] = None
        
        if 'legal-cases' in include_sections:
            try:
                data['legal_cases'] = await self.ofdata.get_legal_cases(inn=query)
            except Exception as e:
                log.warning("Could not fetch legal cases", error=str(e))
                data['legal_cases'] = None
        
        if 'enforcements' in include_sections:
            try:
                data['enforcements'] = await self.ofdata.get_enforcements(inn=query)
            except Exception as e:
                log.warning("Could not fetch enforcements", error=str(e))
                data['enforcements'] = None
        
        if 'inspections' in include_sections:
            try:
                data['inspections'] = await self.ofdata.get_inspections(inn=query)
            except Exception as e:
                log.warning("Could not fetch inspections", error=str(e))
                data['inspections'] = None
        
        if 'contracts' in include_sections:
            try:
                data['contracts'] = await self.ofdata.get_contracts(inn=query)
            except Exception as e:
                log.warning("Could not fetch contracts", error=str(e))
                data['contracts'] = None
        
        return data
    
    def _format_to_text(self, data: Dict[str, Any], include_sections: List[str]) -> str:
        """Форматирует данные в человекочитаемый текст"""
        lines = []
        
        # Заголовок
        company_data = data.get('company', {})
        company_name = company_data.get('НаимПолн', company_data.get('НаимСокр', 'Неизвестная компания'))
        inn = company_data.get('ИНН', '—')
        ogrn = company_data.get('ОГРН', '—')
        
        lines.append(f"# {company_name}")
        lines.append(f"ИНН: {inn} | ОГРН: {ogrn}")
        lines.append("")
        
        # Основная информация о компании
        if 'company' in include_sections and data.get('company'):
            lines.append("## РЕКВИЗИТЫ")
            lines.append("=" * 50)
            lines.extend(self._format_company_section(data['company']))
            lines.append("")
        
        # Финансы
        if 'finances' in include_sections and data.get('finances'):
            lines.append("## ФИНАНСОВАЯ ОТЧЁТНОСТЬ")
            lines.append("=" * 50)
            lines.extend(self._format_finances_section(data['finances']))
            lines.append("")
        
        # Арбитражные дела
        if 'legal-cases' in include_sections and data.get('legal_cases'):
            lines.append("## АРБИТРАЖНЫЕ ДЕЛА")
            lines.append("=" * 50)
            lines.extend(self._format_legal_cases_section(data['legal_cases']))
            lines.append("")
        
        # Исполнительные производства
        if 'enforcements' in include_sections and data.get('enforcements'):
            lines.append("## ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА")
            lines.append("=" * 50)
            lines.extend(self._format_enforcements_section(data['enforcements']))
            lines.append("")
        
        # Проверки
        if 'inspections' in include_sections and data.get('inspections'):
            lines.append("## ПРОВЕРКИ")
            lines.append("=" * 50)
            lines.extend(self._format_inspections_section(data['inspections']))
            lines.append("")
        
        # Госзакупки
        if 'contracts' in include_sections and data.get('contracts'):
            lines.append("## ГОСЗАКУПКИ")
            lines.append("=" * 50)
            lines.extend(self._format_contracts_section(data['contracts']))
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_company_section(self, company_data: Dict[str, Any]) -> List[str]:
        """Форматирует секцию с информацией о компании"""
        lines = []
        
        # Основные реквизиты
        for key, alias in self.aliases.items():
            if key in company_data and company_data[key]:
                value = company_data[key]
                if isinstance(value, (int, float)):
                    if 'Сумма' in alias or 'Капитал' in alias:
                        value = f"{value:,.2f} руб."
                    else:
                        value = str(value)
                lines.append(f"{alias}: {value}")
        
        return lines
    
    def _format_finances_section(self, finances_data: Dict[str, Any]) -> List[str]:
        """Форматирует секцию с финансовой отчётностью"""
        lines = []
        
        if 'data' in finances_data:
            for year, year_data in finances_data['data'].items():
                if year.isdigit():
                    lines.append(f"\n{year} год:")
                    for key, value in year_data.items():
                        if isinstance(value, (int, float)) and value != 0:
                            lines.append(f"  {key}: {value:,.2f} руб.")
        
        return lines
    
    def _format_legal_cases_section(self, legal_data: Dict[str, Any]) -> List[str]:
        """Форматирует секцию с арбитражными делами"""
        lines = []
        
        if 'data' in legal_data:
            total_cases = legal_data['data'].get('ЗапВсего', 0)
            total_amount = legal_data['data'].get('ОбщСуммИск', 0)
            
            lines.append(f"Всего дел: {total_cases}")
            if total_amount > 0:
                lines.append(f"Общая сумма исков: {total_amount:,.2f} руб.")
            
            records = legal_data['data'].get('Записи', [])
            if records:
                lines.append("\nПоследние дела:")
                for record in records[:5]:  # Показываем только последние 5
                    case_num = record.get('Номер', '—')
                    court = record.get('Суд', '—')
                    date = record.get('Дата', '—')
                    amount = record.get('СуммИск', 0)
                    lines.append(f"  {case_num} | {court} | {date} | {amount:,.2f} руб.")
        
        return lines
    
    def _format_enforcements_section(self, enforcements_data: Dict[str, Any]) -> List[str]:
        """Форматирует секцию с исполнительными производствами"""
        lines = []
        
        if 'data' in enforcements_data:
            records = enforcements_data['data'].get('Записи', [])
            total_debt = sum(record.get('СумДолг', 0) for record in records)
            
            lines.append(f"Всего производств: {len(records)}")
            if total_debt > 0:
                lines.append(f"Общая сумма долга: {total_debt:,.2f} руб.")
            
            if records:
                lines.append("\nПоследние производства:")
                for record in records[:5]:  # Показываем только последние 5
                    case_num = record.get('ИспПрНомер', '—')
                    debtor = record.get('ДолжНаим', '—')
                    debt = record.get('СумДолг', 0)
                    lines.append(f"  {case_num} | {debtor} | {debt:,.2f} руб.")
        
        return lines
    
    def _format_inspections_section(self, inspections_data: Dict[str, Any]) -> List[str]:
        """Форматирует секцию с проверками"""
        lines = []
        
        if 'data' in inspections_data:
            records = inspections_data['data'].get('Записи', [])
            
            lines.append(f"Всего проверок: {len(records)}")
            
            if records:
                lines.append("\nПоследние проверки:")
                for record in records[:5]:  # Показываем только последние 5
                    case_num = record.get('Номер', '—')
                    inspection_type = record.get('Тип', '—')
                    date = record.get('Дата', '—')
                    fine = record.get('Штраф', 0)
                    lines.append(f"  {case_num} | {inspection_type} | {date} | {fine:,.2f} руб.")
        
        return lines
    
    def _format_contracts_section(self, contracts_data: Dict[str, Any]) -> List[str]:
        """Форматирует секцию с госзакупками"""
        lines = []
        
        if 'data' in contracts_data:
            records = contracts_data['data'].get('Записи', [])
            total_amount = sum(record.get('Цена', 0) for record in records)
            
            lines.append(f"Всего контрактов: {len(records)}")
            if total_amount > 0:
                lines.append(f"Общая сумма: {total_amount:,.2f} руб.")
            
            if records:
                lines.append("\nПоследние контракты:")
                for record in records[:5]:  # Показываем только последние 5
                    contract_num = record.get('РегНомер', '—')
                    customer = record.get('Заказ', {}).get('НаимПолн', '—')
                    price = record.get('Цена', 0)
                    date = record.get('Дата', '—')
                    lines.append(f"  {contract_num} | {customer} | {price:,.2f} руб. | {date}")
        
        return lines
    
    async def _add_openai_sections(self, report_text: str) -> str:
        """Добавляет блоки от OpenAI: История компании и Резюме"""
        try:
            # Генерируем историю компании
            history = await self.openai.generate_company_history(report_text)
            
            # Генерируем резюме
            summary = await self.openai.generate_company_summary(report_text)
            
            # Добавляем к отчёту
            full_report = report_text + "\n\n" + "## История компании\n\n" + history + "\n\n## Резюме\n\n" + summary
            
            return full_report
            
        except Exception as e:
            log.warning("Could not generate OpenAI sections", error=str(e))
            return report_text + "\n\n## История компании\n\nДанные недоступны\n\n## Резюме\n\nДанные недоступны"
