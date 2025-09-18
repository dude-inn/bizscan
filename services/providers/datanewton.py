# -*- coding: utf-8 -*-
"""
DataNewton provider: typed, resilient HTTP client with local rate limiting.
No HTML parsing. Paths are constants to be adjusted per official docs.
"""
from __future__ import annotations

import time
from typing import Optional, Dict, Any, List, Callable

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception,
)

from pydantic import BaseModel
from core.logger import setup_logging
from settings import (
    DATANEWTON_API,
    DATANEWTON_TOKEN,
    DATANEWTON_TIMEOUT,
    DATANEWTON_MAX_RETRIES,
    DATANEWTON_RATE_LIMIT_QPM,
    DATANEWTON_AUTH_SCHEME,
    FEATURE_DATANEWTON,
)

log = setup_logging()

# Endpoint paths (adjust per DataNewton docs)
PATH_RESOLVE = "/v1/party/resolve"
PATH_COMPANY = "/v1/company/core"
PATH_COUNTERPARTY = "/v1/counterparty"
PATH_FINANCE_COMPANY = "/v1/company/finance"
PATH_FINANCE = "/v1/finance"  # finance by inn/ogrn as per public docs
PATH_BATCH_CARDS = "/v1/batchCardsByFilters"
PATH_RISKS = "/v1/risks"
PATH_SUGGESTIONS = "/v1/suggestions"
PATH_DICT_OKVEDS = "/v1/dictionary/okveds"
PATH_DICT_LICENSES = "/v1/dictionary/licenses"
PATH_DICT_LEASE_CLASSIFIER = "/v1/dictionary/lease-classifier"
PATH_TAX_INFO = "/v1/taxInfo"
PATH_PAID_TAXES = "/v1/paidTaxes"
PATH_PROCURE_SUMMARY = "/v1/company/procurement/summary"
PATH_ARBITRATION_CASES = "/v1/arbitration-cases"
PATH_ENFORCEMENT = "/v1/company/enforcement/summary"
PATH_CERTIFICATES = "/v1/company/certificates"
PATH_IP_SUMMARY = "/v1/company/ip/summary"


class DataNewtonConfig(BaseModel):
    base_url: str
    token: Optional[str]
    timeout: int = 10
    max_retries: int = 2
    rate_limit_qpm: int = 70
    auth_scheme: str = "Bearer"  # Bearer | X-API-Key


class _RateLimiter:
    """Very light local rate limiter ~ QPM.
    Uses a sliding window counter with 60s buckets.
    """

    def __init__(self, qpm: int) -> None:
        self.qpm = max(1, qpm)
        self._window_start = time.monotonic()
        self._count = 0

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self._window_start
        if elapsed >= 60.0:
            self._window_start = now
            self._count = 0
        if self._count >= self.qpm:
            # sleep remaining window
            sleep_s = 60.0 - elapsed
            if sleep_s > 0:
                time.sleep(min(sleep_s, 1.0))  # sleep in short bursts
            # re-check recursively
            self.acquire()
            return
        self._count += 1


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in (429, 500, 502, 503, 504)
    if isinstance(exc, httpx.TransportError):
        return True
    return False


