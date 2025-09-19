# services/mappers/datanewton.py
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


def _extract(d: Dict[str, Any], path: str, default=None):
    cur: Any = d
    for key in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return default
    return default if cur is None else cur


def map_status(status_obj: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    # DN: {"active_status": true|false, "date_end": "", "status_rus_short": "Действует", ...}
    active = bool(status_obj.get("active_status"))
    status_rus = status_obj.get("status_rus_short") or None
    date_end = (status_obj.get("date_end") or "").strip()

    if active is True:
        return "ACTIVE", status_rus or "Действует"
    if active is False and date_end:
        return "LIQUIDATED", status_rus or "Прекращено"
    if active is False:
        return "NOT_ACTIVE", status_rus or "Не действует"
    return "UNKNOWN", status_rus


def map_counterparty(raw: Dict[str, Any]) -> CompanyCard:
    # Разворачиваем data если есть
    if "data" in raw and isinstance(raw["data"], dict):
        raw = raw["data"]
    
    # Логируем структуру для отладки
    import logging
    logger = logging.getLogger("mappers")
    logger.setLevel(logging.INFO)
    logger.info(f"Counterparty raw keys: {list(raw.keys())}")
    if "company" in raw:
        logger.info(f"Company keys: {list(raw['company'].keys())}")
    logger.info(f"Full company object: {raw['company']}")
    
    inn = raw.get("inn") or ""
    ogrn = raw.get("ogrn")
    company = raw.get("company") or {}
    names = company.get("company_names") or {}
    status_obj = company.get("status") or {}
    status_code, status_text = map_status(status_obj)

    # address может быть пустым объектом
    addr_obj = company.get("address") or {}
    logger.info(f"Address object: {addr_obj}")
    addr_val = addr_obj.get("line_address") or addr_obj.get("value") or addr_obj.get("full_address") or addr_obj.get("address") or None

    managers = company.get("managers") or []
    logger.info(f"Managers: {managers}")
    manager_name = managers[0].get("fio") or managers[0].get("name") if managers else None
    manager_post = managers[0].get("position") or managers[0].get("post") if managers else None

    okveds = company.get("okveds") or []
    logger.info(f"OKVEDs: {okveds}")
    okved = None
    if okveds:
        # пытаемся найти основной, иначе берём первый
        primary = next((o for o in okveds if o.get("is_main") or o.get("main")), None)
        okved_obj = primary or okveds[0]
        okved = okved_obj.get("value") or okved_obj.get("name") or okved_obj.get("code") or okved_obj.get("description")

    # Признак МСП может жить в отдельном блоке, но в «облегчённых» данных его может не быть
    is_msme = None
    msp_block = company.get("msp_block") or company.get("msme") or {}
    logger.info(f"MSP block: {msp_block}")
    if msp_block:
        is_msme = bool(msp_block.get("msp") or msp_block.get("is_msme") or msp_block.get("is_msme_entity"))

    result = CompanyCard(
        inn=inn,
        ogrn=ogrn,
        kpp=company.get("kpp"),
        name_full=names.get("full_name") or "",
        name_short=names.get("short_name"),
        registration_date=company.get("registration_date"),
        status_code=status_code,
        status_text=status_text,
        address=addr_val,
        manager_name=manager_name,
        manager_post=manager_post,
        okved=okved,
        is_msme=is_msme,
    )
    
    logger.info(f"Mapped company: address={result.address}, manager={result.manager_name}, okved={result.okved}")
    return result


# =======================
# Finance mapping
# =======================

@dataclass
class FinanceSnapshot:
    period: int  # year
    revenue: Optional[Decimal]
    net_profit: Optional[Decimal]
    assets: Optional[Decimal]
    equity: Optional[Decimal]
    liabilities_long: Optional[Decimal]
    liabilities_short: Optional[Decimal]


def _deep_find_code(node: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    """Рекурсивно ищем узел с заданным кодом (0710001/0710002) в childrenMap/indicators."""
    if not isinstance(node, dict):
        return None
    if node.get("code") == code:
        return node
    # childrenMap: dict[str, node]
    for child in (node.get("childrenMap") or {}).values():
        found = _deep_find_code(child, code)
        if found:
            return found
    # indicators: list[node]
    for child in (node.get("indicators") or []) or []:
        found = _deep_find_code(child, code)
        if found:
            return found
    # обойти все словари внутри
    for v in node.values():
        if isinstance(v, dict):
            found = _deep_find_code(v, code)
            if found:
                return found
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    found = _deep_find_code(it, code)
                    if found:
                        return found
    return None


def _value_by_year_from_node(node: Dict[str, Any], year: int) -> Optional[Decimal]:
    sums = (node.get("sum") or {})
    if not isinstance(sums, dict):
        return None
    val = sums.get(str(year))
    return None if val is None else Decimal(str(val))


def map_finance(raw: Dict[str, Any]) -> List[FinanceSnapshot]:
    # Разворачиваем data если есть
    if "data" in raw and isinstance(raw["data"], dict):
        raw = raw["data"]
    
    # Логируем структуру для отладки
    import logging
    logger = logging.getLogger("mappers")
    logger.setLevel(logging.INFO)
    logger.info(f"Finance raw keys: {list(raw.keys())}")
    
    # Ожидается структура с "balances" и списком "years"
    balances = raw.get("balances") or {}
    logger.info(f"Balances keys: {list(balances.keys())}")
    logger.info(f"Full balances object: {balances}")
    years: List[int] = list(balances.get("years") or [])
    if not years:
        return []
    last_three = sorted(years)[-3:]

    # коды:
    # Баланс (0710001): 1600 (Итого активов), 1300 (Капитал), 1400 (Долгоср. обяз.), 1500 (Краткоср. обяз.)
    node_1600 = _deep_find_code(balances, "1600")
    node_1300 = _deep_find_code(balances, "1300")
    node_1400 = _deep_find_code(balances, "1400")
    node_1500 = _deep_find_code(balances, "1500")

    # Отчёт о финрезах (0710002): 2110 (Выручка), 2400 (Чистая прибыль/убыток)
    # Ищем в fin_results, а не в balances
    fin_results = raw.get("fin_results") or {}
    logger.info(f"Fin results keys: {list(fin_results.keys())}")
    logger.info(f"Full fin_results object: {fin_results}")
    
    node_2110 = _deep_find_code(fin_results, "2110")
    node_2400 = _deep_find_code(fin_results, "2400")
    logger.info(f"Found nodes: 2110={node_2110 is not None}, 2400={node_2400 is not None}")
    
    # Дополнительные коды для поиска выручки и прибыли
    if not node_2110:
        node_2110 = _deep_find_code(fin_results, "2110.0") or _deep_find_code(fin_results, "2110.1")
    if not node_2400:
        node_2400 = _deep_find_code(fin_results, "2400.0") or _deep_find_code(fin_results, "2400.1")

    snapshots: List[FinanceSnapshot] = []
    for y in last_three:
        snapshots.append(
            FinanceSnapshot(
                period=y,
                revenue=_value_by_year_from_node(node_2110, y) if node_2110 else None,
                net_profit=_value_by_year_from_node(node_2400, y) if node_2400 else None,
                assets=_value_by_year_from_node(node_1600, y) if node_1600 else None,
                equity=_value_by_year_from_node(node_1300, y) if node_1300 else None,
                liabilities_long=_value_by_year_from_node(node_1400, y) if node_1400 else None,
                liabilities_short=_value_by_year_from_node(node_1500, y) if node_1500 else None,
            )
        )
    # сортировка по убыванию года для красивого вывода
    snapshots.sort(key=lambda s: s.period, reverse=False)
    return snapshots


# =======================
# Paid taxes mapping
# =======================

@dataclass
class PaidTaxItem:
    report_date: Optional[str]
    items: List[Tuple[str, Decimal]]  # (taxName, taxValue)


def map_paid_taxes(raw: Dict[str, Any]) -> List[PaidTaxItem]:
    # Логируем полный ответ API для отладки
    import logging
    logger = logging.getLogger("mappers")
    logger.setLevel(logging.INFO)
    logger.info(f"Paid taxes raw response: {raw}")
    
    # Разворачиваем data если есть
    if "data" in raw and isinstance(raw["data"], list):
        data = raw["data"]
    else:
        data = raw.get("data") or []
    
    logger.info(f"Paid taxes data length: {len(data)}")
    if data:
        logger.info(f"First tax record: {data[0]}")
    result: List[PaidTaxItem] = []
    for row in data:
        rd = row.get("report_date") or row.get("doc_date")
        lst = []
        for t in row.get("tax_info_list") or []:
            name = t.get("taxName") or t.get("name") or t.get("tax_name") or "Налог"
            val = t.get("taxValue") or t.get("value") or t.get("tax_value") or t.get("amount")
            if val is not None and val != "":
                try:
                    lst.append((name, Decimal(str(val))))
                except:
                    pass
        result.append(PaidTaxItem(report_date=rd, items=lst))
    return result


# =======================
# Arbitration mapping
# =======================

@dataclass
class ArbitrationCase:
    number: str
    date_start: Optional[str]
    role: Optional[str]
    claim_sum: Optional[Decimal]
    court: Optional[str]
    instances: Optional[List[str]]


@dataclass
class ArbitrationSummary:
    total: int
    cases: List[ArbitrationCase]


def map_arbitration(raw: Dict[str, Any], limit: int = 10) -> ArbitrationSummary:
    # Разворачиваем data если есть
    if "data" in raw and isinstance(raw["data"], list):
        data = raw["data"]
    else:
        data = raw.get("data") or []
    
    total = int(raw.get("total_cases") or 0)
    # приводим к нужному виду
    cases: List[ArbitrationCase] = []
    for item in data:
        number = item.get("first_number") or ""
        dstart = item.get("date_start")
        # роль компании — из respondents/plaintiffs
        role = None
        if item.get("respondents"):
            role = (item["respondents"][0].get("role")) or "Ответчик"
        elif item.get("plaintiffs"):
            role = (item["plaintiffs"][0].get("role")) or "Истец"
        claim_sum = item.get("sum")
        court = None
        inst = item.get("instances") or []
        if inst:
            court = inst[0]
        cases.append(
            ArbitrationCase(
                number=number,
                date_start=dstart,
                role=role,
                claim_sum=Decimal(str(claim_sum)) if claim_sum is not None else None,
                court=court,
                instances=inst,
            )
        )
    # сортировка по дате убыв, выводим не более limit
    def _key(c: ArbitrationCase):
        return c.date_start or ""
    cases.sort(key=_key, reverse=True)
    return ArbitrationSummary(total=total, cases=cases[:limit])

