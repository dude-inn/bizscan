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
Ты — аналитик. Проведи поиск в интернете и найди информацию по компании.
Найди и предоставь:
- Общие сведения о компании
- История развития
- Значимые факты и достижения
- Текущая деятельность

Формат ответа:
— Краткое описание деятельности и местоположения
— 3-5 ключевых фактов о компании
— Источники информации

Стиль: нейтральный, информативный.
"""

def build_user_prompt(company: Dict[str, Any], official_links: List[str]) -> str:
    """Создает краткий промпт с основными данными компании для поиска в интернете"""
    name = company.get("name_full") or company.get("name") or ""
    inn = company.get("inn") or ""
    address = company.get("address") or ""
    
    # Создаем краткий промпт только с основными данными
    prompt = f"""Проведи поиск в интернете и найди информацию по компании:
- Название: {name}
- Адрес: {address}  
- ИНН: {inn}

Найди и предоставь:
- Общие сведения о компании
- История развития
- Значимые факты и достижения
- Текущая деятельность"""
    
    return prompt

def generate_gamma_section(company: Dict[str, Any], official_links: List[str], *, model: Optional[str] = None) -> str:
    log.info(f"🤖 Generating Gamma section for: {company.get('name_full', 'Unknown')}")
    # official_links should already be strings from build_official_links
    if not official_links:
        official_links = []
    # Ensure all are strings (defensive programming)
    official_links = [str(link) for link in official_links if link]
    log.info(f"🔗 Official links: {len(official_links)}")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.warning("❌ OpenAI API key not set, using fallback")
        # fallback
        parts = [f"**{company.get('name_full') or company.get('name') or 'Компания'}**"]
        if official_links:
            # Ensure all items in official_links are strings
            official_links_str = [str(link) for link in official_links if link]
            parts.append("**Источники:** " + ", ".join(official_links_str[:4]))
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
            # Ensure all items in official_links are strings
            official_links_str = [str(link) for link in official_links if link]
            parts.append("**Источники:** " + ", ".join(official_links_str[:4]))
        return "\n\n".join(parts)
