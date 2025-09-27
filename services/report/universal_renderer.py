# -*- coding: utf-8 -*-
"""
Универсальный рендерер для отображения всех полей API в человекочитаемом виде
"""
from typing import Any, Dict, List, Union
from .formatters import format_money, format_date, format_list, format_percent
from .aliases_ru import COMMON_ALIASES, COMPANY_ALIASES, ENTREPRENEUR_ALIASES
import re


def clean_text(text: str) -> str:
    """Очищает текст от лишних символов"""
    if not text:
        return "^н/д^"
    return str(text).strip()


def format_value(value: Any, field_type: str = "text") -> str:
    """Форматирует значение в зависимости от типа поля"""
    if value is None or value == "":
        return "^н/д^"
    
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    
    if isinstance(value, (int, float)):
        if field_type == "money":
            return format_money(value)
        elif field_type == "percent":
            return format_percent(value)
        else:
            return str(value)
    
    if isinstance(value, str):
        if field_type == "date" and re.match(r'\d{4}-\d{2}-\d{2}', value):
            return format_date(value)
        return clean_text(value)
    
    if isinstance(value, list):
        if not value:
            return "^н/д^"
        if field_type == "list":
            return format_list(value)
        else:
            return f"[{len(value)} элементов]"
    
    if isinstance(value, dict):
        if not value:
            return "^н/д^"
        return f"[{len(value)} полей]"
    
    return str(value)


def render_field(key: str, value: Any, aliases: Dict[str, str]) -> str:
    """Рендерит одно поле с алиасом"""
    # Получаем русское название поля
    display_name = aliases.get(key, key)
    
    # Определяем тип поля по ключу
    field_type = "text"
    if any(x in key.lower() for x in ['сумма', 'цена', 'долг', 'капитал', 'прибыль']):
        field_type = "money"
    elif any(x in key.lower() for x in ['дата', 'год']):
        field_type = "date"
    elif any(x in key.lower() for x in ['процент', 'доля']):
        field_type = "percent"
    elif '[]' in key or key.endswith('ы') or key.endswith('и'):
        field_type = "list"
    
    formatted_value = format_value(value, field_type)
    return f"{display_name}: {formatted_value}"


def render_section(title: str, data: Dict[str, Any], aliases: Dict[str, str], 
                  max_items: int = None) -> List[str]:
    """Рендерит секцию с заголовком"""
    lines = [f"\n{title}", "=" * 50]
    
    if not data:
        lines.append("^н/д^")
        return lines
    
    # Сортируем ключи для предсказуемого порядка
    sorted_keys = sorted(data.keys())
    
    for key in sorted_keys:
        value = data[key]
        
        # Обрабатываем вложенные структуры
        if isinstance(value, dict):
            if not value:
                lines.append(f"{aliases.get(key, key)}: ^н/д^")
            else:
                lines.append(f"\n{aliases.get(key, key)}:")
                for sub_key, sub_value in value.items():
                    sub_alias = aliases.get(f"{key}.{sub_key}", sub_key)
                    formatted_value = format_value(sub_value)
                    lines.append(f"  {sub_alias}: {formatted_value}")
        
        # Обрабатываем списки
        elif isinstance(value, list):
            if not value:
                lines.append(f"{aliases.get(key, key)}: ^н/д^")
            else:
                lines.append(f"\n{aliases.get(key, key)}:")
                items_to_show = value[:max_items] if max_items else value
                for i, item in enumerate(items_to_show, 1):
                    if isinstance(item, dict):
                        lines.append(f"  {i}. {format_dict_item(item, aliases)}")
                    else:
                        lines.append(f"  {i}. {format_value(item)}")
                
                if max_items and len(value) > max_items:
                    lines.append(f"  ... и еще {len(value) - max_items} элементов")
        
        # Обрабатываем простые значения
        else:
            formatted_value = format_value(value)
            lines.append(f"{aliases.get(key, key)}: {formatted_value}")
    
    return lines


def format_dict_item(item: Dict[str, Any], aliases: Dict[str, str]) -> str:
    """Форматирует элемент словаря в одну строку"""
    parts = []
    for key, value in item.items():
        if value and value != "":
            formatted_value = format_value(value)
            if formatted_value != "^н/д^":
                parts.append(f"{aliases.get(key, key)}: {formatted_value}")
    
    return " | ".join(parts) if parts else "^н/д^"


