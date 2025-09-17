# -*- coding: utf-8 -*-
from typing import List
from io import BytesIO
import os
from pathlib import Path
import re
import textwrap
from core.logger import setup_logging

log = setup_logging()
from domain.models import CompanyFull
from settings import BRAND_NAME, BRAND_LINK

FREE_LOCK = "— доступно в платном отчёте"

def render_free(company: CompanyFull) -> List[str]:
    """Генерация бесплатного отчета с базовой информацией"""
    lines = []
    
    # Заголовок
    lines.append(f"✨ {BRAND_NAME}: Бесплатный отчёт")
    
    # Карточка компании
    card_lines = []
    if company.short_name:
        card_lines.append(f"📋 Название: {company.short_name}")
    if company.full_name and company.full_name != company.short_name:
        card_lines.append(f"📋 Полное наименование: {company.full_name}")
    if company.inn:
        card_lines.append(f"🔢 ИНН: {company.inn}")
    if company.ogrn:
        ogrn_text = f"🔢 ОГРН: {company.ogrn}"
        if company.ogrn_date:
            ogrn_text += f" (от {company.ogrn_date})"
        card_lines.append(ogrn_text)
    if company.kpp:
        card_lines.append(f"🔢 КПП: {company.kpp}")
    if company.status:
        card_lines.append(f"📊 Статус: {company.status}")
    if company.reg_date:
        card_lines.append(f"📅 Дата регистрации: {company.reg_date}")
    if company.address:
        card_lines.append(f"📍 Адрес: {company.address}")
    if company.director:
        card_lines.append(f"👤 Руководитель: {company.director}")
    
    if card_lines:
        lines.append("📋 КАРТОЧКА КОМПАНИИ")
        lines.append("\n".join(card_lines))
    
    # Секции с ограниченным доступом
    sections = []
    
    # Деятельность
    activity_lines = []
    if company.okved_main:
        activity_lines.append(f"Основной вид деятельности: {company.okved_main}")
    if company.okved_additional:
        activity_lines.append(f"Дополнительные виды: {len(company.okved_additional)} шт.")
    if activity_lines:
        sections.append("🏢 ДЕЯТЕЛЬНОСТЬ\n" + "\n".join(activity_lines) + f"\n{chr(0x1F512)} Подробности {FREE_LOCK}")
    
    # Реквизиты
    requisites_lines = []
    if company.msp_status:
        requisites_lines.append(f"МСП-статус: {company.msp_status}")
    if company.tax_authority:
        requisites_lines.append(f"Налоговый орган: {company.tax_authority}")
    if company.stats_codes:
        requisites_lines.append(f"Коды статистики: {len(company.stats_codes)} шт.")
    if requisites_lines:
        sections.append("📄 РЕКВИЗИТЫ\n" + "\n".join(requisites_lines) + f"\n{chr(0x1F512)} Полный список {FREE_LOCK}")
    
    # Контакты
    if company.contacts:
        contact_lines = []
        for contact_type, values in company.contacts.items():
            if values:
                contact_lines.append(f"{contact_type}: {', '.join(values[:2])}")  # Показываем только первые 2
        if contact_lines:
            sections.append("📞 КОНТАКТЫ\n" + "\n".join(contact_lines) + f"\n{chr(0x1F512)} Все контакты {FREE_LOCK}")
    
    # Финансы
    if company.finance:
        sections.append("💰 ФИНАНСЫ\n" + f"Данные за {len(company.finance)} лет\n{chr(0x1F512)} Детальная отчетность {FREE_LOCK}")
    
    # Правовые индикаторы
    if company.flags:
        sections.append("⚖️ ПРАВОВЫЕ ИНДИКАТОРЫ\n" + f"Проверено {len([f for f in company.flags.__dict__.values() if f is not None])} показателей\n{chr(0x1F512)} Подробный анализ {FREE_LOCK}")
    
    # Учредители
    if company.founders:
        sections.append("👥 УЧРЕДИТЕЛИ\n" + f"Найдено {len(company.founders)} учредителей\n{chr(0x1F512)} Полный список {FREE_LOCK}")
    
    # Лицензии
    if company.licenses:
        sections.append("📜 ЛИЦЕНЗИИ\n" + f"Найдено {len(company.licenses)} лицензий\n{chr(0x1F512)} Детальная информация {FREE_LOCK}")
    
    # Добавляем секции
    for section in sections:
        lines.append("")
        lines.append(section)
    
    # Подпись
    lines.append("")
    lines.append(f"📝 Подпись: {BRAND_LINK}")
    
    return lines

