# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.main import main_menu_kb, report_menu_kb, results_kb, choose_report_kb
from bot.states import SearchState, MenuState
from core.logger import setup_logging
from scraping.client import ThrottledClient
from scraping.search import search_by_name
from scraping.normalize import normalize_digits

router = Router(name="search")
log = setup_logging()

@router.callback_query(F.data == "search_inn")
async def ask_inn(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Введите ИНН (10 или 12 цифр):")
    await state.set_state(SearchState.ASK_INN)
    await cb.answer()

@router.message(SearchState.ASK_INN)
async def got_inn(msg: Message, state: FSMContext):
    inn = normalize_digits(msg.text or "")
    if len(inn) not in (10,12):
        await msg.answer("Неверный формат ИНН. Повторите (10 или 12 цифр).")
        return
    # Прямой переход на карточку компании по ИНН: на rusprofile обычно есть прямой путь /search?query=ИНН
    await state.update_data(inn=inn)
    await msg.answer(f"Поиск компании с ИНН {inn}...")
    # Используем поиск по названию как универсальный путь (rusprofile выдаёт карточку в топе)
    client = ThrottledClient()
    try:
        results = await search_by_name(client, inn)
    finally:
        await client.close()
    if not results:
        await msg.answer("Ничего не найдено.", reply_markup=report_menu_kb())
        await state.set_state(MenuState.REPORT_MENU)
        return
    # Если найден ровно один результат — сразу переходим к выбору отчёта
    if len(results) == 1:
        one = results[0].model_dump()
        await state.update_data(selected=one)
        # Короткая сводка
        name = one.get('name') or 'Компания'
        inn_val = one.get('inn') or '—'
        ogrn_val = one.get('ogrn') or '—'
        address = one.get('address') or ''
        summary_lines = [
            f"Выбрана компания: {name}",
            f"ИНН: {inn_val} | ОГРН: {ogrn_val}",
        ]
        if address:
            summary_lines.append(address)
        # Сразу показываем выбор вида отчёта
        await msg.answer("\n".join(summary_lines), reply_markup=choose_report_kb())
        await state.set_state(SearchState.SELECT)
        return
    # Иначе — показываем список
    await state.update_data(results=[r.model_dump() for r in results], page=0)
    await show_page(msg, state)
    await state.set_state(SearchState.PAGING)

@router.callback_query(F.data == "search_name")
async def ask_name(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Введите наименование компании для поиска:")
    await state.set_state(SearchState.ASK_NAME)
    await cb.answer()

@router.message(SearchState.ASK_NAME)
async def got_name(msg: Message, state: FSMContext):
    q = (msg.text or "").strip()
    if len(q) < 2:
        await msg.answer("Слишком короткий запрос. Повторите.")
        return
    await msg.answer(f"Ищу: {q}")
    client = ThrottledClient()
    try:
        results = await search_by_name(client, q)
    finally:
        await client.close()
    if not results:
        await msg.answer("Ничего не найдено.", reply_markup=report_menu_kb())
        await state.set_state(MenuState.REPORT_MENU)
        return
    await state.update_data(results=[r.model_dump() for r in results], page=0)
    await show_page(msg, state)
    await state.set_state(SearchState.PAGING)

async def show_page(msg_or_cbmsg, state: FSMContext):
    data = await state.get_data()
    results = data.get("results", [])
    page = int(data.get("page", 0))
    page_size = 10
    total_pages = max(1, (len(results) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    chunk = results[start:start+page_size]

    text_lines = ["Результаты поиска:"]
    for idx, item in enumerate(chunk, start=1):
        text_lines.append(f"{idx}. {item.get('name','')} | ИНН {item.get('inn','')} | ОГРН {item.get('ogrn','') or '—'}")
    text_lines.append("Выберите номер (отправьте цифру) или листайте ◀️▶️")

    await state.update_data(page=page)
    await msg_or_cbmsg.answer("\n".join(text_lines), reply_markup=results_kb(page, total_pages, "sel", "page"))
    # После вывода страницы активируем режим выбора по номеру
    await state.set_state(SearchState.PAGING)

@router.callback_query(F.data.startswith("page:"))
async def page_nav(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = int(data.get("page", 0))
    direction = cb.data.split(":")[1]
    page = page - 1 if direction == "prev" else page + 1
    await state.update_data(page=page)
    await cb.message.delete()
    await show_page(cb.message, state)
    await cb.answer()

@router.message(SearchState.PAGING)
async def select_by_number(msg: Message, state: FSMContext):
    data = await state.get_data()
    results = data.get("results", [])
    page = int(data.get("page", 0))
    page_size = 10
    start = page * page_size
    try:
        n = int((msg.text or "").strip())
    except:
        await msg.answer("Введите номер из списка или листайте ◀️▶️")
        return
    idx = start + (n - 1)
    if idx < 0 or idx >= len(results):
        await msg.answer("Неверный номер. Повторите.")
        return
    await state.update_data(selected=results[idx])
    await msg.answer("Компания выбрана. Теперь выберите тип отчёта.", reply_markup=__import__("bot.keyboards.main", fromlist=['']).choose_report_kb())
    await state.set_state(SearchState.SELECT)

# Переводим состояние после вывода страницы (для обработки цифр)
@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.PAGING)
    # Не показываем алерт, просто тихо подтверждаем, чтобы убрать "часики"
    await cb.answer()
