# -*- coding: utf-8 -*-
"""
Сервис агрегации данных о компаниях из различных источников
"""
import asyncio
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from domain.models import CompanyAggregate, CompanyBase, MsmeInfo, BankruptcyInfo, ArbitrationInfo, FinanceSnapshot, ProcurementStats, License
from services.providers.dadata import get_company_by_inn, search_company_by_name
from services.providers.msme import check_msme_status
from services.providers.efrsb import check_bankruptcy_status
from services.providers.kad import get_arbitration_cases
from services.providers.girbo import get_company_finances
from services.providers.pb_opendata import get_company_open_data
from services.providers.zakupki import get_procurement_stats
from services.providers.fsrar import get_fsrar_licenses
from services.cache import get_cached, set_cached
from core.logger import setup_logging

log = setup_logging()


class AggregatorConfig:
    """Конфигурация агрегатора"""
    def __init__(
        self,
        dadata_api_key: str,
        dadata_secret_key: Optional[str] = None,
        msme_data_url: Optional[str] = None,
        msme_local_file: Optional[str] = None,
        efrsb_api_url: Optional[str] = None,
        efrsb_api_key: Optional[str] = None,
        efrsb_enabled: bool = False,
        kad_api_url: Optional[str] = None,
        kad_api_key: Optional[str] = None,
        kad_enabled: bool = False,
        kad_max_cases: int = 5,
        # Новые провайдеры
        girbo_base_url: Optional[str] = None,
        girbo_token: Optional[str] = None,
        girbo_enabled: bool = True,
        zakupki_mode: str = "soap",
        zakupki_wsdl_url: Optional[str] = None,
        zakupki_dataset_url: Optional[str] = None,
        zakupki_enabled: bool = False,
        fsrar_api_url: Optional[str] = None,
        fsrar_dataset_url: Optional[str] = None,
        fsrar_enabled: bool = False,
        pb_datasets: Optional[Dict[str, str]] = None,
        pb_enabled: bool = True,
        request_timeout: int = 10,
        max_retries: int = 2
    ):
        self.dadata_api_key = dadata_api_key
        self.dadata_secret_key = dadata_secret_key
        self.msme_data_url = msme_data_url
        self.msme_local_file = msme_local_file
        self.efrsb_api_url = efrsb_api_url
        self.efrsb_api_key = efrsb_api_key
        self.efrsb_enabled = efrsb_enabled
        self.kad_api_url = kad_api_url
        self.kad_api_key = kad_api_key
        self.kad_enabled = kad_enabled
        self.kad_max_cases = kad_max_cases
        # Новые провайдеры
        self.girbo_base_url = girbo_base_url
        self.girbo_token = girbo_token
        self.girbo_enabled = girbo_enabled
        self.zakupki_mode = zakupki_mode
        self.zakupki_wsdl_url = zakupki_wsdl_url
        self.zakupki_dataset_url = zakupki_dataset_url
        self.zakupki_enabled = zakupki_enabled
        self.fsrar_api_url = fsrar_api_url
        self.fsrar_dataset_url = fsrar_dataset_url
        self.fsrar_enabled = fsrar_enabled
        self.pb_datasets = pb_datasets or {}
        self.pb_enabled = pb_enabled
        self.request_timeout = request_timeout
        self.max_retries = max_retries


