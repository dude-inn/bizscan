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
    opf: Optional[str] = None
    charter_capital: Optional[Decimal] = None
    owners: Optional[List[Dict[str, Any]]] = None
    tax_mode: Optional[str] = None
    workers_count: Optional[int] = None
    contacts: Optional[Dict[str, Any]] = None
    predecessors: Optional[List[Dict[str, Any]]] = None
    successors: Optional[List[Dict[str, Any]]] = None
    negative_lists: Optional[Dict[str, Any]] = None


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


@dataclass
class ContractItem:
    number: str
    date: Optional[str]
    price: Optional[Decimal]
    customer: Optional[str]
    eis_url: Optional[str]


@dataclass
class ContractsSummary:
    total: int
    items: List[ContractItem]


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
    from core.logger import setup_logging
    log = setup_logging()
    
    log.info("map_status_ofdata: processing status", 
            status_obj_type=type(status_obj).__name__,
            status_obj_value=str(status_obj)[:200])
    
    if isinstance(status_obj, str):
        status_name = status_obj.lower()
        status_text = status_obj
    elif isinstance(status_obj, dict):
        status_name = (status_obj.get("Наим") or status_obj.get("name") or "").lower()
        status_text = status_obj.get("Наим") or status_obj.get("name")
    else:
        log.warning("map_status_ofdata: unknown status object type", 
                   status_obj_type=type(status_obj).__name__)
        return "UNKNOWN", None

    log.info("map_status_ofdata: status analysis", 
            status_name=status_name,
            status_text=status_text,
            is_dict=isinstance(status_obj, dict))

    if "действующ" in status_name or "active" in status_name or (isinstance(status_obj, dict) and status_obj.get("active_status") in (True, 1, "1", "true")):
        result = "ACTIVE", status_text or "Действует"
        log.info("map_status_ofdata: mapped to ACTIVE", result=result)
        return result
    if "ликвидирован" in status_name or "liquidat" in status_name or (isinstance(status_obj, dict) and (status_obj.get("date_end") or "")):
        result = "LIQUIDATED", status_text or "Ликвидировано"
        log.info("map_status_ofdata: mapped to LIQUIDATED", result=result)
        return result
    if "не действует" in status_name or "исключен" in status_name or "inactive" in status_name:
        result = "NOT_ACTIVE", status_text or "Не действует"
        log.info("map_status_ofdata: mapped to NOT_ACTIVE", result=result)
        return result
    
    result = "UNKNOWN", status_text
    log.warning("map_status_ofdata: mapped to UNKNOWN", 
               result=result,
               status_name=status_name,
               status_text=status_text)
    return result


