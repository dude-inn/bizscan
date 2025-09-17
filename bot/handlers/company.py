# -*- coding: utf-8 -*-
import os
import tempfile
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from bot.states import SearchState, ReportState
from bot.keyboards.main import choose_report_kb, report_menu_kb
from aiogram.types import FSInputFile
from scraping.client import ThrottledClient
from domain.models import CompanyFull
from scraping.company import parse_company_html
from reports.renderer import render_free, render_full
from reports.pdf import generate_pdf
from core.logger import setup_logging
from settings import GENERATE_PDF_FREE

router = Router(name="company")
log = setup_logging()


def _split_text(text: str, limit: int = 4096):
    if len(text) <= limit:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(len(text), start + limit)
        # стараемся резать по переводу строки
        nl = text.rfind("\n", start, end)
        if nl != -1 and nl > start:
            yield text[start:nl]
            start = nl + 1
        else:
            yield text[start:end]
            start = end


def _sanitize_outgoing_text(text: str) -> str:
    # Убираем упоминания источника
    if not text:
        return text
    lowered = text.lower()
    if "rusprofile" in lowered or "rusprofile.ru" in lowered:
        # простая замена домена и слова
        text = text.replace("rusprofile.ru", "").replace("Rusprofile", "").replace("RUSPROFILE", "")
    return text

