# services/aggregator.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple, Dict, Any

from services.providers.base import CompanyProvider
from services.providers.ofdata import OFDataClient, OFDataClientError, OFDataServerTemporaryError
from services.mappers.ofdata import (
    map_company_ofdata,
    map_finance_ofdata,
    map_arbitration_ofdata,
    CompanyCard,
    FinanceSnapshot,
    ArbitrationSummary,
)
from utils.formatting import format_amount  # сделай helper: Decimal -> '1 234 567₽' (или подключи свой)
from utils.log import logger  # твой логгер; если нет — замени на logging.getLogger(__name__)
import re


def get_provider() -> CompanyProvider:
    """Return OFData provider only (DataNewton disabled)."""
    from services.providers.ofdata import API_KEY
    if not API_KEY or API_KEY == "your_ofdata_api_key_here":
        raise OFDataClientError("OFData selected but OFDATA_KEY is not configured")
    logger.info("🔍 Using OFData provider")
    return OFDataClient()


def _detect_id_kind(s: str) -> Tuple[str, str]:
    """Возвращает ('inn'|'ogrn', value) или ('', '') если невалидно."""
    s = re.sub(r"\D+", "", s or "")
    if re.fullmatch(r"\d{10}|\d{12}", s):
        return "inn", s
    if re.fullmatch(r"\d{13}|\d{15}", s):
        return "ogrn", s
    return "", ""


async def fetch_company_profile(input_str: str) -> Dict[str, Any]:
    """
    Fetch complete company profile by INN/OGRN or name query
    
    Args:
        input_str: INN, OGRN, or company name
        
    Returns:
        Dict with company data and sources
    """
    # OFData only
    user_source = "ofdata"
    
    # Detect if input is INN/OGRN
    kind, value = _detect_id_kind(input_str)
    
    if kind:
        # Direct INN/OGRN lookup
        inn = value if kind == "inn" else None
        ogrn = value if kind == "ogrn" else None
    else:
        # Try name search via OFData
        provider = get_provider()
        inn, ogrn = provider.resolve_by_query(input_str)
        
        if not inn and not ogrn:
            return {
                "error": "Компания не найдена. Уточните название или введите ИНН/ОГРН",
                "sources": _fmt_sources()
            }
    
    # Fetch data from provider
    provider = get_provider()
    
    try:
        # Get counterparty data with caching
        identifier = inn or ogrn
        cache_key = f"counterparty:{identifier}"
        
        # Try cache first
        from services.cache import get_cached, set_cached
        raw_card = await get_cached(user_source, "counterparty", identifier)
        
        if raw_card is None:
            # Cache miss - fetch from provider
            raw_card = provider.get_counterparty(inn=inn, ogrn=ogrn)
            await set_cached(user_source, "counterparty", identifier, raw_card)
        
        # Map using OFData mapper
        card = map_company_ofdata(raw_card)
        
        # Get financial data with caching
        try:
            raw_finance = await get_cached(user_source, "finance", identifier)
            if raw_finance is None:
                raw_finance = provider.get_finance(inn=inn, ogrn=ogrn)
                await set_cached(user_source, "finance", identifier, raw_finance)
            
            finances = map_finance_ofdata(raw_finance)
        except (DNClientError, DNServerTemporaryError, OFDataClientError, OFDataServerTemporaryError) as e:
            logger.warning("Finance data unavailable: %s", e)
            finances = []
        
        # Get paid taxes data with caching
        try:
            raw_taxes = await get_cached(user_source, "paid_taxes", identifier)
            if raw_taxes is None:
                raw_taxes = provider.get_paid_taxes(inn=inn, ogrn=ogrn)
                await set_cached(user_source, "paid_taxes", identifier, raw_taxes)
            
            # OFData may not support paid taxes - skip silently
            taxes = []
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            logger.warning("Paid taxes data unavailable: %s", e)
            taxes = []
        
        # Get arbitration data with caching
        try:
            raw_arbitration = await get_cached(user_source, "arbitration", identifier)
            if raw_arbitration is None:
                raw_arbitration = provider.get_arbitration_cases(inn=inn, ogrn=ogrn)
                await set_cached(user_source, "arbitration", identifier, raw_arbitration)
            
            arbitration = map_arbitration_ofdata(raw_arbitration)
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            logger.warning("Arbitration data unavailable: %s", e)
            arbitration = ArbitrationSummary(total=0, cases=[])
        
        return {
            "base": card,
            "finances": finances,
            "taxes": taxes,
            "arbitration": arbitration,
            "sources": _fmt_sources()
        }
        
    except (OFDataClientError, OFDataServerTemporaryError) as e:
        logger.error("Provider error: %s", e)
        return {
            "error": f"Ошибка получения данных: {e}",
            "sources": _fmt_sources()
        }


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
    # показываем только последние 5 периодов
    if len(fin_list) > 5:
        fin_list = fin_list[-5:]
    for f in fin_list:
        rev = format_amount(f.revenue) if f.revenue is not None else "N/A"
        prof = format_amount(f.net_profit) if f.net_profit is not None else "N/A"
        assets = format_amount(f.assets) if f.assets is not None else "N/A"
        equity = format_amount(f.equity) if f.equity is not None else "N/A"
        liab_long = format_amount(f.liabilities_long) if f.liabilities_long is not None else "N/A"
        liab_short = format_amount(f.liabilities_short) if f.liabilities_short is not None else "N/A"
        lines.append(f"{f.period}: выручка {rev}, прибыль {prof}, активы {assets}, капитал {equity}, долг.обяз. {liab_long}, кратк.обяз. {liab_short}")
    return "\n".join(lines)


