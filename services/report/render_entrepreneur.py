# -*- coding: utf-8 -*-
"""
Рендер секции с информацией об ИП
"""
from typing import Dict, Any, List
from .formatters import format_money, format_date, format_list, clean_text
from .flattener import flatten, apply_aliases, extract_nested_value
from .aliases_ru import COMMON_ALIASES, ENTREPRENEUR_ALIASES


def render_entrepreneur(data: Dict[str, Any]) -> str:
    """
    Рендерит информацию об ИП
    
    Args:
        data: Данные ИП
        
    Returns:
        Информация об ИП
    """
    lines = []
    
    if not data:
        return "—"
    
    # Разворачиваем данные
    flat_data = flatten(data)
    aliases = {**COMMON_ALIASES, **ENTREPRENEUR_ALIASES}
    aliased_data = apply_aliases(flat_data, aliases)
    
    # Основные реквизиты
    main_fields = [
        'Полное наименование',
        'Краткое наименование',
        'ИНН',
        'ОГРН',
        'Дата регистрации',
        'Дата ликвидации',
        'Юридический адрес',
        'Населённый пункт',
        'Регион',
        'ОКВЭД (основной) — код',
        'ОКВЭД (основной) — описание',
        'Среднесписочная численность'
    ]
    
    for field in main_fields:
        if field in aliased_data and aliased_data[field]:
            value = aliased_data[field]
            if 'Дата' in field:
                value = format_date(value)
            lines.append(f"{field}: {value}")
    
    # Особые налоговые режимы (ИП)
    taxes = data.get('Налоги', {})
    if taxes:
        regimes = taxes.get('ОсобРежим', [])
        if regimes:
            lines.append(f"Особые налоговые режимы (ИП): {format_list(regimes)}")
    
    return "\n".join(lines) if lines else "—"