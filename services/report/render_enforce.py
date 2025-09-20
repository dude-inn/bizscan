# -*- coding: utf-8 -*-
"""
Рендер секции с исполнительными производствами
"""
from typing import Dict, Any, List
from .formatters import format_money, format_date, clean_text
from .flattener import flatten, apply_aliases, extract_nested_value, count_array_items, sum_array_field


def render_enforce(data: Dict[str, Any]) -> str:
    """
    Рендерит исполнительные производства
    
    Args:
        data: Данные исполнительных производств
        
    Returns:
        Исполнительные производства
    """
    lines = []
    
    if not data or 'data' not in data:
        return "—"
    
    data_section = data['data']
    
    # Итоги
    records = data_section.get('Записи', [])
    total_records = len(records)
    
    if total_records == 0:
        return "—"
    
    # Суммы
    total_debt = sum(record.get('СумДолг', 0) for record in records)
    total_remaining = sum(record.get('ОстЗадолж', 0) for record in records)
    
    lines.append(f"Всего производств: {total_records}")
    
    if total_debt > 0:
        lines.append(f"Общая сумма долга: {format_money(total_debt)}")
    
    if total_remaining > 0:
        lines.append(f"Остаток задолженности: {format_money(total_remaining)}")
    
    # Список производств
    if records:
        lines.append(f"\n10 последних производств:")
        
        for i, record in enumerate(records[:10]):  # Показываем только первые 10
            case_num = record.get('ИспПрНомер', '—')
            date = record.get('ИспПрДата', '—')
            bailiff = record.get('СудПристНаим', '—')
            debt = record.get('СумДолг', 0)
            remaining = record.get('ОстЗадолж', 0)
            
            # Форматируем дату
            formatted_date = format_date(date) if date != '—' else '—'
            
            lines.append(f"• №{clean_text(case_num)} от {formatted_date}, Приставы: {clean_text(bailiff)}, Долг: {format_money(debt)}, Остаток: {format_money(remaining)}")
    else:
        lines.append("\nПроизводства не найдены")
    
    return "\n".join(lines)