# -*- coding: utf-8 -*-
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сформировать отчёт", callback_data="menu_report")],
        [InlineKeyboardButton(text="Информация", callback_data="menu_info")],
    ])

def report_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Найти по ИНН", callback_data="search_inn")],
        [InlineKeyboardButton(text="Найти по наименованию", callback_data="search_name")],
        [InlineKeyboardButton(text="Назад в меню", callback_data="back_main")],
    ])

def results_kb(page: int, total_pages: int, select_prefix: str, page_cb_prefix: str):
    buttons = []
    buttons.append([InlineKeyboardButton(text="◀️", callback_data=f"{page_cb_prefix}:prev"),
                    InlineKeyboardButton(text=f"стр. {page+1}/{total_pages}", callback_data="noop"),
                    InlineKeyboardButton(text="▶️", callback_data=f"{page_cb_prefix}:next")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def choose_report_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Простой отчёт (бесплатно)", callback_data="report_free")],
        [InlineKeyboardButton(text="Полный отчёт (70 ₽)", callback_data="report_paid")],
        [InlineKeyboardButton(text="TXT (черновик)", callback_data="report_txt")],
        [InlineKeyboardButton(text="Назад к результатам", callback_data="back_results")],
    ])

def payment_stub_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить (ЮKassa)", callback_data="pay_yk")],
        [InlineKeyboardButton(text="Отмена", callback_data="pay_cancel")],
    ])
