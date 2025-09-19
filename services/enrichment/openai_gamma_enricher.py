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
Ты — аналитик. На основе базовых реестровых данных и веб-сниппетов
собери блок для Gamma.app:
— абзац: краткая справка (деятельность, местоположение, рынок/продукты).
— список 3–6 фактов (новости, контракты, мощности, экспорт, участие государства).
— строка "Источники": 3–6 URL.
Тон нейтральный, фактический. Не придумывай; используй только сниппеты/данные.
"""

def build_user_prompt(company: Dict[str, Any], snippets: List[Dict[str, Any]]) -> str:
    name = company.get("name_full") or company.get("name") or ""
    inn = company.get("inn") or ""
    ogrn = company.get("ogrn") or ""
    okved = company.get("okved") or ""
    city = (company.get("address") or "").split(",")[0] if company.get("address") else ""
    header = f"{name} (ИНН {inn}, ОГРН {ogrn})"
    if okved:
        header += f"; ОКВЭД: {okved}"
    if city:
        header += f"; локация: {city}"
    lines = [header, "", "### Сниппеты"]
    for s in snippets:
        url = s.get("url", "")
        title = s.get("title", "") or url
        snippet = s.get("snippet", "")
        if snippet and len(snippet) > 400:
            snippet = snippet[:397] + "…"
        lines.append(f"- {title}\n  {snippet}\n  Источник: {url}")
    return "\n".join(lines)

def generate_gamma_section(company: Dict[str, Any], snippets: List[Dict[str, Any]], *, model: Optional[str] = None) -> str:
    log.info(f"🤖 Generating Gamma section for: {company.get('name_full', 'Unknown')}")
    log.info(f"📊 Snippets available: {len(snippets)}")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.warning("❌ OpenAI API key not set, using fallback")
        # fallback
        parts = [f"**{company.get('name_full') or company.get('name') or 'Компания'}**"]
        parts.append("_Добавьте OPENAI_API_KEY для генерации сводки._")
        if snippets:
            urls = [s.get("url", "") for s in snippets if s.get("url")]
            parts.append("**Источники:** " + ", ".join(set(urls)))
        return "\n\n".join(parts)
    
    try:
        log.info("🔧 Initializing OpenAI client")
        client = OpenAI(api_key=api_key)
        mdl = model or DEFAULT_MODEL
        log.info(f"📝 Building prompt for model: {mdl}")
        
        user_prompt = build_user_prompt(company, snippets)
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
        if snippets:
            urls = [s.get("url", "") for s in snippets if s.get("url")]
            parts.append("**Источники:** " + ", ".join(set(urls)))
        return "\n\n".join(parts)
