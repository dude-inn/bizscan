# services/mappers/ofdata.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


# =======================
# Card / Company mapping
# =======================

@dataclass
class CompanyCard:
    inn: str
    ogrn: Optional[str]
    kpp: Optional[str]
    name_full: str
    name_short: Optional[str]
    registration_date: Optional[str]
    status_code: str  # ACTIVE | LIQUIDATED | NOT_ACTIVE | UNKNOWN
    status_text: Optional[str]
    address: Optional[str]
    manager_name: Optional[str]
    manager_post: Optional[str]
    okved: Optional[str]
    is_msme: Optional[bool]


@dataclass
class FinanceSnapshot:
    period: str
    revenue: Optional[Decimal]
    net_profit: Optional[Decimal]
    assets: Optional[Decimal]
    equity: Optional[Decimal]
    long_term_liabilities: Optional[Decimal]
    short_term_liabilities: Optional[Decimal]


@dataclass
class ArbitrationCase:
    number: str
    date_start: Optional[str]
    role: Optional[str]
    amount: Optional[Decimal]
    court: Optional[str]
    instances: Optional[str]


@dataclass
class ArbitrationSummary:
    total: int
    cases: List[ArbitrationCase]


def _extract(d: Dict[str, Any], path: str, default=None):
    """Extract nested value from dict using dot notation"""
    cur: Any = d
    for key in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return default
    return default if cur is None else cur


def map_status_ofdata(status_obj: Dict[str, Any] | str) -> Tuple[str, Optional[str]]:
    """Map OFData status to our status codes (supports dict or string)."""
    if isinstance(status_obj, str):
        status_name = status_obj.lower()
        status_text = status_obj
    elif isinstance(status_obj, dict):
        status_name = (status_obj.get("Наим") or status_obj.get("name") or "").lower()
        status_text = status_obj.get("Наим") or status_obj.get("name")
    else:
        return "UNKNOWN", None

    if "действующ" in status_name or "active" in status_name:
        return "ACTIVE", status_text or "Действует"
    if "ликвидирован" in status_name or "liquidat" in status_name:
        return "LIQUIDATED", status_text or "Ликвидировано"
    if "не действует" in status_name or "исключен" in status_name or "inactive" in status_name:
        return "NOT_ACTIVE", status_text or "Не действует"
    return "UNKNOWN", status_text


def map_company_ofdata(raw: Dict[str, Any]) -> CompanyCard:
    """Map OFData company response to CompanyCard.
    Supports payloads like {inn, ogrn, company: {...}} or {data: {...}} or flat.
    """
    import logging
    log = logging.getLogger(__name__)

    # Determine container with company fields
    container: Dict[str, Any] = (
        raw.get("company") if isinstance(raw.get("company"), dict) else None
    ) or (
        raw.get("data") if isinstance(raw.get("data"), dict) else None
    ) or raw

    log.info(f"🔍 OFData mapping - raw keys: {list(raw.keys())}")
    try:
        log.info(f"🧩 Company container keys: {list(container.keys())}")
    except Exception:
        pass

    # Basic ids (prefer top-level when provided)
    inn = (raw.get("inn") or raw.get("ИНН") or container.get("ИНН") or container.get("inn") or "").strip()
    ogrn = raw.get("ogrn") or raw.get("ОГРН") or container.get("ОГРН") or container.get("ogrn")
    kpp = raw.get("kpp") or container.get("КПП") or container.get("kpp")

    # Names
    name_full = (
        container.get("НаимПолн")
        or container.get("name_full")
        or container.get("full_name")
        or container.get("name")
        or ""
    )
    name_short = (
        container.get("НаимСокр")
        or container.get("name_short")
        or container.get("short_name")
    )

    # Dates
    registration_date = container.get("ДатаРег") or container.get("registration_date")

    # Status
    status_obj = container.get("Статус") or container.get("status") or {}
    status_code, status_text = map_status_ofdata(status_obj) if isinstance(status_obj, dict) else ("UNKNOWN", None)

    # Address
    addr = container.get("ЮрАдрес") or container.get("address") or {}
    if isinstance(addr, dict):
        address = addr.get("АдресРФ") or addr.get("full_address") or addr.get("address")
    else:
        address = None

    # Manager
    managers = container.get("Руковод") or container.get("managers") or []
    manager_name = None
    manager_post = None
    if isinstance(managers, list) and managers:
        m0 = managers[0] or {}
        manager_name = m0.get("ФИО") or m0.get("ФИОПолн") or m0.get("fio") or m0.get("name") or m0.get("full_name")
        manager_post = m0.get("НаимДолжн") or m0.get("position")

    # OKVED
    okved_obj = container.get("ОКВЭД") or container.get("okved") or {}
    if isinstance(okved_obj, dict):
        okved = okved_obj.get("Наим") or okved_obj.get("name") or okved_obj.get("description") or okved_obj.get("Код") or okved_obj.get("code")
    else:
        okved = None

    # MSME
    msme_obj = container.get("РМСП") or container.get("msme") or {}
    is_msme = None
    if isinstance(msme_obj, dict):
        is_msme = msme_obj.get("Кат") is not None

    log.info(
        f"📊 Mapped company: {name_full[:50]}... | INN: {inn} | Status: {status_code} | "
        f"Address: {bool(address)} | Manager: {manager_name is not None} | OKVED: {okved is not None}"
    )

    return CompanyCard(
        inn=inn,
        ogrn=ogrn,
        kpp=kpp,
        name_full=name_full,
        name_short=name_short,
        registration_date=registration_date,
        status_code=status_code,
        status_text=status_text,
        address=address,
        manager_name=manager_name,
        manager_post=manager_post,
        okved=okved,
        is_msme=is_msme,
    )


