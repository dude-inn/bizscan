# -*- coding: utf-8 -*-
"""
Обработчики статистики бота
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from core.logger import get_logger
from services.stats import StatsService
from core.config import load_settings

router = Router(name="stats")
log = get_logger(__name__)

# Admin user IDs (добавь свои)
ADMIN_IDS = [123456789]  # Замени на реальные ID админов

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in ADMIN_IDS

@router.message(F.text == "/stats")
async def stats_command(msg: Message, state: FSMContext):
    """Команда /stats для админов"""
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Доступ запрещён. Эта команда только для администраторов.")
        return
    
    try:
        settings = load_settings()
        stats = StatsService(settings.SQLITE_PATH)
        data = await stats.get_stats(days=30)
        
        # Форматируем статистику
        text = f"""📊 **Статистика бота (последние {data['period_days']} дней)**

👥 **Пользователи:** {data['total_users']} уникальных
🔍 **Поиски:** {data['total_searches']}
📄 **Отчёты:** {data['total_reports']}
📈 **Конверсия:** {data['conversion_rate']}%

**📅 Последние 7 дней:**
"""
        
        for day in data['daily_stats'][:7]:
            text += f"• {day['date']}: {day['unique_users']} пользователей, {day['searches']} поисков, {day['reports']} отчётов\n"
        
        if data['top_hours']:
            text += "\n**🕐 Топ часов активности:**\n"
            for hour_data in data['top_hours']:
                text += f"• {hour_data['hour']}:00 — {hour_data['count']} событий\n"
        
        await msg.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        log.error("Stats command failed", error=str(e), user_id=msg.from_user.id)
        await msg.answer("❌ Ошибка получения статистики.")

@router.callback_query(F.data == "stats_7d")
async def stats_7d(cb: CallbackQuery, state: FSMContext):
    """Статистика за 7 дней"""
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        stats = StatsService(settings.SQLITE_PATH)
        data = await stats.get_stats(days=7)
        
        text = f"""📊 **Статистика за 7 дней**

👥 Пользователи: {data['total_users']}
🔍 Поиски: {data['total_searches']}
📄 Отчёты: {data['total_reports']}
📈 Конверсия: {data['conversion_rate']}%
"""
        await cb.message.edit_text(text)
        await cb.answer()
        
    except Exception as e:
        log.error("Stats 7d failed", error=str(e), user_id=cb.from_user.id)
        await cb.answer("❌ Ошибка получения статистики", show_alert=True)

@router.callback_query(F.data == "stats_30d")
async def stats_30d(cb: CallbackQuery, state: FSMContext):
    """Статистика за 30 дней"""
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        settings = load_settings()
        stats = StatsService(settings.SQLITE_PATH)
        data = await stats.get_stats(days=30)
        
        text = f"""📊 **Статистика за 30 дней**

👥 Пользователи: {data['total_users']}
🔍 Поиски: {data['total_searches']}
📄 Отчёты: {data['total_reports']}
📈 Конверсия: {data['conversion_rate']}%
"""
        await cb.message.edit_text(text)
        await cb.answer()
        
    except Exception as e:
        log.error("Stats 30d failed", error=str(e), user_id=cb.from_user.id)
        await cb.answer("❌ Ошибка получения статистики", show_alert=True)
