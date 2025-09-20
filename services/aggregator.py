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
    map_contracts_ofdata,
    map_inspections_ofdata,
    map_enforcements_ofdata,
    map_paid_taxes_ofdata,
    CompanyCard,
    FinanceSnapshot,
    ArbitrationSummary,
    ContractsSummary,
    InspectionsSummary,
    EnforcementsSummary,
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
    from core.logger import setup_logging
    log = setup_logging()
    log.info("fetch_company_profile: starting", input_str=input_str)
    
    # OFData only
    user_source = "ofdata"
    provider = get_provider()
    
    # Detect if input is INN/OGRN
    kind, value = _detect_id_kind(input_str)
    
    if kind:
        # Direct INN/OGRN lookup
        inn = value if kind == "inn" else None
        ogrn = value if kind == "ogrn" else None
    else:
        # Try name search via OFData
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
        
        # Get financial data with caching (prefer OGRN for better data availability)
        try:
            raw_finance = await get_cached(user_source, "finance", identifier)
            if raw_finance is None:
                raw_finance = provider.get_finance(inn=inn, ogrn=ogrn)
                await set_cached(user_source, "finance", identifier, raw_finance)
            
            finances = map_finance_ofdata(raw_finance)
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            logger.warning("Finance data unavailable: %s", e)
            finances = []
        
        # Get paid taxes data with caching
        try:
            raw_taxes = await get_cached(user_source, "paid_taxes", identifier)
            if raw_taxes is None:
                raw_taxes = provider.get_paid_taxes(inn=inn, ogrn=ogrn)
                await set_cached(user_source, "paid_taxes", identifier, raw_taxes)
            taxes = map_paid_taxes_ofdata(raw_taxes)
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            log.warning("Paid taxes data unavailable: %s", e)
            taxes = []
        
        # Get company tax information
        try:
            log.info("fetch_company_profile: starting company_taxes fetch", inn=inn, kpp=card.kpp)
            company_taxes = await get_cached(user_source, "company_taxes", identifier)
            if company_taxes is None:
                log.info("fetch_company_profile: company_taxes cache miss, calling API")
                company_taxes = provider.fetch_company_taxes(inn=inn, kpp=card.kpp)
                await set_cached(user_source, "company_taxes", identifier, company_taxes)
            else:
                log.info("fetch_company_profile: company_taxes cache hit")
            
            log.info("company_taxes: raw received", 
                     type=type(company_taxes).__name__,
                     keys=list(company_taxes.keys()) if isinstance(company_taxes, dict) else None)
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            log.warning("Company taxes data unavailable: %s", e)
            company_taxes = None
        
        # Get arbitration data with caching
        try:
            log.info("fetch_company_profile: starting arbitration fetch", inn=inn, ogrn=ogrn)
            raw_arbitration = await get_cached(user_source, "arbitration", identifier)
            if raw_arbitration is None:
                log.info("fetch_company_profile: arbitration cache miss, calling API")
                raw_arbitration = provider.get_arbitration_cases(inn=inn, ogrn=ogrn)
                await set_cached(user_source, "arbitration", identifier, raw_arbitration)
            else:
                log.info("fetch_company_profile: arbitration cache hit")
            
            log.info("arbitration: raw received", 
                     type=type(raw_arbitration).__name__,
                     keys=list(raw_arbitration.keys()) if isinstance(raw_arbitration, dict) else None)
            arbitration = map_arbitration_ofdata(raw_arbitration)
            log.info("arbitration: mapped", total=getattr(arbitration, 'total', None),
                     cases_count=len(getattr(arbitration, 'cases', []) or []))
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            log.warning("Arbitration data unavailable: %s", e)
            arbitration = ArbitrationSummary(total=0, cases=[])
        except Exception as e:
            log.error("Arbitration error: %s", e)
            arbitration = ArbitrationSummary(total=0, cases=[])

        # Get contracts data with caching
        try:
            log.info("fetch_company_profile: starting contracts fetch", inn=inn, ogrn=ogrn)
            raw_contracts = await get_cached(user_source, "contracts", identifier)
            if raw_contracts is None:
                log.info("fetch_company_profile: contracts cache miss, calling API")
                raw_contracts = provider.get_contracts(inn=inn, ogrn=ogrn, law="44", page=1, limit=20, sort="-date")
                await set_cached(user_source, "contracts", identifier, raw_contracts)
            else:
                log.info("fetch_company_profile: contracts cache hit")
            
            log.info("contracts: raw received",
                     type=type(raw_contracts).__name__,
                     keys=list(raw_contracts.keys()) if isinstance(raw_contracts, dict) else None,
                     data_keys=list((raw_contracts.get('data') or {}).keys()) if isinstance(raw_contracts, dict) else None,
                     total=(raw_contracts.get('data') or {}).get('ЗапВсего') if isinstance(raw_contracts, dict) else None,
                     records_len=len((raw_contracts.get('data') or {}).get('Записи') or []) if isinstance(raw_contracts, dict) else None)
            contracts = map_contracts_ofdata(raw_contracts)
            log.info("contracts: mapped", total=getattr(contracts, 'total', None),
                     items_count=len(getattr(contracts, 'items', []) or []))
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            log.warning("Contracts data unavailable: %s", e)
            contracts = None
        except Exception as e:
            log.error("Contracts error: %s", e)
            contracts = None

        # Get inspections data with caching
        try:
            raw_insp = await get_cached(user_source, "inspections", identifier)
            if raw_insp is None:
                raw_insp = provider.get_inspections(inn=inn, ogrn=ogrn, sort="-date", limit=20)
                await set_cached(user_source, "inspections", identifier, raw_insp)
            inspections = map_inspections_ofdata(raw_insp)
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            logger.warning("Inspections data unavailable: %s", e)
            inspections = None

        # Get enforcements data with caching
        try:
            raw_enf = await get_cached(user_source, "enforcements", identifier)
            if raw_enf is None:
                raw_enf = provider.get_enforcements(inn=inn, ogrn=ogrn, sort="-date", limit=20)
                await set_cached(user_source, "enforcements", identifier, raw_enf)
            enforcements = map_enforcements_ofdata(raw_enf)
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            logger.warning("Enforcements data unavailable: %s", e)
            enforcements = None
        
        result = {
            "base": card,
            "finances": finances,
            "taxes": taxes,
            "company_taxes": company_taxes,
            "arbitration": arbitration,
            "contracts": contracts,
            "inspections": inspections,
            "enforcements": enforcements,
            "sources": _fmt_sources()
        }
        
        log.info("fetch_company_profile: completed successfully", 
                    has_base=bool(result.get("base")),
                    finances_count=len(result.get("finances", [])),
                    arbitration_total=getattr(result.get("arbitration"), 'total', 0) if result.get("arbitration") else 0)
        
        return result
        
    except (OFDataClientError, OFDataServerTemporaryError) as e:
        log.error("Provider error: %s", e)
        return {
            "error": f"Ошибка получения данных: {e}",
            "sources": _fmt_sources()
        }