class CompanyAggregator:
    """Агрегатор данных о компаниях"""
    
    def __init__(self, config: AggregatorConfig):
        self.config = config
    
    def _normalize_query(self, query: str) -> str:
        """Нормализует поисковый запрос"""
        # Убираем лишние пробелы
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Если это ИНН или ОГРН, оставляем только цифры
        if re.match(r'^\d+$', query):
            return query
        
        return query
    
    def _is_inn(self, query: str) -> bool:
        """Проверяет, является ли запрос ИНН"""
        return re.match(r'^\d{10}$|^\d{12}$', query) is not None
    
    def _is_ogrn(self, query: str) -> bool:
        """Проверяет, является ли запрос ОГРН"""
        return re.match(r'^\d{13}$|^\d{15}$', query) is not None
    
    async def _get_company_by_inn_with_retry(self, inn: str) -> Optional[CompanyBase]:
        """Получает данные компании по ИНН с повторными попытками"""
        for attempt in range(self.config.max_retries + 1):
            try:
                # Проверяем кэш
                cache_key = f"company_inn_{inn}"
                cached = await get_cached(cache_key)
                if cached:
                    log.info("Company data found in cache", inn=inn)
                    return CompanyBase(**cached)
                
                # Запрашиваем данные
                company = await get_company_by_inn(
                    inn, 
                    self.config.dadata_api_key, 
                    self.config.dadata_secret_key
                )
                
                if company:
                    # Сохраняем в кэш
                    await set_cached(cache_key, company.dict(), ttl_hours=24)
                    return company
                
                return None
                
            except Exception as e:
                log.warning("Attempt failed", attempt=attempt + 1, inn=inn, error=str(e))
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                else:
                    log.error("All attempts failed", inn=inn, error=str(e))
                    return None
    
    async def _search_company_by_name_with_retry(self, name: str) -> List[CompanyBase]:
        """Поиск компании по названию с повторными попытками"""
        for attempt in range(self.config.max_retries + 1):
            try:
                companies = await search_company_by_name(
                    name,
                    self.config.dadata_api_key,
                    self.config.dadata_secret_key
                )
                return companies
                
            except Exception as e:
                log.warning("Search attempt failed", attempt=attempt + 1, name=name, error=str(e))
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    log.error("All search attempts failed", name=name, error=str(e))
                    return []
    
    async def _get_msme_info(self, inn: str) -> Optional[MsmeInfo]:
        """Получает информацию о МСП"""
        try:
            cache_key = f"msme_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return MsmeInfo(**cached)
            
            msme_info = await check_msme_status(
                inn,
                self.config.msme_data_url,
                self.config.msme_local_file
            )
            
            # Кэшируем на 30 дней
            await set_cached(cache_key, msme_info.dict(), ttl_hours=24 * 30)
            return msme_info
            
        except Exception as e:
            log.error("MSME check failed", inn=inn, error=str(e))
            return None
    
    async def _get_bankruptcy_info(self, inn: str) -> Optional[BankruptcyInfo]:
        """Получает информацию о банкротстве"""
        if not self.config.efrsb_enabled:
            return None
        
        try:
            cache_key = f"bankruptcy_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return BankruptcyInfo(**cached)
            
            bankruptcy_info = await check_bankruptcy_status(
                inn,
                self.config.efrsb_api_url,
                self.config.efrsb_api_key,
                self.config.efrsb_enabled
            )
            
            # Кэшируем на 7 дней
            await set_cached(cache_key, bankruptcy_info.dict(), ttl_hours=24 * 7)
            return bankruptcy_info
            
        except Exception as e:
            log.error("Bankruptcy check failed", inn=inn, error=str(e))
            return None
    
    async def _get_arbitration_info(self, inn: str) -> Optional[ArbitrationInfo]:
        """Получает информацию об арбитраже"""
        if not self.config.kad_enabled:
            return None
        
        try:
            cache_key = f"arbitration_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return ArbitrationInfo(**cached)
            
            arbitration_info = await get_arbitration_cases(
                inn,
                self.config.kad_api_url,
                self.config.kad_api_key,
                self.config.kad_enabled,
                self.config.kad_max_cases
            )
            
            # Кэшируем на 7 дней
            await set_cached(cache_key, arbitration_info.dict(), ttl_hours=24 * 7)
            return arbitration_info
            
        except Exception as e:
            log.error("Arbitration check failed", inn=inn, error=str(e))
            return None
    
    async def _get_finances_info(self, inn: str) -> List[FinanceSnapshot]:
        """Получает финансовые показатели из ГИР БО"""
        if not self.config.girbo_enabled or not self.config.girbo_base_url:
            return []
        
        try:
            cache_key = f"finances_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return [FinanceSnapshot(**item) for item in cached]
            
            finances = await get_company_finances(
                inn,
                self.config.girbo_base_url,
                self.config.girbo_token
            )
            
            # Кэшируем на 30 дней
            await set_cached(cache_key, [f.dict() for f in finances], ttl_hours=24 * 30)
            return finances
            
        except Exception as e:
            log.error("Finances check failed", inn=inn, error=str(e))
            return []
    
    async def _get_procurement_info(self, inn: str) -> Optional[ProcurementStats]:
        """Получает статистику по госзакупкам"""
        if not self.config.zakupki_enabled:
            return None
        
        try:
            cache_key = f"procurement_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return ProcurementStats(**cached)
            
            procurement_stats = await get_procurement_stats(
                inn,
                self.config.zakupki_mode,
                self.config.zakupki_wsdl_url,
                self.config.zakupki_dataset_url
            )
            
            if procurement_stats:
                # Кэшируем на 14 дней
                await set_cached(cache_key, procurement_stats.dict(), ttl_hours=24 * 14)
            
            return procurement_stats
            
        except Exception as e:
            log.error("Procurement check failed", inn=inn, error=str(e))
            return None
    
    async def _get_licenses_info(self, inn: str) -> List[License]:
        """Получает лицензии РАР"""
        if not self.config.fsrar_enabled:
            return []
        
        try:
            cache_key = f"licenses_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return [License(**item) for item in cached]
            
            licenses = await get_fsrar_licenses(
                inn,
                self.config.fsrar_api_url,
                self.config.fsrar_dataset_url
            )
            
            # Кэшируем на 30 дней
            await set_cached(cache_key, [l.dict() for l in licenses], ttl_hours=24 * 30)
            return licenses
            
        except Exception as e:
            log.error("Licenses check failed", inn=inn, error=str(e))
            return []
    
    async def _get_open_data_info(self, inn: str) -> Dict[str, Any]:
        """Получает открытые данные о компании"""
        if not self.config.pb_enabled or not self.config.pb_datasets:
            return {}
        
        try:
            cache_key = f"open_data_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return cached
            
            open_data = await get_company_open_data(inn, self.config.pb_datasets)
            
            # Кэшируем на 7 дней
            await set_cached(cache_key, open_data, ttl_hours=24 * 7)
            return open_data
            
        except Exception as e:
            log.error("Open data check failed", inn=inn, error=str(e))
            return {}
    
    async def fetch_company_profile(self, query: str) -> Optional[CompanyAggregate]:
        """Получает полный профиль компании"""
        query = self._normalize_query(query)
        
        log.info("Fetching company profile", query=query)
        
        # Определяем тип запроса и получаем базовую информацию
        company_base = None
        
        try:
            if self._is_inn(query):
                log.info("Query identified as INN", query=query)
                # Прямой поиск по ИНН
                company_base = await self._get_company_by_inn_with_retry(query)
            elif self._is_ogrn(query):
                log.info("Query identified as OGRN", query=query)
                # Поиск по ОГРН (через DaData suggest)
                companies = await self._search_company_by_name_with_retry(query)
                if companies:
                    company_base = companies[0]  # Берем первое совпадение
                    log.info("Company found via OGRN search", companies_count=len(companies))
            else:
                log.info("Query identified as company name", query=query)
                # Поиск по названию
                companies = await self._search_company_by_name_with_retry(query)
                if companies:
                    company_base = companies[0]  # Берем первое совпадение
                    log.info("Company found via name search", companies_count=len(companies))
        except Exception as e:
            log.error("Failed to get company base info", query=query, error=str(e))
            return None
        
        if not company_base:
            log.warning("Company not found", query=query)
            return None
        
        # Получаем дополнительную информацию параллельно
        log.info("Fetching additional company data", inn=company_base.inn)
        tasks = [
            self._get_msme_info(company_base.inn),
            self._get_bankruptcy_info(company_base.inn),
            self._get_arbitration_info(company_base.inn),
            self._get_finances_info(company_base.inn),
            self._get_procurement_info(company_base.inn),
            self._get_licenses_info(company_base.inn),
            self._get_open_data_info(company_base.inn)
        ]
        
        try:
            log.info("Executing parallel data fetching tasks")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            log.info("Parallel data fetching completed")
        except Exception as e:
            log.error("Failed to fetch additional data", error=str(e))
            results = [None] * 7
        
        msme_info = results[0] if not isinstance(results[0], Exception) else None
        bankruptcy_info = results[1] if not isinstance(results[1], Exception) else None
        arbitration_info = results[2] if not isinstance(results[2], Exception) else None
        finances = results[3] if not isinstance(results[3], Exception) else []
        procurement = results[4] if not isinstance(results[4], Exception) else None
        licenses = results[5] if not isinstance(results[5], Exception) else []
        open_data = results[6] if not isinstance(results[6], Exception) else {}
        
        log.info("Additional data fetched", 
                msme_success=msme_info is not None,
                bankruptcy_success=bankruptcy_info is not None,
                arbitration_success=arbitration_info is not None,
                finances_success=len(finances) > 0,
                procurement_success=procurement is not None,
                licenses_success=len(licenses) > 0,
                open_data_success=bool(open_data))
        
        # Формируем источники данных
        sources = {
            "DaData": "API v4.1",
            "Реестр МСП": "Открытые данные ФНС"
        }
        
        if self.config.girbo_enabled and finances:
            sources["ГИР БО"] = "ФНС"
        
        if self.config.zakupki_enabled and procurement:
            sources["ЕИС"] = "zakupki.gov.ru"
        
        if self.config.fsrar_enabled and licenses:
            sources["РАР"] = "fsrar.gov.ru"
        
        if self.config.pb_enabled and open_data:
            sources["Прозрачный бизнес"] = "pb.nalog.ru"
        
        if self.config.efrsb_enabled:
            sources["ЕФРСБ"] = "API-провайдер"
        
        if self.config.kad_enabled:
            sources["КАД"] = "API-провайдер"
        
        try:
            log.info("Creating company aggregate object")
            aggregate = CompanyAggregate(
                base=company_base,
                msme=msme_info,
                bankruptcy=bankruptcy_info,
                arbitration=arbitration_info,
                finances=finances,
                procurement=procurement,
                licenses=licenses,
                sources=sources
            )
            log.info("Company profile created successfully", 
                    company_name=company_base.name_full,
                    inn=company_base.inn)
            return aggregate
        except Exception as e:
            log.error("Failed to create company aggregate", error=str(e))
            return None


