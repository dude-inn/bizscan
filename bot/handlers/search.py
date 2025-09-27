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
from services.providers.ofdata import OFDataClient, OFDataClientError, OFDataServerTemporaryError
from services.aggregator import fetch_company_report_markdown
# Name-based search and DN suggestions are disabled by plan
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
    """Запрос ИНН/ОГРН для поиска"""
    await state.update_data(search_type="inn", gamma_export_as=None)
    await cb.message.edit_text(
        "🔍 **Поиск компании**\n\n"
        "Введите ИНН (10 или 12 цифр) или ОГРН (13 или 15 цифр)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")]
        ]),
        disable_web_page_preview=True,
    )
    await state.set_state(SearchState.ASK_INN)
    await cb.answer()
@router.callback_query(F.data == "search_name")
async def ask_name(cb: CallbackQuery, state: FSMContext):
    """Запрос названия компании для поиска"""
    await state.update_data(search_type="name", gamma_export_as=None)
    await cb.message.edit_text(
        "🔍 **Поиск по названию компании**\n\n"
        "Введите название компании для поиска",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")]
        ]),
        disable_web_page_preview=True,
    )
    await state.set_state(SearchState.ASK_NAME)
    await cb.answer()
async def _show_company_choices(message_or_cb, companies: list, state: FSMContext, page: int = 0):
    """Показывает список найденных компаний для выбора с пагинацией"""
    log.info("_show_company_choices: starting", 
            companies_type=type(companies).__name__,
            companies_length=len(companies) if hasattr(companies, '__len__') else 'no length',
            page=page,
            companies_preview=str(companies)[:200] if companies else 'empty')
    # Убеждаемся, что companies - это список
    if not isinstance(companies, list):
        log.error("_show_company_choices: companies is not a list", 
                 companies_type=type(companies).__name__,
                 companies_value=str(companies)[:500])
        await message_or_cb.answer("❌ Ошибка формата данных.")
        return
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
        inn = company.get("inn") or company.get("ИНН") or company.get("tax_number")
        if not inn:
            await message_or_cb.answer("❌ У найденной компании отсутствует ИНН.")
            return
        company_name = (
            company.get("НаимПолн")
            or company.get("name_full")
            or company.get("full_name")
            or company.get("name")
            or "Неизвестно"
        )
        await state.update_data(
            query=inn,
            company_name=company_name,
            company_inn=inn,
            company_address=company.get("address"),
        )
        lines_to_send = [
            f"✅ Найдено: {company_name}",
            f"ИНН: {inn}",
            "",
            "Выберите формат отчёта:",
        ]
        await message_or_cb.answer(
            "\n".join(lines_to_send),
            reply_markup=choose_report_kb()
        )
        await state.set_state(SearchState.SELECT)
        return
    # Несколько — показываем кнопки с пагинацией
    buttons = []
    try:
        # Настройки пагинации
        items_per_page = 8  # Показываем 8 компаний на странице
        total_pages = (len(companies) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        # Безопасно получаем компании для текущей страницы
        try:
            companies_to_show = companies[start_idx:end_idx]
        except TypeError as e:
            log.error("_show_company_choices: slice error", 
                     error=str(e),
                     companies_type=type(companies).__name__,
                     companies_value=str(companies)[:200])
            await message_or_cb.answer("❌ Ошибка обработки результатов поиска.")
            return
        log.info("_show_company_choices: pagination info", 
                total_companies=len(companies),
                current_page=page,
                total_pages=total_pages,
                items_per_page=items_per_page,
                start_idx=start_idx,
                end_idx=end_idx,
                companies_to_show_count=len(companies_to_show))
        for i, c in enumerate(companies_to_show):
            log.info("_show_company_choices: processing company", 
                    index=i,
                    company_type=type(c).__name__,
                    company_keys=list(c.keys()) if isinstance(c, dict) else 'not dict',
                    company_preview=str(c)[:100])
            # Убеждаемся, что c - это словарь
            if not isinstance(c, dict):
                log.warning("_show_company_choices: company item is not dict", 
                           company_type=type(c).__name__,
                           company_value=str(c)[:100])
                continue
            # Извлекаем данные из результата поиска
            inn = c.get("inn") or c.get("ИНН") or c.get("tax_number") or "—"
            name_short = c.get("НаимСокр") or c.get("name_short") or c.get("short_name")
            name_full = c.get("НаимПолн") or c.get("name_full") or c.get("full_name") or c.get("name")
            title = name_short or name_full or "Неизвестно"
            # Ограничиваем длину названия, чтобы кнопка оставалась читаемой
            max_title_len = 40
            if len(title) > max_title_len:
                title = title[:max_title_len - 1] + "…"
            # Извлекаем город из адреса, если доступен
            city = None
            # Пытаемся получить город/первую часть адреса из разных возможных мест
            addr_obj = (
                c.get("ЮрАдрес")
                or c.get("Адрес")
                or c.get("АдресРФ")
                or c.get("address")
                or c.get("full_address")
                or c.get("value")
                or {}
            )
            def _first_part(s: str) -> str:
                parts = [p.strip() for p in s.split(",") if p.strip()]
                return parts[0] if parts else s.strip()
            if isinstance(addr_obj, dict):
                city = (
                    addr_obj.get("НасПункт")
                    or addr_obj.get("city")
                    or ( _first_part(addr_obj.get("АдресРФ") or "") if addr_obj.get("АдресРФ") else None )
                    or ( _first_part(addr_obj.get("value") or "") if addr_obj.get("value") else None )
                    or ( _first_part(addr_obj.get("full_address") or "") if addr_obj.get("full_address") else None )
                    or ( _first_part(addr_obj.get("address") or "") if addr_obj.get("address") else None )
                )
            elif isinstance(addr_obj, str):
                city = _first_part(addr_obj)
            short_city = city or ""
            log.info("_show_company_choices: company processed", 
                    index=i,
                    inn=inn,
                    title=title,
                    city=short_city or None,
                    button_text=(f"{title} — ИНН {inn}" + (f", {short_city}" if short_city else "")))
            # Одна кнопка: Название — ИНН NNNNNNNNNN
            main_btn = InlineKeyboardButton(text=f"{title} — ИНН {inn}", callback_data=f"select_company:{inn}")
            buttons.append([main_btn])
    except Exception as e:
        log.error("_show_company_choices: error processing companies", error=str(e))
        await message_or_cb.answer("❌ Ошибка обработки результатов поиска.")
        return
    # Добавляем кнопки навигации если есть несколько страниц
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="➡️ Следующая", callback_data=f"page:{page+1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
    # Добавляем кнопки навигации
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_search")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
    log.info("_show_company_choices: sending response", 
            buttons_count=len(buttons),
            total_pages=total_pages,
            current_page=page,
            buttons_preview=[btn[0].text for btn in buttons[:3]])
    # Определяем, нужно ли редактировать сообщение или отправлять новое
    if hasattr(message_or_cb, 'edit_text'):
        # Это CallbackQuery - редактируем существующее сообщение
        log.info("_show_company_choices: editing message", 
                message_type="CallbackQuery",
                page=page,
                total_pages=total_pages)
        await message_or_cb.edit_text(
            f"📄 Найдено {len(companies)} компаний. Выберите нужную (стр. {page+1}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # Это Message - отправляем новое сообщение
        log.info("_show_company_choices: sending new message", 
                message_type="Message",
                page=page,
                total_pages=total_pages)
        await message_or_cb.answer(
            f"📄 Найдено {len(companies)} компаний. Выберите нужную (стр. {page+1}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    await state.set_state(SearchState.PAGING)
@router.message(SearchState.ASK_NAME)
async def got_name_query(msg: Message, state: FSMContext):
    """Обработка поиска по названию компании"""
    log.info("got_name_query: starting", user_id=msg.from_user.id)
    query = _normalize_query(msg.text or "")
    log.info("got_name_query: query normalized", query=query, user_id=msg.from_user.id)
    if len(query) < 3:
        await msg.answer("❌ Введите название компании (минимум 3 символа).")
        return
    # Показываем индикатор загрузки
    status_msg = await msg.answer("⏳ Ищу компании по названию...")
    log.info("got_name_query: status message sent", user_id=msg.from_user.id)
    try:
        # Получаем список компаний через OFData
        import asyncio
        client = OFDataClient()
        # Выполняем поиск напрямую (синхронно)
        search_results = client.search_filtered(
            by="name",
            obj="org", 
            query=query,
            limit=20,
            page=1
        )
        log.info("got_name_query: search results received", 
                query=query,
                search_results_type=type(search_results).__name__,
                search_results_keys=list(search_results.keys()) if isinstance(search_results, dict) else 'not dict',
                user_id=msg.from_user.id)
        # OFData API возвращает данные в формате: {"data": {"Записи": [...]}}
        data = search_results.get("data", {})
        companies = data.get("Записи", []) or data.get("records", []) or data.get("companies", []) or []
        log.info("got_name_query: companies extracted", 
                data_keys=list(data.keys()) if isinstance(data, dict) else 'not dict',
                companies_type=type(companies).__name__,
                companies_length=len(companies) if hasattr(companies, '__len__') else 'no length',
                user_id=msg.from_user.id)
        # Убеждаемся, что companies - это список
        if not isinstance(companies, list):
            log.error("got_name_query: companies is not a list", 
                     companies_type=type(companies).__name__,
                     companies_value=str(companies)[:200],
                     user_id=msg.from_user.id)
            await status_msg.edit_text("❌ Ошибка формата данных от API.")
            return
        if not companies:
            await status_msg.edit_text(
                "❌ Компании не найдены. Уточните название или введите ИНН/ОГРН.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                ])
            )
            return
        # Проверяем количество результатов
        if len(companies) > 50:
            log.info("got_name_query: too many results", 
                    companies_count=len(companies),
                    query=query,
                    user_id=msg.from_user.id)
            await status_msg.edit_text(
                f"❌ Найдено слишком много результатов ({len(companies)} компаний).\n\n"
                "🔍 Пожалуйста, уточните запрос:\n"
                "• Добавьте больше слов в название\n"
                "• Укажите город или регион\n"
                "• Используйте более конкретное название\n\n"
                "Или введите ИНН/ОГРН для точного поиска.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                ])
            )
            return
        # Сохраняем все компании в состоянии для пагинации
        await state.update_data(all_companies=companies, current_page=0)
        # Показываем список найденных компаний
        log.info("got_name_query: calling _show_company_choices", 
                companies_count=len(companies),
                user_id=msg.from_user.id)
        await _show_company_choices(status_msg, companies, state)
    except asyncio.TimeoutError:
        log.error("Name search timeout", user_id=msg.from_user.id)
        await status_msg.edit_text(
            "⏰ Поиск занял слишком много времени.\n\n"
            "🔧 Возможные причины:\n"
            "• Медленное интернет-соединение\n"
            "• Перегрузка сервера API\n"
            "• Временные проблемы с сетью\n\n"
            "⏳ Попробуйте позже или используйте поиск по ИНН/ОГРН.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
            ])
        )
    except (OFDataClientError, OFDataServerTemporaryError) as e:
        log.error("Name search failed", error=str(e), user_id=msg.from_user.id)
        error_msg = str(e).lower()
        # Обработка ошибки 400 - неверные параметры запроса
        if "400" in error_msg or "bad request" in error_msg or "неверно указаны параметры" in error_msg:
            await status_msg.edit_text(
                "❌ Неверные параметры поиска.\n\n"
                "🔧 Возможные причины:\n"
                "• Название слишком короткое (минимум 3 символа)\n"
                "• Специальные символы в названии\n"
                "• Пустой или некорректный запрос\n\n"
                "💡 Попробуйте:\n"
                "• Ввести полное название компании\n"
                "• Использовать поиск по ИНН/ОГРН\n"
                "• Убрать специальные символы",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                ])
            )
        elif "timeout" in error_msg or "timed out" in error_msg:
            await status_msg.edit_text(
                "❌ Таймаут подключения к API.\n\n"
                "🔧 Возможные причины:\n"
                "• Проблемы с интернет-соединением\n"
                "• Временная недоступность сервиса\n"
                "• Блокировка API\n\n"
                "⏳ Попробуйте позже или используйте поиск по ИНН/ОГРН.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                ])
            )
        else:
            await status_msg.edit_text(
                f"❌ Ошибка при поиске: {str(e)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                ])
            )
    except Exception as e:
        log.error("Name search failed", 
                 error=str(e), 
                 error_type=type(e).__name__,
                 error_args=getattr(e, 'args', None),
                 user_id=msg.from_user.id)
        await status_msg.edit_text(
            f"❌ Неожиданная ошибка при поиске: {type(e).__name__}\n\n"
            "🔧 Попробуйте:\n"
            "• Проверить интернет-соединение\n"
            "• Использовать поиск по ИНН/ОГРН\n"
            "• Попробовать позже",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_search")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
            ])
        )
