# -*- coding: utf-8 -*-
"""
Mapping helpers for DataNewton responses to domain models.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal

from domain.models import CompanyBase, FinanceSnapshot


def map_company_core_to_base(core: Dict[str, Any]) -> Optional[CompanyBase]:
    """Map DataNewton company core response to CompanyBase.
    Expects fields like inn, ogrn, name, address, okved, manager, etc.
    """
    if not core:
        return None
    try:
        inn = core.get("inn") or core.get("taxpayer_inn")
        name_full = core.get("name_full") or core.get("name") or core.get("short_name") or ""
        if not inn or not name_full:
            return None
        return CompanyBase(
            inn=str(inn),
            ogrn=core.get("ogrn"),
            kpp=core.get("kpp"),
            name_full=name_full,
            name_short=core.get("short_name") or core.get("name_short"),
            okved=core.get("okved_main") or core.get("okved"),
            address=core.get("address") or (core.get("address_block") or {}).get("full_address"),
            management_name=(core.get("managers_block") or {}).get("manager_name") or core.get("manager_name"),
            management_post=(core.get("managers_block") or {}).get("manager_position") or core.get("manager_position"),
            authorized_capital=core.get("charter_capital"),
        )
    except Exception:
        return None


def _to_decimal(value: Any) -> Optional[Decimal]:
    try:
        if value is None:
            return None
        return Decimal(str(value))
    except Exception:
        return None


def map_finance_to_snapshots(finance: Dict[str, Any]) -> List[FinanceSnapshot]:
    """Map DataNewton finance tree into a flat list of FinanceSnapshot by years.
    Uses balances/fin_results totals when available to derive high-level metrics.
    """
    if not finance:
        return []

    years = []
    try:
        years = (finance.get("balances") or {}).get("years") or []
    except Exception:
        years = []

    snapshots: List[FinanceSnapshot] = []

    # Try to resolve summary values for each year
    balances = finance.get("balances") or {}
    liabilities = (balances.get("liabilities") or {})
    assets = (balances.get("assets") or {})
    fin_results = finance.get("fin_results") or {}

    assets_sum = (balances.get("sum") or {})
    liabilities_sum = (liabilities.get("sum") or {})

    # Net profit may be in fin_results under indicators; try common codes
    fin_indicators = (fin_results.get("indicators") or [])
    net_profit_by_year: Dict[str, Any] = {}
    for ind in fin_indicators:
        code = ind.get("code")
        if code in ("2400", "2400/ЧП", "ЧП") or (ind.get("name") or "").lower().startswith("чистая прибыль"):
            sums = ind.get("sum") or {}
            net_profit_by_year.update(sums)

    revenue_by_year: Dict[str, Any] = {}
    for ind in fin_indicators:
        code = ind.get("code")
        if code in ("2110", "Выручка") or (ind.get("name") or "").lower().startswith("выручка"):
            sums = ind.get("sum") or {}
            revenue_by_year.update(sums)

    for y in years:
        y_str = str(y)
        snapshots.append(
            FinanceSnapshot(
                period=y_str,
                revenue=_to_decimal(revenue_by_year.get(y_str)),
                net_profit=_to_decimal(net_profit_by_year.get(y_str)),
                assets=_to_decimal((assets_sum or {}).get(y_str)),
                equity=None,
                liabilities_short=None,
                liabilities_long=None,
                source="DataNewton",
            )
        )

    return snapshots


