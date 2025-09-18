# -*- coding: utf-8 -*-
"""
Сервис агрегации данных о компаниях из различных источников
"""
import asyncio
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from domain.models import CompanyAggregate, CompanyBase, MsmeInfo, BankruptcyInfo, ArbitrationInfo, FinanceSnapshot, ProcurementStats, License
from services.providers.datanewton import get_dn_client
from services.mappers.datanewton import (
    map_company_core_to_base,
    map_finance_to_snapshots,
    map_counterparty_to_base,
)
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
        # NEW: msme feature flag
        msme_enabled: bool = True,
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
        self.msme_enabled = msme_enabled
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

    async def _get_company_base_via_dn(self, query: str) -> Optional[CompanyBase]:
        """Получает базовую информацию через DataNewton, с учётом тарифа.
        - INN/OGRN: сначала /v1/counterparty, затем фолбек /v1/company/core
        - Name: не поддерживаем на текущем плане — вернём None
        """
        try:
            cache_key = f"dn_core_{query}"
            cached = await get_cached(cache_key)
            if cached:
                return CompanyBase(**cached)

            client = get_dn_client()
            if not client:
                return None

            # Only INN/OGRN supported here
            if self._is_inn(query):
                # Try counterparty first
                cp = client.get_counterparty(inn=query)
                base = map_counterparty_to_base(cp or {})
                if not base:
                    core = client.get_company_core(query)
                    base = map_company_core_to_base(core or {})
            elif self._is_ogrn(query):
                cp = client.get_counterparty(ogrn=query)
                base = map_counterparty_to_base(cp or {})
                if not base:
                    core = client.get_company_core(query)
                    base = map_company_core_to_base(core or {})
            else:
                log.info("DN: Name search disabled for current plan; request INN/OGRN", query=query)
                base = None
            if base:
                # counterparty/base TTL: 72h
                await set_cached(cache_key, base.dict(), ttl_hours=72)
            return base
        except Exception as e:
            log.warning("DN core fetch failed", query=query, error=str(e))
            return None
    
    # DaData fallback removed; all resolution via DataNewton
    
    async def _get_msme_info(self, inn: str) -> Optional[MsmeInfo]:
        """Получает информацию о МСП"""
        if not getattr(self.config, "msme_enabled", True):
            log.debug("Skipping MSME: feature disabled")
            return None
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
            log.debug("Skipping EFRSB: feature disabled")
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
        """Получает информацию об арбитраже через DataNewton"""
        try:
            cache_key = f"dn_arbitration_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return ArbitrationInfo(**cached)

            client = get_dn_client()
            if not client:
                return None
            data = client.get_arbitration_cases(inn=inn)
            # DataNewton may return {total_cases, data: [...]} or {count, cases: [...]}
            items = (data or {}).get("data") or (data or {}).get("cases") or []
            total = (
                (data or {}).get("total_cases")
                or (data or {}).get("count")
                or len(items)
            )
            info = ArbitrationInfo(total=total, cases=items[: self.config.kad_max_cases])
            # arbitration TTL: 12h
            await set_cached(cache_key, info.dict(), ttl_hours=12)
            return info
        except Exception as e:
            log.error("DN arbitration fetch failed", inn=inn, error=str(e))
            return None
    
    async def _get_finances_info(self, inn: str) -> List[FinanceSnapshot]:
        """Получает финансовые показатели из DataNewton (замена GIR BO)."""
        try:
            cache_key = f"dn_finance_{inn}"
            cached = await get_cached(cache_key)
            if cached:
                return [FinanceSnapshot(**item) for item in cached]

            client = get_dn_client()
            if not client:
                log.debug("DataNewton client not configured")
                return []

            data = client.get_finance(inn=inn)
            snapshots = map_finance_to_snapshots(data)
            # finance TTL: 168h (7 days)
            await set_cached(cache_key, [f.dict() for f in snapshots], ttl_hours=168)
            return snapshots

        except Exception as e:
            log.error("DataNewton finance fetch failed", inn=inn, error=str(e))
            return []
    
    async def _get_procurement_info(self, inn: str) -> Optional[ProcurementStats]:
        """Получает статистику по госзакупкам"""
        if not self.config.zakupki_enabled:
            log.debug("Skipping ZAKUPKI: feature disabled")
            return None
        if self.config.zakupki_mode == "soap" and not self.config.zakupki_wsdl_url:
            log.warning("Skipping ZAKUPKI SOAP: WSDL URL not configured")
            return None
        if self.config.zakupki_mode == "dataset" and not self.config.zakupki_dataset_url:
            log.warning("Skipping ZAKUPKI DATASET: dataset URL not configured")
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
            log.debug("Skipping FSRAR: feature disabled")
            return []
        if not (self.config.fsrar_api_url or self.config.fsrar_dataset_url):
            log.warning("Skipping FSRAR: neither API nor dataset URL configured")
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
        if not self.config.pb_enabled:
            log.debug("Skipping PB OpenData: feature disabled")
            return {}
        if not self.config.pb_datasets:
            log.warning("Skipping PB OpenData: datasets mapping is empty")
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
            company_base = await self._get_company_base_via_dn(query)
        except Exception as e:
            log.error("Failed to get company base info", query=query, error=str(e))
            return None
        
        if not company_base:
            log.warning("Company not found", query=query)
            return None
        
        # Снимок конфигурации провайдеров
        log.info(
            "Providers configuration snapshot",
            msme_enabled=getattr(self.config, "msme_enabled", True),
            msme_url=bool(self.config.msme_data_url),
            girbo_enabled=self.config.girbo_enabled,
            girbo_base_url=bool(self.config.girbo_base_url),
            zakupki_enabled=self.config.zakupki_enabled,
            zakupki_mode=self.config.zakupki_mode,
            zakupki_wsdl_url=bool(self.config.zakupki_wsdl_url),
            zakupki_dataset_url=bool(self.config.zakupki_dataset_url),
            fsrar_enabled=self.config.fsrar_enabled,
            fsrar_api_url=bool(self.config.fsrar_api_url),
            fsrar_dataset_url=bool(self.config.fsrar_dataset_url),
            pb_enabled=self.config.pb_enabled,
            pb_datasets_count=len(self.config.pb_datasets or {}),
            efrsb_enabled=self.config.efrsb_enabled,
            kad_enabled=self.config.kad_enabled,
        )
        
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
        
        # DataNewton-specific extras (risks, taxation, certificates/procure summary)
        dn_extras: Dict[str, Any] = {}
        try:
            client = get_dn_client()
            if client:
                # Fetch in sequence to respect rate limit; cache each
                key_r = f"dn_risks_{company_base.inn}"
                cached_r = await get_cached(key_r)
                if cached_r:
                    dn_extras["risks"] = cached_r
                else:
                    dn_extras["risks"] = client.get_risks(inn=company_base.inn)
                    await set_cached(key_r, dn_extras["risks"], ttl_hours=24 * 7)

                key_tax = f"dn_taxinfo_{company_base.inn}"
                cached_tax = await get_cached(key_tax)
                if cached_tax:
                    dn_extras["tax_info"] = cached_tax
                else:
                    dn_extras["tax_info"] = client.get_tax_info(inn=company_base.inn)
                    await set_cached(key_tax, dn_extras["tax_info"], ttl_hours=24 * 30)

                key_pt = f"dn_paidtaxes_{company_base.inn}"
                cached_pt = await get_cached(key_pt)
                if cached_pt:
                    dn_extras["paid_taxes"] = cached_pt
                else:
                    dn_extras["paid_taxes"] = client.get_paid_taxes(inn=company_base.inn)
                    # paidTaxes TTL: 168h (7 days)
                    await set_cached(key_pt, dn_extras["paid_taxes"], ttl_hours=168)

                key_ps = f"dn_procure_{company_base.inn}"
                cached_ps = await get_cached(key_ps)
                if cached_ps:
                    dn_extras["procure_summary"] = cached_ps
                else:
                    dn_extras["procure_summary"] = client.get_procure_summary(company_base.inn)
                    await set_cached(key_ps, dn_extras["procure_summary"], ttl_hours=24 * 7)

                key_cert = f"dn_cert_{company_base.inn}"
                cached_cert = await get_cached(key_cert)
                if cached_cert:
                    dn_extras["certificates"] = cached_cert
                else:
                    dn_extras["certificates"] = client.get_certificates(company_base.inn)
                    await set_cached(key_cert, dn_extras["certificates"], ttl_hours=24 * 30)
        except Exception as e:
            log.warning("DN extras fetch failed", inn=company_base.inn, error=str(e))

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
            "DataNewton": "API v1",
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
                sources=sources,
                extra=dn_extras
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
        msme_enabled=True if msme_data_url else False,
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
