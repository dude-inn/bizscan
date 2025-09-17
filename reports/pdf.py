# -*- coding: utf-8 -*-
from typing import Literal
from domain.models import CompanyFull
from settings import BRAND_NAME, BRAND_LINK, DATE_FORMAT
from core.logger import setup_logging
from datetime import datetime
from fpdf import FPDF
import re

log = setup_logging()

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        
        # Используем встроенные Unicode шрифты fpdf2
        try:
            # fpdf2 имеет встроенные Unicode шрифты
            self.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
            self.add_font('DejaVu', 'B', 'DejaVuSansCondensed-Bold.ttf', uni=True)
            self.add_font('DejaVu', 'I', 'DejaVuSansCondensed-Oblique.ttf', uni=True)
            self.unicode_font = 'DejaVu'
            log.debug("PDF: Built-in Unicode font DejaVu loaded successfully")
        except Exception as e:
            log.warning("PDF: Failed to load built-in DejaVu font, using Helvetica with transliteration", error=str(e))
            # Fallback: используем Helvetica с транслитерацией
            self.unicode_font = 'Helvetica'
        
        # Добавляем страницу после инициализации шрифта
        self.add_page()
        
    def header(self):
        # Логотип и заголовок
        self.set_font(self.unicode_font, 'B', 16)
        self.set_text_color(37, 99, 235)  # Синий цвет
        self.cell(0, 10, BRAND_NAME, 0, 1, 'C')
        
        # Линия под заголовком
        self.set_draw_color(37, 99, 235)
        self.line(20, 25, 190, 25)
        
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font(self.unicode_font, 'I', 8)
        self.set_text_color(128, 128, 128)
        if self.unicode_font == 'Helvetica':
            footer_text = f'Stranitsa {self.page_no()}'
        else:
            footer_text = f'Страница {self.page_no()}'
        self.cell(0, 10, footer_text, 0, 0, 'C')
    
    def add_section_title(self, title: str, emoji: str = ""):
        self.ln(5)
        self.set_font(self.unicode_font, 'B', 14)
        self.set_text_color(30, 64, 175)  # Темно-синий
        # Используем оригинальный текст для Unicode шрифта или транслитерацию для Helvetica
        if self.unicode_font == 'Helvetica':
            title_text = sanitize_text(title)
        else:
            title_text = title
        self.cell(0, 8, title_text, 0, 1)
        self.ln(2)
    
    def add_field(self, label: str, value: str):
        if not value:
            return
            
        # Используем оригинальный текст для Unicode шрифта или транслитерацию для Helvetica
        if self.unicode_font == 'Helvetica':
            label_text = sanitize_text(label)
            value_text = sanitize_text(value)
        else:
            label_text = label
            value_text = value
            
        self.set_font(self.unicode_font, 'B', 10)
        self.set_text_color(55, 65, 81)  # Серый
        self.cell(40, 6, f"{label_text}:", 0, 0)
        
        self.set_font(self.unicode_font, '', 10)
        self.set_text_color(0, 0, 0)  # Черный
        # Переносим длинные значения
        if len(value_text) > 50:
            self.cell(0, 6, value_text[:47] + "...", 0, 1)
        else:
            self.cell(0, 6, value_text, 0, 1)
    
    def add_locked_field(self, text: str):
        self.set_font(self.unicode_font, 'I', 9)
        self.set_text_color(156, 163, 175)  # Светло-серый
        self.cell(0, 5, f"[ЗАБЛОКИРОВАНО] {text}", 0, 1)

