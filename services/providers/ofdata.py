# services/providers/ofdata.py
from __future__ import annotations

import os
import time
from collections import deque
from typing import Any, Dict, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import CompanyProvider
import logging

DEFAULT_BASE_URL = os.getenv("OFDATA_API", "https://api.ofdata.ru")
API_KEY = os.getenv("OFDATA_KEY")
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
RATE_QPM = int(os.getenv("OFDATA_RATE_LIMIT_QPM", "70"))

# OFData endpoint paths
SEARCH_PATH = os.getenv("OFDATA_PATH_SEARCH", "/v2/search")
COMPANY_PATH = os.getenv("OFDATA_PATH_COMPANY", "/v2/company")
FINANCES_PATH = os.getenv("OFDATA_PATH_FINANCES", "/v2/finances")
LEGAL_CASES_PATH = os.getenv("OFDATA_PATH_LEGAL_CASES", "/v2/legal-cases")
CONTRACTS_PATH = os.getenv("OFDATA_PATH_CONTRACTS", "/v2/contracts")
ENFORCEMENTS_PATH = os.getenv("OFDATA_PATH_ENFORCEMENTS", "/v2/enforcements")
INSPECTIONS_PATH = os.getenv("OFDATA_PATH_INSPECTIONS", "/v2/inspections")


class OFDataClientError(Exception):
    pass


class OFDataServerTemporaryError(Exception):
    pass


