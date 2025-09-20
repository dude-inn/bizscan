# -*- coding: utf-8 -*-
"""
Рендер секции с госзакупками
"""
from typing import Dict, Any, List, Tuple
from .formatters import format_money, format_date, clean_text


def render_contracts(data_by_mode: Dict[Tuple[str, str], Dict[str, Any]]) -> str:
    """
    Рендерит госзакупки
    
    Args:
        data_by_mode: Словарь вида {("44","customer"): dict, ("44","supplier"): dict, ("223","customer"): dict, ...}
        
    Returns:
        Госзакупки
    """
    lines = []
    
    if not data_by_mode:
        return "—"
    
    # Обрабатываем каждую пару (law, role)
    for (law, role), data in data_by_mode.items():
        if not data or 'data' not in data:
            continue
        
        data_section = data['data']
        records = data_section.get('Записи', [])
        
        if not records:
            continue
        
        # Заголовок режима
        law_name = get_law_name(law)
        role_name = get_role_name(role)
        lines.append(f"\n{law_name} — {role_name}")
        lines.append("=" * 50)
        
        lines.append(f"Всего: {len(records)}")
        
        # Топ-10 по цене
        sorted_by_price = sorted(records, key=lambda x: x.get('Цена', 0), reverse=True)
        lines.append(f"\nТоп-10 по цене:")
        
        for i, record in enumerate(sorted_by_price[:10]):
            contract_num = record.get('РегНомер', '—')
            date = record.get('Дата', '—')
            price = record.get('Цена', 0)
            
            # Заказчик/Поставщик
            if role == 'customer':
                counterparty = record.get('Заказ', {}).get('НаимПолн', '—')
            else:
                suppliers = record.get('Постав', [])
                if suppliers:
                    counterparty = suppliers[0].get('НаимПолн', '—')
                else:
                    counterparty = '—'
            
            # Объект
            objects = record.get('Объекты', [])
            if objects:
                object_name = objects[0].get('Наим', '—')
            else:
                object_name = '—'
            
            # Форматируем дату
            formatted_date = format_date(date) if date != '—' else '—'
            
            lines.append(f"• {clean_text(contract_num)}, {formatted_date}, {format_money(price)}, {clean_text(counterparty)}, {clean_text(object_name)}")
        
        # Последние 10 по дате
        sorted_by_date = sorted(records, key=lambda x: x.get('Дата', ''), reverse=True)
        lines.append(f"\nПоследние 10 по дате:")
        
        for i, record in enumerate(sorted_by_date[:10]):
            contract_num = record.get('РегНомер', '—')
            date = record.get('Дата', '—')
            price = record.get('Цена', 0)
            
            # Заказчик/Поставщик
            if role == 'customer':
                counterparty = record.get('Заказ', {}).get('НаимПолн', '—')
            else:
                suppliers = record.get('Постав', [])
                if suppliers:
                    counterparty = suppliers[0].get('НаимПолн', '—')
                else:
                    counterparty = '—'
            
            # Объект
            objects = record.get('Объекты', [])
            if objects:
                object_name = objects[0].get('Наим', '—')
            else:
                object_name = '—'
            
            # Форматируем дату
            formatted_date = format_date(date) if date != '—' else '—'
            
            lines.append(f"• {clean_text(contract_num)}, {formatted_date}, {format_money(price)}, {clean_text(counterparty)}, {clean_text(object_name)}")
    
    return "\n".join(lines) if lines else "—"


def get_law_name(law: str) -> str:
    """
    Возвращает название закона
    
    Args:
        law: Код закона
        
    Returns:
        Название закона
    """
    law_names = {
        '44': '44-ФЗ',
        '94': '94-ФЗ',
        '223': '223-ФЗ'
    }
    return law_names.get(law, law)


def get_role_name(role: str) -> str:
    """
    Возвращает название роли
    
    Args:
        role: Роль
        
    Returns:
        Название роли
    """
    role_names = {
        'customer': 'Заказчик',
        'supplier': 'Поставщик'
    }
    return role_names.get(role, role)