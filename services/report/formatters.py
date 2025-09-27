# -*- coding: utf-8 -*-
"""
Форматирование данных для отчёта
"""
from typing import Any, Union
from datetime import datetime
import re


def format_money(x: Union[int, float, str, None]) -> str:
    """
    Форматирует денежную сумму в российском стиле
    
    Args:
        x: Сумма для форматирования
        
    Returns:
        Отформатированная строка
    """
    if x is None:
        return "—"
    
    try:
        # Преобразуем в число
        if isinstance(x, str):
            # Убираем все нецифровые символы кроме точки и запятой
            clean_amount = re.sub(r'[^\d.,]', '', x)
            if not clean_amount:
                return "—"
            # Заменяем запятую на точку
            clean_amount = clean_amount.replace(',', '.')
            x = float(clean_amount)
        
        if not isinstance(x, (int, float)):
            return "—"
        
        # Форматируем с неразрывными пробелами как разделителями тысяч
        formatted = f"{x:,.2f}".replace(',', ' ').replace('.', ',')
        return f"{formatted} ₽"
        
    except (ValueError, TypeError):
        return "—"


def format_date(s: Union[str, None]) -> str:
    """
    Форматирует дату из YYYY-MM-DD в DD.MM.YYYY
    
    Args:
        s: Строка с датой
        
    Returns:
        Отформатированная дата
    """
    if s is None:
        return "—"
    
    try:
        # Если в формате YYYY-MM-DD, конвертируем в DD.MM.YYYY
        if re.match(r'\d{4}-\d{2}-\d{2}', str(s)):
            dt = datetime.strptime(str(s), '%Y-%m-%d')
            return dt.strftime('%d.%m.%Y')
        
        # Иначе возвращаем как есть
        return str(s)
        
    except Exception:
        return "—"


def format_percent(x: Union[int, float, str, None]) -> str:
    """
    Форматирует процентное значение
    
    Args:
        x: Значение для форматирования
        
    Returns:
        Отформатированная строка
    """
    if x is None:
        return "—"
    
    try:
        if isinstance(x, str):
            x = float(x.replace('%', '').replace(',', '.'))
        
        if isinstance(x, (int, float)):
            formatted = f"{x:.2f}".replace(".", ",")
            return f"{formatted} %"
        
        return "—"
    except (ValueError, TypeError):
        return "—"


def format_number(value: Union[int, float, str, None]) -> str:
    """
    Форматирует числовое значение с разделителями тысяч
    
    Args:
        value: Значение для форматирования
        
    Returns:
        Отформатированная строка
    """
    if value is None:
        return "—"
    
    try:
        if isinstance(value, str):
            # Убираем все нецифровые символы кроме точки и запятой
            clean_value = re.sub(r'[^\d.,]', '', value)
            if not clean_value:
                return "—"
            # Заменяем запятую на точку
            clean_value = clean_value.replace(',', '.')
            value = float(clean_value)
        
        if isinstance(value, (int, float)):
            # Форматируем с пробелами как разделителями тысяч
            formatted = f"{value:,.0f}".replace(',', ' ')
            return formatted
        
        return "—"
    except (ValueError, TypeError):
        return "—"


def format_boolean(value: Any) -> str:
    """
    Форматирует булево значение
    
    Args:
        value: Значение для форматирования
        
    Returns:
        Отформатированная строка
    """
    if value is None:
        return "—"
    
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ['true', 'да', 'yes', '1']:
            return "Да"
        elif lower_value in ['false', 'нет', 'no', '0']:
            return "Нет"
    
    return "—"


def format_list(items: Union[list, None]) -> str:
    """
    Форматирует список элементов
    
    Args:
        items: Список элементов
        
    Returns:
        Отформатированная строка
    """
    if not items or not isinstance(items, list) or len(items) == 0:
        return "—"
    
    # Преобразуем все элементы в строки и объединяем через ", "
    formatted_items = [str(item) for item in items]
    return ", ".join(formatted_items)


def format_address(address_data: Union[dict, str, None]) -> str:
    """
    Форматирует адрес
    
    Args:
        address_data: Данные адреса
        
    Returns:
        Отформатированный адрес
    """
    if not address_data:
        return "—"
    
    if isinstance(address_data, str):
        return address_data
    
    if isinstance(address_data, dict):
        parts = []
        
        # Собираем части адреса
        if address_data.get('НасПункт'):
            parts.append(address_data['НасПункт'])
        
        if address_data.get('АдресРФ'):
            parts.append(address_data['АдресРФ'])
        
        if address_data.get('Регион', {}).get('Наим'):
            parts.append(address_data['Регион']['Наим'])
        
        if parts:
            return ", ".join(parts)
    
    return "—"


def format_contact_info(contact_data: Union[dict, None]) -> str:
    """
    Форматирует контактную информацию
    
    Args:
        contact_data: Данные контактов
        
    Returns:
        Отформатированная контактная информация
    """
    if not contact_data:
        return "—"
    
    if not isinstance(contact_data, dict):
        return "—"
    
    parts = []
    
    # Телефоны
    if contact_data.get('Тел'):
        phones = contact_data['Тел']
        if isinstance(phones, list):
            parts.extend(phones)
        else:
            parts.append(str(phones))
    
    # Email
    if contact_data.get('Емэйл'):
        emails = contact_data['Емэйл']
        if isinstance(emails, list):
            parts.extend(emails)
        else:
            parts.append(str(emails))
    
    # Веб-сайт
    if contact_data.get('ВебСайт'):
        parts.append(contact_data['ВебСайт'])
    
    if parts:
        return " • ".join(parts)
    
    return "—"


def clean_text(text: Union[str, None]) -> str:
    """
    Очищает текст от лишних символов
    
    Args:
        text: Текст для очистки
        
    Returns:
        Очищенный текст
    """
    if not text:
        return "—"
    
    if not isinstance(text, str):
        return str(text)
    
    # Убираем лишние пробелы и переносы строк
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Убираем HTML теги если есть
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    
    return cleaned if cleaned else "—"

