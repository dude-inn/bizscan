# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional


def build_official_links(inn: Optional[str], ogrn: Optional[str], site: Optional[str]) -> List[str]:
    """
    Build up to 4 official links for a company without using web search.
    - If site is provided, include it first
    - Always include base official registries (EGRUL, BO, KAD)
    - Deduplicate, drop empties, keep order, cap to 4
    """
    candidates: List[str] = []

    if site:
        s = site.strip()
        if s and not s.startswith("http"):
            s = "https://" + s
        candidates.append(s)

    # Official registries
    candidates.extend([
        "https://egrul.nalog.ru/",
        "https://bo.nalog.ru/",
        "https://kad.arbitr.ru/",
    ])

    # Deduplicate preserving order
    seen = set()
    out: List[str] = []
    for url in candidates:
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= 4:
            break

    return out


