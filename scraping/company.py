# -*- coding: utf-8 -*-
from typing import Optional
from bs4 import BeautifulSoup
from domain.models import CompanyFull, FinanceYear, Flags, Founder, License
from scraping.normalize import normalize_whitespace
from scraping.extractors import (
    extract_company_basic_info, extract_contacts, extract_stats_codes,
    extract_okveds, extract_founders_directors, extract_finance_table,
    extract_legal_flags, extract_licenses,
    extract_core_requisites, extract_okved_main_detail, extract_stats_codes_block,
    extract_finance_summary, extract_reliability_summary, extract_executions_summary,
    extract_procurements_summary, extract_checks_summary, extract_trademarks_summary,
    extract_events_summary
)
from scraping.validators import validate_company_data
from scraping.normalize import normalize_date, normalize_digits
from core.logger import setup_logging

log = setup_logging()

async def parse_company_html(html: str, url: Optional[str] = None) -> CompanyFull:
    """Парсинг HTML страницы компании с использованием новых модулей"""
    soup = BeautifulSoup(html, "html.parser")
    data = CompanyFull(source_url=url)

    try:
        # Название компании
        h1 = soup.select_one("h1")
        if h1:
            data.short_name = normalize_whitespace(h1.get_text())

        # Полное наименование
        full_name_el = soup.find(text=lambda t: t and "полное наименование" in t.lower())
        if full_name_el and full_name_el.parent:
            parent = full_name_el.parent
            # Ищем значение в следующих элементах
            current = parent.next_sibling
            while current:
                if hasattr(current, 'get_text'):
                    text = current.get_text(strip=True)
                    if text and len(text) > len(data.short_name or ""):
                        data.full_name = text
                        break
                current = current.next_sibling
        
        if not data.full_name:
            data.full_name = data.short_name

        # Извлекаем основную информацию
        basic_info = extract_company_basic_info(soup)
        core = extract_core_requisites(soup)
        
        # Заполняем поля
        data.status = core.get('status') or basic_info.get('status')
        data.inn = core.get('inn') or basic_info.get('inn')
        data.kpp = core.get('kpp') or basic_info.get('kpp')
        data.ogrn = core.get('ogrn') or basic_info.get('ogrn')
        data.ogrn_date = normalize_date(core.get('ogrn_date') or basic_info.get('ogrn_date'))
        data.reg_date = normalize_date(core.get('reg_date') or basic_info.get('reg_date'))
        data.address = core.get('address') or basic_info.get('address')
        data.director = core.get('director') or basic_info.get('director')
        data.okved_main = basic_info.get('okved_main')
        data.msp_status = core.get('msp_status') or basic_info.get('msp_status')
        data.tax_authority = core.get('tax_authority') or basic_info.get('tax_authority')
        data.authorized_capital = core.get('authorized_capital')

        # Жёсткая нормализация числовых идентификаторов до валидной длины
        if data.inn:
            data.inn = normalize_digits(data.inn)[:12]  # ИНН 10/12, не больше 12
        if data.kpp:
            data.kpp = normalize_digits(data.kpp)[:9]   # КПП строго 9
        if data.ogrn:
            data.ogrn = normalize_digits(data.ogrn)[:15]  # ОГРН 13/15, не больше 15

        # Извлекаем коды статистики
        data.stats_codes = extract_stats_codes_block(soup)

        # Извлекаем контакты
        data.contacts = extract_contacts(soup)

        # Извлекаем ОКВЭДы
        okveds = extract_okveds(soup)
        if okveds['main']:
            data.okved_main = okveds['main'][0]  # берем первый основной
        data.okved_additional = okveds['additional']
        # Сохраним подробности ОКВЭД (код, заголовок), если найдены
        try:
            setattr(data, 'okveds', okveds)
        except Exception:
            pass
        code, title = extract_okved_main_detail(soup)
        if code:
            data.okved_main_code = code
        if title:
            data.okved_main_title = title

        # Извлекаем учредителей и руководителей
        people = extract_founders_directors(soup)
        data.founders = [Founder(**founder) for founder in people['founders']]
        if people['directors'] and not data.director:
            data.director = people['directors'][0]['name']

        # Извлекаем финансовые данные
        finance_data = extract_finance_table(soup)
        for year, indicators in finance_data.items():
            try:
                fy = FinanceYear(year=int(year))
                fy.revenue = indicators.get('revenue', '')
                fy.profit = indicators.get('profit', '')
                fy.assets = indicators.get('assets', '')
                fy.liabilities = indicators.get('liabilities', '')
                data.finance.append(fy)
            except ValueError:
                log.warning("Invalid year in finance data", year=year)

        # Извлекаем правовые индикаторы
        legal_flags = extract_legal_flags(soup)
        flags = Flags()
        flags.mass_director = legal_flags.get('массовый руководитель', False)
        flags.mass_founder = legal_flags.get('массовый учредитель', False)
        flags.unreliable_address = legal_flags.get('недостоверность адреса', False)
        flags.unreliable_director = legal_flags.get('недостоверность руководителя', False)
        flags.unreliable_founder = legal_flags.get('недостоверность учредителя', False)
        flags.tax_debt = legal_flags.get('налоговая задолженность', False)
        flags.disqualified = legal_flags.get('дисквалифицированные лица', False)
        flags.unreliable_supplier = legal_flags.get('недобросовестные поставщики', False)
        data.flags = flags

        # Извлекаем лицензии
        licenses_data = extract_licenses(soup)
        data.licenses = [License(**license) for license in licenses_data]

        # Адрес: жёсткие CSS-фолбэки
        if not data.address:
            addr_el = (soup.select_one("[itemprop='address']") or
                       soup.select_one(".company-address, .company-info__address"))
            if addr_el:
                data.address = addr_el.get_text(" ", strip=True)

        # Статус: по пиле/классу или ключевым словам
        if not data.status:
            st_el = soup.select_one(".company-status, .company-status__text, .status")
            if st_el:
                data.status = st_el.get_text(" ", strip=True)
        if not data.status:
            page_txt = soup.get_text(" ", strip=True).lower()
            for k in ["действующ", "ликвидирован", "в стадии ликвидации", "реорганизац"]:
                if k in page_txt:
                    data.status = "Действующая" if "действующ" in k else "Не действует"
                    break
        # Ограничим статус по длине, чтобы не захватывать длинные описания
        if data.status and len(data.status) > 150:
            data.status = data.status[:150]

        # Валидация данных
        validated_data = validate_company_data({
            'inn': data.inn,
            'ogrn': data.ogrn,
            'kpp': data.kpp,
            'reg_date': data.reg_date,
            'ogrn_date': data.ogrn_date,
            'contacts': data.contacts
        })
        
        # Обновляем валидированные поля
        data.inn = validated_data.get('inn')
        data.ogrn = validated_data.get('ogrn')
        data.kpp = validated_data.get('kpp')
        data.reg_date = validated_data.get('reg_date')
        data.ogrn_date = validated_data.get('ogrn_date')
        data.contacts = validated_data.get('contacts', {})

        # Логируем предупреждения для пустых ключевых полей
        if not data.inn:
            log.warning("INN not found for company", company=data.short_name)
        if not data.ogrn:
            log.warning("OGRN not found for company", company=data.short_name)
        if not data.status:
            log.warning("Status not found for company", company=data.short_name)
        if not data.address:
            log.warning("Address not found for company", company=data.short_name)

        log.info("Company parsed successfully", 
                company=data.short_name, 
                inn=data.inn, 
                ogrn=data.ogrn,
                has_contacts=bool(data.contacts),
                finance_years=len(data.finance))

        # Расширенные саммари (в extra)
        data.extra = {
            'finance': extract_finance_summary(soup),
            'reliability': extract_reliability_summary(soup),
            'executions': extract_executions_summary(soup),
            'procurements': extract_procurements_summary(soup),
            'checks': extract_checks_summary(soup),
            'trademarks': extract_trademarks_summary(soup),
            'events': extract_events_summary(soup),
        }

    except Exception as e:
        log.exception("Error parsing company HTML", exc_info=e)

    return data