def map_company_ofdata(raw: Dict[str, Any]) -> CompanyCard:
    """Map OFData company response to CompanyCard.
    Supports payloads like {inn, ogrn, company: {...}} or {data: {...}} or flat.
    """
    from core.logger import setup_logging
    log = setup_logging()

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
    status_code, status_text = map_status_ofdata(status_obj)

    # Address
    addr = container.get("ЮрАдрес") or container.get("address") or {}
    if isinstance(addr, dict):
        address = (
            addr.get("value")
            or addr.get("АдресРФ")
            or addr.get("full_address")
            or addr.get("address")
        )
        if not address:
            parts = [addr.get(k) for k in ("region", "area", "city", "street", "house", "building")]
            parts = [p for p in parts if p]
            address = ", ".join(parts) if parts else None
    elif isinstance(addr, str):
        address = addr
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

    # OKVED: OFData may return list okveds or single object
    okved = None
    okveds_list = container.get("okveds") or container.get("ОКВЭДДоп")
    if isinstance(okveds_list, list) and okveds_list:
        main = next((x for x in okveds_list if isinstance(x, dict) and x.get("is_main")), okveds_list[0])
        if isinstance(main, dict):
            code = main.get("code") or main.get("Код")
            name = main.get("name") or main.get("Наим")
            if code and name:
                okved = f"{code} {name}"
            elif code:
                okved = str(code)
            elif name:
                okved = str(name)
    else:
        okved_obj = container.get("ОКВЭД") or container.get("okved") or {}
        if isinstance(okved_obj, dict):
            code = okved_obj.get("Код") or okved_obj.get("code")
            name = okved_obj.get("Наим") or okved_obj.get("name") or okved_obj.get("description")
            if code and name:
                okved = f"{code} {name}"
            elif code:
                okved = str(code)
            elif name:
                okved = str(name)

    # MSME
    msme_obj = container.get("РМСП") or container.get("msme") or {}
    is_msme = None
    if isinstance(msme_obj, dict):
        is_msme = msme_obj.get("Кат") is not None

    # OPF
    opf_obj = container.get("ОКОПФ") or container.get("opf") or {}
    opf_name = None
    if isinstance(opf_obj, dict):
        opf_name = opf_obj.get("Наим") or opf_obj.get("name")

    # Charter capital
    cap_obj = container.get("УстКап") or container.get("charter_capital") or {}
    cap_amount: Optional[Decimal] = None
    if isinstance(cap_obj, dict):
        cap_val = cap_obj.get("Сумма") or cap_obj.get("amount")
        try:
            cap_amount = Decimal(str(cap_val)) if cap_val is not None else None
        except Exception:
            cap_amount = None

    # Owners (best-effort)
    owners = container.get("owners") or []
    if not owners:
        uchr = container.get("Учред")
        if isinstance(uchr, dict):
            owners = uchr.get("ФЛ") or uchr.get("РосОрг") or uchr.get("ИнОрг") or []

    # Tax mode (special regimes)
    tax_mode = None
    nalogi = container.get("Налоги") or container.get("taxes") or {}
    if isinstance(nalogi, dict):
        modes = nalogi.get("ОсобРежим") or nalogi.get("special_modes")
        if isinstance(modes, list) and modes:
            tax_mode = ", ".join(map(str, modes))
        else:
            log.info("No tax modes found in Налоги section", nalogi_keys=list(nalogi.keys()) if isinstance(nalogi, dict) else None)
    else:
        log.info("No Налоги section found in container", container_keys=list(container.keys()))

    # Workers count
    workers_count = container.get("СЧР") or container.get("workers_count")
    if workers_count is None:
        log.info("No СЧР (workers_count) found in container", container_keys=list(container.keys()))
    try:
        workers_count = int(workers_count) if workers_count is not None else None
    except Exception:
        workers_count = None

    # Contacts (normalize to site/emails/phones)
    raw_contacts = container.get("Контакты") or container.get("contacts") or {}
    contacts: Dict[str, Any] = {}
    if isinstance(raw_contacts, dict):
        site = raw_contacts.get("ВебСайт") or raw_contacts.get("site") or raw_contacts.get("website")
        emails = raw_contacts.get("Емэйл") or raw_contacts.get("emails") or raw_contacts.get("email") or []
        phones = raw_contacts.get("Тел") or raw_contacts.get("phones") or raw_contacts.get("tel") or []
        # normalize scalars to lists
        if isinstance(emails, str):
            emails = [emails]
        if isinstance(phones, str):
            phones = [phones]
        contacts = {"site": site, "emails": emails, "phones": phones}

    # Predecessors/successors
    predecessors = container.get("Правопредш") or container.get("predecessors") or []
    successors = container.get("Правопреем") or container.get("successors") or []

    # Negative lists flags
    negative_lists = {
        "НедобПост": container.get("НедобПост") or container.get("is_blacklisted_supplier"),
        "ДисквЛица": container.get("ДисквЛица"),
        "МассРуковод": container.get("МассРуковод"),
        "МассУчред": container.get("МассУчред"),
        "НелегалФин": container.get("НелегалФин"),
        "Санкции": container.get("Санкции"),
    }

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
        opf=opf_name,
        charter_capital=cap_amount,
        owners=owners if isinstance(owners, list) else [],
        tax_mode=tax_mode,
        workers_count=workers_count,
        contacts=contacts if isinstance(contacts, dict) else {},
        predecessors=predecessors if isinstance(predecessors, list) else [],
        successors=successors if isinstance(successors, list) else [],
        negative_lists=negative_lists,
    )


def map_finance_ofdata(raw: Dict[str, Any]) -> List[FinanceSnapshot]:
    """Map OFData finance response to FinanceSnapshot list.
    Supports:
    - raw['data'] as a list of snapshots with flat fields
    - raw['data'] as a dict of {year: { code->value or code->{'СумОтч': value} }}
    """
    data = raw.get("data") if isinstance(raw, dict) else None

    # helper to coerce to Decimal

    def to_decimal(val):
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    snapshots: List[FinanceSnapshot] = []
    # Case 1: list format
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            period = str(item.get("period") or item.get("year") or "")
            revenue = item.get("revenue") or item.get("income") or item.get("2110")
            net_profit = item.get("net_profit") or item.get("profit") or item.get("2400")
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

    # Case 2: dict keyed by year
    if isinstance(data, dict):
        def pick_val(code_container: Any) -> Any:
            if isinstance(code_container, dict):
                # Prefer current-period value
                return (
                    code_container.get("СумОтч")
                    or code_container.get("СумОтчет")
                    or code_container.get("sum")
                    or code_container.get("value")
                )
            return code_container

        for year, payload in data.items():
            if not isinstance(payload, dict):
                continue
            period = str(year)
            revenue = pick_val(payload.get("2110"))
            net_profit = pick_val(payload.get("2400"))
            assets = pick_val(payload.get("1600"))
            equity = pick_val(payload.get("1300"))
            lt = pick_val(payload.get("1400"))
            st = pick_val(payload.get("1500"))

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

        # sort by period descending if numeric years
        try:
            snapshots.sort(key=lambda s: int(s.period), reverse=True)
        except Exception:
            snapshots.sort(key=lambda s: s.period, reverse=True)
        return snapshots

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


