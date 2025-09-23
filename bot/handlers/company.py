# -*- coding: utf-8 -*-
"""
Обработчики для работы с компаниями (исправленная версия)
"""
import json
import tempfile
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from bot.states import SearchState, ReportState
from bot.keyboards.main import choose_report_kb, report_menu_kb
from services.aggregator import fetch_company_report_markdown, fetch_company_profile
from core.logger import setup_logging, get_logger

# Настройка логирования
setup_logging()
log = get_logger(__name__)

# Создаём роутер
router = Router(name="company_fixed")

@router.callback_query(F.data == "report_free")
async def free_report(cb: CallbackQuery, state: FSMContext):
    """Генерация бесплатного отчёта"""
    print("DEBUG: free_report handler called")  # Тестовый вывод
    print(f"DEBUG: callback_data={cb.data}, user_id={cb.from_user.id}")  # Дополнительная диагностика
    log.info("free_report: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    # Отвечаем на callback query сразу, чтобы избежать timeout
    try:
        await cb.answer()
    except Exception as e:
        log.warning("Could not answer callback query", error=str(e))
    
    # Показываем индикатор загрузки
    status_msg = await cb.message.answer("⏳ Собираю данные о компании...")
    file_sent = False
    
    try:
        # Получаем данные из состояния
        log.info("Getting state data", user_id=cb.from_user.id)
        data = await state.get_data()
        query = data.get("query", "")
        log.info("State data retrieved", query=query, user_id=cb.from_user.id)
        
        if not query:
            log.warning("No query in state", user_id=cb.from_user.id)
            await status_msg.edit_text("❌ Не указан поисковый запрос")
            return
        
        # Получаем отчёт компании через агрегатор
        log.info("Fetching company report using aggregator", query=query, user_id=cb.from_user.id)
        response = await fetch_company_report_markdown(query)
        log.info("Report generation completed", 
                response_length=len(response) if response else 0, 
                response_preview=response[:200] if response else None,
                user_id=cb.from_user.id)
        
        if not response or response.startswith("❌"):
            log.warning("Invalid query or company not found", query=query, response=response[:200] if response else None, user_id=cb.from_user.id)
            await status_msg.edit_text("❌ Компания не найдена или некорректный ИНН/ОГРН")
            return
        
        log.info("Company report fetched successfully", 
                query=query,
                response_length=len(response),
                user_id=cb.from_user.id)
        
        # (Опционально) попытка сделать PDF через Gamma Generate API
        pdf_path = None
        try:
            from settings import ENABLE_GAMMA_PDF, GAMMA_THEME
            if ENABLE_GAMMA_PDF:
                log.info("Starting Gamma PDF generation", user_id=cb.from_user.id)
                # Обновляем статус о начале PDF генерации
                await status_msg.edit_text("⏳ Формирую PDF-версию отчёта...\n\n📄 Это может занять до 15 минут, так как нужно собрать данные из множества источников и сформировать структурированный PDF.")
                import time
                start_time = time.time()
                
                # Функция для обновления прогресса
                async def update_progress(status, elapsed, timeout):
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    progress_text = f"⏳ Формирую PDF-версию отчёта...\n\n📄 Статус: {status}\n⏰ Прошло: {minutes}м {seconds}с\n\n⏰ Пожалуйста, подождите..."
                    await status_msg.edit_text(progress_text)
                
                from services.export.gamma_exporter import generate_pdf_from_report_text
                pdf_path = generate_pdf_from_report_text(response, language="ru", theme_name=GAMMA_THEME or None, progress_callback=update_progress)
                end_time = time.time()
                log.info("Gamma PDF generation completed", user_id=cb.from_user.id, duration=end_time-start_time, pdf_path=pdf_path)
        except Exception as e:
            log.warning("Gamma PDF failed", error=str(e), user_id=cb.from_user.id)

        # Генерируем DOCX вместо TXT
        log.info("Generating DOCX report", user_id=cb.from_user.id)
        from docx import Document
        from docx.shared import Pt
        from docx.oxml.ns import qn
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        # Базовый стиль
        style = doc.styles['Normal']
        style.font.name = 'Calibri'
        style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
        style.font.size = Pt(11)

        # Разбиваем отчёт по строкам и добавляем абзацы
        for line in response.splitlines():
            if line.strip() == '':
                doc.add_paragraph('')
                continue
            # Заголовки секций (====) делаем жирными
            if set(line.strip()) == {'='} and len(line.strip()) >= 10:
                # Это разделитель — пропускаем, т.к. предыдущая строка уже заголовок
                continue
            p = doc.add_paragraph()
            run = p.add_run(line)
            # Если предыдущая строка была заглавными буквами/заголовком
            if line.isupper() and len(line) < 60:
                run.bold = True

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            doc.save(tmp.name)
            temp_path = tmp.name
        log.info("DOCX report saved", temp_path=temp_path, user_id=cb.from_user.id)
        
        # Отправляем файл пользователю
        log.info("Sending report file to user", user_id=cb.from_user.id)
        with open(temp_path, 'rb') as file:
            document = BufferedInputFile(file.read(), filename="company_report.docx")
            
            await status_msg.edit_text("✅ Отчёт готов!")
            await cb.message.answer_document(
                document,
                caption="📊 Отчёт о компании (DOCX)\n\nФайл содержит полную информацию о компании, включая финансовую отчётность, арбитражные дела, проверки и госзакупки."
            )
            # Если есть PDF — отправим его вторым сообщением
            if pdf_path:
                with open(pdf_path, 'rb') as fpdf:
                    from aiogram.types import BufferedInputFile as BIF
                    await cb.message.answer_document(
                        BIF(fpdf.read(), filename=os.path.basename(pdf_path)),
                        caption="📄 PDF-версия (Gamma)"
                    )
            file_sent = True
        log.info("Report file sent successfully", user_id=cb.from_user.id)
        
        # Удаляем временный файл
        import os
        os.unlink(temp_path)
        log.info("Temporary file deleted", temp_path=temp_path, user_id=cb.from_user.id)
        
        # Переходим в состояние выбора типа отчёта
        await state.set_state(ReportState.choose_report)
        await cb.message.answer(
            "📊 Отчёт сформирован! Выберите действие:",
            reply_markup=choose_report_kb()
        )
        
    except Exception as e:
        log.error("Error in free_report", error=str(e), error_type=type(e).__name__, user_id=cb.from_user.id)
        # Если файл уже отправлен, не затираем успешный статус ошибкой
        if not file_sent:
            await status_msg.edit_text("❌ Произошла ошибка при формировании отчёта")


@router.callback_query(F.data == "report_pdf_gamma")
async def report_pdf_gamma(cb: CallbackQuery, state: FSMContext):
    """Формирует PDF через Gamma по текущему запросу"""
    await cb.answer()
    status = await cb.message.answer("⏳ Формирую PDF через Gamma…")
    try:
        from settings import ENABLE_GAMMA_PDF, GAMMA_THEME
        if not ENABLE_GAMMA_PDF:
            await status.edit_text("❌ PDF через Gamma отключён администратором")
            return
        data = await state.get_data()
        query = data.get("query", "")
        if not query:
            await status.edit_text("❌ Не указан запрос для отчёта")
            return
        report_text = await fetch_company_report_markdown(query)
        if not report_text or report_text.startswith("❌"):
            await status.edit_text("❌ Не удалось получить отчетные данные")
            return
        
        # Обновляем статус с информацией о времени ожидания
        await status.edit_text("⏳ Формирую PDF-версию отчёта...\n\n📄 Это может занять до 15 минут, так как нужно собрать данные из множества источников и сформировать структурированный PDF.\n\n⏰ Пожалуйста, подождите...")
        
        # Функция для обновления прогресса
        async def update_progress(status, elapsed, timeout):
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            progress_text = f"⏳ Формирую PDF-версию отчёта...\n\n📄 Статус: {status}\n⏰ Прошло: {minutes}м {seconds}с\n\n⏰ Пожалуйста, подождите..."
            await status.edit_text(progress_text)
        
        from services.export.gamma_exporter import generate_pdf_from_report_text
        log.info("Starting Gamma PDF generation from button", user_id=cb.from_user.id)
        import time
        start_time = time.time()
        pdf_path = generate_pdf_from_report_text(report_text, language="ru", theme_name=GAMMA_THEME or None, progress_callback=update_progress)
        end_time = time.time()
        log.info("Gamma PDF generation from button completed", user_id=cb.from_user.id, duration=end_time-start_time, pdf_path=pdf_path)
        if not pdf_path:
            await status.edit_text("❌ Не удалось сформировать PDF через Gamma")
            return
        from aiogram.types import BufferedInputFile
        import os
        with open(pdf_path, 'rb') as f:
            await status.edit_text("✅ PDF готов!")
            await cb.message.answer_document(
                BufferedInputFile(f.read(), filename=os.path.basename(pdf_path)),
                caption="📄 PDF-версия (Gamma)"
            )
    except Exception as e:
        log.warning("Gamma PDF button failed", error=str(e))
        await status.edit_text("❌ Ошибка формирования PDF")
