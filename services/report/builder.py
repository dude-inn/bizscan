# -*- coding: utf-8 -*-
"""
Сборщик отчёта
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .ofdata_client import OFDataClient
from .simple_company_renderer import render_company_simple
from .simple_finances_renderer import render_finances_simple
from .render_legal import render_legal
from .render_enforce import render_enforce
from .render_inspect import render_inspect
from .simple_contracts_renderer import render_contracts_simple
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
            log.debug("_fetch_data: checking company data", 
                     has_company_data=bool(company_data),
                     has_data_key=bool(company_data.get('data') if company_data else None))
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
        
        # 1. ОСНОВНОЕ
        if 'company' in data and data['company']:
            company_info = render_company_simple(data['company'])
            sections.append(company_info)
        
        # 2. ФИНАНСОВАЯ ОТЧЁТНОСТЬ
        if 'finances' in include_sections and data.get('finances'):
            finances = render_finances_simple(data['finances'])
            sections.append(finances)
        
        # 3. АРБИТРАЖНЫЕ ДЕЛА
        if 'legal-cases' in include_sections and data.get('legal_cases'):
            legal_cases = render_legal(data['legal_cases'])
            sections.append(legal_cases)
        
        # 4. ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА
        if 'enforcements' in include_sections and data.get('enforcements'):
            enforcements = render_enforce(data['enforcements'])
            sections.append(enforcements)
        
        # 5. ПРОВЕРКИ
        if 'inspections' in include_sections and data.get('inspections'):
            inspections = render_inspect(data['inspections'])
            sections.append(inspections)
        
        # 6. ГОСЗАКУПКИ
        if 'contracts' in include_sections and data.get('contracts'):
            contracts = render_contracts_simple(data['contracts'])
            sections.append(contracts)
        
        # 8. ИП (если есть)
        if 'entrepreneur' in include_sections and data.get('entrepreneur'):
            entrepreneur = render_entrepreneur(data['entrepreneur'])
            sections.append(entrepreneur)
        
        # Объединяем все секции
        report_text = "\n\n".join(sections)
        
        # Добавляем секции ИСТОРИЯ КОМПАНИИ и РЕЗЮМЕ
        report_text = self._add_openai_sections(report_text)
        
        return report_text
    
    def _add_openai_sections(self, report_text: str) -> str:
        """Отключено: возвращаем исходный отчёт без секций OpenAI"""
        log.info("_add_openai_sections: disabled — returning report without OpenAI sections")
        return report_text
    
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
        log.info("build_simple_report: starting", ident=ident)
        from .formatters import format_money, format_date
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
            
            # 2. Получаем данные
            company_info = company_data.get('data', company_data)
            
            # 3. Загружаем дополнительные данные
            log.info("build_simple_report: loading additional data", include=include)
            
            # Загружаем финансы
            if 'finances' in include:
                try:
                    finances_data = self.client.get_finances(**ident)
                    if finances_data:
                        company_data['finances'] = finances_data
                        log.info("build_simple_report: finances loaded")
                except Exception as e:
                    log.warning("Could not load finances", error=str(e))
            
            # Загружаем арбитражные дела
            if 'legal-cases' in include:
                try:
                    legal_data = self.client.get_legal_cases(**ident)
                    if legal_data:
                        company_data['legal_cases'] = legal_data
                        log.info("build_simple_report: legal cases loaded")
                except Exception as e:
                    log.warning("Could not load legal cases", error=str(e))
            
            # Загружаем исполнительные производства
            if 'enforcements' in include:
                try:
                    enforce_data = self.client.get_enforcements(**ident)
                    if enforce_data:
                        company_data['enforcements'] = enforce_data
                        log.info("build_simple_report: enforcements loaded")
                except Exception as e:
                    log.warning("Could not load enforcements", error=str(e))
            
            # Загружаем проверки
            if 'inspections' in include:
                try:
                    inspect_data = self.client.get_inspections(**ident)
                    if inspect_data:
                        company_data['inspections'] = inspect_data
                        log.info("build_simple_report: inspections loaded")
                except Exception as e:
                    log.warning("Could not load inspections", error=str(e))
            
            # Загружаем контракты
            if 'contracts' in include:
                try:
                    # Загружаем контракты для разных законов и ролей
                    contracts_data = {}
                    
                    # 44-ФЗ как заказчик
                    try:
                        contracts_44_customer = self.client.get_contracts(law='44', role='customer', **ident)
                        if contracts_44_customer:
                            contracts_data['44_customer'] = contracts_44_customer
                    except Exception as e:
                        log.warning("Could not load 44-FZ customer contracts", error=str(e))
                    
                    # 44-ФЗ как поставщик
                    try:
                        contracts_44_supplier = self.client.get_contracts(law='44', role='supplier', **ident)
                        if contracts_44_supplier:
                            contracts_data['44_supplier'] = contracts_44_supplier
                    except Exception as e:
                        log.warning("Could not load 44-FZ supplier contracts", error=str(e))
                    
                    # 223-ФЗ как заказчик
                    try:
                        contracts_223_customer = self.client.get_contracts(law='223', role='customer', **ident)
                        if contracts_223_customer:
                            contracts_data['223_customer'] = contracts_223_customer
                    except Exception as e:
                        log.warning("Could not load 223-FZ customer contracts", error=str(e))
                    
                    # 223-ФЗ как поставщик
                    try:
                        contracts_223_supplier = self.client.get_contracts(law='223', role='supplier', **ident)
                        if contracts_223_supplier:
                            contracts_data['223_supplier'] = contracts_223_supplier
                    except Exception as e:
                        log.warning("Could not load 223-FZ supplier contracts", error=str(e))
                    
                    if contracts_data:
                        company_data['contracts'] = contracts_data
                        log.info("build_simple_report: contracts loaded", contracts_keys=list(contracts_data.keys()))
                except Exception as e:
                    log.warning("Could not load contracts", error=str(e))
            
            # Для налоговых данных нужно искать в правильном месте
            taxes_data = company_info.get('Налоги', {})
            
            # 3. Собираем секции
            sections = []
            
            # ОСНОВНОЕ
            if 'company' in include:
                from .simple_company_renderer import render_company_simple
                company_section = render_company_simple(company_info)
                sections.append(company_section)
            
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
                    if isinstance(total_paid, (int, float)) and total_paid > 0:
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
                    if isinstance(arrears, (int, float)) and arrears > 0:
                        formatted_date = format_date(arrears_date) if arrears_date != '—' else '—'
                        tax_lines.append(f"Недоимка: {format_money(arrears)} (на {formatted_date})")
                    
                    sections.append("\n".join(tax_lines))
                else:
                    sections.append("НАЛОГИ\n" + "=" * 50 + "\nДанные недоступны")
            
            # ФИНАНСОВАЯ ОТЧЁТНОСТЬ
            if 'finances' in include:
                try:
                    # Сначала проверяем, есть ли финансы в company_data (как в примере пользователя)
                    if 'data' in company_data and any(key.isdigit() and len(key) == 4 for key in company_data['data'].keys()):
                        finances = render_finances_simple(company_data)
                        sections.append(finances)
                    # Затем проверяем, есть ли финансы в company_data['finances']
                    elif company_data.get('finances') and 'data' in company_data['finances']:
                        finances = render_finances_simple(company_data['finances'])
                        sections.append(finances)
                    else:
                        sections.append("ФИНАНСОВАЯ ОТЧЁТНОСТЬ\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch finances", error=str(e))
                    sections.append("ФИНАНСОВАЯ ОТЧЁТНОСТЬ\n" + "=" * 50 + "\nДанные недоступны")
            
            # АРБИТРАЖНЫЕ ДЕЛА
            if 'legal-cases' in include:
                try:
                    if company_data.get('legal_cases') and 'data' in company_data['legal_cases']:
                        legal = render_legal(company_data['legal_cases'])
                        sections.append(legal)
                    else:
                        sections.append("АРБИТРАЖНЫЕ ДЕЛА\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch legal cases", error=str(e))
                    sections.append("АРБИТРАЖНЫЕ ДЕЛА\n" + "=" * 50 + "\nДанные недоступны")
            
            # ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА
            if 'enforcements' in include:
                try:
                    if company_data.get('enforcements') and 'data' in company_data['enforcements']:
                        enforce = render_enforce(company_data['enforcements'])
                        sections.append(enforce)
                    else:
                        sections.append("ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch enforcements", error=str(e))
                    sections.append("ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА\n" + "=" * 50 + "\nДанные недоступны")
            
            # ПРОВЕРКИ
            if 'inspections' in include:
                try:
                    if company_data.get('inspections') and 'data' in company_data['inspections']:
                        inspect = render_inspect(company_data['inspections'])
                        sections.append(inspect)
                    else:
                        sections.append("ПРОВЕРКИ\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not render inspections", error=str(e))
                    sections.append("ПРОВЕРКИ\n" + "=" * 50 + f"\nОшибка обработки данных: {str(e)}")
            
            # ГОСЗАКУПКИ
            if 'contracts' in include:
                try:
                    if company_data.get('contracts'):
                        contracts = render_contracts_simple(company_data['contracts'])
                        sections.append(contracts)
                    else:
                        sections.append("ГОСЗАКУПКИ\n" + "=" * 50 + "\nДанные недоступны")
                except Exception as e:
                    log.warning("Could not fetch contracts", error=str(e))
                    sections.append("ГОСЗАКУПКИ\n" + "=" * 50 + "\nДанные недоступны")
            
            # 4. Собираем полный текст
            full_text = "\n\n".join(sections)
            
            # 5. Добавляем OpenAI секции (только основные данные)
            try:
                # Извлекаем только основные данные компании для OpenAI
                company_name = company_info.get('НаимПолн', company_info.get('НаимСокр', 'Не указано'))
                inn = company_info.get('ИНН', 'Не указан')
                address = company_info.get('ЮрАдрес', company_info.get('Адрес', 'Не указан'))
                
                # Создаем краткий текст только с основными данными
                basic_data = f"НАЗВАНИЕ: {company_name}\nИНН: {inn}\nАДРЕС: {address}"
                
                history, bullets = self.summarize_history_and_bullets(basic_data)
                # Добавляем секции к отчёту
                full_text += f"\n\nИСТОРИЯ КОМПАНИИ\n{'=' * 50}\n{history}\n\nРЕЗЮМЕ\n{'=' * 50}\n{bullets}"
            except Exception as e:
                log.warning("Could not generate OpenAI sections", error=str(e))
                full_text += f"\n\nИСТОРИЯ КОМПАНИИ\n{'=' * 50}\nДанные недоступны\n\nРЕЗЮМЕ\n{'=' * 50}\nДанные недоступны"
            
            return full_text
            
        except Exception as e:
            log.error("ReportBuilder: error building simple report", error=str(e), ident=ident)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
    def summarize_history_and_bullets(self, full_text: str) -> Tuple[str, str]:
        """
        Генерирует историю компании и резюме с помощью OpenAI
        
        Args:
            full_text: Полный текст отчёта
            
        Returns:
            Кортеж (история, резюме)
        """
        try:
            # Используем OpenAI для генерации
            from services.providers.openai_provider import OpenAIProvider
            
            openai_provider = OpenAIProvider()
            
            # Генерируем историю и резюме асинхронно
            import asyncio
            
            async def generate_sections():
                history = await openai_provider.generate_company_history(full_text)
                summary = await openai_provider.generate_company_summary(full_text)
                return history, summary
            
            # Запускаем асинхронную генерацию
            try:
                # Проверяем, есть ли уже запущенный event loop
                loop = asyncio.get_running_loop()
                # Если есть, создаем задачу
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, generate_sections())
                    history, summary = future.result()
            except RuntimeError:
                # Если нет запущенного loop, создаем новый
                history, summary = asyncio.run(generate_sections())
            
            return history, summary
                
        except Exception as e:
            log.warning("Could not generate sections with OpenAI", error=str(e))
            return "Данные недоступны", "Данные недоступны"
