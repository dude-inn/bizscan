# -*- coding: utf-8 -*-
import re
from datetime import datetime
from settings import DATE_FORMAT

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def normalize_digits(s: str) -> str:
    s = s or ""
    s = s.replace("\xa0", " ").replace("\u202f", " ")
    s = re.sub(r"[^0-9]", "", s)
    return s

def format_int(num_str: str) -> str:
    if not num_str: return ""
    try:
        n = int(num_str)
        return f"{n:,}".replace(",", "\u00A0")  # неразрывные пробелы
    except:
        return num_str

def normalize_date(s: str) -> str:
    s = s or ""
    # Попробуем найти DD.MM.YYYY или YYYY-MM-DD
    m = re.search(r"(\d{2})[.](\d{2})[.](\d{4})", s)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return s.strip()
