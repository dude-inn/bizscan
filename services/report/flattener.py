# -*- coding: utf-8 -*-
"""
Разворачивание JSON в плоскую структуру с dot-нотацией
"""
from typing import Dict, Any, List, Union


def flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    """
    Разворачивает вложенный объект в плоскую структуру с dot-нотацией
    
    Args:
        obj: Объект для разворачивания
        prefix: Префикс для ключей
        
    Returns:
        Плоский словарь с ключами в dot-нотации
    """
    result = {}
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                result.update(flatten(value, new_prefix))
            else:
                result[new_prefix] = value
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_prefix = f"{prefix}[{i}]" if prefix else f"[{i}]"
            if isinstance(item, (dict, list)):
                result.update(flatten(item, new_prefix))
            else:
                result[new_prefix] = item
    else:
        # Примитивное значение
        if prefix:
            result[prefix] = obj
    
    return result


def apply_aliases(flat: Dict[str, Any], aliases: Dict[str, str]) -> Dict[str, Any]:
    """
    Применяет алиасы к плоским данным с учётом шаблонов
    
    Args:
        flat: Плоские данные
        aliases: Словарь алиасов
        
    Returns:
        Данные с применёнными алиасами
    """
    result = {}
    
    for key, value in flat.items():
        # Ищем точное совпадение
        if key in aliases:
            result[aliases[key]] = value
        else:
            # Ищем шаблоны для массивов
            found_alias = None
            for alias_key, alias_value in aliases.items():
                if alias_key.endswith("[]") and key.startswith(alias_key[:-2]):
                    found_alias = alias_value
                    break
                # Ищем шаблоны для дат по годам в finances
                elif "<year>" in alias_key:
                    # Заменяем <year> на фактический год из ключа
                    if "data." in key and "." in key:
                        parts = key.split(".")
                        if len(parts) >= 3 and parts[0] == "data" and parts[1].isdigit():
                            year = parts[1]
                            template_key = alias_key.replace("<year>", year)
                            if key.startswith(template_key):
                                found_alias = alias_value
                                break
            
            if found_alias:
                result[found_alias] = value
            else:
                # Оставляем оригинальный ключ
                result[key] = value
    
    return result


def extract_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Извлекает значение по dot-пути из вложенного объекта
    
    Args:
        data: Исходные данные
        path: Путь в dot-нотации
        default: Значение по умолчанию
        
    Returns:
        Найденное значение или default
    """
    try:
        keys = path.split('.')
        current = data
        
        for key in keys:
            if key.startswith('[') and key.endswith(']'):
                # Массив
                index = int(key[1:-1])
                current = current[index]
            else:
                # Обычный ключ
                current = current[key]
        
        return current
    except (KeyError, IndexError, TypeError):
        return default


def get_array_items(data: Dict[str, Any], array_path: str) -> List[Dict[str, Any]]:
    """
    Получает элементы массива по пути
    
    Args:
        data: Исходные данные
        array_path: Путь к массиву
        
    Returns:
        Список элементов массива
    """
    try:
        array_data = extract_nested_value(data, array_path, [])
        if isinstance(array_data, list):
            return array_data
        return []
    except Exception:
        return []


def count_array_items(data: Dict[str, Any], array_path: str) -> int:
    """
    Подсчитывает количество элементов в массиве
    
    Args:
        data: Исходные данные
        array_path: Путь к массиву
        
    Returns:
        Количество элементов
    """
    try:
        array_data = extract_nested_value(data, array_path, [])
        if isinstance(array_data, list):
            return len(array_data)
        return 0
    except Exception:
        return 0


def pick(flat: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    """
    Возвращает поднабор пар, начинающихся с prefix
    
    Args:
        flat: Плоские данные
        prefix: Префикс для фильтрации
        
    Returns:
        Отфильтрованные данные
    """
    result = {}
    
    for key, value in flat.items():
        if key.startswith(prefix):
            # Убираем префикс из ключа
            new_key = key[len(prefix):]
            if new_key.startswith('.'):
                new_key = new_key[1:]
            result[new_key] = value
    
    return result


def sum_array_field(data: Dict[str, Any], array_path: str, field_path: str) -> float:
    """
    Суммирует поле в массиве
    
    Args:
        data: Исходные данные
        array_path: Путь к массиву
        field_path: Путь к полю в элементах массива
        
    Returns:
        Сумма значений поля
    """
    try:
        array_data = extract_nested_value(data, array_path, [])
        if not isinstance(array_data, list):
            return 0.0
        
        total = 0.0
        for item in array_data:
            if isinstance(item, dict):
                value = extract_nested_value(item, field_path, 0)
                if isinstance(value, (int, float)):
                    total += float(value)
        
        return total
    except Exception:
        return 0.0
