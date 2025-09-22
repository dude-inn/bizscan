# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.main import main_menu_kb
from bot.states import MenuState
from settings import BRAND_NAME

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
