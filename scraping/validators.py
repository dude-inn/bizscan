# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, Optional
from core.logger import setup_logging

log = setup_logging()

def validate_inn(inn: str) -> Optional[str]:
    """Валидация ИНН"""
    if not inn:
        return None
    
    # Убираем все нецифровые символы
    inn_clean = re.sub(r'[^0-9]', '', inn)
    
    # ИНН может быть 10 или 12 цифр
    if len(inn_clean) not in [10, 12]:
        log.warning("Invalid INN length", inn=inn_clean)
        return None
    
    # Простая проверка на валидность (можно расширить)
    if not inn_clean.isdigit():
        return None
        
    return inn_clean

def validate_ogrn(ogrn: str) -> Optional[str]:
    """Валидация ОГРН"""
    if not ogrn:
        return None
    
    # Убираем все нецифровые символы
    ogrn_clean = re.sub(r'[^0-9]', '', ogrn)
    
    # ОГРН может быть 13 или 15 цифр
    if len(ogrn_clean) not in [13, 15]:
        log.warning("Invalid OGRN length", ogrn=ogrn_clean)
        return None
    
    if not ogrn_clean.isdigit():
        return None
        
    return ogrn_clean

def validate_kpp(kpp: str) -> Optional[str]:
    """Валидация КПП"""
    if not kpp:
        return None
    
    # Убираем все нецифровые символы
    kpp_clean = re.sub(r'[^0-9]', '', kpp)
    
    # КПП должен быть 9 цифр
    if len(kpp_clean) != 9:
        log.warning("Invalid KPP length", kpp=kpp_clean)
        return None
    
    if not kpp_clean.isdigit():
        return None
        
    return kpp_clean

def validate_date(date_str: str) -> Optional[str]:
    """Валидация даты"""
    if not date_str:
        return None
    
    # Проверяем формат DD.MM.YYYY
    date_pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
    match = re.match(date_pattern, date_str.strip())
    
    if not match:
        log.warning("Invalid date format", date=date_str)
        return None
    
    day, month, year = match.groups()
    
    # Простая проверка на разумность даты
    try:
        day_int, month_int, year_int = int(day), int(month), int(year)
        if not (1 <= day_int <= 31 and 1 <= month_int <= 12 and 1900 <= year_int <= 2100):
            log.warning("Invalid date values", date=date_str)
            return None
    except ValueError:
        log.warning("Invalid date conversion", date=date_str)
        return None
    
    return date_str.strip()

def validate_contacts(contacts: Dict[str, Any]) -> Dict[str, Any]:
    """Валидация контактных данных"""
    if not contacts:
        return {}
    
    validated = {}
    
    # Валидация телефонов
    if 'phones' in contacts:
        phones = contacts['phones']
        if isinstance(phones, list):
            validated_phones = []
            for phone in phones:
                if phone and isinstance(phone, str):
                    # Убираем все кроме цифр, +, -, (, ), пробелов
                    phone_clean = re.sub(r'[^0-9+\-() ]', '', phone)
                    if phone_clean:
                        validated_phones.append(phone_clean)
            if validated_phones:
                validated['phones'] = validated_phones
    
    # Валидация email
    if 'email' in contacts:
        email = contacts['email']
        if email and isinstance(email, str):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, email.strip()):
                validated['email'] = email.strip()
    
    # Валидация сайта
    if 'website' in contacts:
        website = contacts['website']
        if website and isinstance(website, str):
            website_clean = website.strip()
            if website_clean and not website_clean.startswith('http'):
                website_clean = 'http://' + website_clean
            validated['website'] = website_clean
    
    return validated

def validate_company_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Валидация данных компании"""
    validated = {}
    
    # Валидируем основные поля
    if 'inn' in data:
        validated['inn'] = validate_inn(data['inn'])
    
    if 'ogrn' in data:
        validated['ogrn'] = validate_ogrn(data['ogrn'])
    
    if 'kpp' in data:
        validated['kpp'] = validate_kpp(data['kpp'])
    
    if 'reg_date' in data:
        validated['reg_date'] = validate_date(data['reg_date'])
    
    if 'ogrn_date' in data:
        validated['ogrn_date'] = validate_date(data['ogrn_date'])
    
    if 'contacts' in data:
        validated['contacts'] = validate_contacts(data['contacts'])
    
    return validated