def _fmt_contacts(card: CompanyCard) -> str:
    contacts = getattr(card, "contacts", {}) or {}
    if not isinstance(contacts, dict):
        return "—"
    site = contacts.get("site") or contacts.get("website")
    emails = contacts.get("emails") or contacts.get("email") or []
    phones = contacts.get("phones") or contacts.get("tel") or []
    if isinstance(emails, str):
        emails = [emails]
    if isinstance(phones, str):
        phones = [phones]
    # normalize possible dict items to strings
    def _to_str_list(items):
        out = []
        for it in items or []:
            if isinstance(it, dict):
                val = it.get("value") or it.get("email") or it.get("phone") or it.get("number") or it.get("display")
                if val:
                    out.append(str(val))
            else:
                out.append(str(it))
        return out
    emails = _to_str_list(emails)
    phones = _to_str_list(phones)
    parts = []
    if site:
        if isinstance(site, dict):
            site_val = site.get("value") or site.get("url") or site.get("site")
            if site_val:
                parts.append(str(site_val))
        else:
            parts.append(str(site))
    if emails:
        parts.append("email: " + ", ".join(emails[:3]))
    if phones:
        parts.append("тел: " + ", ".join(phones[:3]))
    return "; ".join(parts) if parts else "—"


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
    for c in ar.cases[:10]:
        parts = [c.number]
        if c.date_start:
            parts.append(c.date_start)
        if c.role:
            parts.append(c.role)
        if getattr(c, "amount", None) is not None:
            parts.append(f"сумма {format_amount(c.amount)}")
        # court: prefer first instance if list provided
        court_name = None
        if c.instances and isinstance(c.instances, (list, tuple)) and len(c.instances) > 0:
            court_name = c.instances[0]
        elif c.court:
            court_name = c.court
        if court_name:
            parts.append(court_name)
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

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    md = []
    md.append(f"🧾 {card.name_full} • {card.name_short or ''} — {today}")
    md.append("")
    md.append("**Реквизиты**")
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
    # Дополнительные данные (если есть)
    if getattr(card, "opf", None) or getattr(card, "charter_capital", None):
        opf = getattr(card, "opf", None) or "—"
        cap = format_amount(card.charter_capital) if getattr(card, "charter_capital", None) is not None else "—"
        md.append("🏢 **Орг. форма и капитал**")
        md.append(f"ОПФ: {opf}; Уставный капитал: {cap}")
        md.append("")
    if getattr(card, "owners", None):
        try:
            owners = card.owners or []
            owner_lines = []
            for o in owners[:5]:
                if not isinstance(o, dict):
                    continue
                name = o.get("name") or o.get("НаимПолн") or o.get("НаимСокр") or "—"
                share = None
                if o.get("Доля") and isinstance(o.get("Доля"), dict):
                    share = o["Доля"].get("Процент")
                share = share or o.get("share") or o.get("percent")
                if share is not None:
                    owner_lines.append(f"{name} — {share}%")
                else:
                    owner_lines.append(name)
            if owner_lines:
                md.append("👥 **Собственники**")
                md.append("; ".join(owner_lines))
                md.append("")
        except Exception:
            pass
    if getattr(card, "tax_mode", None) or getattr(card, "workers_count", None):
        md.append("🏛️ **Налоги и сотрудники**")
        md.append(f"Режим: {getattr(card, 'tax_mode', None) or '—'}; СЧР: {getattr(card, 'workers_count', None) or '—'}")
        md.append("")
    md.append("📞 **Контакты**")
    md.append(_fmt_contacts(card))
    md.append("")
    if getattr(card, "predecessors", None) or getattr(card, "successors", None) or getattr(card, "negative_lists", None):
        flags = []
        if getattr(card, "predecessors", None):
            flags.append("правопредшественники")
        if getattr(card, "successors", None):
            flags.append("правопреемники")
        neg = getattr(card, "negative_lists", None) or {}
        if isinstance(neg, dict) and any(bool(v) for v in neg.values()):
            flags.append("негативные списки")
        if flags:
            md.append("⚠️ **Особые отметки**")
            md.append(", ".join(flags))
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
    
    # Дополнительный блок для Gamma отправляется отдельным сообщением в хендлере
    
    # Добавляем блок для Gamma (описательная секция на основе карточки/реестров)
    try:
        from services.enrichment.official_sources import build_official_links
        from services.enrichment.openai_gamma_enricher import generate_gamma_section
        # Собираем базовые поля компании
        company_dict = {
            "name_full": card.name_full,
            "name": card.name_short,
            "inn": card.inn,
            "ogrn": card.ogrn,
            "okved": card.okved,
            "opf": getattr(card, "opf", None),
            "status_code": getattr(card, "status_code", None),
            "status_text": getattr(card, "status_text", None),
            "registration_date": getattr(card, "registration_date", None),
            "address": card.address,
            "manager_name": getattr(card, "manager_name", None),
            "manager_post": getattr(card, "manager_post", None),
            "charter_capital": getattr(card, "charter_capital", None),
            "owners": getattr(card, "owners", None),
            "tax_mode": getattr(card, "tax_mode", None),
            "workers_count": getattr(card, "workers_count", None),
            "contacts": getattr(card, "contacts", None),
            "predecessors": getattr(card, "predecessors", None),
            "successors": getattr(card, "successors", None),
            "negative_flags": getattr(card, "negative_lists", None),
        }
        # Финансы компакт: последний период
        fin_digest = {}
        if finances:
            last = sorted(finances, key=lambda x: x.period)[-1]
            fin_digest = {
                "last_year": last.period,
                "revenue": last.revenue,
                "profit": last.net_profit,
                "assets": last.assets,
                "equity": last.equity,
            }
        company_dict["finances_digest"] = fin_digest
        # Official links
        site = None
        if isinstance(getattr(card, "contacts", None), dict):
            c = card.contacts or {}
            site = c.get("site") or c.get("website")
            if isinstance(site, dict):
                site = site.get("value") or site.get("url") or site.get("site")
        official_links = build_official_links(card.inn, card.ogrn, site)
        gamma_md = generate_gamma_section(company_dict, official_links)
        if gamma_md:
            md.append("### 🌐 Дополнительно (для Gamma)")
            md.append(gamma_md)
            md.append("")
    except Exception:
        # Если обогащение недоступно — продолжаем без ошибки
        pass

    # Дисклеймер
    md.append("Данные собраны из официальных открытых реестров РФ (ЕГРЮЛ/Росстат, ФНС — ГИР БО, КАД).")
    return "\n".join(md)


async def fetch_company_report_markdown(query: str) -> str:
    """Generate markdown report for company"""
    profile = await fetch_company_profile(query)
    
    if "error" in profile:
        return profile["error"]
    
    return build_markdown_report(
        profile["base"],
        profile["finances"], 
        profile["taxes"],
        profile["arbitration"]
    )
