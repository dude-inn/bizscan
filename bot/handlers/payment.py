# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from payments.service import initiate_payment, ensure_payment
from scraping.client import ThrottledClient
from scraping.company import parse_company_html
from reports.renderer import render_full
from bot.keyboards.main import report_menu_kb
from bot.states import ReportState

router = Router(name="payment")

@router.callback_query(F.data == "pay_yk")
async def pay_yk(cb: CallbackQuery, state: FSMContext):
    st = await initiate_payment(cb.from_user.id)
    if not st.get("ok"):
        await cb.message.answer("Не удалось создать платеж. Попробуйте позже.")
        await cb.answer()
        return
    # Симулируем проверку
    ok = await ensure_payment(st.get("payment_id"))
    if not ok:
        await cb.message.answer("Платёж не подтвержден. Попробуйте снова.")
        await cb.answer()
        return

    data = await state.get_data()
    selected = data.get("selected") or {}
    url = selected.get("url") or f"/search?query={selected.get('inn','')}"
    client = ThrottledClient()
    try:
        r = await client.get(url)
        company = await parse_company_html(r.text, url=r.request.url.path)
    finally:
        await client.close()

    for block in render_full(company):
        await cb.message.answer(block)

    await cb.message.answer("Готово. Спасибо за покупку!", reply_markup=report_menu_kb())
    await cb.answer()
    await state.set_state(ReportState.GENERATE)

@router.callback_query(F.data == "pay_cancel")
async def pay_cancel(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Отменено.")
    await cb.answer()
