# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from typing import List, Tuple
from .client import ThrottledClient, log
from domain.models import CompanyBrief
from scraping.normalize import normalize_whitespace

# Поиск по наименованию на rusprofile.ru
# Пример поискового URL: /search?query={q}
SEARCH_PATH = "/search?query={q}"

async def search_by_name(client: ThrottledClient, query: str) -> List[CompanyBrief]:
    url = SEARCH_PATH.format(q=query)
    r = await client.get(url)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    items = []

    # Если нас перенаправило сразу на страницу компании (/id/...), парсим карточку
    try:
        current_url = str(r.url)
    except Exception:
        current_url = ""
    if "/id/" in current_url or soup.select_one(".company-header, .company-header__title, .company-name"):
        name_el = soup.select_one(
            ".company-header__name, .company-header__title, .company-name, h1[itemprop='name']"
        )
        # Ищем ИНН/ОГРН по меткам
        def find_value_by_label(label: str) -> str:
            # Поиск в dt/dd парах
            for row in soup.select(".company-info dl, dl.company-requisites, dl"):
                dts = row.select("dt")
                dds = row.select("dd")
                for dt, dd in zip(dts, dds):
                    if label in dt.get_text():
                        return dd.get_text(strip=True)
            # Поиск в тексте
            txt = soup.get_text(" ")
            if label in txt:
                try:
                    return txt.split(label)[-1].strip().split()[0]
                except Exception:
                    return ""
            return ""

        inn_val = find_value_by_label("ИНН")
        ogrn_val = find_value_by_label("ОГРН") or None
        items.append(CompanyBrief(
            name=name_el.get_text(strip=True) if name_el else "Компания",
            inn=inn_val,
            ogrn=ogrn_val,
            region=None,
            url=current_url
        ))
        log.info("search_by_name", count=len(items))
        return items
    # Руспрофиль меняет вёрстку; ориентируемся на карточки в списке результатов
    for card in soup.select(
        "div.company-item, div#companies-list .company-item, .search-result div.company-item, "
        "div.search-page__result .company-item, div.company-search-result .company-item"
    ) or []:
        name_el = card.select_one("a[href*='/id/'], a.org-link, a.company-item__title, a.org__link")
        inn_text = card.find(string=lambda t: isinstance(t, str) and "ИНН" in t)
        ogrn_text = card.find(string=lambda t: isinstance(t, str) and "ОГРН" in t)
        region_el = card.select_one(".company-item__region, .company-item__text, .company-item__desc")
        href = name_el.get("href") if name_el else None
        items.append(CompanyBrief(
            name=normalize_whitespace(name_el.get_text() if name_el else ""),
            inn=(inn_text or "").split()[-1] if inn_text else "",
            ogrn=(ogrn_text or "").split()[-1] if ogrn_text else None,
            region=normalize_whitespace(region_el.get_text()) if region_el else None,
            url=href
        ))
    # Фолбэк, если вёрстка другая: ищем строки таблицы
    if not items:
        for row in soup.select("table tr")[:80]:
            link = row.select_one("a[href*='/id/']")
            if not link: 
                continue
            txt = normalize_whitespace(row.get_text(" "))
            # грубый парс
            inn = ""
            ogrn = None
            if "ИНН" in txt:
                try: inn = txt.split("ИНН")[-1].strip().split()[0]
                except: pass
            if "ОГРН" in txt:
                try: ogrn = txt.split("ОГРН")[-1].strip().split()[0]
                except: pass
            items.append(CompanyBrief(
                name=normalize_whitespace(link.get_text()),
                inn=inn, ogrn=ogrn,
                url=link.get("href"),
                region=None
            ))
    # Ещё один фолбэк: берём любые ссылки на карточки, если ничего не нашли
    if not items:
        seen = set()
        for link in soup.select("a[href*='/id/'], a[href^='/ul/']"):
            href = link.get("href")
            if not href or href in seen:
                continue
            seen.add(href)
            name = normalize_whitespace(link.get_text()) or "Компания"
            # Пытаемся вытащить ИНН из ближайшего текста
            inn = ""
            parent_text = normalize_whitespace(link.find_parent().get_text(" ")) if link.find_parent() else ""
            if "ИНН" in parent_text:
                try:
                    inn = parent_text.split("ИНН")[-1].strip().split()[0]
                except:
                    inn = ""
            items.append(CompanyBrief(name=name, inn=inn, ogrn=None, url=href, region=None))
    log.info("search_by_name", count=len(items))
    return items
