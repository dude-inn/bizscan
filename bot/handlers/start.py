# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.main import main_menu_kb
from bot.states import MenuState
from settings import BRAND_NAME
from settings import REPORT_PRICE

router = Router(name="start")

@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext):
    await message.answer(
        "👋 Привет!\n"
        "Я соберу для тебя 📊 надёжный бизнес-профиль компании прямо из госисточников РФ.\n"
        "👉 Проверка контрагентов, 📈 финансы, ⚖️ судебные дела — всё в одном месте!\n"
        "Что будем искать? 🔎",
        reply_markup=main_menu_kb(),
        disable_web_page_preview=True,
    )
    await state.set_state(MenuState.MAIN)


@router.message(Command("help"))
async def on_help(message: Message):
    HELP_TEXT = (
        "ℹ️ Этот бот помогает быстро проверить компанию.\n\n"
        "• Источники: официальные и открытые реестры РФ (ЕГРЮЛ, ФНС, ФИПС, госзакупки и др.)\n"
        "• Формат: информация предоставляется в виде PDF-отчёта и текстовой версии с исходными данными\n\n"
        f"💳 Стоимость отчёта: {REPORT_PRICE} ₽"
    )
    await message.answer(HELP_TEXT, reply_markup=main_menu_kb(), disable_web_page_preview=True)


@router.message(Command("menu"))
async def on_menu(message: Message, state: FSMContext):
    await message.answer(
        "👋 Привет!\n"
        "Я соберу для тебя 📊 надёжный бизнес-профиль компании прямо из госисточников РФ.\n"
        "👉 Проверка контрагентов, 📈 финансы, ⚖️ судебные дела — всё в одном месте!\n"
        "Что будем искать? 🔎",
        reply_markup=main_menu_kb(),
        disable_web_page_preview=True,
    )
    await state.set_state(MenuState.MAIN)
