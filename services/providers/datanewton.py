# services/providers/datanewton.py
from __future__ import annotations

import os
import time
from collections import deque
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEFAULT_BASE_URL = os.getenv("DATANEWTON_API", "https://api.datanewton.ru")
API_KEY = os.getenv("DATANEWTON_KEY") or os.getenv("DATANEWTON_TOKEN") or os.getenv("DATANEWTON_API_KEY")
TIMEOUT = float(os.getenv("DATANEWTON_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("DATANEWTON_MAX_RETRIES", "2"))
RATE_QPM = int(os.getenv("DATANEWTON_RATE_LIMIT_QPM", "70"))

class DNClientError(Exception):
    pass

class DNServerTemporaryError(Exception):
    pass


class DataNewtonClient:
    """
    Клиент для расширенного тарифа DataNewton:
      - GET /v1/counterparty - общая информация о контрагенте (с фильтрами)
      - GET /v1/finance - финансовая отчетность
      - GET /v1/paidTaxes - уплаченные налоги
      - GET /v1/arbitration-cases - арбитражные дела
      - GET /v1/links - связи между организациями
      - GET /v1/corporateActions - корпоративные действия
    Авторизация: query param ?key=...
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = TIMEOUT):
        if api_key is None:
            api_key = API_KEY
        if not api_key:
            raise DNClientError("DATANEWTON_KEY/TOKEN/API_KEY is not set")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        # Простейший локальный rate limit: не более RATE_QPM в минуту
        self._ticks = deque(maxlen=RATE_QPM)

    def _throttle(self) -> None:
        if RATE_QPM <= 0:
            return
        now = time.time()
        self._ticks.append(now)
        if len(self._ticks) == self._ticks.maxlen:
            # если 70-й запрос за последнюю минуту — ждём, пока окно разъедется
            oldest = self._ticks[0]
            elapsed = now - oldest
            if elapsed < 60:
                time.sleep(60 - elapsed + 0.01)

    @retry(
        reraise=True,
        stop=stop_after_attempt(MAX_RETRIES + 1),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type(DNServerTemporaryError),
    )
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._throttle()
        params = dict(params or {})
        params["key"] = self.api_key  # ключ ВСЕГДА добавляем в query
        url = path if path.startswith("/") else f"/{path}"
        try:
            resp = self._client.get(url, params=params)
        except httpx.RequestError as e:
            raise DNServerTemporaryError(f"network error: {e}") from e

        status = resp.status_code
        if status == 403:
            raise DNClientError("403: доступ запрещён для текущего ключа/тарифа")
        if status in (500, 502, 503, 504):
            raise DNServerTemporaryError(f"{status}: временная ошибка сервера")
        if status == 409:
            # DN часто отдает 409 при неправильном входе/ненайденном контрагенте
            # Пробрасываем наверх как «нет данных»
            return {"_error": "conflict_or_not_found", "_status": status, **(resp.json() if resp.content else {})}
        if status >= 400:
            raise DNClientError(f"{status}: unexpected client error; body={resp.text[:300]}")

        return resp.json() if resp.content else {}

    # === Публичные методы ===
    def get_counterparty(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise DNClientError("counterparty requires inn or ogrn")
        params = {"inn": inn} if inn else {"ogrn": ogrn}
        
        # Добавляем фильтры для получения детальной информации
        filters = [
            "ADDRESS_BLOCK",
            "MANAGER_BLOCK", 
            "OKVED_BLOCK",
            "OWNER_BLOCK",
            "ROSSTAT_BLOCK",
            "CONTACT_BLOCK",
            "WORKERS_COUNT_BLOCK"
        ]
        params["filters"] = ",".join(filters)
        
        return self._get("/v1/counterparty", params=params)

    def get_finance(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise DNClientError("finance requires inn or ogrn")
        params = {"inn": inn} if inn else {"ogrn": ogrn}
        return self._get("/v1/finance", params=params)

    def get_paid_taxes(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise DNClientError("paidTaxes requires inn or ogrn")
        params = {"inn": inn} if inn else {"ogrn": ogrn}
        # Добавляем дополнительные параметры для получения данных
        params.update({
            "limit": 1000,
            "offset": 0
        })
        return self._get("/v1/paidTaxes", params=params)

    def get_arbitration_cases(
        self,
        *,
        inn: Optional[str] = None,
        ogrn: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        if not inn and not ogrn:
            raise DNClientError("arbitration-cases requires inn or ogrn")
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if inn:
            params["inn"] = inn
        else:
            params["ogrn"] = ogrn
        return self._get("/v1/arbitration-cases", params=params)

    def get_links(
        self,
        *,
        ogrn: str,
        level: int = 2,
    ) -> Dict[str, Any]:
        """GET /v1/links - связи между организациями"""
        params = {"ogrn": ogrn, "level": level}
        return self._get("/v1/links", params=params)

    def get_corporate_actions(
        self,
        *,
        inn: Optional[str] = None,
        ogrn: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        group: Optional[str] = None,
        type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /v1/corporateActions - корпоративные действия"""
        if not inn and not ogrn:
            raise DNClientError("corporateActions requires inn or ogrn")
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if inn:
            params["inn"] = inn
        else:
            params["ogrn"] = ogrn
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if group:
            params["group"] = group
        if type:
            params["type"] = type
        return self._get("/v1/corporateActions", params=params)
