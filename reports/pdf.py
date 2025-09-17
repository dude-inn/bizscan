# -*- coding: utf-8 -*-
from typing import Literal, Optional
from domain.models import CompanyFull
from settings import BRAND_NAME, BRAND_LINK, DATE_FORMAT
from core.logger import setup_logging
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
from fpdf.errors import FPDFUnicodeEncodingException
import re

log = setup_logging()

# Карта семейства/стиля в имя файла
FONT_FILES = {
    ("DejaVu", ""): "DejaVuSansCondensed.ttf",
    ("DejaVu", "B"): "DejaVuSansCondensed-Bold.ttf",
    # ("DejaVu", "I"): "DejaVuSansCondensed-Oblique.ttf",  # подключать только если файл реально есть
}


def _find_font_file(filename: str) -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / "assets" / "fonts" / filename,
        here / "assets" / "fonts" / filename,
        here / "fonts" / filename,
        here.parent / "assets" / "fonts" / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Font not found: {filename}; tried: {[str(c) for c in candidates]}"
    )


def _ensure_fonts(pdf: "FPDF") -> None:
    # Регистрируем все необходимые шрифты DejaVu
    registered = []
    for (family, style), fn in FONT_FILES.items():
        path = _find_font_file(fn)
        try:
            pdf.add_font(family, style, str(path), uni=True)
            registered.append(fn)
        except Exception:
            # Игнорируем повторную регистрацию
            pass
    if registered:
        log.info("PDF: fonts registered", fonts=registered)


def _set_font(pdf: "FPDF", style: str = "", size: int = 12) -> None:
    _ensure_fonts(pdf)
    # Не используем курсив, если Oblique-ttf не включён в FONT_FILES
    style = "B" if style == "B" else ""
    pdf.set_font("DejaVu", style, size)


# Универсальная строка с переносами: фиксированная колонка метки и
# автоширина значения без обрезаний/наложений
def row(pdf: "FPDF", label: str, value: Optional[str], *, label_w: int = 55, lh: int = 6) -> None:
    value = value or "—"
    # effective page width
    epw = getattr(pdf, "epw", pdf.w - pdf.l_margin - pdf.r_margin)
    v_w = epw - label_w
    x, y = pdf.get_x(), pdf.get_y()

    # Считаем высоту блока по количеству строк значения
    lines = pdf.multi_cell(v_w, lh, value, split_only=True)
    h = max(lh, lh * len(lines))

    # Метка (занимает всю высоту блока)
    pdf.set_xy(x, y)
    pdf.multi_cell(label_w, h, txt=label, border=0, align="L", new_x="RIGHT", new_y="TOP")

    # Значение с переносами
    pdf.set_xy(x + label_w, y)
    pdf.multi_cell(v_w, lh, txt=value, border=0, align="L", new_x="LMARGIN", new_y="NEXT")


def section(pdf: "FPDF", title: str) -> None:
    pdf.ln(2)
    _set_font(pdf, "B", 12)
    pdf.cell(0, 8, title, ln=1)
    _set_font(pdf, "", 11)


def lock(msg: str = "🔒 Доступно в платном отчёте") -> str:
    return msg