def _fmt_status(card: CompanyCard) -> str:
    from core.logger import setup_logging
    log = setup_logging()
    
    code = card.status_code or "UNKNOWN"
    txt = card.status_text or ""
    
    log.info("_fmt_status: processing status", 
            status_code=code,
            status_text=txt,
            card_inn=card.inn)
    
    mapping = {
        "ACTIVE": "✅ Действует",
        "LIQUIDATED": "⛔ Прекращена",
        "NOT_ACTIVE": "⚠️ Не действует",
        "UNKNOWN": "❓ Неизвестно",
    }
    base = mapping.get(code, "❓ Неизвестно")
    if txt and txt not in base:
        result = f"{base} ({txt})"
        log.info("_fmt_status: combined status", result=result)
        return result
    log.info("_fmt_status: base status", result=base)
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
        liab_long = format_amount(f.long_term_liabilities) if f.long_term_liabilities is not None else "N/A"
        liab_short = format_amount(f.short_term_liabilities) if f.short_term_liabilities is not None else "N/A"
        lines.append(f"{f.period}: выручка {rev}, прибыль {prof}, активы {assets}, капитал {equity}, долг.обяз. {liab_long}, кратк.обяз. {liab_short}")
    return "\n".join(lines)


def _fmt_contracts(contracts: ContractsSummary | None) -> str:
    if not contracts or contracts.total == 0 or not contracts.items:
        return "нет данных"
    lines = [f"Всего контрактов: {contracts.total}"]
    for it in contracts.items[:20]:
        price = format_amount(it.price) if it.price is not None else "—"
        parts = [it.number]
        if it.date:
            parts.append(it.date)
        if it.customer:
            parts.append(it.customer)
        parts.append(f"цена {price}")
        if it.eis_url:
            parts.append(it.eis_url)
        lines.append(" — ".join(parts))
    return "\n".join(lines)


