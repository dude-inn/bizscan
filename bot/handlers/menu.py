# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.main import report_menu_kb, main_menu_kb
from bot.states import MenuState

router = Router(name="menu")


@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    """Возврат в главное меню из любого места"""
    try:
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    except Exception:
        await cb.message.answer("Главное меню:", reply_markup=main_menu_kb())
    await state.set_state(MenuState.MAIN)
    await cb.answer()


@router.callback_query(F.data == "menu_report")
async def menu_report(cb: CallbackQuery, state: FSMContext):
    try:
        await cb.message.edit_text("Выберите способ поиска:", reply_markup=report_menu_kb())
    except Exception:
        await cb.message.answer("Выберите способ поиска:", reply_markup=report_menu_kb())
    await cb.answer()
    await state.set_state(MenuState.REPORT_MENU)




@router.callback_query(F.data == "menu_info")
async def menu_info(cb: CallbackQuery):
    text = (
        "ℹ️ Этот бот помогает быстро проверить компанию.\n"
        "\n"
        "• Бесплатный отчёт: базовые сведения\n"
        "• Полный отчёт: расширенные данные\n"
        "\n"
        "Цена полного отчёта: 70 ₽ (оплата позже через ЮKassa)"
    )
    await cb.message.edit_text(text, reply_markup=main_menu_kb())
    await cb.answer()