def ensure_space(pdf: "FPDF", min_remaining: int = 30) -> None:
    """Добавляет страницу, если осталось мало места."""
    bottom_margin = getattr(pdf, 'b_margin', 15)
    if (pdf.h - bottom_margin - pdf.get_y()) < min_remaining:
        pdf.add_page()

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        # Страницу добавим сразу; шрифт выставляем вызовами _set_font в методах
        self.add_page()
        
    def header(self):
        # Логотип и заголовок
        _set_font(self, 'B', 16)
        self.set_text_color(37, 99, 235)  # Синий цвет
        self.cell(0, 10, BRAND_NAME, 0, 1, 'C')
        
        # Линия под заголовком
        self.set_draw_color(37, 99, 235)
        self.line(20, 25, 190, 25)
        
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        # Не используем курсив, чтобы не требовать Oblique-ttf
        _set_font(self, '', 8)
        self.set_text_color(128, 128, 128)
        footer_text = f'Страница {self.page_no()}'
        self.cell(0, 10, footer_text, 0, 0, 'C')
    
    def add_section_title(self, title: str, emoji: str = ""):
        self.ln(5)
        _set_font(self, 'B', 14)
        self.set_text_color(30, 64, 175)  # Темно-синий
        title_text = title
        self.cell(0, 8, title_text, 0, 1)
        self.ln(2)
    
    def add_field(self, label: str, value: str):
        if not value:
            return
        
        label_text = label
        value_text = value
        
        _set_font(self, 'B', 10)
        self.set_text_color(55, 65, 81)  # Серый
        self.cell(40, 6, f"{label_text}:", 0, 0)
        
        _set_font(self, '', 10)
        self.set_text_color(0, 0, 0)  # Черный
        # Переносим длинные значения
        if len(value_text) > 50:
            self.cell(0, 6, value_text[:47] + "...", 0, 1)
        else:
            self.cell(0, 6, value_text, 0, 1)
    
    def add_locked_field(self, text: str):
        _set_font(self, '', 9)
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
    log.info("PDF start", mode=mode, company_name=company.short_name)
    log.debug("PDF: company data", 
              inn=company.inn, 
              ogrn=company.ogrn, 
              has_contacts=bool(company.contacts),
              finance_count=len(company.finance),
              founders_count=len(company.founders))
    
    pdf = PDFReport()
    # Проверим доступность шрифтов сразу, чтобы при их отсутствии отдать управление вызывающему коду
    _set_font(pdf, 'B', 20)
    
    # Заголовок отчета
    _set_font(pdf, 'B', 20)
    pdf.set_text_color(30, 64, 175)
    title = f"{BRAND_NAME}: {'Бесплатный' if mode == 'free' else 'Полный'} отчёт"
    pdf.cell(0, 15, title, 0, 1, 'C')
    
    # Информация о компании
    pdf.add_section_title("Карточка компании", "")
    
    pdf.add_field("Название", company.short_name)
    if company.full_name and company.full_name != company.short_name:
        pdf.add_field("Полное наименование", company.full_name)
    row(pdf, "ИНН:", company.inn)
    row(pdf, "ОГРН:", company.ogrn)
    if company.ogrn_date:
        row(pdf, "Дата ОГРН:", company.ogrn_date)
    row(pdf, "КПП:", getattr(company, "kpp", None))
    row(pdf, "Статус:", company.status)
    row(pdf, "Дата регистрации:", company.reg_date)
    row(pdf, "Адрес:", company.address)
    row(pdf, "Руководитель:", company.director)
    
    # Деятельность
    if company.okved_main or company.okved_additional:
        pdf.add_section_title("Деятельность", "")
        # Основной ОКВЭД: код — наименование (если доступно)
        okved_code, okved_title = None, None
        try:
            ok_main_detail = getattr(company, "okveds", {}).get("main_detail")
            if ok_main_detail and isinstance(ok_main_detail, (list, tuple)):
                okved_code, okved_title = ok_main_detail[0], ok_main_detail[1]
        except Exception:
            pass
        if not okved_code and company.okved_main:
            okved_code = company.okved_main
        okved_line = f"{okved_code or ''} — {okved_title or ''}".strip().strip("—").strip()
        row(pdf, "Основной вид деятельности:", okved_line or company.okved_main)
        
        if company.okved_additional:
            if mode == "free":
                pdf.add_locked_field(f"Дополнительные виды: {len(company.okved_additional)} шт. — доступно в платном отчёте")
            else:
                _set_font(pdf, 'B', 10)
                pdf.cell(0, 6, "Дополнительные виды деятельности:", 0, 1)
                for okved in company.okved_additional[:10]:
                    _set_font(pdf, '', 9)
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
                _set_font(pdf, 'B', 10)
                pdf.cell(0, 6, "Коды статистики:", 0, 1)
                for code, value in company.stats_codes.items():
                    _set_font(pdf, '', 9)
                    pdf.cell(0, 5, f"• {code}: {value}", 0, 1)
    
    # Контакты
    if company.contacts:
        pdf.add_section_title("Контакты", "")
        for contact_type, values in company.contacts.items():
            if values:
                if mode == "free":
                    pdf.add_locked_field(f"{contact_type.title()}: {len(values)} контактов — доступно в платном отчёте")
                else:
                    _set_font(pdf, 'B', 10)
                    pdf.cell(0, 6, f"{contact_type.title()}:", 0, 1)
                    for value in values:
                        _set_font(pdf, '', 9)
                        pdf.cell(0, 5, f"• {value}", 0, 1)

    # Связи (приоритетно во FULL): агрегаты
    if mode == "full":
        pdf.add_section_title("Связи", "")
        founders_count = len(getattr(company, 'founders', []) or [])
        directors = getattr(company, 'director', None)
        row(pdf, "Учредители:", f"{founders_count} шт.")
        row(pdf, "Руководитель:", directors)
    
    # Финансы (приоритетно во FULL, лимит 5 лет)
    if company.finance:
        pdf.add_section_title("Финансы", "")
        if mode == "free":
            pdf.add_locked_field(f"Данные за {len(company.finance)} лет — доступно в платном отчёте")
        else:
            _set_font(pdf, 'B', 10)
            pdf.cell(30, 6, "Год", 1, 0, 'C')
            pdf.cell(40, 6, "Выручка", 1, 0, 'C')
            pdf.cell(40, 6, "Прибыль", 1, 0, 'C')
            pdf.cell(40, 6, "Активы", 1, 0, 'C')
            pdf.cell(40, 6, "Обязательства", 1, 1, 'C')
            years_sorted = sorted(company.finance, key=lambda x: x.year, reverse=True)[:5]
            for fy in years_sorted:
                _set_font(pdf, '', 9)
                pdf.cell(30, 6, str(fy.year), 1, 0, 'C')
                pdf.cell(40, 6, fy.revenue or '-', 1, 0, 'C')
                pdf.cell(40, 6, fy.profit or '-', 1, 0, 'C')
                pdf.cell(40, 6, fy.assets or '-', 1, 0, 'C')
                pdf.cell(40, 6, fy.liabilities or '-', 1, 1, 'C')
            if len(company.finance) > 5:
                _set_font(pdf, '', 9)
                pdf.cell(0, 6, f"… и ещё {len(company.finance) - 5} лет", 0, 1)
    
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
                    _set_font(pdf, '', 9)
                    pdf.cell(0, 5, f"[!] {flag}", 0, 1)
            else:
                _set_font(pdf, '', 10)
                pdf.set_text_color(16, 185, 129)  # Зеленый
                pdf.cell(0, 6, "[OK] Правовых нарушений не обнаружено", 0, 1)
    
    # Суды и исполнительные производства (FULL)
    if mode == "full":
        ensure_space(pdf)
        pdf.add_section_title("Суды и исполнительные производства", "")
        # Заглушка: выводим счётчики, если представлены во flags/extra
        try:
            extra = getattr(company, 'extra', {}) or {}
            courts = extra.get('courts', {})
            execs = extra.get('executions', {})
            row(pdf, "Арбитражные дела:", str(courts.get('count', '—')))
            row(pdf, "Исп. производства:", str(execs.get('count', '—')))
        except Exception:
            pass
    
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
                _set_font(pdf, '', 9)
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
                _set_font(pdf, '', 9)
                pdf.cell(0, 5, f"• {license_info}", 0, 1)
    
    # Госзакупки / Проверки / История (FULL)
    if mode == "full":
        ensure_space(pdf)
        pdf.add_section_title("Госзакупки", "")
        try:
            extra = getattr(company, 'extra', {}) or {}
            proc = extra.get('procurements', {})
            row(pdf, "Всего закупок:", str(proc.get('count', '—')))
            row(pdf, "Сумма:", str(proc.get('sum', '—')))
        except Exception:
            pass
        ensure_space(pdf)
        pdf.add_section_title("Проверки", "")
        try:
            checks = extra.get('checks', {})
            row(pdf, "Всего:", str(checks.get('total', '—')))
            row(pdf, "С нарушениями:", str(checks.get('with_violations', '—')))
        except Exception:
            pass
        ensure_space(pdf)
        pdf.add_section_title("История", "")
        try:
            events = extra.get('events', {})
            recent = events.get('recent', [])[:5]
            for ev in recent:
                _set_font(pdf, '', 9)
                pdf.cell(0, 5, f"• {ev}", 0, 1)
        except Exception:
            pass

    # Дополнительные обзорные разделы (free: только замки)
    if mode == "free":
        pdf.add_section_title("Суды", "")
        pdf.add_locked_field(lock())
        pdf.add_section_title("Исполнительные производства", "")
        pdf.add_locked_field(lock())
        pdf.add_section_title("Госзакупки", "")
        pdf.add_locked_field(lock())
        pdf.add_section_title("Проверки", "")
        pdf.add_locked_field(lock())
        pdf.add_section_title("Связи", "")
        pdf.add_locked_field(lock())
        pdf.add_section_title("Товарные знаки", "")
        pdf.add_locked_field(lock())
    
    # Подпись
    pdf.ln(10)
    _set_font(pdf, '', 10)
    pdf.set_text_color(107, 114, 128)  # Серый
    pdf.cell(0, 6, f"Подпись: {BRAND_LINK}", 0, 1, 'C')
    pdf.cell(0, 6, f"Дата формирования: {datetime.now().strftime(DATE_FORMAT)}", 0, 1, 'C')
    
    try:
        log.debug("PDF output", mode=mode, company_name=company.short_name)
        pdf_bytes = pdf.output(dest="S")
        log.info("PDF generated", mode=mode, company_name=company.short_name, size=len(pdf_bytes))
        return pdf_bytes
    except (FPDFUnicodeEncodingException, FileNotFoundError) as e:
        # Явно подсказываем про шрифты/юникод
        log.warning(
            "PDF failed; ensure DejaVu fonts in assets/fonts (see README).",
            mode=mode,
            company_name=company.short_name,
            exc_info=e,
        )
        raise
    except Exception as e:
        log.warning("PDF failed", mode=mode, company_name=company.short_name, exc_info=e)
        raise
