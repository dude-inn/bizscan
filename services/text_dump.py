# -*- coding: utf-8 -*-
from typing import Dict
from datetime import datetime

ORDER = [
    "summary",
    "reliability",
    "finance",
    "activity",
    "licenses",
    "procurements",
    "courts",
    "courts_common",
    "executions",
    "checks",
    "trademarks",
    "history",
]

TITLES = {
    "summary": "Сводка / Карточка",
    "reliability": "Надёжность / Существенные факты",
    "finance": "Финансы",
    "activity": "Виды деятельности / ОКВЭД",
    "licenses": "Лицензии",
    "procurements": "Госзакупки",
    "courts": "Суды (арбитраж)",
    "courts_common": "Суды общей юрисдикции",
    "executions": "Исполнительные производства",
    "checks": "Проверки",
    "trademarks": "Товарные знаки",
    "history": "История / изменения",
}


def build_txt(bundle: Dict[str, str], *, source_url: str) -> str:
    parts = []
    parts.append(
        f"# Текстовый дамп компании\nИсточник: {source_url}\nСформировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    for key in ORDER:
        if key in bundle and bundle[key]:
            parts.append(f"\n---\n# {TITLES.get(key, key.capitalize())}\n")
            parts.append(bundle[key])
    missing = [k for k in bundle.keys() if k not in ORDER]
    if missing:
        parts.append("\n---\n# Прочее/неразмеченное\n")
        for k in missing:
            parts.append(f"\n## {k}\n")
            parts.append(bundle.get(k) or "—")
    return "\n".join(parts)


