# -*- coding: utf-8 -*-
"""
Рендер секции с исполнительными производствами - максимально простой
"""
from typing import Dict, Any
from .constants import SECTION_HEADERS, SECTION_SEPARATOR, ERROR_MESSAGES
from .simple_company_renderer import format_value, format_dict_item


def render_enforce(data: Dict[str, Any]) -> str:
    """
    Рендерит исполнительные производства максимально просто
    
    Args:
        data: Данные исполнительных производств
        
    Returns:
        Информация об исполнительных производствах
    """
    lines = []
    aliases = load_enforce_aliases()
    
    for key, value in data.items():
        alias = aliases.get(key, key)
        
        if isinstance(value, dict):
            if not value:
                lines.append(f"{alias}: отсутствуют")
            else:
                lines.append(f"{alias}:")
                for sub_key, sub_value in value.items():
                    # Фильтруем записи по дате для исполнительных производств
                    if sub_key == 'Записи' and isinstance(sub_value, list):
                        current_year = 2025
                        min_year = current_year - 5  # 2020
                        filtered_records = []
                        
                        for record in sub_value:
                            record_date = record.get('ИспПрДата', '')
                            if record_date:
                                try:
                                    # Парсим дату (формат: YYYY-MM-DD)
                                    year = int(record_date.split('-')[0])
                                    if year >= min_year:
                                        filtered_records.append(record)
                                except (ValueError, IndexError):
                                    # Если не можем распарсить дату, включаем запись
                                    filtered_records.append(record)
                            else:
                                # Если даты нет, включаем запись
                                filtered_records.append(record)
                        
                        sub_value = filtered_records
                    
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


def load_enforce_aliases() -> Dict[str, str]:
    """Алиасы для исполнительных производств"""
    return {
        'company': 'Компания',
        'data': 'Данные исполнительных производств',
        'meta': 'Метаданные',
        # Добавить остальные поля по мере необходимости
    }