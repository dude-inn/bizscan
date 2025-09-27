# -*- coding: utf-8 -*-
"""
Клавиатуры для Telegram бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from settings_texts import (
    BTN_SEARCH_REPORT, BTN_HELP, BTN_ENTER_INN, BTN_SEARCH_NAME,
    BTN_BACK, BTN_NEW_SEARCH, BTN_HOME,
    BTN_FEEDBACK, BTN_CHECK_PAYMENT, BTN_BACK_SIMPLE,
    BTN_PAY_YK, BTN_PAY_CANCEL,
)
from settings_texts import BTN_FORMAT_PDF, BTN_FORMAT_PPTX, TEXT_CHOOSE_FORMAT


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_SEARCH_REPORT, callback_data="menu_report")],
        [InlineKeyboardButton(text=BTN_HELP, callback_data="menu_info")],
    ])


def report_menu_kb() -> InlineKeyboardMarkup:
    """Меню поиска"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_ENTER_INN, callback_data="search_inn")],
        [InlineKeyboardButton(text=BTN_SEARCH_NAME, callback_data="search_name")],
        [InlineKeyboardButton(text=BTN_BACK, callback_data="back_main")],
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
    """Выбор формата и генерации отчёта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Сформировать отчёт (PDF)", callback_data="pay_report_pdf")],
        [InlineKeyboardButton(text="📊 Сформировать отчёт (PPTX)", callback_data="pay_report_pptx")],
        [InlineKeyboardButton(text=BTN_NEW_SEARCH, callback_data="search_inn")],
        [InlineKeyboardButton(text=BTN_HOME, callback_data="back_main")],
    ])


def choose_format_kb() -> InlineKeyboardMarkup:
    """Выбор формата основного отчёта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_FORMAT_PDF, callback_data="format_pdf")],
        [InlineKeyboardButton(text=BTN_FORMAT_PPTX, callback_data="format_pptx")],
        [InlineKeyboardButton(text=BTN_BACK, callback_data="back_main")],
    ])


def after_report_kb() -> InlineKeyboardMarkup:
    """Кнопки после выдачи отчёта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_FEEDBACK, callback_data="leave_feedback")],
        [InlineKeyboardButton(text=BTN_HOME, callback_data="back_main")],
    ])

def payment_status_kb() -> InlineKeyboardMarkup:
    """Кнопки для проверки статуса оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_CHECK_PAYMENT, callback_data="check_payment")],
        [InlineKeyboardButton(text=BTN_BACK_SIMPLE, callback_data="back_main")],
    ])


def payment_stub_kb() -> InlineKeyboardMarkup:
    """Клавиатура оплаты (устаревшая)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_PAY_YK, callback_data="pay_yk")],
        [InlineKeyboardButton(text=BTN_PAY_CANCEL, callback_data="pay_cancel")],
    ])