@router.message(SearchState.ASK_INN)
async def got_inn_query(msg: Message, state: FSMContext):
    """Обработка поиска по ИНН/ОГРН"""
    query = _normalize_query(msg.text or "")
    if len(query) < 10:
        await msg.answer("❌ Введите ИНН (10/12) или ОГРН (13/15) цифрами.")
        return
    # Если это ИНН/ОГРН — сразу сохраняем и предлагаем отчёт
    if _is_inn(query) or _is_ogrn(query):
        preview = {"inn": query}
        address = None
        company_name = None
        try:
            client = OFDataClient()
            raw = client.get_counterparty(inn=query if _is_inn(query) else None, ogrn=query if _is_ogrn(query) else None)
            data = raw.get("company") or raw.get("data") or raw
            names = (data.get("company_names") or {}) if isinstance(data, dict) else {}
            company_name = (
                data.get("НаимСокр")
                or names.get("short_name")
                or data.get("short_name")
                or data.get("НаимПолн")
                or names.get("full_name")
                or data.get("full_name")
                or data.get("name")
                or query
            )
            addr_obj = data.get("address") or data.get("ЮрАдрес") or {}
            if isinstance(addr_obj, dict):
                address = (
                    addr_obj.get("АдресРФ")
                    or addr_obj.get("value")
                    or addr_obj.get("full_address")
                    or addr_obj.get("address")
                )
            else:
                address = addr_obj if addr_obj else None
            preview.update({
                "name_full": data.get("НаимПолн") or names.get("full_name") or data.get("full_name") or data.get("name"),
                "name_short": data.get("НаимСокр") or names.get("short_name") or data.get("short_name"),
                "address": address,
                "ogrn": raw.get("ogrn") or data.get("ОГРН") or data.get("ogrn"),
            })
        except (OFDataClientError, OFDataServerTemporaryError) as e:
            log.warning("OFData preview failed", error=str(e))
        await state.update_data(
            query=query,
            company_preview=preview,
            company_name=company_name,
            company_inn=query,
            company_address=address,
        )
        details = [
            f"✅ Найдено: {company_name or query}",
            f"ИНН: {query}",
        ]
        if address:
            details.append(f"Адрес: {address}")
        details.append("")
        details.append("Выберите формат отчёта:")
        await msg.answer(
            "\n".join(details),
            reply_markup=choose_report_kb(),
            disable_web_page_preview=True,
        )
        await state.set_state(SearchState.SELECT)
        return
    # Поиск по названию отключён
    await msg.answer("❌ Поиск по названию недоступен. Введите ИНН или ОГРН.")
    return