@router.callback_query(F.data == "back_results")
async def back_results(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Возвращаемся к результатам…")
    await cb.answer()
    await __import__("bot.handlers.search", fromlist=['']).show_page(cb.message, state)

@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    log.info("back_main: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем приветственное сообщение с главным меню
    await cb.message.answer(
        "🏢 Добро пожаловать в BizScan Bot!\n\n"
        "Выберите действие:",
        reply_markup=report_menu_kb()
    )
    
    await cb.answer()

@router.callback_query(F.data == "report_free")
async def free_report(cb: CallbackQuery, state: FSMContext):
    print(f"DEBUG: free_report handler called with data: {cb.data}")
    log.info("free_report: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    log.debug("free_report: starting report generation", user_id=cb.from_user.id, callback_data=cb.data)
    
    # Показываем индикатор загрузки
    try:
        await cb.message.edit_text("⏳ Формирую отчёт...")
    except Exception:
        await cb.message.answer("⏳ Формирую отчёт...")
    
    try:
        # Получаем данные компании из состояния
        data = await state.get_data()
        selected = data.get("selected") or {}
        url = selected.get("url") or f"/search?query={selected.get('inn','')}"
        
        log.debug("free_report: fetching company data", url=url, user_id=cb.from_user.id)
        
        # Получаем данные компании
        client = ThrottledClient()
        try:
            r = await client.get(url)
            company = await parse_company_html(r.text, url=r.request.url.path)
        except Exception as e:
            log.exception("Company page fetch/parse failed", exc_info=e)
            company = CompanyFull(
                short_name=selected.get("name", "Неизвестная компания"),
                inn=selected.get("inn", ""),
                ogrn=selected.get("ogrn", ""),
                address=selected.get("address"),
                source_url=url,
            )
        finally:
            await client.close()
        
        log.info("free_report: company data received", 
                company_name=company.short_name, 
                inn=company.inn, 
                ogrn=company.ogrn,
                has_contacts=bool(company.contacts),
                user_id=cb.from_user.id)
        
        log.debug("free_report: calling generate_pdf function", user_id=cb.from_user.id)
        
        # Генерируем PDF
        pdf_bytes = generate_pdf(company, "free")
        
        log.info("free_report: PDF generated successfully", 
                size=len(pdf_bytes), 
                user_id=cb.from_user.id)
        
        # Отправляем PDF как документ
        await cb.message.answer_document(
            document=BufferedInputFile(pdf_bytes, filename=f"{company.short_name}_free_report.pdf"),
            caption=f"📊 Бесплатный отчёт по компании {company.short_name}"
        )
        
        log.info("free_report: PDF sent successfully", user_id=cb.from_user.id)
        
    except Exception as e:
        log.error("free_report: PDF generation failed", 
                 error=str(e), 
                 error_type=type(e).__name__,
                 user_id=cb.from_user.id,
                 exc_info=True)
        
        await cb.message.answer("❌ Не удалось сгенерировать PDF. Попробуйте позже.")
    
    await cb.answer()

@router.callback_query(F.data == "report_paid")
async def paid_report(cb: CallbackQuery, state: FSMContext):
    log.info("paid_report: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    # Показываем индикатор загрузки
    try:
        await cb.message.edit_text("⏳ Формирую полный отчёт...")
    except Exception:
        await cb.message.answer("⏳ Формирую полный отчёт...")
    
    try:
        data = await state.get_data()
        selected = data.get("selected") or {}
        url = selected.get("url") or f"/search?query={selected.get('inn','')}"
        
        # Получаем данные компании
        client = ThrottledClient()
        try:
            r = await client.get(url)
            company = await parse_company_html(r.text, url=r.request.url.path)
        except Exception as e:
            log.exception("Company page fetch/parse failed", exc_info=e)
            company = CompanyFull(
                short_name=selected.get("name", "Неизвестная компания"),
                inn=selected.get("inn", ""),
                ogrn=selected.get("ogrn", ""),
                address=selected.get("address"),
                source_url=url,
            )
        finally:
            await client.close()
            
        # Генерируем и отправляем PDF вместо текста
        tmp_path = None
        try:
            pdf_bytes = generate_pdf(company, "full")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name
            await cb.message.answer_document(
                FSInputFile(tmp_path, filename="bizscan_report_full.pdf")
            )
            log.info("PDF sent (full)")
        except Exception as e:
            log.exception("PDF generation/send failed (full)", exc_info=e)
            await cb.message.answer("Не удалось сгенерировать PDF. Попробуйте позже.")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        
        # Создаём кнопку для скачивания PDF
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Скачать PDF", callback_data="download_pdf_full")]
        ])
        
        await cb.message.answer("✅ Полный отчёт готов!", reply_markup=keyboard)
        await cb.answer()
        
    except Exception as e:
        log.exception("paid_report: unexpected error", exc_info=e)
        await cb.message.answer("Произошла ошибка при формировании отчёта.")
        await cb.answer()

@router.callback_query(F.data == "download_pdf_free")
async def download_pdf_free(cb: CallbackQuery, state: FSMContext):
    log.info("download_pdf_free: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    try:
        await cb.message.edit_text("⏳ Генерирую PDF...")
    except Exception:
        await cb.message.answer("⏳ Генерирую PDF...")
    
    try:
        data = await state.get_data()
        selected = data.get("selected") or {}
        url = selected.get("url") or f"/search?query={selected.get('inn','')}"
        
        # Получаем данные компании
        client = ThrottledClient()
        try:
            r = await client.get(url)
            company = await parse_company_html(r.text, url=r.request.url.path)
        except Exception as e:
            log.exception("Company page fetch/parse failed", exc_info=e)
            company = CompanyFull(
                short_name=selected.get("name", "Неизвестная компания"),
                inn=selected.get("inn", ""),
                ogrn=selected.get("ogrn", ""),
                address=selected.get("address"),
                source_url=url,
            )
        finally:
            await client.close()
            
        # Генерируем PDF
        log.info("Starting PDF generation for free report")
        pdf_bytes = generate_pdf(company, "free")
        log.info("PDF generated successfully", size=len(pdf_bytes))
        
        # Сохраняем во временный файл и отправляем
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        log.info("PDF written to temp file", path=tmp_path)
        
        await cb.message.answer_document(
            FSInputFile(tmp_path, filename="bizscan_report_free.pdf")
        )
        log.info("PDF sent to user successfully")
        
        # Удаляем временный файл
        try:
            os.unlink(tmp_path)
            log.info("PDF temp file deleted")
        except Exception as e:
            log.warning("Failed to delete temp file", exc_info=e)
            
        await cb.answer("PDF готов!")
        
    except Exception as e:
        log.exception("download_pdf_free: unexpected error", exc_info=e)
        await cb.message.answer("Не удалось сгенерировать PDF. Попробуйте позже.")
        await cb.answer()

@router.callback_query(F.data == "download_pdf_full")
async def download_pdf_full(cb: CallbackQuery, state: FSMContext):
    log.info("download_pdf_full: handler called", callback_data=cb.data, user_id=cb.from_user.id)
    
    try:
        await cb.message.edit_text("⏳ Генерирую PDF...")
    except Exception:
        await cb.message.answer("⏳ Генерирую PDF...")
    
    try:
        data = await state.get_data()
        selected = data.get("selected") or {}
        url = selected.get("url") or f"/search?query={selected.get('inn','')}"
        
        # Получаем данные компании
        client = ThrottledClient()
        try:
            r = await client.get(url)
            company = await parse_company_html(r.text, url=r.request.url.path)
        except Exception as e:
            log.exception("Company page fetch/parse failed", exc_info=e)
            company = CompanyFull(
                short_name=selected.get("name", "Неизвестная компания"),
                inn=selected.get("inn", ""),
                ogrn=selected.get("ogrn", ""),
                address=selected.get("address"),
                source_url=url,
            )
        finally:
            await client.close()
            
        # Генерируем PDF
        pdf_bytes = generate_pdf(company, "full")
        
        # Сохраняем во временный файл и отправляем
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        await cb.message.answer_document(
            FSInputFile(tmp_path, filename="bizscan_report_full.pdf")
        )
        
        # Удаляем временный файл
        try:
            os.unlink(tmp_path)
        except Exception as e:
            log.warning("Failed to delete temp file", exc_info=e)
            
        await cb.answer("PDF готов!")
        
    except Exception as e:
        log.exception("download_pdf_full: unexpected error", exc_info=e)
        await cb.message.answer("Не удалось сгенерировать PDF. Попробуйте позже.")
        await cb.answer()

# Удален общий обработчик, который перехватывал все callback'и
