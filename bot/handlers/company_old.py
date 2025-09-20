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
from services.report.builder import ReportBuilder
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
    
    await cb.answer()
    
    # Показываем индикатор загрузки
    status_msg = await cb.message.answer("⏳ Собираю данные о компании...")
    
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
        
        # Получаем отчёт компании через новую систему
        log.info("Fetching company report using new system", query=query, user_id=cb.from_user.id)
        
        # Создаём экземпляр нового сборщика отчётов
        log.info("Creating ReportBuilder instance", user_id=cb.from_user.id)
        builder = ReportBuilder()
        log.info("ReportBuilder created successfully", user_id=cb.from_user.id)
        
        # Определяем тип идентификатора
        log.info("Determining identifier type", query=query, user_id=cb.from_user.id)
        if query.isdigit() and len(query) in [10, 12]:
            if len(query) == 10:
                ident = {'inn': query}
                log.info("Using INN identifier", inn=query, user_id=cb.from_user.id)
            else:
                ident = {'ogrn': query}
                log.info("Using OGRN identifier", ogrn=query, user_id=cb.from_user.id)
        else:
            # Поиск по названию
            ident = {'name': query}
            log.info("Using name identifier", name=query, user_id=cb.from_user.id)
        
        # Генерируем отчёт с полным набором секций
        log.info("Starting report generation", ident=ident, user_id=cb.from_user.id)
        response = builder.build_simple_report(
            ident=ident,
            include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
            max_rows=100
        )
        log.info("Report generation completed", response_length=len(response) if response else 0, user_id=cb.from_user.id)
        
        if not response or response.startswith("❌"):
            log.warning("Invalid query or company not found", query=query, response=response[:200] if response else None, user_id=cb.from_user.id)
            await status_msg.edit_text("❌ Компания не найдена или некорректный ИНН/ОГРН")
            return
        
        log.info("Company report fetched successfully", 
                query=query,
                response_length=len(response),
                user_id=cb.from_user.id)
        
        # Сохраняем отчёт в файл
        log.info("Saving report to temporary file", user_id=cb.from_user.id)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            f.write(response)
            temp_path = f.name
        log.info("Report saved to temporary file", temp_path=temp_path, user_id=cb.from_user.id)
        
        # Отправляем файл пользователю
        log.info("Sending report file to user", user_id=cb.from_user.id)
        with open(temp_path, 'rb') as file:
            document = BufferedInputFile(
                file.read(),
                filename="company_report.txt"
            )
            
            await status_msg.edit_text("✅ Отчёт готов!")
            await cb.message.answer_document(
                document,
                caption="📊 Отчёт о компании\n\nФайл содержит полную информацию о компании, включая финансовую отчётность, арбитражные дела, проверки и госзакупки."
            )
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
        await status_msg.edit_text("❌ Произошла ошибка при формировании отчёта")
