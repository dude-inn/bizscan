# -*- coding: utf-8 -*-
"""
Check command handler for direct company lookup
"""
import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states import SearchState
from bot.keyboards.main import choose_report_kb
from services.aggregator import fetch_company_report_markdown
from core.logger import get_logger

router = Router(name="check")
log = get_logger(__name__)


def _is_inn(query: str) -> bool:
    """Check if query is INN"""
    return re.match(r'^\d{10}$|^\d{12}$', query) is not None


def _is_ogrn(query: str) -> bool:
    """Check if query is OGRN"""
    return re.match(r'^\d{13}$|^\d{15}$', query) is not None


def _is_digits_only(query: str) -> bool:
    """Check if query contains only digits"""
    return re.match(r'^\d+$', query) is not None


@router.message(Command("check"))
async def check_command(msg: Message, state: FSMContext):
    """Handle /check command with company query"""
    log.info("check_command", user_id=msg.from_user.id)
    
    # Extract query from command
    query = msg.text.replace("/check", "").strip()
    log.debug("extracted query", query=query, user_id=msg.from_user.id)
    
    if not query:
        await msg.answer(
            "❌ **Использование команды**\n\n"
            "`/check <ИНН/ОГРН или название компании>`\n\n"
            "**Примеры:**\n"
            "• `/check 3801098402` (ИНН)\n"
            "• `/check 1083801006860` (ОГРН)\n"
            "• `/check Газпром` (название)\n\n"
            "💡 **Подсказка**: Поиск по названию доступен при источнике OFData."
        )
        return
    
    # Check if query is digits only (INN/OGRN)
    if _is_digits_only(query):
        is_inn = _is_inn(query)
        is_ogrn = _is_ogrn(query)
        log.debug("parsed query type", 
                is_digits_only=True, 
                is_inn=is_inn, 
                is_ogrn=is_ogrn, 
                query=query, 
                user_id=msg.from_user.id)
        
        if is_inn or is_ogrn:
            # Valid INN/OGRN - proceed with report
            log.debug("valid INN/OGRN", query=query, user_id=msg.from_user.id)
            await _process_valid_query(msg, state, query)
        else:
            log.warning("check_command: invalid INN/OGRN format", query=query, user_id=msg.from_user.id)
            await msg.answer(
                "❌ **Некорректный ИНН/ОГРН**\n\n"
                "• ИНН: 10 или 12 цифр\n"
                "• ОГРН: 13 или 15 цифр\n\n"
                "Проверьте правильность ввода."
            )
    else:
        # Text query - check if name search is available
        log.debug("text query", query=query, user_id=msg.from_user.id)
        try:
            from bot.handlers.settings import get_user_data_source
            user_source = get_user_data_source(msg.from_user.id)
        except ImportError:
            from settings import DATASOURCE
            user_source = DATASOURCE
        
        log.debug("data source", user_source=user_source, user_id=msg.from_user.id)
        
        if user_source == "ofdata":
            # Try name search
            log.debug("proceed with name search", query=query, user_id=msg.from_user.id)
            await _process_name_search(msg, state, query)
        else:
            log.debug("name search not available", user_source=user_source, user_id=msg.from_user.id)
            await msg.answer(
                "❌ **Поиск по названию недоступен**\n\n"
                "Текущий источник: **Источник 1**\n"
                "Доступен только поиск по ИНН/ОГРН.\n\n"
                "Для поиска по названию:\n"
                "1. Используйте команду `/source`\n"
                "2. Переключите на источник **OFData**\n"
                "3. Повторите поиск"
            )


async def _process_valid_query(msg: Message, state: FSMContext, query: str):
    """Process valid INN/OGRN query"""
    log.info("process_valid_query", query=query, user_id=msg.from_user.id)
    
    # Show loading message
    status_msg = await msg.answer("⏳ Собираю данные о компании...")
    log.debug("loading message sent", user_id=msg.from_user.id)
    
    try:
        # Get company report
        log.debug("calling fetch_company_report_markdown", query=query, user_id=msg.from_user.id)
        response = await fetch_company_report_markdown(query)
        log.debug("aggregator response", length=len(response) if response else 0, user_id=msg.from_user.id)
        
        if not response or response.startswith("Укажите корректный") or response.startswith("Ошибка"):
            await status_msg.edit_text("❌ Компания не найдена или некорректный ИНН/ОГРН")
            return
        
        # Report is ready
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Скачать TXT", callback_data="download_txt")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_inn")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
        
        await status_msg.edit_text(
            "✅ Отчет готов! Нажмите кнопку ниже для скачивания файла.",
            reply_markup=keyboard
        )
        
        # Save data for download
        log.debug("saving company_text", length=len(response), user_id=msg.from_user.id)
        await state.update_data(company_text=response)
        log.debug("company_text saved", user_id=msg.from_user.id)
        
    except Exception as e:
        log.error("Check command failed", error=str(e), user_id=msg.from_user.id)
        await status_msg.edit_text(f"❌ Ошибка при получении данных: {str(e)}")


async def _process_name_search(msg: Message, state: FSMContext, query: str):
    """Process name search query"""
    log.info("process_name_search", query=query, user_id=msg.from_user.id)
    
    # Show loading message
    status_msg = await msg.answer("⏳ Ищу компанию по названию...")
    
    try:
        # Get company report (this will try name search)
        response = await fetch_company_report_markdown(query)
        
        if not response or response.startswith("Компания не найдена") or response.startswith("Введите ИНН/ОГРН"):
            await status_msg.edit_text(
                "❌ **Компания не найдена**\n\n"
                "Попробуйте:\n"
                "• Уточнить название компании\n"
                "• Ввести ИНН или ОГРН\n"
                "• Проверить правильность написания"
            )
            return
        
        if response.startswith("Ошибка"):
            await status_msg.edit_text(f"❌ {response}")
            return
        
        # Report is ready
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Скачать TXT", callback_data="download_txt")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_inn")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
        ])
        
        await status_msg.edit_text(
            "✅ Отчет готов! Нажмите кнопку ниже для скачивания файла.",
            reply_markup=keyboard
        )
        
        # Save data for download
        log.info("_process_name_search: saving company_text to state", 
                text_length=len(response),
                text_preview=response[:200] if response else None,
                user_id=msg.from_user.id)
        await state.update_data(company_text=response)
        log.info("_process_name_search: company_text saved to state successfully", user_id=msg.from_user.id)
        
    except Exception as e:
        log.error("Name search failed", error=str(e), user_id=msg.from_user.id)
        await status_msg.edit_text(f"❌ Ошибка при поиске компании: {str(e)}")