@router.callback_query(F.data == "back_search")
async def back_to_search(cb: CallbackQuery, state: FSMContext):
    # Определяем, какой тип поиска был активен
    data = await state.get_data()
    if "search_type" in data and data["search_type"] == "name":
        await cb.message.edit_text(
            "🔍 **Поиск по названию компании**\n\nВведите название компании для поиска:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")]
            ]),
            disable_web_page_preview=True,
        )
        await state.set_state(SearchState.ASK_NAME)
    else:
        await cb.message.edit_text(
            "🔍 **Поиск компании**\n\nВведите ИНН или ОГРН:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")]
            ]),
            disable_web_page_preview=True,
        )
        await state.set_state(SearchState.ASK_INN)
    await cb.answer()
@router.callback_query(F.data.startswith("select_company:"))
async def select_company(cb: CallbackQuery, state: FSMContext):
    inn = cb.data.split(":", 1)[1]
    await state.update_data(query=inn)
    # Пытаемся взять название/адрес/статус без доп. запросов
    data = await state.get_data()
    title = None
    address = None
    status_text = None
    # 1) Если есть предпросмотр (ветка поиска по ИНН)
    preview = data.get("company_preview") or {}
    if isinstance(preview, dict):
        if (preview.get("inn") == inn) or (str(preview.get("ИНН")) == inn):
            title = preview.get("name_short") or preview.get("name_full")
            # Адрес в предпросмотре может быть строкой или объектом
            addr_obj = preview.get("address") or preview.get("ЮрАдрес")
            if isinstance(addr_obj, dict):
                address = (
                    addr_obj.get("АдресРФ")
                    or addr_obj.get("value")
                    or addr_obj.get("full_address")
                    or addr_obj.get("address")
                )
            else:
                address = addr_obj
    # 2) Если выбирали из списка (ветка поиска по названию)
    if not title:
        companies = data.get("all_companies", []) or []
        if isinstance(companies, list):
            for c in companies:
                if not isinstance(c, dict):
                    continue
                c_inn = c.get("inn") or c.get("ИНН") or c.get("tax_number")
                if str(c_inn) == inn:
                    name_short = c.get("НаимСокр") or c.get("name_short") or c.get("short_name")
                    name_full = c.get("НаимПолн") or c.get("name_full") or c.get("full_name") or c.get("name")
                    title = name_short or name_full
                    # адрес
                    addr_obj = c.get("ЮрАдрес") or c.get("address") or c.get("АдресРФ") or c.get("Адрес") or {}
                    if isinstance(addr_obj, dict):
                        address = (
                            addr_obj.get("АдресРФ")
                            or addr_obj.get("value")
                            or addr_obj.get("full_address")
                            or addr_obj.get("address")
                        )
                    elif isinstance(addr_obj, str):
                        address = addr_obj
                    # статус
                    status_text = (
                        (c.get("Статус") if isinstance(c.get("Статус"), str) else None)
                        or (c.get("Статус", {}) or {}).get("Наим")
                        or c.get("status")
                    )
                    break
    # Нормализуем статус и подберём отметку
    status_line = None
    if status_text:
        normalized = str(status_text).strip().lower()
        is_active = normalized in {"действует", "active", "активен", "активная", "активно"}
        mark = "✅" if is_active else "❌"
        human_status = "Действует" if is_active else "Не действует"
        status_line = f"Статус: {mark} {human_status}"
    # Формируем текст подтверждения в требуемом формате
    lines = []
    if title:
        lines.append(title)
    else:
        lines.append("Компания")
    lines.append(f"ИНН: {inn}")
    if address:
        lines.append(f"Адрес: {address}")
    if status_line:
        lines.append(status_line)
    lines.append("\nВыберите тип отчёта:")
    await state.update_data(
        company_name=title or data.get("company_name"),
        company_inn=inn,
        company_address=address,
    )
    kb = choose_report_kb()
    kb.inline_keyboard.insert(2, [InlineKeyboardButton(text="🔙 Назад к результатам", callback_data="back_results")])
    await cb.message.edit_text("\n".join(lines), reply_markup=kb)
    await state.set_state(SearchState.SELECT)
    await cb.answer()
