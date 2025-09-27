# -*- coding: utf-8 -*-
"""
Максимально простой рендерер для финансов
"""
import json
import os
from typing import Dict, Any
from .simple_company_renderer import format_value, format_dict_item
from loguru import logger


def render_finances_simple(data: Dict[str, Any]) -> str:
    """Простой рендерер финансов с развернутыми данными"""
    logger.info("render_finances_simple: starting", data_keys=list(data.keys()) if isinstance(data, dict) else "not_dict")
    lines = []
    aliases = load_finances_aliases()
    logger.info("render_finances_simple: loaded aliases", aliases_count=len(aliases))
    
    # Обрабатываем финансовые данные по годам
    current_year = 2025  # Текущий год
    min_year = current_year - 7  # Минимальный год (расширяем горизонт до 7 лет)
    
    for key, value in data.items():
        # Пропускаем явные нефинансовые блоки, если они затесались в структуру
        if key in {"company", "Компания", "meta", "Метаданные", "bo.nalog.ru", "Налоги", "Компания:"}:
            continue
        logger.debug(f"render_finances_simple: processing key {key}", 
                    value_type=type(value).__name__,
                    value_length=len(value) if isinstance(value, (list, dict)) else "not_collection")
        
        if key.isdigit() and len(key) == 4:  # Год (например, 2012, 2013)
            year = int(key)
            if year < min_year:
                logger.info(f"render_finances_simple: skipping year {year} (older than {min_year})")
                continue
            logger.info(f"render_finances_simple: processing year {key}")
            lines.append(f"ФИНАНСОВЫЕ ДАННЫЕ - {key} ГОД")
            lines.append("=" * 50)
            
            if isinstance(value, dict):
                logger.debug(f"render_finances_simple: year {key} is dict", 
                           year_keys=list(value.keys()),
                           year_keys_count=len(value.keys()))
                # Разворачиваем все поля финансового года
                for field_key, field_value in value.items():
                    field_alias = aliases.get(field_key, field_key)
                    logger.debug(f"render_finances_simple: processing field {field_key} -> {field_alias}", 
                               field_value_type=type(field_value).__name__,
                               field_value_length=len(field_value) if isinstance(field_value, (list, dict)) else "not_collection")
                    formatted_value = format_value(field_value)
                    logger.debug(f"render_finances_simple: formatted field {field_key}", 
                               formatted_value=formatted_value[:100] if len(str(formatted_value)) > 100 else formatted_value)
                    lines.append(f"{field_alias}: {formatted_value}")
            else:
                logger.warning(f"render_finances_simple: year {key} is not dict", 
                             year_type=type(value).__name__)
                lines.append("Данные недоступны")
            lines.append("")
        
        elif key == 'meta':
            logger.info("render_finances_simple: skipping meta field")
            # Пропускаем метаданные - они не нужны пользователю
            continue
        
        elif key == 'data' and isinstance(value, dict):
            logger.info("render_finances_simple: processing data field", 
                       data_keys=list(value.keys()),
                       data_keys_count=len(value.keys()))
            # Обрабатываем данные из поля data
            for year_key, year_data in value.items():
                logger.debug(f"render_finances_simple: processing data year {year_key}", 
                            year_data_type=type(year_data).__name__,
                            year_data_length=len(year_data) if isinstance(year_data, (list, dict)) else "not_collection")
                
                if year_key.isdigit() and len(year_key) == 4:
                    year = int(year_key)
                    if year < min_year:
                        logger.info(f"render_finances_simple: skipping data year {year} (older than {min_year})")
                        continue
                logger.info(f"render_finances_simple: processing data year {year_key}")
                lines.append(f"ФИНАНСОВЫЕ ДАННЫЕ - {year_key} ГОД")
                lines.append("=" * 50)
                
                if isinstance(year_data, dict):
                    logger.debug(f"render_finances_simple: year {year_key} data is dict", 
                               year_data_keys=list(year_data.keys()),
                               year_data_keys_count=len(year_data.keys()))
                    # Проверяем есть ли данные в году
                    has_data = False
                    year_lines = []
                    
                    for field_key, field_value in year_data.items():
                        field_alias = aliases.get(field_key, field_key)
                        logger.debug(f"render_finances_simple: processing data field {field_key} -> {field_alias}", 
                                   field_value_type=type(field_value).__name__,
                                   field_value_length=len(field_value) if isinstance(field_value, (list, dict)) else "not_collection")
                        
                        # Если поле содержит список, разворачиваем его полностью
                        if isinstance(field_value, list):
                            if not field_value:
                                logger.debug(f"render_finances_simple: skipping empty list for field {field_key}")
                                # Не добавляем пустые поля в отчет
                                continue
                            else:
                                has_data = True
                                year_lines.append(f"{field_alias}:")
                                logger.debug(f"render_finances_simple: expanding list for field {field_key}", 
                                           list_length=len(field_value))
                                for i, item in enumerate(field_value, 1):
                                    if isinstance(item, dict):
                                        # Разворачиваем словарь полностью
                                        item_parts = []
                                        logger.debug(f"render_finances_simple: expanding dict item {i} for field {field_key}", 
                                                   item_keys=list(item.keys()))
                                        for sub_key, sub_value in item.items():
                                            sub_alias = aliases.get(f"{field_key}.{sub_key}", aliases.get(sub_key, sub_key))
                                            sub_formatted = format_value(sub_value)
                                            item_parts.append(f"{sub_alias}: {sub_formatted}")
                                        year_lines.append(f"  {i}. {' | '.join(item_parts)}")
                                    else:
                                        formatted_value = format_value(item)
                                        year_lines.append(f"  {i}. {formatted_value}")
                        elif isinstance(field_value, dict):
                            if not field_value:
                                continue
                            has_data = True
                            # Печатаем заголовок показателя, затем его состав
                            year_lines.append(f"{field_alias}:")
                            for sub_key, sub_value in field_value.items():
                                sub_alias = aliases.get(f"{field_key}.{sub_key}", aliases.get(sub_key, sub_key))
                                if isinstance(sub_value, list):
                                    if not sub_value:
                                        continue
                                    year_lines.append(f"  {sub_alias}:")
                                    for j, sub_item in enumerate(sub_value, 1):
                                        if isinstance(sub_item, dict):
                                            sub_item_parts = []
                                            for deep_key, deep_val in sub_item.items():
                                                deep_alias = aliases.get(f"{field_key}.{sub_key}.{deep_key}", aliases.get(deep_key, deep_key))
                                                sub_item_parts.append(f"{deep_alias}: {format_value(deep_val)}")
                                            year_lines.append(f"    {j}. {' | '.join(sub_item_parts)}")
                                        else:
                                            year_lines.append(f"    {j}. {format_value(sub_item)}")
                                else:
                                    year_lines.append(f"  {sub_alias}: {format_value(sub_value)}")
                        else:
                            formatted_value = format_value(field_value)
                            if formatted_value and formatted_value != "отсутствуют":
                                has_data = True
                                year_lines.append(f"{field_alias}: {formatted_value}")
                                logger.debug(f"render_finances_simple: added field {field_key} with value {formatted_value[:50]}...")
                    
                    # Добавляем данные года только если есть данные
                    if has_data:
                        logger.info(f"render_finances_simple: year {year_key} has data, adding to report", 
                                   lines_count=len(year_lines))
                        lines.extend(year_lines)
                        lines.append("")
                    else:
                        logger.info(f"render_finances_simple: year {year_key} has no data, skipping")
                else:
                    logger.warning(f"render_finances_simple: year {year_key} data is not dict", 
                                 year_data_type=type(year_data).__name__)
                    # Не добавляем пустые годы в отчет
                    continue
        
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
    
    result = "\n".join(lines)
    logger.info("render_finances_simple: completed", result_length=len(result))
    return result


