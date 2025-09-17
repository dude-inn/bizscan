# -*- coding: utf-8 -*-
import re
import asyncio
from typing import Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from .client import ThrottledClient

TAB_RX = {
    "summary": re.compile(r"(сводк|осн|карточк|общие сведени|реквизит)", re.I),
    "finance": re.compile(r"финанс", re.I),
    "courts": re.compile(r"(арбитраж|суды)", re.I),
    "courts_common": re.compile(r"суды общей юрисдикции", re.I),
    "procurements": re.compile(r"госзакуп", re.I),
    "executions": re.compile(r"исполн.*производ", re.I),
    "checks": re.compile(r"проверки", re.I),
    "licenses": re.compile(r"лиценз", re.I),
    "reliability": re.compile(r"(надёжн|надежн|сущфакт|факт)", re.I),
    "trademarks": re.compile(r"(товарн|знак)", re.I),
    "history": re.compile(r"(истор|изменен)", re.I),
    "activity": re.compile(r"(вид.*деят|оквэд)", re.I),
}


def _plain_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for sel in ["script", "style", "noscript", "nav", "header", "footer"]:
        for t in soup.select(sel):
            t.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def _discover_tabs(soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
    links: Dict[str, str] = {}
    for a in soup.select("a[href]"):
        txt = a.get_text(" ", strip=True).lower()
        href = a.get("href") or ""
        if not href:
            continue
        for key, rx in TAB_RX.items():
            if rx.search(txt):
                links.setdefault(key, urljoin(base_url, href))
    return links


async def fetch_all_texts(url: str, client: ThrottledClient, *, include_main: bool = True) -> Dict[str, str]:
    out: Dict[str, str] = {}
    r = await client.get(url)
    base = str(r.url)
    soup = BeautifulSoup(r.text, "html.parser")

    if include_main:
        out["summary"] = _plain_text(r.text)

    tab_urls = _discover_tabs(soup, base)

    async def grab(name: str, href: str):
        try:
            rr = await client.get(href)
            out[name] = _plain_text(rr.text)
        except Exception as e:
            out[name] = f"[Ошибка загрузки {href}: {e}]"

    await asyncio.gather(*[grab(k, v) for k, v in tab_urls.items()])
    return out


