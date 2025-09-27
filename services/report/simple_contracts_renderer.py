# -*- coding: utf-8 -*-
"""
Максимально простой рендерер для контрактов
Переводит ВСЕ поля API в человекочитаемый вид
"""
from typing import Dict, Any, List
from .simple_company_renderer import format_value, format_dict_item
from .formatters import format_money
from loguru import logger


def render_contracts_simple(data: Dict[str, Any]) -> str:
    """
    Максимально простой рендерер контрактов
    Показывает ВСЕ поля из API в человекочитаемом виде
    """
    logger.info("render_contracts_simple: starting", data_keys=list(data.keys()) if isinstance(data, dict) else "not_dict")
    lines = []
    
    # Загружаем алиасы
    aliases = load_contracts_aliases()
    logger.info("render_contracts_simple: loaded aliases", aliases_count=len(aliases))
    
    # Обрабатываем данные контрактов по типам
    for contract_type, contract_data in data.items():
        logger.debug(f"render_contracts_simple: processing contract type {contract_type}", 
                   contract_data_type=type(contract_data).__name__,
                   contract_data_keys=list(contract_data.keys()) if isinstance(contract_data, dict) else "not_dict")
        
        if contract_type in ['44_customer', '44_supplier', '223_customer', '223_supplier']:
            logger.info(f"render_contracts_simple: processing {contract_type}")
            lines.append(f"ГОСЗАКУПКИ - {contract_type.upper()}")
            lines.append("=" * 50)
            
            if contract_data:
                logger.debug(f"render_contracts_simple: {contract_type} has data", 
                           data_type=type(contract_data).__name__,
                           data_keys=list(contract_data.keys()) if isinstance(contract_data, dict) else "not_dict")
                try:
                    # Проверяем разные форматы данных
                    if isinstance(contract_data, dict) and 'data' in contract_data:
                        logger.debug(f"render_contracts_simple: {contract_type} data is dict with data field")
                        records = contract_data['data'].get('Записи', [])
                    elif isinstance(contract_data, list):
                        logger.debug(f"render_contracts_simple: {contract_type} data is list")
                        records = contract_data
                    else:
                        logger.warning(f"render_contracts_simple: {contract_type} data is not dict or list", 
                                     data_type=type(contract_data).__name__)
                        records = []
                    
                    logger.info(f"render_contracts_simple: {contract_type} records count", records_count=len(records))
                    
                    if records:
                        # Статистика
                        total_contracts = len(records)
                        total_amount = sum(contract.get('Цена', 0) for contract in records if isinstance(contract.get('Цена'), (int, float)))
                        
                        logger.info(f"render_contracts_simple: {contract_type} statistics", 
                                   total_contracts=total_contracts, total_amount=total_amount)
                        
                        lines.append(f"Всего контрактов: {total_contracts}")
                        lines.append(f"Общая сумма: {format_money(total_amount)}")
                        lines.append("")
                        
                        # Список контрактов (сокращенный формат)
                        lines.append("Список контрактов:")
                        for i, contract in enumerate(records, 1):
                            logger.debug(f"render_contracts_simple: processing contract {i}", 
                                       contract_type=type(contract).__name__,
                                       contract_keys=list(contract.keys()) if isinstance(contract, dict) else "not_dict")
                            
                            try:
                                # Проверяем что contract - это словарь
                                if isinstance(contract, dict):
                                    logger.debug(f"render_contracts_simple: contract {i} is dict", 
                                               contract_keys=list(contract.keys()))
                                    
                                    # Логируем содержимое contract для отладки
                                    logger.debug(f"render_contracts_simple: contract {i} content", 
                                               contract_content=str(contract)[:200])
                                    
                                    # Сокращаем название заказчика/поставщика
                                    customer = contract.get('Заказ', {})
                                    supplier = contract.get('Постав', {})
                                    
                                    logger.debug(f"render_contracts_simple: contract {i} customer/supplier", 
                                               customer_type=type(customer).__name__,
                                               supplier_type=type(supplier).__name__)
                                    
                                    # Обрабатываем customer
                                    if isinstance(customer, dict):
                                        customer_name = customer.get('НаимСокр') or customer.get('НаимПолн') or 'N/A'
                                    elif isinstance(customer, list) and customer:
                                        # Если customer - список, берем первый элемент
                                        first_customer = customer[0]
                                        if isinstance(first_customer, dict):
                                            customer_name = first_customer.get('НаимСокр') or first_customer.get('НаимПолн') or 'N/A'
                                        else:
                                            customer_name = str(first_customer) if first_customer else 'N/A'
                                    else:
                                        customer_name = 'N/A'
                                    
                                    # Обрабатываем supplier
                                    if isinstance(supplier, dict):
                                        supplier_name = supplier.get('НаимСокр') or supplier.get('НаимПолн') or 'N/A'
                                    elif isinstance(supplier, list) and supplier:
                                        # Если supplier - список, берем первый элемент
                                        first_supplier = supplier[0]
                                        if isinstance(first_supplier, dict):
                                            supplier_name = first_supplier.get('НаимСокр') or first_supplier.get('НаимПолн') or 'N/A'
                                        else:
                                            supplier_name = str(first_supplier) if first_supplier else 'N/A'
                                    else:
                                        supplier_name = 'N/A'
                                    
                                    # Проверяем и обрезаем названия, если они не None
                                    if customer_name and len(customer_name) > 30:
                                        customer_name = customer_name[:27] + "..."
                                    if supplier_name and len(supplier_name) > 30:
                                        supplier_name = supplier_name[:27] + "..."
                                    
                                    # Форматируем цену
                                    price = contract.get('Цена', 0)
                                    price_str = format_money(price) if isinstance(price, (int, float)) else str(price)
                                    
                                    # Сокращенная запись
                                    contract_line = f"{i}. {contract.get('РегНомер', 'N/A')} | {contract.get('Дата', 'N/A')} | {customer_name} | {supplier_name} | {price_str}"
                                    lines.append(contract_line)
                                    logger.debug(f"render_contracts_simple: added contract {i}", 
                                               contract_line=contract_line[:100] + "..." if len(contract_line) > 100 else contract_line)
                                elif isinstance(contract, list):
                                    logger.debug(f"render_contracts_simple: contract {i} is list", 
                                               list_length=len(contract))
                                    # Если contract - это список, обрабатываем каждый элемент
                                    contract_parts = []
                                    for j, item in enumerate(contract):
                                        if isinstance(item, dict):
                                            item_parts = []
                                            for key, value in item.items():
                                                item_parts.append(f"{key}: {value}")
                                            contract_parts.append(f"  {j+1}. {' | '.join(item_parts)}")
                                        else:
                                            contract_parts.append(f"  {j+1}. {str(item)}")
                                    lines.append(f"{i}. {'; '.join(contract_parts)}")
                                    logger.debug(f"render_contracts_simple: added list contract {i}")
                                else:
                                    logger.warning(f"render_contracts_simple: contract {i} is not dict or list", 
                                                 contract_type=type(contract).__name__)
                                    # Если contract не словарь и не список, показываем как есть
                                    lines.append(f"{i}. {str(contract)[:100]}...")
                            except Exception as e:
                                logger.error(f"render_contracts_simple: error processing contract {i}", 
                                           error=str(e), contract_type=type(contract).__name__)
                                # Показываем что именно в contract
                                logger.error(f"render_contracts_simple: contract {i} content", 
                                           contract_content=str(contract)[:200])
                                # Показываем полную ошибку
                                import traceback
                                logger.error(f"render_contracts_simple: full traceback for contract {i}", 
                                           traceback=traceback.format_exc())
                                lines.append(f"{i}. Ошибка обработки контракта: {str(e)}")
                    else:
                        logger.info(f"render_contracts_simple: {contract_type} has no records")
                        lines.append("Контракты отсутствуют")
                except Exception as e:
                    lines.append(f"Ошибка обработки данных: {str(e)}")
            else:
                lines.append("Данные недоступны")
            
            lines.append("")
    
    result = "\n".join(lines)
    logger.info("render_contracts_simple: completed", result_length=len(result))
    return result


