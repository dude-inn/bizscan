# services/aggregator.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from services.providers.datanewton import DataNewtonClient, DNClientError, DNServerTemporaryError
from services.mappers.datanewton import (
    map_counterparty,
    map_finance,
    map_paid_taxes,
    map_arbitration,
    CompanyCard,
    FinanceSnapshot,
    ArbitrationSummary,
)
from utils.formatting import format_amount  # сделай helper: Decimal -> '1 234 567₽' (или подключи свой)
from utils.log import logger  # твой логгер; если нет — замени на logging.getLogger(__name__)
import re


def _detect_id_kind(s: str) -> Tuple[str, str]:
    """Возвращает ('inn'|'ogrn', value) или ('', '') если невалидно."""
    s = re.sub(r"\D+", "", s or "")
    if re.fullmatch(r"\d{10}|\d{12}", s):
        return "inn", s
    if re.fullmatch(r"\d{13}|\d{15}", s):
        return "ogrn", s
    return "", ""


def _fmt_status(card: CompanyCard) -> str:
    code = card.status_code or "UNKNOWN"
    txt = card.status_text or ""
    mapping = {
        "ACTIVE": "✅ Действует",
        "LIQUIDATED": "⛔ Прекращена",
        "NOT_ACTIVE": "⚠️ Не действует",
        "UNKNOWN": "❓ Неизвестно",
    }
    base = mapping.get(code, "❓ Неизвестно")
    if txt and txt not in base:
        return f"{base} ({txt})"
    return base


def _fmt_finances(fin_list: list[FinanceSnapshot]) -> str:
    if not fin_list:
        return "нет данных"
    lines = []
    # упорядочим по году возрастанию
    fin_list = sorted(fin_list, key=lambda x: x.period)
    for f in fin_list:
        rev = format_amount(f.revenue) if f.revenue is not None else "N/A"
        prof = format_amount(f.net_profit) if f.net_profit is not None else "N/A"
        assets = format_amount(f.assets) if f.assets is not None else "N/A"
        lines.append(f"{f.period}: выручка {rev}, прибыль {prof}, активы {assets}")
    return "\n".join(lines)


def _fmt_paid_taxes(items) -> str:
    if not items:
        return "нет данных"
    out = []
    for it in items:
        if not it.items:
            # дата есть — но список пуст
            out.append(f"{it.report_date}: —")
            continue
        lines = "; ".join([f"{name} {format_amount(val)}" for name, val in it.items])
        if it.report_date:
            out.append(f"{it.report_date}: {lines}")
        else:
            out.append(lines)
    return "\n".join(out)


def _fmt_arbitration(ar: ArbitrationSummary) -> str:
    if ar.total == 0 or not ar.cases:
        return "Нет дел"
    lines = [f"Всего дел: {ar.total}"]
    for c in ar.cases:
        parts = [c.number]
        if c.date_start:
            parts.append(c.date_start)
        if c.role:
            parts.append(c.role)
        if c.claim_sum is not None:
            parts.append(f"сумма {format_amount(c.claim_sum)}")
        if c.court:
            parts.append(c.court)
        lines.append(" — ".join(parts))
    return "\n".join(lines)


def _fmt_sources() -> str:
    # Без упоминания посредника. Только официальные источники.
    return (
        "ЕГРЮЛ/Росстат; Бухгалтерская отчётность (ФНС ГИР БО); "
        "ФНС — данные об уплате налогов; Картотека арбитражных дел"
    )


def build_markdown_report(card, finances, taxes, arbitr) -> str:
    # Адрес/ОКВЭД/руководитель могут отсутствовать — аккуратно отрисовываем
    address = card.address or "—"
    okved = card.okved or "—"
    head = f"{card.manager_name} — {card.manager_post}" if (card.manager_name or card.manager_post) else "—"

    msme_line = "—"
    if card.is_msme is True:
        msme_line = "Является субъектом МСП"
    elif card.is_msme is False:
        msme_line = "Не является субъектом МСП"

    md = []
    md.append("🧾 **Реквизиты**")
    short = f' • {card.name_short}' if card.name_short else ""
    md.append(f'{card.name_full}{short}')
    md.append(f'ИНН {card.inn} • ОГРН {card.ogrn or "—"}{f" • КПП {card.kpp}" if card.kpp else ""}')
    if card.registration_date:
        md.append(f"📅 Регистрация: {card.registration_date}")
    md.append(f"**Статус:** {_fmt_status(card)}")
    md.append(f"📍 **Адрес:** {address}")
    md.append(f"🏷️ **ОКВЭД:** {okved}")
    md.append("")
    md.append("🧑‍💼 **Руководитель**")
    md.append(head)
    md.append("")
    md.append("🧩 **МСП**")
    md.append(msme_line)
    md.append("")
    md.append("📊 **Финансы**")
    md.append(_fmt_finances(finances))
    md.append("")
    md.append("💰 **Уплаченные налоги**")
    md.append(_fmt_paid_taxes(taxes))
    md.append("")
    md.append("📄 **Арбитраж**")
    md.append(_fmt_arbitration(arbitr))
    md.append("")
    md.append("🔗 **Источники:** " + _fmt_sources())
    return "\n".join(md)


def fetch_company_report_markdown(query: str) -> str:
    kind, value = _detect_id_kind(query)
    if not kind:
        return "Укажите корректный ИНН (10/12) или ОГРН (13/15)."

    client = DataNewtonClient()

    inn = value if kind == "inn" else None
    ogrn = value if kind == "ogrn" else None

    # 1) Карточка
    try:
        raw_card = client.get_counterparty(inn=inn, ogrn=ogrn)
    except DNClientError as e:
        logger.warning("counterparty client error: %s", e)
        return f"Ошибка запроса карточки: {e}"
    except DNServerTemporaryError as e:
        logger.warning("counterparty server temp error: %s", e)
        raw_card = {}

    card = map_counterparty(raw_card) if raw_card else CompanyCard(
        inn=value, ogrn=None, kpp=None, name_full=value, name_short=None,
        registration_date=None, status_code="UNKNOWN", status_text=None,
        address=None, manager_name=None, manager_post=None, okved=None, is_msme=None
    )

    # 2) Финансы
    finances = []
    try:
        raw_fin = client.get_finance(inn=inn, ogrn=ogrn)
        finances = map_finance(raw_fin)
    except (DNClientError, DNServerTemporaryError) as e:
        logger.warning("finance error: %s", e)

    # 3) Налоги
    taxes = []
    try:
        raw_tax = client.get_paid_taxes(inn=inn, ogrn=ogrn)
        taxes = map_paid_taxes(raw_tax)
    except (DNClientError, DNServerTemporaryError) as e:
        logger.warning("paidTaxes error: %s", e)

    # 4) Арбитраж
    arbitr = None
    try:
        raw_arb = client.get_arbitration_cases(inn=inn, ogrn=ogrn, limit=1000, offset=0)
        arbitr = map_arbitration(raw_arb, limit=10)
    except (DNClientError, DNServerTemporaryError) as e:
        logger.warning("arbitration error: %s", e)
        arbitr = map_arbitration({"total_cases": 0, "data": []})

    return build_markdown_report(card, finances, taxes, arbitr)
