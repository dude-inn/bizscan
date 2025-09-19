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

DEFAULT_BASE_URL = os.getenv("OFDATA_API", "https://ofdata.ru/api")
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
            raise OFDataClientError(f"{status}: unexpected client error; body={resp.text[:300]}")

        return resp.json() if resp.content else {}

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

    def get_counterparty(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise OFDataClientError("counterparty requires inn or ogrn")
        params = {"inn": inn} if inn else {"ogrn": ogrn}
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

    def get_arbitration_cases(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None, 
                            limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise OFDataClientError("arbitration-cases requires inn or ogrn")
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if inn:
            params["inn"] = inn
        else:
            params["ogrn"] = ogrn
        return self._get(LEGAL_CASES_PATH, params=params)
