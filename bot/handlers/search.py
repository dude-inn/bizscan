# -*- coding: utf-8 -*-
"""
Обработчики поиска компаний (новая архитектура)
"""
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.main import main_menu_kb, report_menu_kb, results_kb, choose_report_kb
from bot.states import SearchState, MenuState
from core.logger import setup_logging

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
        "• Название компании"
    )
    await state.set_state(SearchState.ASK_INN)
    await cb.answer()


@router.message(SearchState.ASK_INN)
async def got_query(msg: Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = _normalize_query(msg.text or "")
    
    if len(query) < 2:
        await msg.answer("❌ Слишком короткий запрос. Повторите.")
        return
    
    # Сохраняем запрос в состоянии
    await state.update_data(query=query)
    
    # Определяем тип запроса
    if _is_inn(query):
        query_type = "ИНН"
    elif _is_ogrn(query):
        query_type = "ОГРН"
    else:
        query_type = "название"
    
    await msg.answer(f"🔍 Ищу по {query_type}: {query}")
    
    # Показываем выбор типа отчёта
    await msg.answer(
        "✅ Запрос сохранён. Выберите тип отчёта:",
        reply_markup=choose_report_kb()
    )
    await state.set_state(SearchState.SELECT)


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
    
    # Сохраняем запрос в состоянии
    await state.update_data(query=query)
    
    await msg.answer(f"🔍 Ищу: {query}")
    
    # Показываем выбор типа отчёта
    await msg.answer(
        "✅ Запрос сохранён. Выберите тип отчёта:",
        reply_markup=choose_report_kb()
    )
    await state.set_state(SearchState.SELECT)


async def show_page(msg_or_cbmsg, state: FSMContext):
    """Показ страницы результатов (устаревший функционал)"""
    # В новой архитектуре поиск происходит через агрегатор
    # Этот метод оставлен для совместимости
    await msg_or_cbmsg.answer(
        "ℹ️ В новой версии поиск происходит автоматически при выборе отчёта."
    )


@router.callback_query(F.data.startswith("page:"))
async def page_nav(cb: CallbackQuery, state: FSMContext):
    """Навигация по страницам (устаревший функционал)"""
    await cb.answer("ℹ️ Пагинация не используется в новой версии")


@router.message(SearchState.PAGING)
async def select_by_number(msg: Message, state: FSMContext):
    """Выбор по номеру (устаревший функционал)"""
    await msg.answer("ℹ️ В новой версии используйте кнопки для выбора отчёта")


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery, state: FSMContext):
    """Пустой обработчик"""
    await cb.answer()