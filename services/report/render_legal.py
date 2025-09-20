# -*- coding: utf-8 -*-
"""
Рендер секции с арбитражными делами
"""
from typing import Dict, Any, List
from .formatters import format_money, format_date, format_list, clean_text
from .flattener import flatten, apply_aliases, extract_nested_value, count_array_items, sum_array_field


def render_legal(data: Dict[str, Any]) -> str:
    """
    Рендерит арбитражные дела
    
    Args:
        data: Данные арбитражных дел
        
    Returns:
        Арбитражные дела
    """
    lines = []
    
    if not data or 'data' not in data:
        return "—"
    
    data_section = data['data']
    
    # Итоги
    total_cases = data_section.get('ЗапВсего', 0)
    total_amount = data_section.get('ОбщСуммИск', 0)
    
    lines.append(f"Всего дел: {total_cases}")
    
    if total_amount > 0:
        lines.append(f"Общая сумма исков: {format_money(total_amount)}")
        
        if total_cases > 0:
            avg_amount = total_amount / total_cases
            lines.append(f"Средняя сумма иска: {format_money(avg_amount)}")
    
    # Список дел
    records = data_section.get('Записи', [])
    if records:
        lines.append(f"\n10 последних дел:")
        
        for i, record in enumerate(records[:10]):  # Показываем только первые 10
            case_num = record.get('Номер', '—')
            date = record.get('Дата', '—')
            court = record.get('Суд', '—')
            amount = record.get('СуммИск', 0)
            
            # Участники дела
            plaintiffs = record.get('Ист', [])
            defendants = record.get('Ответ', [])
            
            # Форматируем участников
            plaintiffs_text = format_list(plaintiffs) if plaintiffs else "—"
            defendants_text = format_list(defendants) if defendants else "—"
            
            # Форматируем дату
            formatted_date = format_date(date) if date != '—' else '—'
            
            lines.append(f"• {clean_text(case_num)}, {formatted_date}, {clean_text(court)}, Истцы: {plaintiffs_text}, Ответчики: {defendants_text}, Сумма: {format_money(amount)}")
    else:
        lines.append("\nДела не найдены")
    
    return "\n".join(lines)