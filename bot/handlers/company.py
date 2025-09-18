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
    
    # Финансы (DataNewton)
    if company.finances:
        response += f"\n\n📊 **Финансы (DataNewton)**"
        for finance in company.finances[-3:]:  # Последние 3 года
            year = finance.period
            revenue = f"{finance.revenue:,.0f}" if finance.revenue else "N/A"
            profit = f"{finance.net_profit:,.0f}" if finance.net_profit else "N/A"
            assets = f"{finance.assets:,.0f}" if finance.assets else "N/A"
            response += f"\n{year}: выручка {revenue}₽, прибыль {profit}₽, активы {assets}₽"
    
    # Закупки (ЕИС)
    if company.procurement:
        contracts = company.procurement.total_contracts
        amount = f"{company.procurement.total_amount:,.0f}₽" if company.procurement.total_amount else "N/A"
        last_date = company.procurement.last_contract_date.strftime('%Y-%m-%d') if company.procurement.last_contract_date else "N/A"
        response += f"\n\n🛒 **Закупки (ЕИС)**\nКонтрактов: {contracts}, сумма: {amount}, последний: {last_date}"
    
    # Лицензии (РАР)
    if company.licenses:
        active_licenses = [l for l in company.licenses if l.status == "ACTIVE"]
        inactive_licenses = [l for l in company.licenses if l.status != "ACTIVE"]
        
        response += f"\n\n🥃 **Лицензии (РАР)**"
        if active_licenses:
            response += f"\nАктивные ({len(active_licenses)}):"
            for license in active_licenses[:3]:
                activity = license.activity or "N/A"
                valid_to = license.valid_to.strftime('%Y-%m-%d') if license.valid_to else "N/A"
                response += f"\n• {license.number} — {activity} (до {valid_to})"
        
        if inactive_licenses:
            response += f"\nПрекращенные ({len(inactive_licenses)}):"
            for license in inactive_licenses[:2]:
                activity = license.activity or "N/A"
                response += f"\n• {license.number} — {activity}"
    
    # DataNewton extras
    extras = getattr(company, "extra", {}) or {}

    # Risks
    risks = extras.get("risks") or {}
    flags = risks.get("flags") or []
    if flags:
        true_flags = [f for f in flags if f.get("value") is True]
        if true_flags:
            response += f"\n\n🚩 **Риски (DataNewton)**\nАктивных признаков: {len(true_flags)}"
            for f in true_flags[:5]:
                name = f.get("name", "?")
                ftype = f.get("type", "?")
                response += f"\n• {name} ({ftype})"

    # Tax info (fines/debts and offences)
    tax_info = extras.get("tax_info") or {}
    fines_debts = (tax_info.get("fines_debts") or [])
    tax_off = (tax_info.get("tax_offences") or [])
    if fines_debts or tax_off:
        response += f"\n\n💼 **Налоги (DataNewton)**"
        if fines_debts:
            last_fd = fines_debts[-1]
            arrears = sum((item.get("total_sum") or 0) for item in (last_fd.get("arrears_sum_infos") or []))
            response += f"\nЗадолженности/штрафы (посл.): {arrears:,.0f}₽"
        if tax_off:
            response += f"\nНарушения: {len(tax_off)}"

    # Paid taxes summary
    paid = extras.get("paid_taxes") or {}
    paid_data = paid.get("data") or []
    if paid_data:
        last = paid_data[-1]
        report_date = last.get("report_date", "")
        total_paid = 0.0
        for t in (last.get("tax_info_list") or []):
            try:
                total_paid += float(str(t.get("taxValue", "0")).replace(" ", ""))
            except Exception:
                pass
        response += f"\n\n💳 **Уплаченные налоги (DataNewton)**\n{report_date}: всего {total_paid:,.0f}₽"

    # Procurement summary (DN)
    ps = extras.get("procure_summary") or {}
    if ps:
        total_cnt = ps.get("total_contracts") or ps.get("count") or ps.get("contracts_count")
        total_amt = ps.get("total_amount") or ps.get("amount")
        response += "\n\n🛒 **Закупки (DataNewton)**"
        if total_cnt is not None:
            response += f"\nКонтрактов: {total_cnt}"
        if total_amt is not None:
            try:
                response += f"\nСумма: {float(total_amt):,.0f}₽"
            except Exception:
                response += f"\nСумма: {total_amt}₽"

    # Certificates (DN)
    certs = extras.get("certificates") or []
    if isinstance(certs, dict):
        cert_list = certs.get("items") or []
    else:
        cert_list = certs
    if cert_list:
        response += f"\n\n📜 **Сертификаты/декларации (DataNewton)**\nЗаписей: {len(cert_list)}"

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
            [InlineKeyboardButton(text="📝 Скачать TXT", callback_data="download_txt")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_inn")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
        
        await cb.message.answer(
            "✅ Данные получены!",
            reply_markup=keyboard
        )
        log.info("Free report completed successfully", user_id=cb.from_user.id)
        
        # Сохраняем данные в состоянии для скачивания JSON
        await state.update_data(company_data=company.dict(), company_text=response)
        
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
        company_data = data.get("company_data")
        
        if not company_text or not company_data:
            await cb.message.answer("❌ Данные не найдены. Выполните поиск заново.")
            return
        
        company_name = company_data.get("base", {}).get("name_short") or company_data.get("base", {}).get("name_full", "company")
        safe_name = "".join(ch for ch in company_name if ch.isalnum() or ch in (" ", "_", "-"))[:64]
        filename = f"{safe_name}_report.txt"
        
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