async def fetch_company_profile(
    query: str,
    dadata_api_key: str,
    dadata_secret_key: Optional[str] = None,
    msme_data_url: Optional[str] = None,
    msme_local_file: Optional[str] = None,
    efrsb_api_url: Optional[str] = None,
    efrsb_api_key: Optional[str] = None,
    efrsb_enabled: bool = False,
    kad_api_url: Optional[str] = None,
    kad_api_key: Optional[str] = None,
    kad_enabled: bool = False,
    kad_max_cases: int = 5,
    request_timeout: int = 10,
    max_retries: int = 2
) -> Optional[CompanyAggregate]:
    """Получает профиль компании (удобная функция)"""
    config = AggregatorConfig(
        dadata_api_key=dadata_api_key,
        dadata_secret_key=dadata_secret_key,
        msme_data_url=msme_data_url,
        msme_local_file=msme_local_file,
        efrsb_api_url=efrsb_api_url,
        efrsb_api_key=efrsb_api_key,
        efrsb_enabled=efrsb_enabled,
        kad_api_url=kad_api_url,
        kad_api_key=kad_api_key,
        kad_enabled=kad_enabled,
        kad_max_cases=kad_max_cases,
        request_timeout=request_timeout,
        max_retries=max_retries
    )
    
    aggregator = CompanyAggregator(config)
    return await aggregator.fetch_company_profile(query)