class DataNewtonClient:
    def __init__(self, cfg: DataNewtonConfig) -> None:
        self.cfg = cfg
        headers: Dict[str, str] = {
            "User-Agent": "BizScan/1.0 (+https://github.com/dude-inn/bizscan)",
            "Accept": "application/json",
        }
        if self.cfg.token:
            if self.cfg.auth_scheme.lower() == "x-api-key":
                headers["X-API-Key"] = self.cfg.token
            else:
                headers["Authorization"] = f"Bearer {self.cfg.token}"
        self._client = httpx.Client(
            base_url=self.cfg.base_url.rstrip("/"),
            headers=headers,
            timeout=self.cfg.timeout,
        )
        self._limiter = _RateLimiter(self.cfg.rate_limit_qpm)
        log.info(
            "DataNewton client created",
            base_url=self.cfg.base_url,
            auth_scheme=self.cfg.auth_scheme,
            timeout=self.cfg.timeout,
            rate_limit_qpm=self.cfg.rate_limit_qpm,
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def _retry_wrapper(self, fn: Callable[[], httpx.Response]) -> httpx.Response:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.cfg.max_retries),
            wait=wait_exponential_jitter(initial=0.2, max=2.0),
            retry=retry_if_exception(_is_retryable),
        )
        def _wrapped() -> httpx.Response:
            self._limiter.acquire()
            resp = fn()
            # Manual 429 handling: respect Retry-After when present
            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After")
                if ra:
                    try:
                        sleep_s = float(ra)
                        time.sleep(min(max(sleep_s, 0), 5))
                    except Exception:
                        time.sleep(1)
                raise httpx.HTTPStatusError("429 Too Many Requests", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp

        return _wrapped()

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = path
        method_upper = method.upper()
        start = time.monotonic()
        safe_params = dict(params or {})
        # redact potential key
        if "key" in safe_params:
            safe_params["key"] = "***"
        log.info("DN request", method=method_upper, path=path, params=safe_params, has_body=bool(json))
        def do_request() -> httpx.Response:
            if method_upper == "GET":
                return self._client.get(url, params=params)
            elif method_upper == "POST":
                return self._client.post(url, params=params, json=json)
            elif method_upper == "PUT":
                return self._client.put(url, params=params, json=json)
            elif method_upper == "DELETE":
                return self._client.delete(url, params=params)
            else:
                return self._client.request(method_upper, url, params=params, json=json)

        if method_upper == "GET":
            try:
                resp = self._retry_wrapper(do_request)
            finally:
                duration = (time.monotonic() - start) * 1000
                try:
                    sc = locals().get("resp").status_code  # type: ignore
                except Exception:
                    sc = None
                log.info("DN response", method=method_upper, path=path, status_code=sc, duration_ms=int(duration))
        else:
            # non-idempotent — single shot
            self._limiter.acquire()
            resp = do_request()
            if resp.status_code == 429:
                log.warning("DataNewton 429 on non-idempotent", path=path)
                time.sleep(1)
                resp = do_request()
            resp.raise_for_status()
            duration = (time.monotonic() - start) * 1000
            log.info("DN response", method=method_upper, path=path, status_code=resp.status_code, duration_ms=int(duration))
        return resp.json()

    # Public API
    def resolve_party(self, query: str) -> Dict[str, Any]:
        log.info("DN resolve_party", query=query)
        return self._request("GET", PATH_RESOLVE, params={"query": query})

    def get_company_core(self, inn_or_ogrn: str) -> Dict[str, Any]:
        log.info("DN get_company_core", id=inn_or_ogrn)
        return self._request("GET", PATH_COMPANY, params={"id": inn_or_ogrn})

    def get_counterparty(self, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """GET /v1/counterparty with inn or ogrn; supports query-key auth."""
        params: Dict[str, Any] = {}
        if inn:
            params["inn"] = inn
        if ogrn:
            params["ogrn"] = ogrn
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_counterparty", inn=inn, ogrn=ogrn)
        return self._request("GET", PATH_COUNTERPARTY, params=params)

    def get_finance_company(self, inn_or_ogrn: str) -> List[Dict[str, Any]]:
        """Legacy/company-scoped finance endpoint using id param.
        Kept for backward compatibility if aggregator already expects it.
        """
        log.info("DN get_finance_company", id=inn_or_ogrn)
        data = self._request("GET", PATH_FINANCE_COMPANY, params={"id": inn_or_ogrn})
        return data if isinstance(data, list) else data.get("items", [])

    def get_finance(self, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """Public finance endpoint: GET /v1/finance with inn or ogrn.
        If auth_scheme is 'query', pass the API key as ?key=...
        """
        params: Dict[str, Any] = {}
        if inn:
            params["inn"] = inn
        if ogrn:
            params["ogrn"] = ogrn
        # Optional query key support
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_finance", inn=inn, ogrn=ogrn)
        return self._request("GET", PATH_FINANCE, params=params)

    def get_procure_summary(self, inn_or_ogrn: str) -> Dict[str, Any]:
        log.info("DN get_procure_summary", id=inn_or_ogrn)
        return self._request("GET", PATH_PROCURE_SUMMARY, params={"id": inn_or_ogrn})

    def get_enforcement_summary(self, inn_or_ogrn: str) -> Dict[str, Any]:
        log.info("DN get_enforcement_summary", id=inn_or_ogrn)
        return self._request("GET", PATH_ENFORCEMENT, params={"id": inn_or_ogrn})

    def get_certificates(self, inn_or_ogrn: str) -> List[Dict[str, Any]]:
        log.info("DN get_certificates", id=inn_or_ogrn)
        data = self._request("GET", PATH_CERTIFICATES, params={"id": inn_or_ogrn})
        return data if isinstance(data, list) else data.get("items", [])

    def get_ip_summary(self, inn_or_ogrn: str, name: Optional[str]) -> Dict[str, Any]:
        params: Dict[str, Any] = {"id": inn_or_ogrn}
        if name:
            params["name"] = name
        log.info("DN get_ip_summary", id=inn_or_ogrn, has_name=bool(name))
        return self._request("GET", PATH_IP_SUMMARY, params=params)

    def get_batch_by_filters(self, limit: int, offset: int, body: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/batchCardsByFilters with limit/offset and JSON body.
        If auth_scheme is 'query', pass the API key as ?key=...
        Returns dict including data, total, limit, offset, available_count.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_batch_by_filters", limit=limit, offset=offset)
        return self._request("POST", PATH_BATCH_CARDS, params=params, json=body)

    def get_risks(self, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """GET /v1/risks with inn or ogrn; supports query-key auth.
        Returns a dict with ogrn, flags[], available_count.
        """
        params: Dict[str, Any] = {}
        if inn:
            params["inn"] = inn
        if ogrn:
            params["ogrn"] = ogrn
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_risks", inn=inn, ogrn=ogrn)
        return self._request("GET", PATH_RISKS, params=params)

    def suggestions(self, search_query: str, type: str = "all", is_active: Optional[bool] = None) -> Dict[str, Any]:
        """POST /v1/suggestions to get up to 10 matches for a query.
        Body: {search_query, type?, is_active?}. Supports query-key auth.
        """
        params: Dict[str, Any] = {}
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        body: Dict[str, Any] = {"search_query": search_query}
        if type:
            body["type"] = type
        if is_active is not None:
            body["is_active"] = is_active
        log.info("DN suggestions", type=type, is_active=is_active)
        return self._request("POST", PATH_SUGGESTIONS, params=params, json=body)

    # Dictionaries and additional endpoints
    def get_okved_dictionary(self) -> List[Dict[str, Any]]:
        """GET /v1/dictionary/okveds"""
        log.info("DN get_okved_dictionary")
        return self._request("GET", PATH_DICT_OKVEDS)

    def get_licenses_dictionary(self) -> Dict[str, Any]:
        """GET /v1/dictionary/licenses"""
        log.info("DN get_licenses_dictionary")
        return self._request("GET", PATH_DICT_LICENSES)

    def get_lease_classifier(self) -> Dict[str, Any]:
        """GET /v1/dictionary/lease-classifier"""
        log.info("DN get_lease_classifier")
        return self._request("GET", PATH_DICT_LEASE_CLASSIFIER)

    def get_tax_info(self, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """GET /v1/taxInfo with inn or ogrn; supports query-key auth."""
        params: Dict[str, Any] = {}
        if inn:
            params["inn"] = inn
        if ogrn:
            params["ogrn"] = ogrn
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_tax_info", inn=inn, ogrn=ogrn)
        return self._request("GET", PATH_TAX_INFO, params=params)

    def get_paid_taxes(self, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """GET /v1/paidTaxes with inn or ogrn; supports query-key auth."""
        params: Dict[str, Any] = {}
        if inn:
            params["inn"] = inn
        if ogrn:
            params["ogrn"] = ogrn
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_paid_taxes", inn=inn, ogrn=ogrn)
        return self._request("GET", PATH_PAID_TAXES, params=params)

    def get_arbitration_cases(self, inn: Optional[str] = None, ogrn: Optional[str] = None, *, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """GET /v1/arbitration-cases with inn or ogrn; supports query-key auth."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if inn:
            params["inn"] = inn
        if ogrn:
            params["ogrn"] = ogrn
        if self.cfg.auth_scheme.lower() == "query" and self.cfg.token:
            params["key"] = self.cfg.token
        log.info("DN get_arbitration_cases", inn=inn, ogrn=ogrn)
        return self._request("GET", PATH_ARBITRATION_CASES, params=params)


# Convenience helpers used by aggregator

def get_dn_client() -> Optional[DataNewtonClient]:
    if not FEATURE_DATANEWTON or not DATANEWTON_API:
        log.debug("DataNewton disabled or base URL missing")
        return None
    cfg = DataNewtonConfig(
        base_url=DATANEWTON_API,
        token=DATANEWTON_TOKEN,
        timeout=DATANEWTON_TIMEOUT,
        max_retries=DATANEWTON_MAX_RETRIES,
        rate_limit_qpm=DATANEWTON_RATE_LIMIT_QPM,
        auth_scheme=DATANEWTON_AUTH_SCHEME,
    )
    return DataNewtonClient(cfg)
