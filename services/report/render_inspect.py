# -*- coding: utf-8 -*-
"""
Рендер секции с проверками
"""
from typing import Dict, Any, List
from .formatters import format_money, format_date, clean_text
from .flattener import flatten, apply_aliases, extract_nested_value, count_array_items, sum_array_field


def render_inspect(data: Dict[str, Any]) -> str:
    """
    Рендерит проверки
    
    Args:
        data: Данные проверок
        
    Returns:
        Проверки
    """
    lines = []
    
    if not data:
        return "—"
    
    # Проверяем разные возможные структуры данных
    if 'data' in data:
        data_section = data['data']
        records = data_section.get('Записи', [])
    else:
        records = data.get('Записи', [])
    
    if not records:
        return "—"
    
    lines.append(f"Всего проверок: {len(records)}")
    
    # 10 последних проверок
    lines.append(f"\n10 последних проверок:")
    
    for i, record in enumerate(records[:10]):  # Показываем только первые 10
        # Ищем дату в разных полях
        date = record.get('Дата', '—')
        if not date or date == '—':
            date = record.get('ДатаНачала', '—')
        if not date or date == '—':
            date = record.get('ДатаПроведения', '—')
        
        # Ищем орган в разных полях
        org = record.get('Орган', '—')
        if not org or org == '—':
            org = record.get('НаимОрг', '—')
        if not org or org == '—':
            org = record.get('Наименование', '—')
        if not org or org == '—':
            org = record.get('НаименованиеОргана', '—')
        if not org or org == '—':
            org = record.get('ОрганКонтроля', '—')
        
        # Ищем описание
        description = record.get('Описание', '—')
        if not description or description == '—':
            description = record.get('Наименование', '—')
        if not description or description == '—':
            description = record.get('Тип', '—')
        if not description or description == '—':
            description = record.get('ВидПроверки', '—')
        
        # Ищем номер
        number = record.get('Номер', '—')
        if not number or number == '—':
            number = record.get('РегНомер', '—')
        if not number or number == '—':
            number = record.get('НомерПроверки', '—')
        if not number or number == '—':
            number = record.get('Индекс', '—')
        
        # Форматируем дату
        formatted_date = format_date(date) if date != '—' else '—'
        
        # Формируем строку - только непустые части
        line_parts = []
        if formatted_date != '—':
            line_parts.append(formatted_date)
        if org != '—':
            line_parts.append(clean_text(org))
        if description != '—' and description != org:
            line_parts.append(clean_text(description))
        if number != '—':
            line_parts.append(f"№{clean_text(number)}")
        
        # Если нет данных, показываем номер
        if not line_parts and number != '—':
            line_parts.append(f"№{clean_text(number)}")
        
        # Добавляем строку
        if line_parts:
            lines.append(f"• {' — '.join(line_parts)}")
        else:
            lines.append(f"• Данные недоступны")
    
    return "\n".join(lines)