def load_contracts_aliases() -> Dict[str, str]:
    """Загружает словарь алиасов для контрактов"""
    return {
        # Основные поля
        'company': 'Компания',
        'entrepreneur': 'Индивидуальный предприниматель',
        'data': 'Данные контрактов',
        
        # Компания
        'company.ОГРН': 'ОГРН',
        'company.ИНН': 'ИНН',
        'company.КПП': 'КПП',
        'company.НаимСокр': 'Краткое наименование',
        'company.НаимПолн': 'Полное наименование',
        'company.ДатаРег': 'Дата регистрации',
        'company.Статус': 'Статус',
        'company.ДатаЛикв': 'Дата ликвидации',
        'company.РегионКод': 'Код региона',
        'company.ЮрАдрес': 'Юридический адрес',
        'company.ОКВЭД': 'ОКВЭД',
        
        # ИП
        'entrepreneur.ОГРНИП': 'ОГРНИП',
        'entrepreneur.ИНН': 'ИНН',
        'entrepreneur.ФИО': 'ФИО',
        'entrepreneur.Тип': 'Тип ИП',
        'entrepreneur.ДатаРег': 'Дата регистрации',
        'entrepreneur.Статус': 'Статус',
        'entrepreneur.ДатаПрекращ': 'Дата прекращения',
        'entrepreneur.РегионКод': 'Код региона',
        'entrepreneur.ОКВЭД': 'ОКВЭД',
        
        # Данные контрактов
        'data.ЗапВсего': 'Всего записей',
        'data.СтрВсего': 'Всего страниц',
        'data.СтрТекущ': 'Текущая страница',
        'data.Записи': 'Контракты',
        
        # Контракт
        'РегНомер': 'Регистрационный номер',
        'СтрЕИС': 'Ссылка в ЕИС',
        'РегионКод': 'Код региона',
        'Дата': 'Дата подписания',
        'ДатаИсп': 'Дата исполнения',
        'Цена': 'Цена контракта',
        'Заказ': 'Заказчик',
        'Постав': 'Поставщики',
        'Объекты': 'Объекты закупки',
        
        # Заказчик
        'Заказ.ИНН': 'ИНН заказчика',
        'Заказ.КПП': 'КПП заказчика',
        'Заказ.НаимСокр': 'Краткое наименование заказчика',
        'Заказ.НаимПолн': 'Полное наименование заказчика',
        
        # Поставщик
        'Постав.ИНН': 'ИНН поставщика',
        'Постав.КПП': 'КПП поставщика',
        'Постав.НаимСокр': 'Краткое наименование поставщика',
        'Постав.НаимПолн': 'Полное наименование поставщика',
        'Постав.ФИО': 'ФИО ИП',
        
        # Объекты закупки
        'Объекты.Наим': 'Наименование объекта',
        'Объекты.ОКДП': 'Код ОКДП',
        'Объекты.ОКПД': 'Код ОКПД',
        'Объекты.ОКПД2': 'Код ОКПД2',
        
        # Мета
        'meta': 'Метаданные',
        'meta.status': 'Статус',
        'meta.today_request_count': 'Запросов сегодня',
        'meta.balance': 'Баланс',
        'meta.message': 'Сообщение',
    }