def map_contracts_ofdata(raw: Dict[str, Any]) -> ContractsSummary:
    """Map OFData contracts (/v2/contracts) to ContractsSummary."""
    data = raw.get("data") or {}
    total = data.get("ЗапВсего") or raw.get("total") or 0
    records = data.get("Записи") or []
    items: List[ContractItem] = []
    for it in records[:20]:
        if not isinstance(it, dict):
            continue
        num = it.get("РегНомер") or it.get("number") or ""
        date = it.get("Дата") or it.get("date")
        price = it.get("Цена") or it.get("price")
        try:
            price_dec = Decimal(str(price)) if price is not None else None
        except Exception:
            price_dec = None
        customer_obj = it.get("Заказ") or {}
        customer = customer_obj.get("НаимСокр") or customer_obj.get("НаимПолн") or customer_obj.get("name")
        eis = it.get("СтрЕИС") or it.get("url")
        items.append(ContractItem(number=num, date=str(date) if date else None, price=price_dec, customer=customer, eis_url=eis))
    return ContractsSummary(total=int(total or 0), items=items)


# ===============
# Inspections
# ===============

@dataclass
class InspectionItem:
    number: str
    status: Optional[str]
    date_start: Optional[str]
    date_end: Optional[str]
    type: Optional[str]
    controller: Optional[str]
    address: Optional[str]


@dataclass
class InspectionsSummary:
    total: int
    items: List[InspectionItem]


def map_inspections_ofdata(raw: Dict[str, Any]) -> InspectionsSummary:
    data = raw.get("data") or {}
    total = data.get("ЗапВсего") or data.get("ОбщКолич") or 0
    records = data.get("Записи") or []
    items: List[InspectionItem] = []
    for it in records[:20]:
        if not isinstance(it, dict):
            continue
        num = it.get("Номер") or it.get("number") or ""
        status = it.get("Статус") or it.get("status")
        d1 = it.get("ДатаНач") or it.get("date_start") or it.get("Дата") or it.get("date")
        d2 = it.get("ДатаОконч") or it.get("date_end")
        typ = it.get("ТипПров") or it.get("type")
        ctrl = None
        org = it.get("ОргКонтр") or {}
        if isinstance(org, dict):
            ctrl = org.get("Наим") or org.get("name")
        addr = None
        objs = it.get("Объекты") or []
        if isinstance(objs, list) and objs:
            first = objs[0] or {}
            if isinstance(first, dict):
                addr = first.get("Адрес") or first.get("address")
        items.append(InspectionItem(number=num, status=status, date_start=str(d1) if d1 else None,
                                    date_end=str(d2) if d2 else None, type=typ, controller=ctrl, address=addr))
    return InspectionsSummary(total=int(total or 0), items=items)


# ===============
# Enforcements
# ===============

@dataclass
class EnforcementItem:
    number: str
    date: Optional[str]
    doc_type: Optional[str]
    subject: Optional[str]
    amount: Optional[Decimal]
    remainder: Optional[Decimal]


@dataclass
class EnforcementsSummary:
    total: int
    total_amount: Optional[Decimal]
    remainder_amount: Optional[Decimal]
    items: List[EnforcementItem]


def map_enforcements_ofdata(raw: Dict[str, Any]) -> EnforcementsSummary:
    data = raw.get("data") or {}
    total = data.get("ЗапВсего") or data.get("ОбщКолич") or 0
    total_amount = data.get("ОбщСум")
    remainder = data.get("ОстЗадолж")
    try:
        total_amount = Decimal(str(total_amount)) if total_amount is not None else None
    except Exception:
        total_amount = None
    try:
        remainder = Decimal(str(remainder)) if remainder is not None else None
    except Exception:
        remainder = None
    records = data.get("Записи") or []
    items: List[EnforcementItem] = []
    for it in records[:20]:
        if not isinstance(it, dict):
            continue
        num = it.get("ИспПрНомер") or it.get("number") or ""
        d = it.get("ИспПрДата") or it.get("date")
        doc_type = it.get("ИспДокТип") or it.get("doc_type")
        subject = it.get("ПредмИсп") or it.get("subject")
        amt = it.get("СумДолг")
        rem = it.get("ОстЗадолж")
        try:
            amt_dec = Decimal(str(amt)) if amt is not None else None
        except Exception:
            amt_dec = None
        try:
            rem_dec = Decimal(str(rem)) if rem is not None else None
        except Exception:
            rem_dec = None
        items.append(EnforcementItem(number=num, date=str(d) if d else None, doc_type=doc_type, subject=subject, amount=amt_dec, remainder=rem_dec))
    return EnforcementsSummary(total=int(total or 0), total_amount=total_amount, remainder_amount=remainder, items=items)


def map_paid_taxes_ofdata(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map OFData paid taxes response to list of tax items."""
    if not raw or not isinstance(raw, dict):
        return []
    
    items = raw.get("data", []) or raw.get("items", []) or []
    if not isinstance(items, list):
        return []
    
    mapped_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        mapped_items.append({
            "report_date": item.get("report_date") or item.get("Дата") or None,
            "items": item.get("items", []) or item.get("Налоги", []) or []
        })
    
    return mapped_items
