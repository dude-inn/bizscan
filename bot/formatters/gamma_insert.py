# -*- coding: utf-8 -*-
"""
Gamma.app integration for company enrichment
"""
from __future__ import annotations
from typing import Dict, Any
from services.enrichment.openai_gamma_enricher import generate_gamma_section
from services.enrichment.official_sources import build_official_links

def build_gamma_block_for_company(base_company: Dict[str, Any]) -> str:
    """
    base_company expected keys:
      - name_full, inn, ogrn, okved, address
    Returns Markdown string ready for Gamma.app.
    """
    # Build official links (site optional)
    site = None
    contacts = base_company.get("contacts") if isinstance(base_company, dict) else None
    if isinstance(contacts, dict):
        site = contacts.get("site") or contacts.get("website")
    official_links = build_official_links(base_company.get("inn"), base_company.get("ogrn"), site)

    return generate_gamma_section(
        {
            "name_full": base_company.get("name_full"),
            "name": base_company.get("name_short"),
            "inn": base_company.get("inn"),
            "ogrn": base_company.get("ogrn"),
            "okved": base_company.get("okved"),
            "address": base_company.get("address"),
        },
        official_links
    )