@router.callback_query(F.data == "back_results")
async def back_to_results(cb: CallbackQuery, state: FSMContext):
    """Возврат к списку результатов поиска на текущую страницу"""
    data = await state.get_data()
    all_companies = data.get("all_companies", [])
    current_page = data.get("current_page", 0)
    if not all_companies:
        await cb.answer("Результаты поиска недоступны", show_alert=False)
        return
    await _show_company_choices(cb.message, all_companies, state, current_page)
    await cb.answer()
# Удалены обработчики поиска по названию
async def show_page(msg_or_cbmsg, state: FSMContext):
    """Показ страницы результатов (устаревший функционал)"""
    await msg_or_cbmsg.answer(
        "ℹ️ В новой версии поиск выполняется автоматически при выборе/выборе компании."
    )
@router.callback_query(F.data.startswith("page:"))
async def page_nav(cb: CallbackQuery, state: FSMContext):
    """Обработка навигации по страницам"""
    try:
        # Извлекаем номер страницы из callback_data
        page = int(cb.data.split(":")[1])
        # Получаем все компании из состояния
        data = await state.get_data()
        all_companies = data.get("all_companies", [])
        if not all_companies:
            await cb.answer("❌ Данные поиска не найдены")
            return
        # Обновляем текущую страницу в состоянии
        await state.update_data(current_page=page)
        # Показываем компании для новой страницы
        await _show_company_choices(cb.message, all_companies, state, page)
        log.info("page_nav: navigation successful", 
                page=page,
                total_companies=len(all_companies),
                user_id=cb.from_user.id)
    except (ValueError, IndexError) as e:
        log.error("page_nav: invalid page number", error=str(e), user_id=cb.from_user.id)
        await cb.answer("❌ Неверный номер страницы")
    except Exception as e:
        log.error("page_nav: error", error=str(e), user_id=cb.from_user.id)
        await cb.answer("❌ Ошибка навигации")
@router.message(SearchState.PAGING)
async def select_by_number(msg: Message, state: FSMContext):
    """Выбор по номеру (устаревший функционал)"""
    await msg.answer("ℹ️ Используйте кнопки ниже для выбора компании")
@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery, state: FSMContext):
    """Пустой обработчик"""
    await cb.answer()
