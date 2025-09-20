# -*- coding: utf-8 -*-
"""
Сборщик отчёта
"""
import asyncio
from typing import Dict, Any, List, Optional
from .ofdata_client import OFDataClient
from .render_company import render_company
from .render_finances import render_finances
from .render_legal import render_legal
from .render_enforce import render_enforce
from .render_inspect import render_inspect
from .render_contracts import render_contracts
from .render_entrepreneur import render_entrepreneur
from core.logger import setup_logging, get_logger

setup_logging()
log = get_logger(__name__)


class ReportBuilder:
    """Сборщик отчёта"""
    
    def __init__(self):
        """Инициализация сборщика"""
        self.client = OFDataClient()
        self.openai_client = None  # Будет инициализирован при необходимости
    
    def build_report(self, query: str, include_sections: List[str] = None) -> str:
        """
        Строит полный отчёт
        
        Args:
            query: ИНН, ОГРН или название компании
            include_sections: Список секций для включения
            
        Returns:
            Готовый отчёт
        """
        if include_sections is None:
            include_sections = ['company', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts']
        
        log.info("ReportBuilder: starting report generation", query=query, sections=include_sections)
        
        try:
            # 1. Получаем данные
            log.info("Fetching data from API", query=query, sections=include_sections)
            data = self._fetch_data(query, include_sections)
            log.info("Data fetched successfully", data_keys=list(data.keys()) if data else None)
            
            # 2. Строим отчёт
            log.info("Building report sections", sections=include_sections)
            report = self._build_report_sections(data, include_sections)
            log.info("Report sections built successfully", report_length=len(report) if report else 0)
            
            # 3. Добавляем OpenAI секции
            full_report = self._add_openai_sections(report)
            
            log.info("ReportBuilder: report generated successfully", length=len(full_report))
            return full_report
            
        except Exception as e:
            log.error("ReportBuilder: error generating report", error=str(e), query=query)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
    def _fetch_data(self, query: str, include_sections: List[str]) -> Dict[str, Any]:
        """Получает данные из OFData API"""
        log.info("_fetch_data: starting", query=query, sections=include_sections)
        data = {}
        
        # Определяем тип запроса и получаем базовую информацию
        if query.isdigit() and len(query) in [10, 12]:
            # ИНН или ОГРН
            if len(query) == 10:
                log.info("Fetching company by INN", inn=query)
                company_data = self.client.get_company(inn=query)
            else:
                log.info("Fetching company by OGRN", ogrn=query)
                company_data = self.client.get_company(ogrn=query)
            
        # Проверяем, что компания найдена
        print(f"DEBUG: company_data = {company_data}")
        print(f"DEBUG: company_data.get('data') = {company_data.get('data') if company_data else None}")
        if not company_data or not company_data.get('data'):
            log.warning("Company not found in API response", query=query, response=company_data)
            raise ValueError("Компания не найдена")
            
            log.info("Company data fetched successfully", company_keys=list(company_data.keys()) if company_data else None)
            data['company'] = company_data
        else:
            # Поиск по названию
            search_results = self.client.search(by='name', obj='company', query=query)
            if search_results and 'data' in search_results:
                records = search_results['data'].get('Записи', [])
                if records:
                    first_result = records[0]
                    inn = first_result.get('ИНН')
                    if inn:
                        company_data = self.client.get_company(inn=inn)
                        if not company_data or not company_data.get('data'):
                            raise ValueError("Компания не найдена")
                        data['company'] = company_data
                    else:
                        raise ValueError("Компания не найдена")
                else:
                    raise ValueError("Компания не найдена")
            else:
                raise ValueError("Компания не найдена")
        
        # Получаем дополнительные данные
        if 'finances' in include_sections:
            try:
                inn = data['company']['data'].get('ИНН')
                if inn:
                    data['finances'] = self.client.get_finances(inn=inn)
            except Exception as e:
                log.warning("Could not fetch finances", error=str(e))
                data['finances'] = None
        
        if 'legal-cases' in include_sections:
            try:
                inn = data['company']['data'].get('ИНН')
                if inn:
                    data['legal_cases'] = self.client.get_legal_cases(inn=inn)
            except Exception as e:
                log.warning("Could not fetch legal cases", error=str(e))
                data['legal_cases'] = None
        
        if 'enforcements' in include_sections:
            try:
                inn = data['company']['data'].get('ИНН')
                if inn:
                    data['enforcements'] = self.client.get_enforcements(inn=inn)
            except Exception as e:
                log.warning("Could not fetch enforcements", error=str(e))
                data['enforcements'] = None
        
        if 'inspections' in include_sections:
            try:
                inn = data['company']['data'].get('ИНН')
                if inn:
                    data['inspections'] = self.client.get_inspections(inn=inn)
            except Exception as e:
                log.warning("Could not fetch inspections", error=str(e))
                data['inspections'] = None
        
        if 'contracts' in include_sections:
            try:
                inn = data['company']['data'].get('ИНН')
                if inn:
                    # Получаем контракты по всем законам и ролям
                    contracts_44_customer = self.client.get_contracts(law='44', role='customer', inn=inn)
                    contracts_44_supplier = self.client.get_contracts(law='44', role='supplier', inn=inn)
                    contracts_94_customer = self.client.get_contracts(law='94', role='customer', inn=inn)
                    contracts_94_supplier = self.client.get_contracts(law='94', role='supplier', inn=inn)
                    contracts_223_customer = self.client.get_contracts(law='223', role='customer', inn=inn)
                    contracts_223_supplier = self.client.get_contracts(law='223', role='supplier', inn=inn)
                    
                    # Объединяем все контракты
                    all_contracts = []
                    for contracts in [contracts_44_customer, contracts_44_supplier, contracts_94_customer, 
                                    contracts_94_supplier, contracts_223_customer, contracts_223_supplier]:
                        if contracts and 'data' in contracts:
                            records = contracts['data'].get('Записи', [])
                            all_contracts.extend(records)
                    
                    # Создаём объединённый объект
                    data['contracts'] = {
                        'data': {
                            'ЗапВсего': len(all_contracts),
                            'Записи': all_contracts
                        }
                    }
            except Exception as e:
                log.warning("Could not fetch contracts", error=str(e))
                data['contracts'] = None
        
        return data
    
    def _build_report_sections(self, data: Dict[str, Any], include_sections: List[str]) -> str:
        """Строит секции отчёта"""
        sections = []
        
        # 1. ЗАГОЛОВОК
        if 'company' in data and data['company']:
            company_name = data['company'].get('НаимПолн') or data['company'].get('НаимСокр', 'Неизвестная компания')
            inn = data['company'].get('ИНН', '—')
            ogrn = data['company'].get('ОГРН', '—')
            sections.append(f"# {company_name}\nИНН: {inn} | ОГРН: {ogrn}")
        
        # 2. ОСНОВНОЕ
        if 'company' in data and data['company']:
            company_info = render_company(data['company'])
            sections.append(company_info)
        
        # 3. ФИНАНСОВАЯ ОТЧЁТНОСТЬ
        if 'finances' in include_sections and data.get('finances'):
            finances = render_finances(data['finances'])
            sections.append(finances)
        
        # 4. АРБИТРАЖНЫЕ ДЕЛА
        if 'legal-cases' in include_sections and data.get('legal_cases'):
            legal_cases = render_legal(data['legal_cases'])
            sections.append(legal_cases)
        
        # 5. ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА
        if 'enforcements' in include_sections and data.get('enforcements'):
            enforcements = render_enforce(data['enforcements'])
            sections.append(enforcements)
        
        # 6. ПРОВЕРКИ
        if 'inspections' in include_sections and data.get('inspections'):
            inspections = render_inspect(data['inspections'])
            sections.append(inspections)
        
        # 7. ГОСЗАКУПКИ
        if 'contracts' in include_sections and data.get('contracts'):
            contracts = render_contracts(data['contracts'])
            sections.append(contracts)
        
        # 8. ИП (если есть)
        if 'entrepreneur' in include_sections and data.get('entrepreneur'):
            entrepreneur = render_entrepreneur(data['entrepreneur'])
            sections.append(entrepreneur)
        
        return "\n\n".join(sections)
    
    def _add_openai_sections(self, report_text: str) -> str:
        """Добавляет секции от OpenAI"""
        try:
            # Инициализируем OpenAI клиент если нужно
            if not self.openai_client:
                from services.providers.openai import OpenAIProvider
                self.openai_client = OpenAIProvider()
            
            # Генерируем историю компании
            history = self.openai_client.generate_company_history(report_text)
            
            # Генерируем резюме
            summary = self.openai_client.generate_company_summary(report_text)
            
            # Добавляем к отчёту
            full_report = report_text + "\n\n" + "ИСТОРИЯ КОМПАНИИ\n" + "=" * 50 + "\n" + history + "\n\n" + "РЕЗЮМЕ\n" + "=" * 50 + "\n" + summary
            
            return full_report
            
        except Exception as e:
            log.warning("Could not generate OpenAI sections", error=str(e))
            return report_text + "\n\n" + "ИСТОРИЯ КОМПАНИИ\n" + "=" * 50 + "\n" + "Данные недоступны\n\n" + "РЕЗЮМЕ\n" + "=" * 50 + "\n" + "Данные недоступны"
    
    def build_company_profile(self, query: str) -> Dict[str, Any]:
        """
        Строит профиль компании (для совместимости с bot/)
        
        Args:
            query: ИНН, ОГРН или название компании
            
        Returns:
            Профиль компании
        """
        try:
            # Получаем только базовую информацию о компании
            data = self._fetch_data(query, ['company'])
            
            return {
                'company': data.get('company', {}),
                'error': None
            }
            
        except Exception as e:
            log.error("ReportBuilder: error building profile", error=str(e), query=query)
            return {
                'company': {},
                'error': str(e)
            }
    
    def build_simple_report(self, ident: Dict[str, Any], include: List[str], max_rows: int = 100) -> str:
        """
        Строит простой отчёт по идентификаторам
        
        Args:
            ident: Словарь с идентификаторами (inn, ogrn, okpo, kpp)
            include: Список секций для включения
            max_rows: Максимальное количество строк в отчёте
            
        Returns:
            Готовый отчёт
        """
        try:
            # 1. Получаем данные компании
            company_data = self.client.get_company(**ident)
            
            if not company_data or 'data' not in company_data:
                # Пробуем поиск по названию если есть
                if 'name' in ident:
                    search_results = self.client.search(by='name', obj='company', query=ident['name'])
                    if search_results and 'data' in search_results:
                        records = search_results['data'].get('Записи', [])
                        if records:
                            first_result = records[0]
                            inn = first_result.get('ИНН')
                            if inn:
                                company_data = self.client.get_company(inn=inn)
                
                if not company_data or 'data' not in company_data:
                    return "❌ Компания не найдена"
            
            # 2. Заголовок
            company_info = company_data.get('data', company_data)
            
            # Для налоговых данных нужно искать в правильном месте
            taxes_data = company_info.get('Налоги', {})
            name = company_info.get('НаимПолн') or company_info.get('НаимСокр', 'Неизвестная компания')
            inn = company_info.get('ИНН', '—')
            ogrn = company_info.get('ОГРН', '—')
            reg_date = company_info.get('ДатаРег', '—')
            
            if reg_date != '—':
                from .formatters import format_date
                reg_date = format_date(reg_date)
            
            header_lines = [name]
            if inn != '—' or ogrn != '—' or reg_date != '—':
                header_parts = []
                if inn != '—':
                    header_parts.append(f"ИНН {inn}")
                if ogrn != '—':
                    header_parts.append(f"ОГРН {ogrn}")
                if reg_date != '—':
                    header_parts.append(f"Дата регистрации {reg_date}")
                header_lines.append(" • ".join(header_parts))
            
            # 3. Собираем секции
            sections = []
            
            # ОСНОВНОЕ
            if 'company' in include:
                company_info = render_company(data)
                sections.append(company_info)
            
            # НАЛОГИ
            if 'taxes' in include:
                if taxes_data and any(taxes_data.values()):
                    tax_lines = ["НАЛОГИ", "=" * 50]
                    
                    # Особые режимы
                    regimes = taxes_data.get('ОсобРежим', [])
                    if regimes:
                        from .formatters import format_list
                        tax_lines.append(f"Режимы: {format_list(regimes)}")
                    
                    # Год уплаты
                    year = taxes_data.get('СведУплГод', '—')
                    if year != '—':
                        tax_lines.append(f"Год: {year}")
                    
                    # Всего уплачено
                    total_paid = taxes_data.get('СумУпл', 0)
                    if total_paid > 0:
                        from .formatters import format_money
                        tax_lines.append(f"Всего уплачено: {format_money(total_paid)}")
                    
                    # Топ-5 уплаченных налогов
                    paid_taxes = taxes_data.get('СведУпл', [])
                    if paid_taxes:
                        sorted_taxes = sorted(paid_taxes, key=lambda x: x.get('Сумма', 0), reverse=True)
                        tax_lines.append("Топ-5 уплаченных налогов:")
                        for tax in sorted_taxes[:5]:
                            name = tax.get('Наим', '—')
                            amount = tax.get('Сумма', 0)
                            tax_lines.append(f"• {name}: {format_money(amount)}")
                    
                    # Недоимка
                    arrears = taxes_data.get('СумНедоим', 0)
                    arrears_date = taxes_data.get('НедоимДата', '—')
                    if arrears > 0:
                        formatted_date = format_date(arrears_date) if arrears_date != '—' else '—'
                        tax_lines.append(f"Недоимка: {format_money(arrears)} (на {formatted_date})")
                    
                    sections.append("\n".join(tax_lines))
                else:
                    sections.append("НАЛОГИ\n" + "=" * 50 + "\nДанные недоступны")
            
            # ФИНАНСОВАЯ ОТЧЁТНОСТЬ
            if 'finances' in include:
                try:
                    # Сначала проверяем, есть ли финансы в data['data'] (как в примере пользователя)
                    if 'data' in data and any(key.isdigit() and len(key) == 4 for key in data['data'].keys()):
                        finances = render_finances(data)
                        sections.append(finances)
                    # Затем проверяем, есть ли финансы в data['finances']
                    elif data.get('finances') and 'data' in data['finances']:
                        finances = render_finances(data['finances'])
                        sections.append(finances)
                    else:
                        sections.append("ФИНАНСОВАЯ ОТЧЁТНОСТЬ\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch finances", error=str(e))
                    sections.append("ФИНАНСОВАЯ ОТЧЁТНОСТЬ\n" + "=" * 50 + "\nДанные недоступны")
            
            # АРБИТРАЖНЫЕ ДЕЛА
            if 'legal-cases' in include:
                try:
                    if data.get('legal_cases') and 'data' in data['legal_cases']:
                        legal = render_legal(data['legal_cases'])
                        sections.append(legal)
                    else:
                        sections.append("АРБИТРАЖНЫЕ ДЕЛА\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch legal cases", error=str(e))
                    sections.append("АРБИТРАЖНЫЕ ДЕЛА\n" + "=" * 50 + "\nДанные недоступны")
            
            # ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА
            if 'enforcements' in include:
                try:
                    if data.get('enforcements') and 'data' in data['enforcements']:
                        enforce = render_enforce(data['enforcements'])
                        sections.append(enforce)
                    else:
                        sections.append("ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch enforcements", error=str(e))
                    sections.append("ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА\n" + "=" * 50 + "\nДанные недоступны")
            
            # ПРОВЕРКИ
            if 'inspections' in include:
                try:
                    if data.get('inspections') and 'data' in data['inspections']:
                        inspect = render_inspect(data['inspections'])
                        sections.append(inspect)
                    else:
                        sections.append("ПРОВЕРКИ\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch inspections", error=str(e))
                    sections.append("ПРОВЕРКИ\n" + "=" * 50 + "\nДанные недоступны")
            
            # ГОСЗАКУПКИ
            if 'contracts' in include:
                try:
                    if data.get('contracts'):
                        contracts = render_contracts(data['contracts'])
                        sections.append(contracts)
                    else:
                        sections.append("ГОСЗАКУПКИ\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch contracts", error=str(e))
                    sections.append("ГОСЗАКУПКИ\n" + "=" * 50 + "\nДанные недоступны")
            
            # 4. Собираем полный текст
            full_text = "\n\n".join(["\n".join(header_lines)] + sections)
            
            # 5. Добавляем OpenAI секции
            try:
                history, bullets = self.summarize_history_and_bullets(full_text)
                # Добавляем секции к отчёту
                full_text += f"\n\nИСТОРИЯ КОМПАНИИ\n{'=' * 50}\n{history}\n\nРЕЗЮМЕ\n{'=' * 50}\n{bullets}"
            except Exception as e:
                log.warning("Could not generate OpenAI sections", error=str(e))
                full_text += f"\n\nИСТОРИЯ КОМПАНИИ\n{'=' * 50}\nДанные недоступны\n\nРЕЗЮМЕ\n{'=' * 50}\nДанные недоступны"
            
            return full_text
            
        except Exception as e:
            log.error("ReportBuilder: error building simple report", error=str(e), ident=ident)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
        def summarize_history_and_bullets(self, full_text: str) -> tuple:
            """
            Генерирует историю компании и резюме с помощью OpenAI
            
            Args:
                full_text: Полный текст отчёта
                
            Returns:
                Кортеж (история, резюме)
            """
            try:
                # Простая генерация без OpenAI (пока)
                # Извлекаем ключевые данные из отчёта
                lines = full_text.split('\n')
                
                # Ищем название компании
                company_name = "Компания"
                for line in lines[:10]:  # В первых 10 строках
                    if line and not line.startswith('ИНН') and not line.startswith('ОГРН') and not line.startswith('='):
                        if len(line) > 5:
                            company_name = line.strip()
                            break
                
                # Ищем дату регистрации
                reg_date = "неизвестно"
                for line in lines:
                    if "Дата регистрации:" in line:
                        reg_date = line.split(":")[-1].strip()
                        break
                
                # Ищем регион
                region = "неизвестно"
                for line in lines:
                    if "Регион:" in line:
                        region = line.split(":")[-1].strip()
                        break
                
                # Генерируем простую историю
                history = f"{company_name} была зарегистрирована {reg_date} в {region}. "
                
                # Ищем арбитражные дела
                for line in lines:
                    if "Всего дел:" in line:
                        cases_count = line.split(":")[-1].strip()
                        history += f"Компания участвовала в {cases_count} арбитражных делах. "
                        break
                
                # Ищем проверки
                for line in lines:
                    if "Всего проверок:" in line:
                        inspections_count = line.split(":")[-1].strip()
                        history += f"Проведено {inspections_count} проверок. "
                        break
                
                history += "Компания ведет активную хозяйственную деятельность."
                
                # Генерируем резюме
                bullets = [
                    f"• Название: {company_name}",
                    f"• Дата регистрации: {reg_date}",
                    f"• Регион: {region}",
                ]
                
                # Добавляем данные о делах
                for line in lines:
                    if "Всего дел:" in line:
                        cases_count = line.split(":")[-1].strip()
                        bullets.append(f"• Арбитражные дела: {cases_count}")
                        break
                
                # Добавляем данные о проверках
                for line in lines:
                    if "Всего проверок:" in line:
                        inspections_count = line.split(":")[-1].strip()
                        bullets.append(f"• Проверки: {inspections_count}")
                        break
                
                # Добавляем контакты
                for line in lines:
                    if "Телефоны:" in line:
                        phones = line.split(":")[-1].strip()
                        bullets.append(f"• Контакты: {phones[:50]}...")
                        break
                
                bullets.append("• Статус: Действующая организация")
                
                summary = "\n".join(bullets)
                
                return history, summary
                
            except Exception as e:
                log.warning("Could not generate sections", error=str(e))
                return "Данные недоступны", "Данные недоступны"