def render_all_company_data(data: Dict[str, Any]) -> str:
    """Рендерит ВСЕ данные компании в человекочитаемом виде"""
    lines = []
    
    # Заголовок
    name = data.get('НаимЮЛПолн', data.get('НаимЮЛСокр', '^н/д^'))
    inn = data.get('ИНН', '^н/д^')
    ogrn = data.get('ОГРН', '^н/д^')
    reg_date = data.get('ДатаРег', '^н/д^')
    
    if reg_date and reg_date != '^н/д^':
        from .formatters import format_date
        reg_date = format_date(reg_date)
    
    lines.append(f"{clean_text(name)}")
    lines.append(f"ИНН {inn} • ОГРН {ogrn} • Дата регистрации {reg_date}")
    
    # Объединяем все алиасы
    all_aliases = {**COMMON_ALIASES, **COMPANY_ALIASES, **ENTREPRENEUR_ALIASES}
    
    # Основные секции с ограничением количества элементов
    sections = [
        ("ОСНОВНЫЕ РЕКВИЗИТЫ", ["ОГРН", "ИНН", "КПП", "ОКПО", "НаимЮЛПолн", "НаимЮЛСокр", 
                              "НаимАнгл", "ДатаРег", "ДатаЛикв", "Статус"]),
        ("АДРЕС И РЕГИОН", ["ЮрАдрес", "Регион"]),
        ("ОКВЭД", ["ОКВЭД", "ОКВЭДДоп"]),
        ("КЛАССИФИКАЦИОННЫЕ КОДЫ", ["ОКОПФ", "ОКФС", "ОКОГУ", "ОКАТО", "ОКТМО"]),
        ("НАЛОГОВЫЕ ОРГАНЫ", ["РегФНС", "ТекФНС"]),
        ("ФОНДЫ", ["РегПФР", "РегФСС"]),
        ("УСТАВНЫЙ КАПИТАЛ", ["УстКап"]),
        ("УПРАВЛЯЮЩАЯ ОРГАНИЗАЦИЯ", ["УпрОрг"]),
        ("РУКОВОДСТВО", ["Руковод"]),
        ("УЧРЕДИТЕЛИ", ["Учред"]),
        ("СВЯЗАННЫЕ УЧРЕДИТЕЛИ", ["СвязУчред"]),
        ("РЕЕСТР АКЦИОНЕРОВ", ["ДержРеестрАО"]),
        ("ЛИЦЕНЗИИ", ["Лиценз"]),
        ("ТОВАРНЫЕ ЗНАКИ", ["ТоварЗнак"]),
        ("ПОДРАЗДЕЛЕНИЯ", ["Подразд"]),
        ("ПРАВОПРЕДШЕСТВЕННИКИ", ["Правопредш"]),
        ("ПРАВОПРЕЕМНИКИ", ["Правопреем"]),
        ("КОНТАКТЫ", ["Контакты"]),
        ("НАЛОГИ", ["Налоги"]),
        ("РЕЕСТР МСП", ["РМСП"]),
        ("ПОДДЕРЖКА МСП", ["ПоддержМСП"]),
        ("СРЕДНЕСПИСОЧНАЯ ЧИСЛЕННОСТЬ", ["СЧР"]),
        ("ЕФРСБ", ["ЕФРСБ"]),
        ("ФЛАГИ", ["НедобПост", "ДисквЛица", "МассРуковод", "МассУчред", 
                   "НелегалФин", "Санкции", "МассАдрес"])
    ]
    
    for section_title, field_keys in sections:
        section_data = {}
        for key in field_keys:
            if key in data:
                section_data[key] = data[key]
        
        if section_data:
            # Увеличиваем лимиты элементов для развернутого отчёта
            max_items = 50 if "ОКВЭД" in section_title else 50
            section_lines = render_section(section_title, section_data, all_aliases, max_items)
            lines.extend(section_lines)
    
    # Добавляем все остальные поля, которые не попали в основные секции
    used_fields = set()
    for _, field_keys in sections:
        used_fields.update(field_keys)
    
    remaining_fields = {}
    for key, value in data.items():
        if key not in used_fields:
            remaining_fields[key] = value
    
    if remaining_fields:
        remaining_lines = render_section("ПРОЧИЕ ДАННЫЕ", remaining_fields, all_aliases, 20)
        lines.extend(remaining_lines)

    # ЕФРСБ: при отсутствии — показать критерии поиска и 0 найдено
    if 'ЕФРСБ' not in data:
        inn_value = data.get('ИНН', '^н/д^')
        lines.append("\nЕФРСБ")
        lines.append("=" * 50)
        lines.append(f"Критерии поиска: ИНН {inn_value}")
        lines.append("Найдено: 0")
    
    # Специальная обработка флага ОгрДоступ
    if data.get('ОгрДоступ', False):
        lines.append("\nОГРАНИЧЕНИЕ ДОСТУПА")
        lines.append("=" * 50)
        lines.append("Данные скрыты согласно ФЗ №129")
    
    return "\n".join(lines)
