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
        "Привет! Я соберу профиль компании из официальных источников РФ (ЕГРЮЛ/Росстат, ФНС, КАД).",
        reply_markup=main_menu_kb()
    )
    await state.set_state(MenuState.MAIN)
