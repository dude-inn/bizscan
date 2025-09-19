# -*- coding: utf-8 -*-
"""
OpenAI-powered Gamma.app section generator for company enrichment
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from openai import OpenAI

DEFAULT_MODEL = os.getenv("OPENAI_MODEL_GAMMA", "gpt-4o-mini")

# Логирование
import logging
log = logging.getLogger(__name__)

def _log_openai_status():
    """Логирует статус OpenAI API"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    log.info("=== OpenAI API Status ===")
    log.info(f"OpenAI API Key: {'✅ Set' if api_key else '❌ Not set'}")
    log.info(f"Model: {DEFAULT_MODEL}")
    if not api_key:
        log.warning("⚠️ OpenAI API key not set - Gamma enrichment will be disabled")

# Логируем при импорте модуля
_log_openai_status()

SYSTEM_PROMPT = """\
Ты — аналитик. Составь краткий блок для презентации Gamma.app ТОЛЬКО из переданных данных карточки компании.
Запрещено придумывать факты. Используй только то, что есть в карточке и официальных источниках.
Формат:
— Абзац (2–4 строки): деятельность (по ОКВЭД), местоположение (адрес/регион), форма (ОПФ/статус).
— 3–6 маркеров: капитал и собственники; налоговый режим; численность работников; контакты; правопреемство; негативные списки (если есть).
— Строка «Источники»: список официальных ссылок (макс 4).
Стиль: нейтральный, лаконичный.
"""

def build_user_prompt(company: Dict[str, Any], official_links: List[str]) -> str:
    name = company.get("name_full") or company.get("name") or ""
    inn = company.get("inn") or ""
    ogrn = company.get("ogrn") or ""
    okved = company.get("okved") or ""
    opf = company.get("opf") or company.get("org_form") or ""
    status_code = company.get("status_code") or company.get("status") or ""
    status_text = company.get("status_text") or ""
    reg_date = company.get("registration_date") or company.get("date_reg") or ""
    address = company.get("address") or ""
    head_name = company.get("manager_name") or company.get("head_name") or ""
    head_post = company.get("manager_post") or company.get("head_post") or ""
    charter_capital = company.get("charter_capital") or company.get("ustavnyi_kapital")
    owners = company.get("owners") or []
    tax_mode = company.get("tax_mode") or company.get("osob_rezhim")
    workers_count = company.get("workers_count") or company.get("СЧР")
    contacts = company.get("contacts") or {}
    emails = []
    phones = []
    if isinstance(contacts, dict):
        emails = contacts.get("emails") or contacts.get("email") or []
        phones = contacts.get("phones") or contacts.get("tel") or []
        if isinstance(emails, str):
            emails = [emails]
        if isinstance(phones, str):
            phones = [phones]
    predecessors = company.get("predecessors") or company.get("правопредш") or []
    successors = company.get("successors") or company.get("правопреем") or []
    negative_lists = company.get("negative_lists") or company.get("негативные_списки") or []
    finances = company.get("finances_digest") or company.get("finances")

    header = f"{name} (ИНН {inn}, ОГРН {ogrn})"
    lines = [header]
    if okved:
        lines.append(f"ОКВЭД: {okved}")
    if opf or status_code or status_text:
        st = status_text or status_code
        lines.append(f"ОПФ/статус: {opf or '-'} / {st or '-'}")
    if reg_date:
        lines.append(f"Дата регистрации: {reg_date}")
    if address:
        lines.append(f"Адрес: {address}")
    if head_name or head_post:
        lines.append(f"Руководитель: {(head_name or '-') + (' — ' + head_post if head_post else '')}")
    if charter_capital is not None:
        lines.append(f"Уставный капитал: {charter_capital}")
    if owners:
        try:
            owner_names = ", ".join([o.get("name") or o.get("НаимПолн") or "?" for o in owners if isinstance(o, dict)])
        except Exception:
            owner_names = ", ".join(map(str, owners))
        if owner_names:
            lines.append(f"Собственники: {owner_names}")
    if tax_mode:
        lines.append(f"Налоговый режим: {tax_mode}")
    if workers_count:
        lines.append(f"СЧР: {workers_count}")
    if emails:
        lines.append(f"Email: {', '.join(emails[:3])}")
    if phones:
        lines.append(f"Тел: {', '.join(phones[:3])}")
    if predecessors:
        lines.append("Правопредшественники: да")
    if successors:
        lines.append("Правопреемники: да")
    if negative_lists:
        lines.append("Негативные списки: да")
    if finances and isinstance(finances, dict):
        # ожидаемые поля: last_year, revenue, profit, assets, equity (если заранее подготовлено)
        parts = []
        for k in ("last_year", "revenue", "profit", "assets", "equity"):
            if finances.get(k) is not None:
                parts.append(f"{k}:{finances.get(k)}")
        if parts:
            lines.append("Финансы (дайджест): " + "; ".join(parts))

    lines.append("")
    lines.append("### Официальные ссылки")
    if official_links:
        for url in official_links[:4]:
            lines.append(f"- {url}")
    else:
        lines.append("- ЕГРЮЛ (ФНС)")
        lines.append("- ГИР БО (ФНС)")
        lines.append("- КАД")

    return "\n".join(lines)

def generate_gamma_section(company: Dict[str, Any], official_links: List[str], *, model: Optional[str] = None) -> str:
    log.info(f"🤖 Generating Gamma section for: {company.get('name_full', 'Unknown')}")
    log.info(f"🔗 Official links: {len(official_links)}")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.warning("❌ OpenAI API key not set, using fallback")
        # fallback
        parts = [f"**{company.get('name_full') or company.get('name') or 'Компания'}**"]
        if official_links:
            parts.append("**Источники:** " + ", ".join(official_links[:4]))
        else:
            parts.append("**Источники:** ЕГРЮЛ (ФНС); ГИР БО (ФНС); КАД")
        return "\n\n".join(parts)
    
    try:
        log.info("🔧 Initializing OpenAI client")
        client = OpenAI(api_key=api_key)
        mdl = model or DEFAULT_MODEL
        log.info(f"📝 Building prompt for model: {mdl}")
        
        user_prompt = build_user_prompt(company, official_links)
        log.info(f"📏 Prompt length: {len(user_prompt)} characters")
        
        log.info("🚀 Sending request to OpenAI")
        resp = client.chat.completions.create(
            model=mdl,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=700,
        )
        
        result = resp.choices[0].message.content.strip()
        log.info(f"✅ OpenAI response received: {len(result)} characters")
        return result
        
    except Exception as e:
        log.error(f"❌ OpenAI generation failed: {e}")
        # Fallback to simple format
        parts = [f"**{company.get('name_full') or company.get('name') or 'Компания'}**"]
        parts.append(f"_Ошибка генерации: {str(e)}_")
        if official_links:
            parts.append("**Источники:** " + ", ".join(official_links[:4]))
        return "\n\n".join(parts)
