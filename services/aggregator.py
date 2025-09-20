# services/aggregator.py
"""
Адаптер для совместимости с bot/
Использует новый простой конвейер формирования отчёта
"""
from __future__ import annotations

from typing import Dict, Any
from services.report import ReportBuilder
from core.logger import setup_logging

log = setup_logging()

# Создаём экземпляр нового сборщика отчётов (отложенная инициализация)
_builder = None


async def fetch_company_profile(input_str: str) -> Dict[str, Any]:
    """
    Адаптер для bot/ - получает профиль компании
    
    Args:
        input_str: ИНН, ОГРН или название компании
        
    Returns:
        Словарь с данными компании
    """
    log.info("fetch_company_profile: using new report builder", input_str=input_str)
    global _builder
    if _builder is None:
        _builder = ReportBuilder()
    return _builder.build_company_profile(input_str)


async def fetch_company_report_markdown(query: str) -> str:
    """
    Адаптер для bot/ - генерирует TXT отчёт
    
    Args:
        query: ИНН, ОГРН или название компании
        
    Returns:
        Готовый отчёт в виде строки
    """
    log.info("fetch_company_report_markdown: using new simple report builder", query=query)
    
    global _builder
    if _builder is None:
        _builder = ReportBuilder()
    
    # Определяем тип идентификатора
    if query.isdigit() and len(query) in [10, 12]:
        if len(query) == 10:
            ident = {'inn': query}
        else:
            ident = {'ogrn': query}
    else:
        # Поиск по названию
        ident = {'name': query}
    
    # Генерируем отчёт с полным набором секций
    return _builder.build_simple_report(
        ident=ident,
        include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
        max_rows=100
    )


async def build_markdown_report(profile: Dict[str, Any]) -> str:
    """
    Адаптер для bot/ - строит TXT отчёт из профиля
    
    Args:
        profile: Профиль компании
        
    Returns:
        Готовый отчёт в виде строки
    """
    log.info("build_markdown_report: using new simple report builder")
    
    global _builder
    if _builder is None:
        _builder = ReportBuilder()
    
    # Извлекаем ИНН из профиля
    company_data = profile.get('company', {})
    inn = company_data.get('ИНН')
    
    if not inn:
        return "❌ ИНН не найден в данных компании"
    
    # Генерируем полный отчёт
    return _builder.build_simple_report(
        ident={'inn': inn},
        include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
        max_rows=100
    )


# Оставляем старые функции для совместимости, но они теперь используют простой конвейер
def get_provider():
    """Заглушка для совместимости"""
    return None


def _detect_id_kind(s: str):
    """Заглушка для совместимости"""
    return "", ""


def _fmt_company_taxes(tax_data: Dict[str, Any] | None) -> str:
    """Заглушка для совместимости"""
    return "Налоговая информация недоступна"


def _fmt_status(status: str | None) -> str:
    """Заглушка для совместимости"""
    return status or "Неизвестно"


def _fmt_arbitration(arbitration: Dict[str, Any] | None) -> str:
    """Заглушка для совместимости"""
    return "Арбитражная информация недоступна"


def _fmt_contracts(contracts: Dict[str, Any] | None) -> str:
    """Заглушка для совместимости"""
    return "Информация о контрактах недоступна"


def _fmt_enforcements(enforcements: Dict[str, Any] | None) -> str:
    """Заглушка для совместимости"""
    return "Информация об исполнительных производствах недоступна"


def _fmt_inspections(inspections: Dict[str, Any] | None) -> str:
    """Заглушка для совместимости"""
    return "Информация о проверках недоступна"
