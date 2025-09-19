# -*- coding: utf-8 -*-
"""
Gamma.app integration for company enrichment
"""
from __future__ import annotations
from typing import Dict, Any
from services.enrichment.search_providers import search_company_context
from services.enrichment.openai_gamma_enricher import generate_gamma_section

def build_gamma_block_for_company(base_company: Dict[str, Any]) -> str:
    """
    base_company expected keys:
      - name_full, inn, ogrn, okved, address
    Returns Markdown string ready for Gamma.app.
    """
    name = base_company.get("name_full") or base_company.get("name") or ""
    query = name or base_company.get("inn") or base_company.get("ogrn") or ""
    snippets = search_company_context(query)
    return generate_gamma_section(
        {
            "name_full": base_company.get("name_full"),
            "name": base_company.get("name_short"),
            "inn": base_company.get("inn"),
            "ogrn": base_company.get("ogrn"),
            "okved": base_company.get("okved"),
            "address": base_company.get("address"),
        },
        snippets
    )
