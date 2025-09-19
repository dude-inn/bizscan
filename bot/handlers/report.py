# bot/handlers/report.py
from aiogram import Router, F
from aiogram.types import Message
from services.aggregator import fetch_company_report_markdown

router = Router()

@router.message(F.text.regexp(r"^\s*(\d{10}|\d{12}|\d{13}|\d{15})\s*$"))
async def handle_inn_ogrn(msg: Message):
    q = msg.text.strip()
    md = await fetch_company_report_markdown(q)
    await msg.answer(md, disable_web_page_preview=True, parse_mode="HTML")

@router.message(F.text)
async def prompt_for_id(msg: Message):
    await msg.answer(
        "Введите ИНН (10/12 цифр) или ОГРН (13/15 цифр) компании для формирования отчёта.",
        disable_web_page_preview=True,
    )