def map_finance_ofdata(raw: Dict[str, Any]) -> List[FinanceSnapshot]:
    """Map OFData finance response to FinanceSnapshot list.
    Supports list in raw['data'] with common keys or code-like keys.
    """
    data = raw.get("data") if isinstance(raw, dict) else None
    if not isinstance(data, list):
        data = []

    def to_decimal(val):
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    snapshots: List[FinanceSnapshot] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        period = str(item.get("period") or item.get("year") or "")
        revenue = (
            item.get("revenue") or item.get("income") or item.get("2110")
        )
        net_profit = (
            item.get("net_profit") or item.get("profit") or item.get("2400")
        )
        assets = item.get("assets") or item.get("1600")
        equity = item.get("equity") or item.get("1300")
        lt = item.get("long_term_liabilities") or item.get("1400")
        st = item.get("short_term_liabilities") or item.get("1500")

        snapshots.append(
            FinanceSnapshot(
                period=period,
                revenue=to_decimal(revenue),
                net_profit=to_decimal(net_profit),
                assets=to_decimal(assets),
                equity=to_decimal(equity),
                long_term_liabilities=to_decimal(lt),
                short_term_liabilities=to_decimal(st),
            )
        )

    return snapshots


def map_arbitration_ofdata(raw: Dict[str, Any]) -> ArbitrationSummary:
    """Map OFData legal cases response to ArbitrationSummary."""
    data = raw.get("data") if isinstance(raw, dict) else None
    if not isinstance(data, list):
        data = []
    total = raw.get("total") or raw.get("total_cases") or len(data)

    cases: List[ArbitrationCase] = []
    for it in data:
        if not isinstance(it, dict):
            continue
        number = it.get("number") or it.get("case_number") or ""
        date_start = it.get("date_start") or it.get("date") or it.get("start_date")
        role = it.get("role") or it.get("participant_role")
        amount = it.get("amount") or it.get("sum")
        court = it.get("court") or it.get("court_name")
        instances = it.get("instances") or it.get("court_instances")

        try:
            amount = Decimal(str(amount)) if amount is not None else None
        except Exception:
            amount = None

        cases.append(
            ArbitrationCase(
                number=number,
                date_start=date_start,
                role=role,
                amount=amount,
                court=court,
                instances=instances,
            )
        )

    return ArbitrationSummary(total=int(total or 0), cases=cases)
