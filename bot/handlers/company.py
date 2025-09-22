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