def render_full(company: CompanyFull) -> List[str]:
    """Генерация полного отчета со всеми данными"""
    lines = []
    
    # Заголовок
    lines.append(f"✨ {BRAND_NAME}: Полный отчёт")
    
    # Карточка компании
    card_lines = []
    if company.short_name:
        card_lines.append(f"📋 Название: {company.short_name}")
    if company.full_name and company.full_name != company.short_name:
        card_lines.append(f"📋 Полное наименование: {company.full_name}")
    if company.inn:
        card_lines.append(f"🔢 ИНН: {company.inn}")
    if company.ogrn:
        ogrn_text = f"🔢 ОГРН: {company.ogrn}"
        if company.ogrn_date:
            ogrn_text += f" (от {company.ogrn_date})"
        card_lines.append(ogrn_text)
    if company.kpp:
        card_lines.append(f"🔢 КПП: {company.kpp}")
    if company.status:
        card_lines.append(f"📊 Статус: {company.status}")
    if company.reg_date:
        card_lines.append(f"📅 Дата регистрации: {company.reg_date}")
    if company.address:
        card_lines.append(f"📍 Адрес: {company.address}")
    if company.director:
        card_lines.append(f"👤 Руководитель: {company.director}")
    
    if card_lines:
        lines.append("📋 КАРТОЧКА КОМПАНИИ")
        lines.append("\n".join(card_lines))
    
    # Деятельность
    if company.okved_main or company.okved_additional:
        lines.append("")
        lines.append("🏢 ДЕЯТЕЛЬНОСТЬ")
        if company.okved_main:
            lines.append(f"Основной вид деятельности: {company.okved_main}")
        if company.okved_additional:
            lines.append("Дополнительные виды деятельности:")
            for okved in company.okved_additional[:10]:  # Показываем первые 10
                lines.append(f"  • {okved}")
            if len(company.okved_additional) > 10:
                lines.append(f"  ... и еще {len(company.okved_additional) - 10}")
    
    # Реквизиты
    if company.msp_status or company.tax_authority or company.stats_codes:
        lines.append("")
        lines.append("📄 РЕКВИЗИТЫ")
        if company.msp_status:
            lines.append(f"MСП-статус: {company.msp_status}")
        if company.tax_authority:
            lines.append(f"Налоговый орган: {company.tax_authority}")
    if company.stats_codes:
            lines.append("Коды статистики:")
            for code, value in company.stats_codes.items():
                lines.append(f"  • {code}: {value}")

    # Контакты
    if company.contacts:
        lines.append("")
        lines.append("📞 КОНТАКТЫ")
        for contact_type, values in company.contacts.items():
            if values:
                lines.append(f"{contact_type.title()}:")
                for value in values:
                    lines.append(f"  • {value}")
    
    # Финансы
    if company.finance:
        lines.append("")
        lines.append("💰 ФИНАНСЫ")
        for fy in sorted(company.finance, key=lambda x: x.year, reverse=True):
            year_data = [f"{fy.year}:"]
            if fy.revenue:
                year_data.append(f"выручка {fy.revenue}")
            if fy.profit:
                year_data.append(f"прибыль {fy.profit}")
            if fy.assets:
                year_data.append(f"активы {fy.assets}")
            if fy.liabilities:
                year_data.append(f"обязательства {fy.liabilities}")
            lines.append(" ".join(year_data))
    
    # Правовые индикаторы
    if company.flags:
        flags = []
        if company.flags.arbitration: flags.append("арбитражные дела")
        if company.flags.bankruptcy: flags.append("банкротство")
        if company.flags.exec_proceedings: flags.append("исполнительные производства")
        if company.flags.inspections: flags.append("проверки")
        if company.flags.mass_director: flags.append("массовый руководитель")
        if company.flags.mass_founder: flags.append("массовый учредитель")
        if company.flags.unreliable_address: flags.append("недостоверность адреса")
        if company.flags.unreliable_director: flags.append("недостоверность руководителя")
        if company.flags.unreliable_founder: flags.append("недостоверность учредителя")
        if company.flags.tax_debt: flags.append("налоговая задолженность")
        if company.flags.disqualified: flags.append("дисквалифицированные лица")
        if company.flags.unreliable_supplier: flags.append("недобросовестные поставщики")
        
        if flags:
            lines.append("")
            lines.append("⚖️ ПРАВОВЫЕ ИНДИКАТОРЫ")
            for flag in flags:
                lines.append(f"  ⚠️ {flag}")
    
    # Учредители
    if company.founders:
        lines.append("")
        lines.append("👥 УЧРЕДИТЕЛИ")
        for founder in company.founders:
            founder_info = founder.name
            if founder.share:
                founder_info += f" (доля: {founder.share})"
            lines.append(f"  • {founder_info}")
    
    # Лицензии
    if company.licenses:
        lines.append("")
        lines.append("📜 ЛИЦЕНЗИИ")
        for license in company.licenses:
            license_info = license.type
            if license.number:
                license_info += f" (№ {license.number})"
            if license.date:
                license_info += f" от {license.date}"
            if license.authority:
                license_info += f" ({license.authority})"
            lines.append(f"  • {license_info}")
    
    # Подпись
    lines.append("")
    lines.append(f"📝 Подпись: {BRAND_LINK}")
    
    return lines

