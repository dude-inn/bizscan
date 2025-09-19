# -*- coding: utf-8 -*-
"""
Обработчики для работы с компаниями (новая архитектура)
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
from services.enrichment.official_sources import build_official_links
from services.enrichment.openai_gamma_enricher import generate_gamma_section
from core.logger import setup_logging
from services.providers.ofdata import OFDataClientError, OFDataServerTemporaryError
from settings import (
    REQUEST_TIMEOUT, MAX_RETRIES
)

router = Router(name="company")
log = setup_logging()


@router.callback_query(F.data == "back_results")
async def back_results(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Возвращаемся к результатам…")
    await cb.answer()
    await __import__("bot.handlers.search", fromlist=['']).show_page(cb.message, state)


@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    log.info("back_main: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем приветственное сообщение с главным меню
    await cb.message.answer(
        "🏢 Добро пожаловать в BizScan Bot!\n\n"
        "Выберите действие:",
        reply_markup=report_menu_kb()
    )
    
    await cb.answer()


@router.callback_query(F.data == "report_free")
async def free_report(cb: CallbackQuery, state: FSMContext):
    """Генерация бесплатного отчёта"""
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
        
        # Получаем отчёт компании
        log.info("Fetching company report", query=query, user_id=cb.from_user.id)
        response = await fetch_company_report_markdown(query)
        
        if not response or response.startswith("Укажите корректный"):
            log.warning("Invalid query or company not found", query=query, user_id=cb.from_user.id)
            await status_msg.edit_text("❌ Компания не найдена или некорректный ИНН/ОГРН")
            return
        
        log.info("Company report fetched successfully", 
                query=query,
                response_length=len(response),
                user_id=cb.from_user.id)
        
        # Отчет готов, не выводим его в сообщение
        log.info("Report generated successfully", response_length=len(response), user_id=cb.from_user.id)
        
        # Добавляем кнопку для скачивания JSON
        log.info("Adding keyboard buttons", user_id=cb.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Скачать TXT", callback_data="download_txt")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_inn")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
        
        await status_msg.edit_text(
            "✅ Отчет готов! Нажмите кнопку ниже для скачивания файла.",
            reply_markup=keyboard
        )
        log.info("Free report completed successfully", user_id=cb.from_user.id)
        
        # Сохраняем данные в состоянии для скачивания TXT
        await state.update_data(company_text=response)

        # Вывод Gamma-блока отключён по требованиям UX
        
    except (OFDataClientError) as e:
        if "404" in str(e) or "409" in str(e):
            await status_msg.edit_text("❌ Контрагент не найден по указанным данным.")
        elif "403" in str(e) or "401" in str(e):
            await status_msg.edit_text("❌ Доступ к источнику ограничен или неверный ключ.")
        elif "404" in str(e) and "Страница не найдена" in str(e):
            await status_msg.edit_text("❌ Источник данных недоступен. Проверьте настройки API ключа.")
        else:
            await status_msg.edit_text(f"❌ Ошибка получения данных: {str(e)}")
    except (OFDataServerTemporaryError) as e:
        await status_msg.edit_text("❌ Источник временно недоступен, повторите позже.")
    except Exception as e:
        log.error("Free report failed", 
                 error=str(e), 
                 user_id=cb.from_user.id,
                 query=query if 'query' in locals() else None)
        await status_msg.edit_text(f"❌ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "download_txt")
async def download_txt(cb: CallbackQuery, state: FSMContext):
    """Скачивание TXT отчёта"""
    log.info("download_txt: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    await cb.answer()
    
    try:
        data = await state.get_data()
        company_text = data.get("company_text")
        
        if not company_text:
            await cb.message.answer("❌ Данные не найдены. Выполните поиск заново.")
            return
        
        # Извлекаем название компании из текста отчета
        lines = company_text.split('\n')
        company_name = "company"
        for line in lines:
            # Ищем строку с названием компании (обычно это первая строка после "🧾 **Реквизиты**")
            if line and not line.startswith('🧾') and not line.startswith('ИНН') and not line.startswith('📅') and not line.startswith('**Статус**'):
                if len(line) > 5:  # Игнорируем короткие строки
                    company_name = line.strip()
                    break
        
        safe_name = "".join(ch for ch in company_name if ch.isalnum() or ch in (" ", "_", "-"))[:64]
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{safe_name}_{today}.txt"
        
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write(company_text)
            tmp_path = tmp.name
        
        await cb.message.answer_document(
            FSInputFile(tmp_path, filename=filename),
            caption="📝 TXT отчёт о компании"
        )
        
        import os
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        
    except Exception as e:
        log.exception("download_txt: failed", exc_info=e)
        await cb.message.answer(f"❌ Ошибка при создании TXT: {str(e)}")


@router.callback_query(F.data == "report_paid")
async def paid_report(cb: CallbackQuery, state: FSMContext):
    """Платный отчёт (пока не реализован)"""
    log.info("paid_report: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    await cb.answer()
    await cb.message.answer(
        "💰 Платные отчёты пока не реализованы.\n"
        "Используйте бесплатный отчёт для получения базовой информации."
    )


@router.callback_query(F.data == "report_txt")
async def report_txt(cb: CallbackQuery, state: FSMContext):
    """Текстовый дамп (устаревший функционал)"""
    log.info("report_txt: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    await cb.answer()
    await cb.message.answer(
        "📝 Текстовые дампы заменены на структурированные данные.\n"
        "Используйте бесплатный отчёт для получения информации о компании."
    )