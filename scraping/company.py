# -*- coding: utf-8 -*-
from typing import Optional
from bs4 import BeautifulSoup
from domain.models import CompanyFull, FinanceYear, Flags, Founder, License
from scraping.normalize import normalize_whitespace
from scraping.extractors import (
    extract_company_basic_info, extract_contacts, extract_stats_codes,
    extract_okveds, extract_founders_directors, extract_finance_table,
    extract_legal_flags, extract_licenses
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
        
        # Заполняем поля
        data.status = basic_info.get('status')
        data.inn = basic_info.get('inn')
        data.kpp = basic_info.get('kpp')
        data.ogrn = basic_info.get('ogrn')
        data.ogrn_date = normalize_date(basic_info.get('ogrn_date'))
        data.reg_date = normalize_date(basic_info.get('reg_date'))
        data.address = basic_info.get('address')
        data.director = basic_info.get('director')
        data.okved_main = basic_info.get('okved_main')
        data.msp_status = basic_info.get('msp_status')
        data.tax_authority = basic_info.get('tax_authority')

        # Жёсткая нормализация числовых идентификаторов до валидной длины
        if data.inn:
            data.inn = normalize_digits(data.inn)[:12]  # ИНН 10/12, не больше 12
        if data.kpp:
            data.kpp = normalize_digits(data.kpp)[:9]   # КПП строго 9
        if data.ogrn:
            data.ogrn = normalize_digits(data.ogrn)[:15]  # ОГРН 13/15, не больше 15

        # Извлекаем коды статистики
        data.stats_codes = extract_stats_codes(soup)

        # Извлекаем контакты
        data.contacts = extract_contacts(soup)

        # Извлекаем ОКВЭДы
        okveds = extract_okveds(soup)
        if okveds['main']:
            data.okved_main = okveds['main'][0]  # берем первый основной
        data.okved_additional = okveds['additional']

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

    except Exception as e:
        log.exception("Error parsing company HTML", exc_info=e)

    return data