def load_account_codes() -> Dict[str, str]:
    """Загружает коды счетов из JSON файла"""
    try:
        # Путь к файлу с кодами счетов
        current_dir = os.path.dirname(os.path.abspath(__file__))
        codes_file = os.path.join(current_dir, '..', 'data', 'account_codes.json')
        
        if not os.path.exists(codes_file):
            logger.warning("Account codes file not found", file_path=codes_file)
            return {}
        
        with open(codes_file, 'r', encoding='utf-8') as f:
            codes_data = json.load(f)
        
        # Преобразуем список в словарь {код: название}
        codes_dict = {}
        for item in codes_data:
            if isinstance(item, dict) and 'code' in item and 'name' in item:
                codes_dict[item['code']] = item['name']
        
        logger.info("Account codes loaded", codes_count=len(codes_dict))
        return codes_dict
        
    except Exception as e:
        logger.error("Failed to load account codes", error=str(e))
        return {}


def load_finances_aliases() -> Dict[str, str]:
    """Алиасы для финансов с расшифровкой кодов счетов"""
    # Загружаем коды счетов
    account_codes = load_account_codes()
    
    # Базовые алиасы
    aliases = {
        'company': 'Компания',
        'data': 'Финансовые данные',
        'meta': 'Метаданные',
        # Часто встречающиеся поля финансовых показателей
        'СумОтч': 'Сумма за отчётный период',
        'СумПред': 'Сумма за предыдущий период',
        'СумПрдщ': 'Сумма за предыдущий период',
        'СумПрдшв': 'Сумма за предшествующие периоды',
        'НаимПок': 'Наименование показателя',
        'ВПокОПП': 'Пояснение к показателю',
        'ДопПокОП': 'Доп. пояснение',
        'Итог': 'Итог',
    }
    
    # Добавляем расшифровки кодов счетов
    aliases.update(account_codes)
    
    return aliases