def _fmt_inspections(ins: InspectionsSummary | None) -> str:
    if not ins or ins.total == 0 or not ins.items:
        return "нет данных"
    lines = [f"Всего проверок: {ins.total}"]
    for it in ins.items[:20]:
        parts = [it.number]
        if it.date_start:
            parts.append(it.date_start)
        if it.type:
            parts.append(it.type)
        if it.status:
            parts.append(it.status)
        if it.controller:
            parts.append(it.controller)
        if it.address:
            parts.append(it.address)
        lines.append(" — ".join(parts))
    return "\n".join(lines)


def _fmt_enforcements(enf: EnforcementsSummary | None) -> str:
    if not enf or (enf.total == 0 and not enf.items):
        return "нет данных"
    header = []
    header.append(f"Всего ИП: {enf.total}")
    if enf.total_amount is not None:
        header.append(f"сумма {format_amount(enf.total_amount)}")
    if enf.remainder_amount is not None:
        header.append(f"остаток {format_amount(enf.remainder_amount)}")
    lines = [", ".join(header)]
    for it in (enf.items or [])[:20]:
        parts = [it.number]
        if it.date:
            parts.append(it.date)
        if it.doc_type:
            parts.append(it.doc_type)
        if it.subject:
            parts.append(it.subject)
        if it.amount is not None:
            parts.append(f"сумма {format_amount(it.amount)}")
        if it.remainder is not None:
            parts.append(f"остаток {format_amount(it.remainder)}")
        lines.append(" — ".join(parts))
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


def _fmt_company_taxes(tax_data: Dict[str, Any] | None) -> str:
    """Format company tax information for Telegram message."""
    from utils.formatting import format_rub
    from core.logger import setup_logging
    log = setup_logging()
    
    log.info("_fmt_company_taxes: processing tax data", 
             tax_data_type=type(tax_data).__name__,
             tax_data_keys=list(tax_data.keys()) if isinstance(tax_data, dict) else None)
    
    if not tax_data:
        return (
            "<b>Налоги</b>\n"
            "• Режимы: <code>—</code>\n"
            "• Уплачено (год —): <code>—</code>\n"
            "• Недоимка на —: <code>—</code>"
        )
    
    # Format regimes
    regimes = tax_data.get("regimes", [])
    regimes_str = ", ".join(regimes) if regimes else "—"
    
    # Format paid total and year
    paid_total = format_rub(tax_data.get("paid_total"))
    paid_year = tax_data.get("paid_year") or "—"
    
    # Format arrears
    arrears_total = format_rub(tax_data.get("arrears_total"))
    arrears_date = tax_data.get("arrears_date") or "—"
    
    result = [
        "<b>Налоги</b>",
        f"• Режимы: <code>{regimes_str}</code>",
        f"• Уплачено (год {paid_year}): <code>{paid_total}</code>",
        f"• Недоимка на {arrears_date}: <code>{arrears_total}</code>"
    ]
    
    # Add top 5 paid items if available
    paid_items = tax_data.get("paid_items", [])
    if paid_items:
        # Sort by amount descending and take top 5
        sorted_items = sorted(paid_items, key=lambda x: x.get("amount", 0), reverse=True)[:5]
        for item in sorted_items:
            name = item.get("name", "—")
            amount = format_rub(item.get("amount"))
            result.append(f"— {name}: <code>{amount}</code>")
    
    return "\n".join(result)


def _fmt_arbitration(ar: ArbitrationSummary) -> str:
    if ar.total == 0 or not ar.cases:
        return "Нет дел"
    lines = [f"Всего дел: {ar.total}"]
    for c in ar.cases[:20]:
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