class OFDataClient(CompanyProvider):
    """
    OFData API client for company data:
      - GET /v2/search - search companies by name
      - GET /v2/company - company information
      - GET /v2/finances - financial reports
      - GET /v2/legal-cases - arbitration cases
    Authorization: query param ?key=...
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = TIMEOUT):
        if api_key is None:
            api_key = API_KEY
        if not api_key:
            raise OFDataClientError("OFDATA_KEY is not set")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        self._log = logging.getLogger(__name__)
        # Simple local rate limit: not more than RATE_QPM per minute
        self._ticks = deque(maxlen=RATE_QPM)

    def _throttle(self) -> None:
        if RATE_QPM <= 0:
            return
        now = time.time()
        self._ticks.append(now)
        if len(self._ticks) == self._ticks.maxlen:
            # if 70th request in the last minute — wait until window opens
            oldest = self._ticks[0]
            elapsed = now - oldest
            if elapsed < 60:
                time.sleep(60 - elapsed + 0.01)

    @retry(
        reraise=True,
        stop=stop_after_attempt(MAX_RETRIES + 1),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type(OFDataServerTemporaryError),
    )
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._throttle()
        params = dict(params or {})
        params["key"] = self.api_key  # key ALWAYS added to query
        url = path if path.startswith("/") else f"/{path}"
        try:
            # Log outbound request (redact key)
            log_params = {k: ("***" if k == "key" else v) for k, v in params.items()}
            self._log.info("OFData GET", extra={"url": url, "params": log_params})
            resp = self._client.get(url, params=params)
        except httpx.RequestError as e:
            self._log.error("OFData network error", extra={"url": url, "error": str(e)})
            raise OFDataServerTemporaryError(f"network error: {e}") from e

        status = resp.status_code
        body_preview = resp.text[:500] if resp.content else ""
        self._log.info("OFData RESP", extra={"url": url, "status": status, "bytes": len(resp.content or b'') , "body_preview": body_preview})
        if status == 403:
            raise OFDataClientError("403: access denied for current key/tariff")
        if status in (500, 502, 503, 504):
            raise OFDataServerTemporaryError(f"{status}: temporary server error")
        if status == 409:
            # OFData often returns 409 for wrong input/not found company
            # Pass through as "no data"
            return {"_error": "conflict_or_not_found", "_status": status, **(resp.json() if resp.content else {})}
        if status >= 400:
            # Специальная обработка для ошибки 400
            if status == 400:
                try:
                    error_data = resp.json() if resp.content else {}
                    error_message = error_data.get("meta", {}).get("message", "Неверные параметры запроса")
                    raise OFDataClientError(f"400: {error_message}")
                except (ValueError, KeyError):
                    raise OFDataClientError(f"400: unexpected client error; body={resp.text[:300]}")
            else:
                raise OFDataClientError(f"{status}: unexpected client error; body={resp.text[:300]}")

        result = resp.json() if resp.content else {}
        self._log.info("OFData JSON result", extra={"result_type": type(result).__name__, "result_keys": list(result.keys()) if isinstance(result, dict) else "not dict", "result_length": len(result) if hasattr(result, '__len__') else 'no length'})
        return result

    # === CompanyProvider interface ===
    def resolve_by_query(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve company by name query to INN/OGRN using OFData search
        """
        try:
            params = {"query": query, "limit": 1}  # Get top result only
            response = self._get(SEARCH_PATH, params=params)
            
            # Check for errors
            if "_error" in response:
                return None, None
            
            # Extract companies from response
            companies = response.get("data", []) or response.get("companies", []) or response.get("results", [])
            if not companies:
                return None, None
            
            # Get first company
            company = companies[0]
            inn = company.get("inn") or company.get("tax_number")
            ogrn = company.get("ogrn") or company.get("ogrn_number")
            
            return inn, ogrn
            
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            # Log error but don't raise - return None, None for graceful fallback
            import logging
            logger = logging.getLogger("ofdata")
            logger.warning("OFData search failed: %s", e)
            return None, None

    def search_filtered(
        self,
        *,
        by: str,
        obj: str,
        query: str,
        region: Optional[str] = None,
        okved: Optional[str] = None,
        opf: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 100,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Generic filtered search wrapper for OFData /v2/search.
        by: name | founder-name | leader-name | okved | reg-date | upd-date
        obj: org | ent
        """
        params: Dict[str, Any] = {
            "by": by,
            "obj": obj,
            "query": query,
            "limit": max(1, min(int(limit or 100), 100)),
            "page": max(1, int(page or 1)),
        }
        if region:
            params["region"] = region
        if okved and by != "okved":
            params["okved"] = okved
        if opf and not (by == "name" or obj == "ent"):
            params["opf"] = opf
        if active is not None:
            params["active"] = "true" if bool(active) else "false"
        result = self._get(SEARCH_PATH, params=params)
        self._log.info("search_filtered result", extra={"result_type": type(result).__name__, "result_keys": list(result.keys()) if isinstance(result, dict) else "not dict", "result_length": len(result) if hasattr(result, '__len__') else 'no length'})
        return result

    def get_counterparty(
        self,
        *,
        inn: Optional[str] = None,
        ogrn: Optional[str] = None,
        kpp: Optional[str] = None,
        okpo: Optional[str] = None,
        source: bool = False,
    ) -> Dict[str, Any]:
        if not (inn or ogrn or okpo):
            raise OFDataClientError("counterparty requires inn or ogrn or okpo")
        params: Dict[str, Any] = {}
        if inn:
            params["inn"] = inn
            if kpp:
                params["kpp"] = kpp
        elif ogrn:
            params["ogrn"] = ogrn
        else:
            params["okpo"] = okpo
        if source:
            params["source"] = "true"
        return self._get(COMPANY_PATH, params=params)

    def get_finance(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise OFDataClientError("finance requires inn or ogrn")
        params = {"inn": inn} if inn else {"ogrn": ogrn}
        params["extended"] = True
        return self._get(FINANCES_PATH, params=params)

    def get_paid_taxes(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        # OFData may not expose paid taxes endpoint in all plans
        # Return empty response for now
        return {"data": [], "available_count": 0}

    def get_arbitration_cases(
        self,
        *,
        inn: Optional[str] = None,
        ogrn: Optional[str] = None,
        kpp: Optional[str] = None,
        role: Optional[str] = None,
        actual: Optional[bool] = None,
        active: Optional[bool] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        claim_amount_from: Optional[float] = None,
        claim_amount_to: Optional[float] = None,
        sort: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
    ) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise OFDataClientError("arbitration-cases requires inn or ogrn")
        params: Dict[str, Any] = {
            "limit": max(1, min(int(limit or 100), 100)),
            "page": max(1, int(page or 1)),
        }
        if inn:
            params["inn"] = inn
            if kpp:
                params["kpp"] = kpp
        else:
            params["ogrn"] = ogrn
        if role in ("plaintiff", "defendant"):
            params["role"] = role
        if actual is not None:
            params["actual"] = "true" if actual else "false"
        if active is not None:
            params["active"] = "true" if active else "false"
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if claim_amount_from is not None:
            params["claim_amount_from"] = claim_amount_from
        if claim_amount_to is not None:
            params["claim_amount_to"] = claim_amount_to
        if sort in ("date", "-date"):
            params["sort"] = sort
        return self._get(LEGAL_CASES_PATH, params=params)

    def get_contracts(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None, law: str = "44", page: int = 1, limit: int = 20, sort: Optional[str] = None) -> Dict[str, Any]:
        """Fetch public procurement contracts (44/223-FZ). Returns raw OFData JSON."""
        if not inn and not ogrn:
            raise OFDataClientError("contracts requires inn or ogrn")
        params: Dict[str, Any] = {"law": law, "page": page, "limit": max(1, min(int(limit or 20), 100))}
        if sort in ("date", "-date"):
            params["sort"] = sort
        if inn:
            params["inn"] = inn
        else:
            params["ogrn"] = ogrn
        return self._get(CONTRACTS_PATH, params=params)

    def get_inspections(
        self,
        *,
        inn: Optional[str] = None,
        ogrn: Optional[str] = None,
        kpp: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch inspections (Единый реестр проверок)."""
        if not inn and not ogrn:
            raise OFDataClientError("inspections requires inn or ogrn")
        params: Dict[str, Any] = {"limit": max(1, min(int(limit or 100), 100)), "page": max(1, int(page or 1))}
        if sort in ("date", "-date"):
            params["sort"] = sort
        if inn:
            params["inn"] = inn
            if kpp:
                params["kpp"] = kpp
        else:
            params["ogrn"] = ogrn
        return self._get(INSPECTIONS_PATH, params=params)

    def get_enforcements(
        self,
        *,
        inn: Optional[str] = None,
        ogrn: Optional[str] = None,
        kpp: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch enforcements (исполнительные производства, ФССП)."""
        if not inn and not ogrn:
            raise OFDataClientError("enforcements requires inn or ogrn")
        params: Dict[str, Any] = {"limit": max(1, min(int(limit or 100), 100)), "page": max(1, int(page or 1))}
        if sort in ("date", "-date"):
            params["sort"] = sort
        if inn:
            params["inn"] = inn
            if kpp:
                params["kpp"] = kpp
        else:
            params["ogrn"] = ogrn
        return self._get(ENFORCEMENTS_PATH, params=params)

    def fetch_company_taxes(self, inn: str, kpp: Optional[str] = None) -> Dict[str, Any]:
        """Fetch company tax information from /company endpoint."""
        if not inn:
            raise OFDataClientError("fetch_company_taxes requires inn")
        
        params = {"inn": inn}
        if kpp:
            params["kpp"] = kpp
            
        raw_response = self._get(COMPANY_PATH, params=params)
        
        # Extract tax data from response
        data = raw_response.get("data", {}) or raw_response.get("company", {}) or raw_response
        taxes = data.get("Налоги", {}) or {}
        
        # Parse tax regimes
        regimes = taxes.get("ОсобРежим", []) or []
        if not isinstance(regimes, list):
            regimes = []
        
        # Parse paid items
        paid_items = taxes.get("СведУпл", []) or []
        if not isinstance(paid_items, list):
            paid_items = []
        
        normalized_paid_items = []
        for item in paid_items:
            if isinstance(item, dict):
                name = item.get("Наим", "") or ""
                amount = item.get("Сумма")
                if name and amount is not None:
                    try:
                        normalized_paid_items.append({
                            "name": str(name),
                            "amount": float(amount)
                        })
                    except (ValueError, TypeError):
                        continue
        
        # Parse other fields
        paid_total = taxes.get("СумУпл")
        if paid_total is not None:
            try:
                paid_total = float(paid_total)
            except (ValueError, TypeError):
                paid_total = None
        
        paid_year = taxes.get("СведУплГод")
        if paid_year:
            paid_year = str(paid_year)
        else:
            paid_year = None
            
        arrears_total = taxes.get("СумНедоим")
        if arrears_total is not None:
            try:
                arrears_total = float(arrears_total)
            except (ValueError, TypeError):
                arrears_total = None
        
        arrears_date = taxes.get("НедоимДата")
        if arrears_date:
            arrears_date = str(arrears_date)
        else:
            arrears_date = None
        
        return {
            "regimes": [str(r) for r in regimes if r],
            "paid_items": normalized_paid_items,
            "paid_total": paid_total,
            "paid_year": paid_year,
            "arrears_total": arrears_total,
            "arrears_date": arrears_date
        }

    def fetch_ip_tax_regimes(self, inn_or_ogrnip: str) -> List[str]:
        """Fetch IP tax regimes from /entrepreneur endpoint."""
        if not inn_or_ogrnip:
            raise OFDataClientError("fetch_ip_tax_regimes requires inn_or_ogrnip")
        
        params = {"inn": inn_or_ogrnip}
        raw_response = self._get("/v2/entrepreneur", params=params)
        
        # Extract tax regimes from response
        data = raw_response.get("data", {}) or raw_response.get("entrepreneur", {}) or raw_response
        taxes = data.get("Налоги", {}) or {}
        regimes = taxes.get("ОсобРежим", []) or []
        
        if not isinstance(regimes, list):
            return []
        
        return [str(r) for r in regimes if r]
