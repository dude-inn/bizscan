# -*- coding: utf-8 -*-
"""
Клавиатуры для Telegram бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти компанию", callback_data="menu_report")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="menu_info")],
    ])


def report_menu_kb() -> InlineKeyboardMarkup:
    """Меню поиска"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔢 Ввести ИНН/ОГРН", callback_data="search_inn")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])


def results_kb(page: int, total_pages: int, select_prefix: str, page_cb_prefix: str):
    """Клавиатура пагинации (устаревшая)"""
    buttons = []
    buttons.append([
        InlineKeyboardButton(text="◀️", callback_data=f"{page_cb_prefix}:prev"),
        InlineKeyboardButton(text=f"стр. {page+1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"{page_cb_prefix}:next")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def choose_report_kb() -> InlineKeyboardMarkup:
    """Выбор типа отчёта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Бесплатный отчёт", callback_data="report_free")],
        [InlineKeyboardButton(text="💰 Полный отчёт (планируется)", callback_data="report_paid")],
        [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_inn")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])


def payment_stub_kb() -> InlineKeyboardMarkup:
    """Клавиатура оплаты (устаревшая)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить (ЮKassa)", callback_data="pay_yk")],
        [InlineKeyboardButton(text="Отмена", callback_data="pay_cancel")],
    ])