def build_markdown_report(card, finances, taxes, arbitr, contracts: ContractsSummary | None = None, inspections: InspectionsSummary | None = None, enforcements: EnforcementsSummary | None = None, company_taxes: Dict[str, Any] | None = None) -> str:
    from core.logger import setup_logging
    log = setup_logging()
    log.info("build_markdown_report: starting", 
                card_name=getattr(card, 'name_full', 'Unknown'),
                finances_count=len(finances) if finances else 0,
                taxes_count=len(taxes) if taxes else 0,
                arbitration_total=getattr(arbitr, 'total', 0) if arbitr else 0)
    
    # Адрес/ОКВЭД/руководитель могут отсутствовать — аккуратно отрисовываем
    address = card.address or "—"
    okved = card.okved or "—"
    head = f"{card.manager_name} — {card.manager_post}" if (card.manager_name or card.manager_post) else "—"

    msme_line = "—"
    if card.is_msme is True:
        msme_line = "✅ Является субъектом МСП (малое/среднее предприятие)"
    elif card.is_msme is False:
        msme_line = "❌ Не является субъектом МСП"

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    md = []
    # Заголовок с названием компании
    company_title = card.name_full
    if card.name_short and card.name_short != card.name_full:
        company_title = f"{card.name_full} • {card.name_short}"
    md.append(f"🧾 {company_title} — {today}")
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
    else:
        md.append("⚠️ **Особые отметки**")
        md.append("Нет особых отметок")
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

    # Госзакупки
    md.append("🛒 **Госзакупки**")
    md.append(_fmt_contracts(contracts))
    md.append("")

    # Проверки
    md.append("🔎 **Проверки**")
    md.append(_fmt_inspections(inspections))
    md.append("")

    # Исполнительные производства
    md.append("⚖️ **Исполнительные производства**")
    md.append(_fmt_enforcements(enforcements))
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
        log.info("build_markdown_report: generating gamma section", 
                company_name=card.name_full,
                official_links_count=len(official_links))
        gamma_md = generate_gamma_section(company_dict, official_links)
        log.info("build_markdown_report: gamma section generated", 
                gamma_md_length=len(gamma_md) if gamma_md else 0,
                gamma_md_preview=gamma_md[:200] if gamma_md else None)
        if gamma_md:
            md.append("### 🌐 Дополнительно (для Gamma)")
            md.append(gamma_md)
            md.append("")
        else:
            log.warning("build_markdown_report: gamma section is empty")
    except Exception as e:
        # Если обогащение недоступно — продолжаем без ошибки
        log.error("build_markdown_report: gamma section error", error=str(e))
        pass

    # Налоговая информация
    log.info("build_markdown_report: processing company_taxes", 
             company_taxes_type=type(company_taxes).__name__,
             company_taxes_keys=list(company_taxes.keys()) if isinstance(company_taxes, dict) else None)
    if company_taxes:
        md.append("")
        md.append(_fmt_company_taxes(company_taxes))
    
    # Дисклеймер
    md.append("")
    md.append("Данные собраны из официальных открытых реестров РФ (ЕГРЮЛ/Росстат, ФНС — ГИР БО, КАД).")
    
    result = "\n".join(md)
    log.info("build_markdown_report: completed", 
                result_length=len(result),
                result_preview=result[:200] if result else None)
    
    return result


async def fetch_company_report_markdown(query: str) -> str:
    """Generate markdown report for company"""
    from core.logger import setup_logging
    log = setup_logging()
    log.info("fetch_company_report_markdown: starting", query=query)
    
    try:
        profile = await fetch_company_profile(query)
        log.info("fetch_company_report_markdown: profile fetched", 
                    has_error="error" in profile,
                    profile_keys=list(profile.keys()) if isinstance(profile, dict) else None)
    except Exception as e:
        log.error("fetch_company_report_markdown: error in fetch_company_profile", error=str(e), query=query)
        return f"❌ Ошибка при получении данных: {str(e)}"
    
    if "error" in profile:
        log.warning("fetch_company_report_markdown: profile has error", error=profile["error"])
        return profile["error"]
    
    log.info("fetch_company_report_markdown: building markdown report")
    result = build_markdown_report(
        profile["base"],
        profile["finances"], 
        profile["taxes"],
        profile["arbitration"],
        profile.get("contracts"),
        profile.get("inspections"),
        profile.get("enforcements"),
        profile.get("company_taxes"),
    )
    
    log.info("fetch_company_report_markdown: markdown report built", 
                result_length=len(result),
                result_preview=result[:200] if result else None)
    
    return result