def sanitize_text(text: str) -> str:
    """Очищает текст от проблемных символов для PDF и транслитерирует кириллицу"""
    if not text:
        return ""
    
    # Сначала заменяем проблемные символы
    text = str(text)
    text = text.replace('№', 'N')  # Заменяем символ номера
    text = text.replace('"', '"').replace('"', '"')  # Заменяем кавычки
    text = text.replace('—', '-').replace('–', '-')  # Заменяем тире
    text = text.replace('…', '...')  # Заменяем многоточие
    
    # Словарь транслитерации
    translit_dict = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    # Транслитерируем кириллицу
    result = ""
    for char in text:
        if char in translit_dict:
            result += translit_dict[char]
        elif char.isalnum() or char in ' .,:;()"/\\-':
            result += char
        # Игнорируем остальные символы (эмодзи и т.д.)
    
    # Удаляем лишние пробелы
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def generate_pdf(company: CompanyFull, mode: Literal["free", "full"]) -> bytes:
    """
    Генерирует PDF отчет для компании используя fpdf2
    """
    log.info("PDF: start generate_pdf", mode=mode, company_name=company.short_name)
    log.debug("PDF: company data", 
              inn=company.inn, 
              ogrn=company.ogrn, 
              has_contacts=bool(company.contacts),
              finance_count=len(company.finance),
              founders_count=len(company.founders))
    
    pdf = PDFReport()
    
    # Заголовок отчета
    pdf.set_font(pdf.unicode_font, 'B', 20)
    pdf.set_text_color(30, 64, 175)
    if pdf.unicode_font == 'Helvetica':
        title = f"{sanitize_text(BRAND_NAME)}: {'Besplatnyy' if mode == 'free' else 'Polnyy'} otchet"
    else:
        title = f"{BRAND_NAME}: {'Бесплатный' if mode == 'free' else 'Полный'} отчёт"
    pdf.cell(0, 15, title, 0, 1, 'C')
    
    # Информация о компании
    pdf.add_section_title("Карточка компании", "")
    
    pdf.add_field("Название", company.short_name)
    if company.full_name and company.full_name != company.short_name:
        pdf.add_field("Полное наименование", company.full_name)
    pdf.add_field("ИНН", company.inn)
    pdf.add_field("ОГРН", company.ogrn)
    if company.ogrn_date:
        pdf.add_field("Дата ОГРН", company.ogrn_date)
    pdf.add_field("КПП", company.kpp)
    pdf.add_field("Статус", company.status)
    pdf.add_field("Дата регистрации", company.reg_date)
    pdf.add_field("Адрес", company.address)
    pdf.add_field("Руководитель", company.director)
    
    # Деятельность
    if company.okved_main or company.okved_additional:
        pdf.add_section_title("Деятельность", "")
        pdf.add_field("Основной вид деятельности", company.okved_main)
        
        if company.okved_additional:
            if mode == "free":
                pdf.add_locked_field(f"Дополнительные виды: {len(company.okved_additional)} шт. — доступно в платном отчёте")
            else:
                pdf.set_font(pdf.unicode_font, 'B', 10)
                pdf.cell(0, 6, "Дополнительные виды деятельности:", 0, 1)
                for okved in company.okved_additional[:10]:
                    pdf.set_font(pdf.unicode_font, '', 9)
                    pdf.cell(0, 5, f"• {okved}", 0, 1)
                if len(company.okved_additional) > 10:
                    pdf.cell(0, 5, f"... и еще {len(company.okved_additional) - 10}", 0, 1)
    
    # Реквизиты
    if company.msp_status or company.tax_authority or company.stats_codes:
        pdf.add_section_title("Реквизиты", "")
        pdf.add_field("МСП-статус", company.msp_status)
        pdf.add_field("Налоговый орган", company.tax_authority)
        
        if company.stats_codes:
            if mode == "free":
                pdf.add_locked_field(f"Коды статистики: {len(company.stats_codes)} шт. — доступно в платном отчёте")
            else:
                pdf.set_font(pdf.unicode_font, 'B', 10)
                pdf.cell(0, 6, "Коды статистики:", 0, 1)
                for code, value in company.stats_codes.items():
                    pdf.set_font(pdf.unicode_font, '', 9)
                    pdf.cell(0, 5, f"• {code}: {value}", 0, 1)
    
    # Контакты
    if company.contacts:
        pdf.add_section_title("Контакты", "")
        for contact_type, values in company.contacts.items():
            if values:
                if mode == "free":
                    pdf.add_locked_field(f"{contact_type.title()}: {len(values)} контактов — доступно в платном отчёте")
                else:
                    pdf.set_font(pdf.unicode_font, 'B', 10)
                    pdf.cell(0, 6, f"{contact_type.title()}:", 0, 1)
                    for value in values:
                        pdf.set_font(pdf.unicode_font, '', 9)
                        pdf.cell(0, 5, f"• {value}", 0, 1)
    
    # Финансы
    if company.finance:
        pdf.add_section_title("Финансы", "")
        if mode == "free":
            pdf.add_locked_field(f"Данные за {len(company.finance)} лет — доступно в платном отчёте")
        else:
            pdf.set_font(pdf.unicode_font, 'B', 10)
            pdf.cell(30, 6, "Год", 1, 0, 'C')
            pdf.cell(40, 6, "Выручка", 1, 0, 'C')
            pdf.cell(40, 6, "Прибыль", 1, 0, 'C')
            pdf.cell(40, 6, "Активы", 1, 0, 'C')
            pdf.cell(40, 6, "Обязательства", 1, 1, 'C')
            
            for fy in sorted(company.finance, key=lambda x: x.year, reverse=True):
                pdf.set_font(pdf.unicode_font, '', 9)
                pdf.cell(30, 6, str(fy.year), 1, 0, 'C')
                pdf.cell(40, 6, fy.revenue or '-', 1, 0, 'C')
                pdf.cell(40, 6, fy.profit or '-', 1, 0, 'C')
                pdf.cell(40, 6, fy.assets or '-', 1, 0, 'C')
                pdf.cell(40, 6, fy.liabilities or '-', 1, 1, 'C')
    
    # Правовые индикаторы
    if company.flags:
        pdf.add_section_title("Правовые индикаторы", "")
        if mode == "free":
            flag_count = len([f for f in company.flags.__dict__.values() if f is not None])
            pdf.add_locked_field(f"Проверено {flag_count} показателей — доступно в платном отчёте")
        else:
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
                for flag in flags:
                    pdf.set_font(pdf.unicode_font, '', 9)
                    pdf.cell(0, 5, f"[!] {flag}", 0, 1)
            else:
                pdf.set_font(pdf.unicode_font, '', 10)
                pdf.set_text_color(16, 185, 129)  # Зеленый
                pdf.cell(0, 6, "[OK] Правовых нарушений не обнаружено", 0, 1)
    
    # Учредители
    if company.founders:
        pdf.add_section_title("Учредители", "")
        if mode == "free":
            pdf.add_locked_field(f"Найдено {len(company.founders)} учредителей — доступно в платном отчёте")
        else:
            for founder in company.founders:
                founder_info = founder.name
                if founder.share:
                    founder_info += f" (доля: {founder.share})"
                pdf.set_font(pdf.unicode_font, '', 9)
                pdf.cell(0, 5, f"• {founder_info}", 0, 1)
    
    # Лицензии
    if company.licenses:
        pdf.add_section_title("Лицензии", "📜")
        if mode == "free":
            pdf.add_locked_field(f"Найдено {len(company.licenses)} лицензий — доступно в платном отчёте")
        else:
            for license in company.licenses:
                license_info = license.type
                if license.number:
                    license_info += f" (№ {license.number})"
                if license.date:
                    license_info += f" от {license.date}"
                if license.authority:
                    license_info += f" ({license.authority})"
                pdf.set_font(pdf.unicode_font, '', 9)
                pdf.cell(0, 5, f"• {license_info}", 0, 1)
    
    # Подпись
    pdf.ln(10)
    pdf.set_font(pdf.unicode_font, 'I', 10)
    pdf.set_text_color(107, 114, 128)  # Серый
    pdf.cell(0, 6, f"Подпись: {BRAND_LINK}", 0, 1, 'C')
    pdf.cell(0, 6, f"Дата формирования: {datetime.now().strftime(DATE_FORMAT)}", 0, 1, 'C')
    
    try:
        log.debug("PDF: calling pdf.output()")
        pdf_bytes = pdf.output(dest="S")
        log.info("PDF: generated successfully", mode=mode, company_name=company.short_name, size=len(pdf_bytes))
        return pdf_bytes
    except Exception as e:
        log.exception("PDF: failed to generate PDF", exc_info=e, mode=mode, company_name=company.short_name)
        log.debug("PDF: error details", error_type=type(e).__name__, error_args=str(e.args))
        raise
