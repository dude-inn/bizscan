# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from payments.service import initiate_payment, ensure_payment
from scraping.client import ThrottledClient
from scraping.company import parse_company_html
from reports.pdf import generate_pdf
from bot.keyboards.main import report_menu_kb
from bot.states import ReportState
from aiogram.types import FSInputFile
import tempfile, os

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
        status = getattr(r, "status_code", None)
        # Унифицированные логи сетевых запросов
        from core.logger import setup_logging
        log = setup_logging()
        log.info("HTTP fetched", url=url, status=status, user_id=cb.from_user.id)
        company = await parse_company_html(r.text, url=r.request.url.path)
    finally:
        await client.close()

    # Генерируем полный PDF и отправляем
    tmp_path = None
    try:
        pdf_bytes = generate_pdf(company, "full")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        await cb.message.answer_document(
            FSInputFile(tmp_path, filename="bizscan_report_full.pdf")
        )
        log.info("PDF sent", mode="full", size=len(pdf_bytes), user_id=cb.from_user.id)
        await cb.message.answer("✅ Полный отчёт готов! Спасибо за покупку!", reply_markup=report_menu_kb())
    except Exception:
        # Фоллбек на текстовый отчёт, если PDF не собрался
        from reports.renderer import render_full
        log = setup_logging()
        log.warning("PDF failed; ensure DejaVu fonts in assets/fonts (see README). Falling back to text.", mode="full", user_id=cb.from_user.id, exc_info=True)
        for block in render_full(company):
            await cb.message.answer(block)
        await cb.message.answer("Готово. Спасибо за покупку!", reply_markup=report_menu_kb())
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    await cb.answer()
    await state.set_state(ReportState.GENERATE)

@router.callback_query(F.data == "pay_cancel")
async def pay_cancel(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Отменено.")
    await cb.answer()
