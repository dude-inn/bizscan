# -*- coding: utf-8 -*-
"""
Рендерер данных о физическом лице (OFData /v2/person)
"""
from typing import Dict, Any, List
from .formatters import format_date, format_money


def _format_company_ref(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    name = item.get('НаимСокр') or item.get('НаимПолн') or '—'
    parts.append(name)
    inn = item.get('ИНН') or '—'
    ogrn = item.get('ОГРН') or '—'
    status = item.get('Статус') or '—'
    date_reg = item.get('ДатаРег') or ''
    if date_reg:
        date_reg = format_date(date_reg)
    parts.append(f"ИНН {inn} • ОГРН {ogrn} • {status} • рег. {date_reg}")
    okved = item.get('ОКВЭД')
    if okved:
        parts.append(f"ОКВЭД {okved}")
    return " | ".join(parts)


def render_person(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    p = data.get('data') or {}
    fio = p.get('ФИО') or '—'
    inn = p.get('ИНН') or '—'
    lines.append(f"ФИЗИЧЕСКОЕ ЛИЦО: {fio}")
    lines.append(f"ИНН: {inn}")
    lines.append("")

    # Факторы риска
    risk_flags: List[str] = []
    if p.get('НедобПост'):
        risk_flags.append("Реестр недобросовестных поставщиков")
    if p.get('МассРуковод'):
        risk_flags.append("Массовый руководитель (ФНС)")
    if p.get('МассУчред'):
        risk_flags.append("Массовый учредитель (ФНС)")
    if p.get('Санкции'):
        countries = p.get('СанкцииСтраны') or []
        risk_flags.append("Санкции: " + ", ".join(countries) if countries else "Санкции")
    if risk_flags:
        lines.append("РИСК-ФАКТОРЫ")
        lines.append("=" * 50)
        for flag in risk_flags:
            lines.append(f"• {flag}")
        lines.append("")

    # РП - записи РНП
    rnp = p.get('НедобПостЗап') or []
    if rnp:
        lines.append("РЕЕСТР НЕДОБРОСОВЕСТНЫХ ПОСТАВЩИКОВ")
        lines.append("=" * 50)
        for i, rec in enumerate(rnp, 1):
            price = rec.get('ЦенаКонтр')
            price_str = format_money(price) if isinstance(price, (int, float)) else (str(price) if price else '—')
            lines.append(
                f"{i}. №{rec.get('РеестрНомер', '—')} | публ. {format_date(rec.get('ДатаПуб'))} | утв. {format_date(rec.get('ДатаУтв'))} | заказчик {rec.get('ЗаказНаимСокр') or rec.get('ЗаказНаимПолн') or '—'} | цена {price_str}"
            )
        lines.append("")

    # Компании как руководитель
    leaders = p.get('Руковод') or []
    if leaders:
        lines.append("КОМПАНИИ КАК РУКОВОДИТЕЛЬ")
        lines.append("=" * 50)
        for i, item in enumerate(leaders[:200], 1):
            lines.append(f"{i}. {_format_company_ref(item)}")
        if len(leaders) > 200:
            lines.append(f"… и ещё {len(leaders) - 200} компаний")
        lines.append("")

    # Компании как учредитель
    founders = p.get('Учред') or []
    if founders:
        lines.append("КОМПАНИИ КАК УЧРЕДИТЕЛЬ")
        lines.append("=" * 50)
        for i, item in enumerate(founders[:200], 1):
            lines.append(f"{i}. {_format_company_ref(item)}")
        if len(founders) > 200:
            lines.append(f"… и ещё {len(founders) - 200} компаний")
        lines.append("")

    # ИП
    ips = p.get('ИП') or []
    if ips:
        lines.append("ИНДИВИДУАЛЬНЫЕ ПРЕДПРИНИМАТЕЛИ")
        lines.append("=" * 50)
        for i, ip in enumerate(ips[:50], 1):
            status = ip.get('Статус') or '—'
            reg = format_date(ip.get('ДатаРег'))
            stop = format_date(ip.get('ДатаПрекращ'))
            okved = ip.get('ОКВЭД') or '—'
            lines.append(f"{i}. ОГРНИП {ip.get('ОГРНИП', '—')} | ИНН {ip.get('ИНН', '—')} | {status} | рег. {reg} | прекращ. {stop} | ОКВЭД {okved}")
        if len(ips) > 50:
            lines.append(f"… и ещё {len(ips) - 50} записей")
        lines.append("")

    # Товарные знаки
    tz = p.get('ТоварЗнак') or []
    if tz:
        lines.append("ТОВАРНЫЕ ЗНАКИ")
        lines.append("=" * 50)
        for i, t in enumerate(tz[:200], 1):
            # добавляем класс МКТУ и правообладателя, если доступны
            mktu = t.get('МКТУ') or t.get('КлассМКТУ')
            holder = t.get('Правообладатель') or t.get('Правооблад')
            extra = []
            if mktu:
                extra.append(f"МКТУ: {mktu}")
            if holder:
                extra.append(f"Правообладатель: {holder}")
            extra_str = f" | {' | '.join(extra)}" if extra else ""
            lines.append(f"{i}. №{t.get('ID', '—')} | рег. {format_date(t.get('ДатаРег'))} | оконч. {format_date(t.get('ДатаОконч'))} | {t.get('URL', '—')}{extra_str}")
        if len(tz) > 200:
            lines.append(f"… и ещё {len(tz) - 200} записей")
        lines.append("")

    # ЕФРСБ
    efrsb = p.get('ЕФРСБ') or []
    if efrsb:
        lines.append("ЕФРСБ")
        lines.append("=" * 50)
        for i, e in enumerate(efrsb[:50], 1):
            lines.append(f"{i}. {e.get('Тип', '—')} | {format_date(e.get('Дата'))} | дело {e.get('Дело', '—')}")
        if len(efrsb) > 50:
            lines.append(f"… и ещё {len(efrsb) - 50} записей")
        lines.append("")
    else:
        # Показываем критерии поиска и 0 найдено
        if inn and inn != '—':
            lines.append("ЕФРСБ")
            lines.append("=" * 50)
            lines.append(f"Критерии поиска: ИНН {inn}")
            lines.append("Найдено: 0")
            lines.append("")

    return "\n".join(lines) if lines else "Данные о физическом лице отсутствуют"