def _find_font_path() -> str:
    # Используем системный шрифт с кириллицей (Windows Arial)
    candidates = []
    env_path = os.getenv("PDF_FONT_PATH")
    if env_path:
        candidates.append(env_path)
    windir = os.getenv("WINDIR", r"C:\\Windows")
    candidates += [
        rf"{windir}\\Fonts\\arial.ttf",
        rf"{windir}\\Fonts\\Arial.ttf",
        rf"{windir}\\Fonts\\segoeui.ttf",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return p
        except Exception:
            continue
    # Последняя попытка: текущая директория проекта
    local = Path(__file__).resolve().parent / "Arial.ttf"
    if local.exists():
        return str(local)
    raise FileNotFoundError("No suitable TTF font found for PDF generation. Set PDF_FONT_PATH to a valid .ttf")


def generate_pdf(data: CompanyFull) -> bytes:
    """Генерация простого PDF для бесплатного отчёта (fpdf2 + системный TTF для кириллицы)."""
    from fpdf import FPDF

    log.info("PDF: start generate_free")
    font_path = _find_font_path()
    log.info("PDF: font path chosen", font_path=font_path)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.add_font("Custom", "", font_path, uni=True)
    log.info("PDF: font added")
    
    pdf.set_font("Custom", size=16)
    pdf.cell(0, 10, txt=f"{BRAND_NAME}: Бесплатный отчет", ln=1)
    log.info("PDF: title added")
    
    pdf.set_font("Custom", size=11)
    log.info("PDF: font set to 11pt")

    def sanitize(text: str) -> str:
        # Удаляем/заменяем символы, которых нет в стандартных TTF (эмодзи, псевдографика)
        replacements = {
            "✨": "*",
            "✅": "+",
            "❌": "-",
            "◀": "<",
            "▶": ">",
            "▪": "-",
            "•": "-",
            "—": "-",
            "–": "-",
            "“": '"',
            "”": '"',
            "’": "'",
            "«": '"',
            "»": '"',
            "░": ".",
            "▒": ".",
            "▓": ".",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Неразрывные и нулевой ширины пробелы → обычный пробел
        text = text.replace("\u00A0", " ")  # NBSP
        text = text.replace("\u200B", "")   # Zero-width space
        text = text.replace("\uFEFF", "")   # BOM
        text = text.replace("\u202F", " ")  # Narrow NBSP
        text = text.replace("\u2009", " ")  # Thin space
        text = text.replace("\u2007", " ")  # Figure space
        text = text.replace("\u2060", "")   # Word joiner
        text = re.sub(r"[\u2000-\u200A\u205F\u3000]", " ", text)
        # Убираем управляющие символы
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
        return text

    def safe_render_text(pdf, text: str) -> None:
        """Безопасный рендеринг текста с принудительным разбиением на очень короткие строки"""
        # Агрессивная очистка текста
        cleaned = re.sub(r"[^0-9A-Za-zА-Яа-яЁё()""'«»№:;.,/\\-\s]", "", text)
        cleaned = cleaned.replace("\u00A0", " ").replace("\u2007", " ").replace("\u202F", " ")
        
        # Разбиваем на очень короткие строки (максимум 25 символов)
        words = cleaned.split()
        current_line = ""
        
        for word in words:
            # Если слово само по себе длиннее 25 символов, разбиваем его
            if len(word) > 25:
                if current_line:
                    try:
                        pdf.multi_cell(0, 6, txt=current_line.strip())
                    except:
                        pass
                    current_line = ""
                
                # Разбиваем длинное слово на части по 20 символов
                for i in range(0, len(word), 20):
                    chunk = word[i:i+20]
                    try:
                        pdf.multi_cell(0, 6, txt=chunk)
                    except:
                        pass
                continue
            
            # Проверяем, поместится ли слово в текущую строку
            test_line = (current_line + " " + word).strip()
            if len(test_line) <= 25:
                current_line = test_line
            else:
                # Печатаем текущую строку и начинаем новую
                if current_line:
                    try:
                        pdf.multi_cell(0, 6, txt=current_line.strip())
                    except:
                        pass
                current_line = word
        
        # Печатаем последнюю строку
        if current_line:
            try:
                pdf.multi_cell(0, 6, txt=current_line.strip())
            except:
                pass

    lines = render_free(data)
    log.info("PDF: lines prepared", blocks=len(lines))
    
    for bi, block in enumerate(lines):
        log.info("PDF: processing block", block_index=bi, block_length=len(block))
        for li, raw_line in enumerate(block.split("\n")):
            line = sanitize(raw_line)
            log.info("PDF: rendering line", block_index=bi, line_index=li, line_length=len(line))
            safe_render_text(pdf, line)
        pdf.ln(2)
        log.info("PDF: block completed", block_index=bi)

    # Возвращаем байты PDF
    log.info("PDF: generating final bytes")
    pdf_bytes: bytes = pdf.output(dest="S")
    log.info("PDF: generated", size=len(pdf_bytes))
    return pdf_bytes
