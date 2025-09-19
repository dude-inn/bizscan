# -*- coding: utf-8 -*-
"""
Web search providers for company context enrichment
"""
from __future__ import annotations
import os
import time
from typing import Any, Dict, List, Optional
import httpx

# Supported providers:
#   - serper   (Google Web via https://serper.dev/)
#   - serpapi  (Google Web via https://serpapi.com/)
#   - bing     (Bing Web Search API)
# Choose with SEARCH_PROVIDER in env.

DEFAULT_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper").strip().lower()

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
BING_KEY = os.getenv("BING_SEARCH_KEY", "")

HTTP_TIMEOUT = float(os.getenv("SEARCH_HTTP_TIMEOUT", "10"))
MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "6"))
QPM = int(os.getenv("SEARCH_QPM", "30"))

# Логирование состояния API ключей
import logging
log = logging.getLogger(__name__)

def _log_api_keys_status():
    """Логирует статус API ключей для веб-поиска"""
    log.info("=== Web Search API Keys Status ===")
    log.info(f"Provider: {DEFAULT_PROVIDER}")
    log.info(f"Serper API Key: {'✅ Set' if SERPER_API_KEY else '❌ Not set'}")
    log.info(f"SerpAPI Key: {'✅ Set' if SERPAPI_KEY else '❌ Not set'}")
    log.info(f"Bing Key: {'✅ Set' if BING_KEY else '❌ Not set'}")
    log.info(f"Max Results: {MAX_RESULTS}, QPM: {QPM}, Timeout: {HTTP_TIMEOUT}s")

# Логируем при импорте модуля
_log_api_keys_status()

_last_min = 0.0
_calls = 0

def _rate_limit():
    global _last_min, _calls
    now = time.time()
    if now - _last_min > 60.0:
        _last_min = now
        _calls = 0
        return
    _calls += 1
    if QPM and _calls > QPM:
        time.sleep(1.0)

def _serper_search(query: str) -> List[Dict[str, Any]]:
    log.info(f"🔍 Serper search: '{query}'")
    if not SERPER_API_KEY:
        log.warning("❌ Serper API key not set, skipping search")
        return []
    
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": MAX_RESULTS, "hl": "ru"}
    
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            r = client.post(url, headers=headers, json=payload)
            log.info(f"📡 Serper response: {r.status_code}")
            if r.status_code != 200:
                log.error(f"❌ Serper API error: {r.status_code}")
                return []
            data = r.json()
        
        results = [
            {"title": it.get("title"), "url": it.get("link"), "snippet": it.get("snippet"), "source": "web"}
            for it in (data.get("organic") or [])[:MAX_RESULTS]
        ]
        log.info(f"✅ Serper found {len(results)} results")
        return results
    except Exception as e:
        log.error(f"❌ Serper search failed: {e}")
        return []

def _serpapi_search(query: str) -> List[Dict[str, Any]]:
    if not SERPAPI_KEY:
        return []
    url = "https://serpapi.com/search.json"
    params = {"engine": "google", "q": query, "hl": "ru", "num": MAX_RESULTS, "api_key": SERPAPI_KEY}
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        r = client.get(url, params=params)
        if r.status_code != 200:
            return []
        data = r.json()
    return [
        {"title": it.get("title"), "url": it.get("link"),
         "snippet": it.get("snippet") or it.get("snippet_highlighted_words") or "",
         "source": "web"}
        for it in (data.get("organic_results") or [])[:MAX_RESULTS]
    ]

def _bing_search(query: str) -> List[Dict[str, Any]]:
    if not BING_KEY:
        return []
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_KEY}
    params = {"q": query, "mkt": "ru-RU", "count": MAX_RESULTS}
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        r = client.get(url, headers=headers, params=params)
        if r.status_code != 200:
            return []
        data = r.json()
    return [
        {"title": it.get("name"), "url": it.get("url"), "snippet": it.get("snippet"), "source": "web"}
        for it in (data.get("webPages", {}).get("value") or [])[:MAX_RESULTS]
    ]

def search_company_context(company_name: str, extra_queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Returns a list of {title, url, snippet}.
    """
    log.info(f"🔍 Starting company context search for: '{company_name}'")
    
    if not company_name:
        log.warning("❌ Empty company name provided")
        return []
    
    queries = [company_name] + [f"{company_name} {p}" for p in
                                ["официальный сайт", "новости", "контакты", "история", "продукция"]]
    if extra_queries:
        queries.extend(extra_queries)
    
    log.info(f"📝 Generated {len(queries)} search queries")
    log.info(f"🔧 Using provider: {DEFAULT_PROVIDER}")

    aggregate: List[Dict[str, Any]] = []
    for i, q in enumerate(queries):
        log.info(f"🔍 Query {i+1}/{len(queries)}: '{q}'")
        _rate_limit()
        
        if DEFAULT_PROVIDER == "serpapi":
            res = _serpapi_search(q)
        elif DEFAULT_PROVIDER == "bing":
            res = _bing_search(q)
        else:
            res = _serper_search(q)
        
        seen = {item["url"] for item in aggregate}
        new_items = 0
        for it in res:
            if it["url"] not in seen:
                aggregate.append(it)
                seen.add(it["url"])
                new_items += 1
        
        log.info(f"📊 Query {i+1} added {new_items} new results (total: {len(aggregate)})")
        
        if len(aggregate) >= MAX_RESULTS:
            log.info(f"✅ Reached max results limit ({MAX_RESULTS}), stopping search")
            break
    
    final_results = aggregate[:MAX_RESULTS]
    log.info(f"🎯 Final search results: {len(final_results)} items")
    return final_results
