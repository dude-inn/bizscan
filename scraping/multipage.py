# -*- coding: utf-8 -*-
import re
import asyncio
from typing import Dict
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .client import ThrottledClient
from .company import parse_company_html
from .extractors import (
    extract_tab_finance,
    extract_tab_courts,
    extract_tab_procurements,
    extract_tab_executions,
    extract_tab_checks,
    extract_tab_licenses,
    extract_tab_history,
    extract_tab_requisites,
    extract_tab_activity,
)

TABS_RX = {
    "finance": re.compile(r"финанс", re.I),
    "courts": re.compile(r"(арбитраж|суды)", re.I),
    "procurements": re.compile(r"госзакуп", re.I),
    "executions": re.compile(r"исполн.*производ", re.I),
    "checks": re.compile(r"проверки", re.I),
    "licenses": re.compile(r"лиценз", re.I),
    "history": re.compile(r"(истор|изменен)", re.I),
    "requisites": re.compile(r"реквизит", re.I),
    "activity": re.compile(r"(вид.*деят|оквэд)", re.I),
}


def discover_tabs(soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
    links: Dict[str, str] = {}
    for a in soup.select("a[href]"):
        text = a.get_text(" ", strip=True).lower()
        href = a.get("href") or ""
        if not href:
            continue
        for key, rx in TABS_RX.items():
            if rx.search(text):
                links.setdefault(key, urljoin(base_url, href))
    return links


async def fetch_company_bundle(client: ThrottledClient, url: str):
    # 1) Главная
    r = await client.get(url)
    base = str(r.url)
    soup = BeautifulSoup(r.text, "html.parser")
    company = await parse_company_html(r.text, url=r.request.url.path)

    # 2) Вкладки
    tab_urls = discover_tabs(soup, base)

    async def grab(key: str, href: str):
        rr = await client.get(href)
        ss = BeautifulSoup(rr.text, "html.parser")
        if key == "finance":
            extract_tab_finance(company, ss)
        elif key == "courts":
            extract_tab_courts(company, ss)
        elif key == "procurements":
            extract_tab_procurements(company, ss)
        elif key == "executions":
            extract_tab_executions(company, ss)
        elif key == "checks":
            extract_tab_checks(company, ss)
        elif key == "licenses":
            extract_tab_licenses(company, ss)
        elif key == "history":
            extract_tab_history(company, ss)
        elif key == "requisites":
            extract_tab_requisites(company, ss)
        elif key == "activity":
            extract_tab_activity(company, ss)

    await asyncio.gather(*[grab(k, v) for k, v in tab_urls.items()])
    return company


