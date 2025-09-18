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
from services.aggregator import fetch_company_profile
from domain.models import CompanyAggregate
from core.logger import setup_logging
from settings import (
    DADATA_API_KEY, DADATA_SECRET_KEY,
    MSME_DATA_URL, MSME_LOCAL_FILE, FEATURE_MSME,
    EFRSB_API_URL, EFRSB_API_KEY, FEATURE_EFRSB,
    KAD_API_URL, KAD_API_KEY, FEATURE_KAD, KAD_MAX_CASES,
    REQUEST_TIMEOUT, MAX_RETRIES
)

router = Router(name="company")
log = setup_logging()


def _format_company_response(company: CompanyAggregate) -> str:
    """Форматирует ответ с информацией о компании"""
    base = company.base
    
    # Заголовок
    response = f"🧾 **Реквизиты**\n"
    response += f"{base.name_full}"
    if base.name_short and base.name_short != base.name_full:
        response += f" • {base.name_short}"
    response += f"\nИНН {base.inn}"
    if base.ogrn:
        response += f" • ОГРН {base.ogrn}"
    if base.kpp:
        response += f" • КПП {base.kpp}"
    
    # Адрес
    if base.address:
        qc_info = f" (qc={base.address_qc})" if base.address_qc else ""
        response += f"\n📍 **Адрес:** {base.address}{qc_info}"
    
    # Даты и статус
    if base.registration_date:
        response += f"\n📅 **Регистрация:** {base.registration_date.strftime('%Y-%m-%d')}"
    if base.liquidation_date:
        response += f" • **Ликвидация:** {base.liquidation_date.strftime('%Y-%m-%d')}"
    
    status_emoji = {
        "ACTIVE": "✅",
        "LIQUIDATING": "⚠️", 
        "LIQUIDATED": "❌",
        "UNKNOWN": "❓"
    }
    response += f"\n**Статус:** {status_emoji.get(base.status, '❓')} {base.status}"
    
    # ОКВЭД
    if base.okved:
        response += f"\n🏷️ **ОКВЭД:** {base.okved}"
    
    # Руководитель
    if base.management_name:
        post = f" — {base.management_post}" if base.management_post else ""
        response += f"\n\n🧑‍💼 **Руководитель**\n{base.management_name}{post}"
    
    # МСП
    if company.msme and company.msme.is_msme:
        category_names = {
            "micro": "микро",
            "small": "малое", 
            "medium": "среднее"
        }
        category = category_names.get(company.msme.category, company.msme.category)
        period = f" (на {company.msme.period})" if company.msme.period else ""
        response += f"\n\n🧩 **МСП**\nКатегория: {category}{period}"
    elif company.msme:
        response += f"\n\n🧩 **МСП**\nНе является субъектом МСП"
    
    # Банкротство
    if company.bankruptcy:
        if company.bankruptcy.has_bankruptcy_records:
            response += f"\n\n⚖️ **Банкротство**\nНайдено {len(company.bankruptcy.records)} записей"
            for i, record in enumerate(company.bankruptcy.records[:3], 1):
                response += f"\n{i}. {record.get('number', 'N/A')} — {record.get('stage', 'N/A')}"
        else:
            response += f"\n\n⚖️ **Банкротство**\nНет записей"
    
    # Арбитраж
    if company.arbitration and company.arbitration.total > 0:
        response += f"\n\n📄 **Арбитраж** (последние {len(company.arbitration.cases)} из {company.arbitration.total})"
        for i, case in enumerate(company.arbitration.cases[:3], 1):
            roles = ", ".join(case.get("roles", []))
            date_str = case.get("date", "N/A")
            instance = case.get("instance", "N/A")
            response += f"\n{i}. {case.get('number', 'N/A')} — {roles}, {date_str} — {instance}"
    elif company.arbitration:
        response += f"\n\n📄 **Арбитраж**\nНет дел"
    
    # Источники
    sources = []
    for source, version in company.sources.items():
        sources.append(f"{source} ({version})")
    response += f"\n\n🔗 **Источники:** {', '.join(sources)}"
    
    return response


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
        
        # Получаем профиль компании
        log.info("Fetching company profile", query=query, user_id=cb.from_user.id)
        company = await fetch_company_profile(
            query=query,
            dadata_api_key=DADATA_API_KEY,
            dadata_secret_key=DADATA_SECRET_KEY,
            msme_data_url=MSME_DATA_URL,
            msme_local_file=MSME_LOCAL_FILE,
            efrsb_api_url=EFRSB_API_URL,
            efrsb_api_key=EFRSB_API_KEY,
            efrsb_enabled=FEATURE_EFRSB,
            kad_api_url=KAD_API_URL,
            kad_api_key=KAD_API_KEY,
            kad_enabled=FEATURE_KAD,
            kad_max_cases=KAD_MAX_CASES,
            request_timeout=REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES
        )
        
        if not company:
            log.warning("Company not found", query=query, user_id=cb.from_user.id)
            await status_msg.edit_text("❌ Компания не найдена")
            return
        
        log.info("Company profile fetched successfully", 
                company_name=company.base.name_full,
                inn=company.base.inn,
                user_id=cb.from_user.id)
        
        # Форматируем ответ
        log.info("Formatting company response", user_id=cb.from_user.id)
        response = _format_company_response(company)
        
        # Разбиваем на части если слишком длинный
        log.info("Checking response length", response_length=len(response), user_id=cb.from_user.id)
        if len(response) > 4096:
            log.info("Response too long, splitting into parts", user_id=cb.from_user.id)
            parts = []
            current = ""
            for line in response.split('\n'):
                if len(current + line + '\n') > 4000:
                    parts.append(current.strip())
                    current = line + '\n'
                else:
                    current += line + '\n'
            if current.strip():
                parts.append(current.strip())
            
            log.info("Response split into parts", parts_count=len(parts), user_id=cb.from_user.id)
            # Отправляем части
            for i, part in enumerate(parts):
                if i == 0:
                    await status_msg.edit_text(part, parse_mode="Markdown")
                else:
                    await cb.message.answer(part, parse_mode="Markdown")
        else:
            log.info("Sending single response", user_id=cb.from_user.id)
            await status_msg.edit_text(response, parse_mode="Markdown")
        
        # Добавляем кнопку для скачивания JSON
        log.info("Adding keyboard buttons", user_id=cb.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Скачать JSON", callback_data="download_json")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_inn")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
        
        await cb.message.answer(
            "✅ Данные получены!",
            reply_markup=keyboard
        )
        log.info("Free report completed successfully", user_id=cb.from_user.id)
        
        # Сохраняем данные в состоянии для скачивания JSON
        await state.update_data(company_data=company.dict())
        
    except Exception as e:
        log.error("Free report failed", 
                 error=str(e), 
                 user_id=cb.from_user.id,
                 query=query if 'query' in locals() else None)
        await status_msg.edit_text(f"❌ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "download_json")
async def download_json(cb: CallbackQuery, state: FSMContext):
    """Скачивание JSON данных"""
    log.info("download_json: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    await cb.answer()
    
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        company_data = data.get("company_data")
        
        if not company_data:
            await cb.message.answer("❌ Данные не найдены. Выполните поиск заново.")
            return
        
        # Создаем JSON файл
        json_str = json.dumps(company_data, ensure_ascii=False, indent=2, default=str)
        
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(json_str)
            tmp_path = tmp.name
        
        # Отправляем файл
        company_name = company_data.get("base", {}).get("name_short", "company")
        filename = f"{company_name}_data.json"
        
        await cb.message.answer_document(
            FSInputFile(tmp_path, filename=filename),
            caption="📄 JSON данные о компании"
        )
        
        # Удаляем временный файл
        import os
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        
    except Exception as e:
        log.exception("download_json: failed", exc_info=e)
        await cb.message.answer(f"❌ Ошибка при создании JSON: {str(e)}")


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