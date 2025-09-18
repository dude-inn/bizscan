# -*- coding: utf-8 -*-
"""
Обработчики поиска компаний (новая архитектура)
"""
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.keyboards.main import main_menu_kb, report_menu_kb, results_kb, choose_report_kb
from bot.states import SearchState, MenuState
from core.logger import setup_logging
from services.providers.datanewton import get_dn_client
from services.mappers.datanewton import map_company_core_to_base

router = Router(name="search")
log = setup_logging()


def _normalize_query(query: str) -> str:
    """Нормализует поисковый запрос"""
    # Убираем лишние пробелы
    query = re.sub(r'\s+', ' ', query.strip())
    return query


def _is_inn(query: str) -> bool:
    """Проверяет, является ли запрос ИНН"""
    return re.match(r'^\d{10}$|^\d{12}$', query) is not None


def _is_ogrn(query: str) -> bool:
    """Проверяет, является ли запрос ОГРН"""
    return re.match(r'^\d{13}$|^\d{15}$', query) is not None


@router.callback_query(F.data == "search_inn")
async def ask_inn(cb: CallbackQuery, state: FSMContext):
    """Запрос ИНН/ОГРН/названия для поиска"""
    await cb.message.edit_text(
        "🔍 **Поиск компании**\n\n"
        "Введите:\n"
        "• ИНН (10 или 12 цифр)\n"
        "• ОГРН (13 или 15 цифр)\n"
        "• Название компании",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
    )
    await state.set_state(SearchState.ASK_INN)
    await cb.answer()


async def _show_company_choices(message_or_cb, companies: list, state: FSMContext):
    """Показывает список найденных компаний для выбора"""
    if not companies:
        await message_or_cb.answer("❌ Ничего не найдено. Уточните запрос.",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                       [InlineKeyboardButton(text="🔙 Назад", callback_data="back_search")],
                                       [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                                   ]))
        return

    # Если одна компания — сразу сохраняем выбор
    if len(companies) == 1:
        company = companies[0]
        await state.update_data(query=company.inn)
        await message_or_cb.answer(
            f"✅ Найдено: {company.name_full} — ИНН {company.inn}\nВыберите тип отчёта:",
            reply_markup=choose_report_kb()
        )
        await state.set_state(SearchState.SELECT)
        return

    # Несколько — показываем кнопки
    buttons = []
    for c in companies[:10]:
        title = c.name_short or c.name_full
        title = f"{title[:48]}" if len(title) > 48 else title
        buttons.append([InlineKeyboardButton(text=f"{title} — {c.inn}", callback_data=f"select_company:{c.inn}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_search")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])

    await message_or_cb.answer(
        "📄 Найдено несколько компаний. Выберите нужную:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(SearchState.PAGING)


@router.message(SearchState.ASK_INN)
async def got_query(msg: Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = _normalize_query(msg.text or "")
    
    if len(query) < 2:
        await msg.answer("❌ Слишком короткий запрос. Повторите.")
        return
    
    # Если это ИНН/ОГРН — сразу сохраняем и предлагаем отчёт
    if _is_inn(query) or _is_ogrn(query):
        await state.update_data(query=query)
        await msg.answer(
            "✅ Запрос сохранён. Выберите тип отчёта:",
            reply_markup=choose_report_kb()
        )
        await state.set_state(SearchState.SELECT)
        return

    # Иначе — это название: запросим подсказки DaData и покажем список
    await msg.answer(f"🔍 Ищу по названию: {query}")
    companies = []
    try:
        client = get_dn_client()
        if client:
            s = client.suggestions(query, type="all")
            items = (s or {}).get("data") or []
            for it in items[:10]:
                core = client.get_company_core(it.get("inn") or it.get("ogrn") or "")
                base = map_company_core_to_base(core or {})
                if base:
                    companies.append(base)
    except Exception as e:
        log.error("DN name search failed", query=query, error=str(e))
        # Fallback to resolve_party if available
        try:
            client = client or get_dn_client()
            if client:
                r = client.resolve_party(query)
                items = (r or {}).get("data") or []
                for it in items[:10]:
                    core = client.get_company_core(it.get("inn") or it.get("ogrn") or "")
                    base = map_company_core_to_base(core or {})
                    if base:
                        companies.append(base)
        except Exception as e2:
            log.error("DN resolve fallback failed", query=query, error=str(e2))
    await _show_company_choices(msg, companies, state)


@router.callback_query(F.data == "back_search")
async def back_to_search(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "🔍 **Поиск компании**\n\nВведите ИНН/ОГРН/название:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
    )
    await state.set_state(SearchState.ASK_INN)
    await cb.answer()


@router.callback_query(F.data.startswith("select_company:"))
async def select_company(cb: CallbackQuery, state: FSMContext):
    inn = cb.data.split(":", 1)[1]
    await state.update_data(query=inn)
    await cb.message.edit_text(
        f"✅ Выбрано: ИНН {inn}. Выберите тип отчёта:",
        reply_markup=choose_report_kb()
    )
    await state.set_state(SearchState.SELECT)
    await cb.answer()


@router.callback_query(F.data == "search_name")
async def ask_name(cb: CallbackQuery, state: FSMContext):
    """Альтернативный способ поиска по названию"""
    await cb.message.edit_text("Введите название компании:")
    await state.set_state(SearchState.ASK_NAME)
    await cb.answer()


@router.message(SearchState.ASK_NAME)
async def got_name(msg: Message, state: FSMContext):
    """Обработка поиска по названию"""
    query = _normalize_query(msg.text or "")
    
    if len(query) < 2:
        await msg.answer("❌ Слишком короткий запрос. Повторите.")
        return
    
    await msg.answer(f"🔍 Ищу: {query}")
    companies = []
    try:
        client = get_dn_client()
        if client:
            s = client.suggestions(query, type="all")
            items = (s or {}).get("data") or []
            for it in items[:10]:
                core = client.get_company_core(it.get("inn") or it.get("ogrn") or "")
                base = map_company_core_to_base(core or {})
                if base:
                    companies.append(base)
    except Exception as e:
        log.error("DN name search failed", query=query, error=str(e))
        try:
            client = client or get_dn_client()
            if client:
                r = client.resolve_party(query)
                items = (r or {}).get("data") or []
                for it in items[:10]:
                    core = client.get_company_core(it.get("inn") or it.get("ogrn") or "")
                    base = map_company_core_to_base(core or {})
                    if base:
                        companies.append(base)
        except Exception as e2:
            log.error("DN resolve fallback failed", query=query, error=str(e2))
    await _show_company_choices(msg, companies, state)


async def show_page(msg_or_cbmsg, state: FSMContext):
    """Показ страницы результатов (устаревший функционал)"""
    await msg_or_cbmsg.answer(
        "ℹ️ В новой версии поиск выполняется автоматически при выборе/выборе компании."
    )


@router.callback_query(F.data.startswith("page:"))
async def page_nav(cb: CallbackQuery, state: FSMContext):
    """Навигация по страницам (устаревший функционал)"""
    await cb.answer("ℹ️ Пагинация не используется в новой версии")


@router.message(SearchState.PAGING)
async def select_by_number(msg: Message, state: FSMContext):
    """Выбор по номеру (устаревший функционал)"""
    await msg.answer("ℹ️ Используйте кнопки ниже для выбора компании")


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery, state: FSMContext):
    """Пустой обработчик"""
    await cb.answer()