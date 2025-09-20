# -*- coding: utf-8 -*-
"""
Рендер секции с информацией о компании
"""
from typing import Dict, Any, List
from .formatters import format_money, format_date, format_list, clean_text
from .flattener import flatten, apply_aliases, extract_nested_value
from .aliases_ru import COMMON_ALIASES, COMPANY_ALIASES


def render_company(data: Dict[str, Any]) -> str:
    """
    Рендерит информацию о компании
    
    Args:
        data: Данные компании
        
    Returns:
        Информация о компании
    """
    lines = []
    
    # Разворачиваем данные
    flat_data = flatten(data)
    aliases = {**COMMON_ALIASES, **COMPANY_ALIASES}
    aliased_data = apply_aliases(flat_data, aliases)
    
    # ОСНОВНОЕ
    lines.append("ОСНОВНОЕ")
    lines.append("=" * 50)
    
    # Ключевые реквизиты
    main_fields = [
        'Полное наименование',
        'Краткое наименование', 
        'ИНН',
        'ОГРН',
        'КПП',
        'ОКПО',
        'Дата регистрации',
        'Дата ликвидации',
        'Юридический адрес',
        'Населённый пункт',
        'Регион',
        'ОКВЭД (основной) — код',
        'ОКВЭД (основной) — описание',
        'ОКОПФ — код',
        'ОКОПФ — наименование',
        'Среднесписочная численность'
    ]
    
    for field in main_fields:
        if field in aliased_data and aliased_data[field]:
            value = aliased_data[field]
            if 'Дата' in field:
                value = format_date(value)
            lines.append(f"{field}: {value}")
    
    # КОНТАКТЫ
    lines.append("\nКОНТАКТЫ")
    lines.append("=" * 50)
    
    contacts = data.get('Контакты', {})
    if contacts:
        phones = contacts.get('Тел', [])
        emails = contacts.get('Емэйл', [])
        website = contacts.get('ВебСайт', '')
        
        if phones:
            lines.append(f"Телефоны: {format_list(phones)}")
        if emails:
            lines.append(f"Email: {format_list(emails)}")
        if website:
            lines.append(f"Сайт: {clean_text(website)}")
    
        # НАЛОГИ убраны - обрабатываются в build_simple_report
    
    # УЧРЕДИТЕЛИ
    lines.append("\nУЧРЕДИТЕЛИ")
    lines.append("=" * 50)
    
    founders = data.get('Учредители', [])
    if founders:
        for i, founder in enumerate(founders[:10]):  # До 10 учредителей
            name = founder.get('Наим', '—')
            share = founder.get('ДоляПроц', '—')
            lines.append(f"{i+1}. {clean_text(name)} — {share}%")
    else:
        lines.append("Данные недоступны")
    
    return "\n".join(lines)


