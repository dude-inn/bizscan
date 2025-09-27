# -*- coding: utf-8 -*-
"""
Сборщик отчёта
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .ofdata_client import OFDataClient
from .simple_company_renderer import render_company_simple, load_aliases
from .simple_finances_renderer import render_finances_simple
from .render_legal import render_legal
from .render_enforce import render_enforce
from .render_inspect import render_inspect
from .simple_contracts_renderer import render_contracts_simple
from .render_entrepreneur import render_entrepreneur
from .render_person import render_person
from core.logger import setup_logging, get_logger
log = get_logger(__name__)


class ReportBuilder:
    """Сборщик отчёта"""
    
    def __init__(self):
        """Инициализация сборщика"""
        self.client = OFDataClient()
        self._aliases = load_aliases()
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
        
        log.info("ReportBuilder: start", query=query)
        
        try:
            # 1. Получаем данные
            log.debug("Fetching data from API", query=query, sections=include_sections)
            data = self._fetch_data(query, include_sections)
            log.debug("Data fetched", data_keys=list(data.keys()) if data else None)
            
            # 2. Строим отчёт
            log.debug("Building report sections", sections=include_sections)
            report = self._build_report_sections(data, include_sections)
            log.debug("Report sections built", report_length=len(report) if report else 0)
            
            # 3. Добавляем OpenAI секции
            full_report = self._add_openai_sections(report)
            
            log.info("ReportBuilder: done", length=len(full_report))
            return full_report
            
        except Exception as e:
            log.error("ReportBuilder: error generating report", error=str(e), query=query)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
    def _fetch_data(self, query: str, include_sections: List[str]) -> Dict[str, Any]:
        """Получает данные из OFData API"""
        log.debug("_fetch_data: start", query=query, sections=include_sections)
        data = {}
        
        # Определяем тип запроса и получаем базовую информацию
        if query.isdigit() and len(query) in [10, 12]:
            # ИНН или ОГРН
            if len(query) == 10:
                log.debug("Fetching company by INN", inn=query)
                company_data = self.client.get_company(inn=query)
            else:
                log.debug("Fetching company by OGRN", ogrn=query)
                company_data = self.client.get_company(ogrn=query)
            
            # Проверяем, что компания найдена
            log.debug("_fetch_data: check company data", 
                     has_company_data=bool(company_data),
                     has_data_key=bool(company_data.get('data') if company_data else None))
            if not company_data or not company_data.get('data'):
                log.warning("Company not found in API response", query=query, response=company_data)
                raise ValueError("Компания не найдена")
            
            log.debug("Company data fetched", company_keys=list(company_data.keys()) if company_data else None)
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
            company_payload = data['company']
            company_section = render_company_simple(company_payload)
            sections.append(company_section)
            company_info = company_payload.get('data', {}) if isinstance(company_payload, dict) else {}
            relationship_sections = self._build_company_relationship_sections(company_info)
            if relationship_sections:
                sections.extend(relationship_sections)
        
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
        
        # 9. ФИЗЛИЦА: руководитель и учредители (если есть ИНН)
        try:
            company = data.get('company', {})
            company_info = company.get('data', {}) if isinstance(company, dict) else {}
            person_inns = set()
            # Руководство
            ruk = company_info.get('Руковод') or {}
            if isinstance(ruk, dict):
                inn_ruk = ruk.get('ИНН')
                if inn_ruk:
                    person_inns.add(str(inn_ruk))
            # Учредители — ФЛ
            uch = company_info.get('Учред') or {}
            fl_list = None
            if isinstance(uch, dict):
                fl_list = uch.get('ФЛ')
            if isinstance(fl_list, list):
                for fl in fl_list:
                    if isinstance(fl, dict) and fl.get('ИНН'):
                        person_inns.add(str(fl['ИНН']))
            # Берём до 5 ИНН, чтобы не перегружать отчёт
            if person_inns:
                person_sections = []
                for inn in list(person_inns)[:5]:
                    try:
                        person = self.client.get_person(inn=inn)
                        if person and person.get('data'):
                            person_sections.append(render_person(person))
                    except Exception as e:
                        log.warning("Could not fetch person", inn=inn, error=str(e))
                if person_sections:
                    sections.append("\nФИЗИЧЕСКИЕ ЛИЦА (РУКОВОДИТЕЛЬ/УЧРЕДИТЕЛИ)\n" + "=" * 50 + "\n" + "\n\n".join(person_sections))
        except Exception as e:
            log.warning("person-section: error", error=str(e))
        
        # Объединяем все секции
        report_text = "\n\n".join(sections)
        
        # Добавляем секции ИСТОРИЯ КОМПАНИИ и РЕЗЮМЕ
        report_text = self._add_openai_sections(report_text)
        
        return report_text
    
    
    def summarize_history_and_bullets(self, report_text: str) -> Tuple[str, str]:
        '''Возвращает краткую историю и маркированный список по тексту отчёта.'''
        if not report_text:
            return "", ""

        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        if not lines:
            return "", ""

        title = lines[0]
        history_parts: List[str] = [title]
        bullet_lines: List[str] = []

        for line in lines[1:]:
            if set(line) == {'='}:
                continue
            if line.lower().startswith('основное'):
                continue
            normalized = line.lower()
            if (
                ':' in line
                or '•' in line
                or any(key in normalized for key in ("инн", "огрн", "регион", "руковод", "выруч", "прибыл"))
            ):
                history_parts.append(line)
                bullet_text = line if line.startswith('•') else f"• {line}"
                bullet_lines.append(bullet_text)
            if len(bullet_lines) >= 5:
                break

        history = "\n".join(history_parts)
        bullets = "\n".join(bullet_lines) if bullet_lines else "• Нет ключевых фактов"
        return history, bullets

    def _add_openai_sections(self, report_text: str) -> str:
        """Отключено: возвращаем исходный отчёт без секций OpenAI"""
        log.info("_add_openai_sections: disabled — returning report without OpenAI sections")
        return report_text

    def _build_company_relationship_sections(self, company_info: Dict[str, Any]) -> List[str]:
        sections: List[str] = []
        if not isinstance(company_info, dict):
            return sections
        founders_section = self._render_founders_section(company_info.get('Учред'))
        if founders_section:
            sections.append(founders_section)
        related_section = self._render_related_companies_section(company_info.get('СвязУчред'))
        if related_section:
            sections.append(related_section)
        leadership_section = self._render_leadership_section(company_info.get('Руковод'))
        if leadership_section:
            sections.append(leadership_section)
        return sections

    def _render_founders_section(self, founders_data: Any) -> Optional[str]:
        if not founders_data:
            return None
        lines: List[str] = []
        if isinstance(founders_data, dict):
            categories = [
                ("Физические лица", "ФЛ"),
                ("Российские организации", "РосОрг"),
                ("Иностранные организации", "ИнОрг"),
                ("ПИФы", "ПИФ"),
                ("Государство/муниципалитеты", "РФ"),
            ]
            handled_keys = set()
            for title, key in categories:
                handled_keys.add(key)
                items = self._collect_items(founders_data.get(key))
                if not items:
                    continue
                lines.append(f"{title}:")
                lines.extend(self._format_dict_list(items, indent="  "))
                lines.append("")
            for key, value in founders_data.items():
                if key in handled_keys:
                    continue
                items = self._collect_items(value)
                if not items:
                    continue
                title = self._aliases.get(f"Учред.{key}", self._aliases.get(key, key))
                lines.append(f"{title}:")
                lines.extend(self._format_dict_list(items, indent="  "))
                lines.append("")
        else:
            items = self._collect_items(founders_data)
            if items:
                lines.extend(self._format_dict_list(items))
        lines = self._trim_trailing_blank_lines(lines)
        if not lines:
            return None
        return "УЧРЕДИТЕЛИ\n" + "=" * 50 + "\n" + "\n".join(lines)

    def _render_related_companies_section(self, related_data: Any) -> Optional[str]:
        items = self._collect_items(related_data)
        if not items:
            return None
        lines = self._trim_trailing_blank_lines(self._format_dict_list(items))
        if not lines:
            return None
        return "СВЯЗАННЫЕ КОМПАНИИ\n" + "=" * 50 + "\n" + "\n".join(lines)

    def _render_leadership_section(self, leadership_data: Any) -> Optional[str]:
        items = self._collect_items(leadership_data)
        if not items:
            return None
        lines = self._trim_trailing_blank_lines(self._format_dict_list(items, max_items=10))
        if not lines:
            return None
        return "РУКОВОДСТВО\n" + "=" * 50 + "\n" + "\n".join(lines)

    def _collect_items(self, value: Any) -> List[Any]:
        if isinstance(value, list):
            return [item for item in value if item not in (None, {}, [])]
        if isinstance(value, dict):
            collected: List[Any] = []
            for sub in value.values():
                if isinstance(sub, list):
                    collected.extend(item for item in sub if item not in (None, {}, []))
            if collected:
                return collected
            return [value]
        if value not in (None, "", [], {}):
            return [value]
        return []

    def _format_dict_list(self, items: List[Any], indent: str = "", max_items: int = 20) -> List[str]:
        lines: List[str] = []
        if not items:
            return lines
        trimmed = [item for item in items if item not in (None, {}, [])]
        if not trimmed:
            return lines
        limited = trimmed[:max_items]
        for item in limited:
            entry = self._format_dict_entry(item)
            if entry:
                lines.append(f"{indent}• {entry}")
        if len(trimmed) > max_items:
            lines.append(f"{indent}• … и ещё {len(trimmed) - max_items} записей")
        return lines

    def _format_dict_entry(self, item: Any) -> str:
        if isinstance(item, dict):
            return format_dict_item(item, self._aliases).strip()
        return str(item).strip()

    def _trim_trailing_blank_lines(self, lines: List[str]) -> List[str]:
        result = list(lines)
        while result and not result[-1].strip():
            result.pop()
        return result

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
            log.debug("build_simple_report: loading additional data", include=include)
            
            # Загружаем финансы
            if 'finances' in include:
                try:
                    finances_data = self.client.get_finances(**ident)
                    if finances_data:
                        company_data['finances'] = finances_data
                        log.debug("build_simple_report: finances loaded")
                except Exception as e:
                    log.warning("Could not load finances", error=str(e))
            
            # Загружаем арбитражные дела
            if 'legal-cases' in include:
                try:
                    legal_data = self.client.get_legal_cases(**ident)
                    if legal_data:
                        company_data['legal_cases'] = legal_data
                        log.debug("build_simple_report: legal cases loaded")
                except Exception as e:
                    log.warning("Could not load legal cases", error=str(e))
            
            # Загружаем исполнительные производства
            if 'enforcements' in include:
                try:
                    enforce_data = self.client.get_enforcements(**ident)
                    if enforce_data:
                        company_data['enforcements'] = enforce_data
                        log.debug("build_simple_report: enforcements loaded")
                except Exception as e:
                    log.warning("Could not load enforcements", error=str(e))
            
            # Загружаем проверки
            if 'inspections' in include:
                try:
                    inspect_data = self.client.get_inspections(**ident)
                    if inspect_data:
                        company_data['inspections'] = inspect_data
                        log.debug("build_simple_report: inspections loaded")
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
                        log.debug("build_simple_report: contracts loaded", contracts_keys=list(contracts_data.keys()))
                except Exception as e:
                    log.warning("Could not load contracts", error=str(e))
            
            # Для налоговых данных нужно искать в правильном месте
            taxes_data = company_info.get('Налоги', {})
            
            # 3. Собираем секции
            sections = []
            
            # ОСНОВНОЕ
            if 'company' in include:
                from .simple_company_renderer import render_company_simple, load_aliases
                company_section = render_company_simple(company_info)
                sections.append(company_section)
                # ФИЗЛИЦА (руководитель и учредители)
                try:
                    from .render_person import render_person
                    person_inns = set()
                    ruk = company_info.get('Руковод')
                    # Руковод может быть dict или list
                    if isinstance(ruk, dict):
                        inn_ruk = ruk.get('ИНН')
                        if inn_ruk:
                            person_inns.add(str(inn_ruk))
                    elif isinstance(ruk, list):
                        for item in ruk:
                            if isinstance(item, dict) and item.get('ИНН'):
                                person_inns.add(str(item['ИНН']))
                    uch = company_info.get('Учред') or {}
                    fl_list = uch.get('ФЛ') if isinstance(uch, dict) else None
                    if isinstance(fl_list, list):
                        for fl in fl_list:
                            if isinstance(fl, dict) and fl.get('ИНН'):
                                person_inns.add(str(fl['ИНН']))
                    # Ограничим до 5 профилей
                    if person_inns:
                        person_blocks = []
                        for inn in list(person_inns)[:5]:
                            try:
                                person = self.client.get_person(inn=inn)
                                if person and person.get('data'):
                                    person_blocks.append(render_person(person))
                            except Exception as e:
                                log.warning("build_simple_report: person fetch failed", inn=inn, error=str(e))
                        if person_blocks:
                            sections.append("ФИЗИЧЕСКИЕ ЛИЦА (РУКОВОДИТЕЛЬ/УЧРЕДИТЕЛИ)\n" + "=" * 50 + "\n" + "\n\n".join(person_blocks))
                except Exception as e:
                    log.warning("build_simple_report: person section error", error=str(e))
            
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
                        # Полный список (в человекочитаемом виде)
                        tax_lines.append("")
                        tax_lines.append("Все уплаченные налоги (полный список):")
                        for tax in sorted_taxes:
                            name = tax.get('Наим', '—')
                            amount = tax.get('Сумма', 0)
                            year = tax.get('Год') or taxes_data.get('СведУплГод') or '—'
                            tax_lines.append(f"• {year}: {name} — {format_money(amount)}")
                    
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
            
            # 5. OpenAI секции отключены
            
            return full_text
            
        except Exception as e:
            log.error("ReportBuilder: error building simple report", error=str(e), ident=ident)
            return f"❌ Ошибка при формировании отчёта: {str(e)}"
    
    # OpenAI summarization disabled: method removed








