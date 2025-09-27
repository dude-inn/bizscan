# services/aggregator.py
"""
Адаптер для совместимости с bot/
Использует новый простой конвейер формирования отчёта
"""
from __future__ import annotations
import asyncio
import functools
from typing import Dict, Any, Tuple
from services.report import ReportBuilder
from core.logger import get_logger
log = get_logger(__name__)

def _normalize_digits(value: str) -> str:
    return ''.join(ch for ch in (value or '') if ch.isdigit())

def _detect_id_kind(raw: str) -> Tuple[str, str]:
    cleaned = _normalize_digits(raw)
    if not cleaned:
        return '', ''
    if len(cleaned) in (10, 12):
        return 'inn', cleaned
    if len(cleaned) in (13, 15):
        return 'ogrn', cleaned
    return '', ''


try:
    from asyncio import to_thread as asyncio_to_thread  # type: ignore
except Exception:
    async def asyncio_to_thread(func, /, *args, **kwargs):  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

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
    log.info("fetch_company_profile", input=input_str)
    global _builder
    if _builder is None:
        log.debug("initializing ReportBuilder")
        _builder = ReportBuilder()
    log.debug("calling build_company_profile", input=input_str)
    result = await asyncio_to_thread(_builder.build_company_profile, input_str)
    log.debug("profile built", keys=list(result.keys()) if result else None)
    return result
async def fetch_company_report_markdown(query: str) -> str:
    """
    Адаптер для bot/ - генерирует TXT отчёт
    
    Args:
        query: ИНН, ОГРН или название компании
        
    Returns:
        Готовый отчёт в виде строки
    """
    log.info("fetch_company_report_markdown", query=query)
    
    global _builder
    if _builder is None:
        log.debug("initializing ReportBuilder")
        _builder = ReportBuilder()
    
    kind, normalized = _detect_id_kind(query)
    if kind == "inn":
        ident = {"inn": normalized}
        log.debug("identifier: INN", inn=normalized)
    elif kind == "ogrn":
        ident = {"ogrn": normalized}
        log.debug("identifier: OGRN", ogrn=normalized)
    else:
        ident = {"name": query.strip()}
        log.debug("identifier: NAME", name=query.strip())
    
    log.debug("calling build_simple_report", ident=ident)
    result = await asyncio_to_thread(
        _builder.build_simple_report,
        ident=ident,
        include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
        max_rows=500
    )
    log.debug("report built", has_result=bool(result))
    return result
async def build_markdown_report(profile: Dict[str, Any]) -> str:
    """
    Адаптер для bot/ - строит TXT отчёт из профиля
    
    Args:
        profile: Профиль компании
        
    Returns:
        Готовый отчёт в виде строки
    """
    log.info("build_markdown_report")
    
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
    )
