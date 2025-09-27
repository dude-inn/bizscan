# -*- coding: utf-8 -*-
"""
Рендер секции с арбитражными делами - максимально простой
"""
from typing import Dict, Any
from .constants import SECTION_HEADERS, SECTION_SEPARATOR, ERROR_MESSAGES
from .simple_company_renderer import format_value, format_dict_item
from .formatters import format_money


def render_legal(data: Dict[str, Any]) -> str:
    """
    Рендерит арбитражные дела с сокращенным форматом
    
    Args:
        data: Данные арбитражных дел
        
    Returns:
        Информация об арбитражных делах
    """
    lines = []
    aliases = load_legal_aliases()
    
    # Обрабатываем основные поля
    for key, value in data.items():
        if key == 'data' and isinstance(value, dict):
            # Обрабатываем данные дел
            records = value.get('Записи', [])
            if records:
                # Фильтруем дела за последние 5 лет
                current_year = 2025
                min_year = current_year - 5  # 2020
                filtered_records = []
                
                for case in records:
                    case_date = case.get('Дата', '')
                    if case_date:
                        try:
                            # Парсим дату (формат: YYYY-MM-DD)
                            year = int(case_date.split('-')[0])
                            if year >= min_year:
                                filtered_records.append(case)
                        except (ValueError, IndexError):
                            # Если не можем распарсить дату, включаем дело
                            filtered_records.append(case)
                    else:
                        # Если даты нет, включаем дело
                        filtered_records.append(case)
                
                records = filtered_records
                lines.append(SECTION_HEADERS.get('legal-cases', 'АРБИТРАЖНЫЕ ДЕЛА'))
                lines.append(SECTION_SEPARATOR)
                
                # Статистика
                total_cases = len(records)
                total_amount = sum(case.get('СуммИск', 0) for case in records if isinstance(case.get('СуммИск'), (int, float)))
                plaintiff_count = sum(1 for case in records if case.get('Ист'))
                defendant_count = sum(1 for case in records if case.get('Ответ'))
                
                lines.append(f"Всего дел: {total_cases}")
                lines.append(f"Общая сумма исков: {format_money(total_amount)}")
                lines.append(f"Как истец: {plaintiff_count} дел")
                lines.append(f"Как ответчик: {defendant_count} дел")
                lines.append("")
                
                # Список дел (сокращенный формат)
                lines.append("Список дел:")
                for i, case in enumerate(records, 1):
                    # Определяем роль компании
                    role = "Истец" if case.get('Ист') else "Ответчик" if case.get('Ответ') else "Неизвестно"
                    
                    # Форматируем сумму
                    amount = case.get('СуммИск', 0)
                    amount_str = format_money(amount) if isinstance(amount, (int, float)) else str(amount)
                    
                    # Развернутая запись с дополнительными полями при наличии
                    extras = []
                    for k in ["Стадия", "Результат", "Категория", "Судья"]:
                        if case.get(k):
                            extras.append(f"{k}: {case.get(k)}")
                    extras_str = f" | {' | '.join(extras)}" if extras else ""
                    case_line = f"{i}. {case.get('Номер', 'N/A')} | {case.get('Дата', 'N/A')} | {case.get('Суд', 'N/A')} | {amount_str} | {role} | {case.get('СтрКАД', 'N/A')}{extras_str}"
                    lines.append(case_line)
            else:
                lines.append(SECTION_HEADERS.get('legal-cases', 'АРБИТРАЖНЫЕ ДЕЛА'))
                lines.append(SECTION_SEPARATOR)
                lines.append(ERROR_MESSAGES.get('data_unavailable', 'Данные недоступны'))
        else:
            # Обрабатываем остальные поля обычно
            alias = aliases.get(key, key)
            
            if isinstance(value, dict):
                if not value:
                    lines.append(f"{alias}: отсутствуют")
                else:
                    lines.append(f"{alias}:")
                    for sub_key, sub_value in value.items():
                        sub_alias = aliases.get(f"{key}.{sub_key}", aliases.get(sub_key, sub_key))
                        formatted_value = format_value(sub_value)
                        lines.append(f"  {sub_alias}: {formatted_value}")
            
            elif isinstance(value, list):
                if not value:
                    lines.append(f"{alias}: отсутствуют")
                else:
                    lines.append(f"{alias}:")
                    for i, item in enumerate(value, 1):
                        if isinstance(item, dict):
                            formatted_item = format_dict_item(item, aliases)
                            lines.append(f"  {i}. {formatted_item}")
                        else:
                            formatted_value = format_value(item)
                            lines.append(f"  {i}. {formatted_value}")
            
            else:
                formatted_value = format_value(value)
                lines.append(f"{alias}: {formatted_value}")
    
    return "\n".join(lines)


def load_legal_aliases() -> Dict[str, str]:
    """Алиасы для арбитражных дел"""
    return {
        'company': 'Компания',
        'data': 'Данные арбитражных дел',
        'meta': 'Метаданные',
        # Добавить остальные поля по мере необходимости
    }