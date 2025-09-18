# -*- coding: utf-8 -*-
"""
Главный файл приложения BizScan Bot
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from core.config import load_settings
from core.db import init_db
from core.logger import setup_logging
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.errors import ErrorsMiddleware

# Routers
from bot.handlers.start import router as start_router
from bot.handlers.menu import router as menu_router
from bot.handlers.search import router as search_router
from bot.handlers.company import router as company_router


async def main():
    """Основная функция запуска бота"""
    log = setup_logging()
    log.info("Starting application initialization")
    
    try:
        log.info("Loading settings...")
        settings = load_settings()
        log.info("Settings loaded successfully", 
                bot_token_present=bool(settings.BOT_TOKEN),
                dadata_key_present=bool(settings.DADATA_API_KEY),
                sqlite_path=settings.SQLITE_PATH)
    except Exception as e:
        log.error("Failed to load settings", error=str(e))
        raise
    
    try:
        log.info("Initializing database", sqlite_path=settings.SQLITE_PATH)
        await init_db(settings.SQLITE_PATH)
        log.info("Database initialized successfully")
    except Exception as e:
        log.error("Failed to initialize database", error=str(e))
        raise
    
    try:
        log.info("Creating bot instance")
        bot = Bot(
            token=settings.BOT_TOKEN, 
            default=DefaultBotProperties(parse_mode="Markdown")
        )
        log.info("Bot instance created successfully")
    except Exception as e:
        log.error("Failed to create bot instance", error=str(e))
        raise
    
    try:
        log.info("Creating dispatcher")
        dp = Dispatcher()
        log.info("Dispatcher created successfully")
    except Exception as e:
        log.error("Failed to create dispatcher", error=str(e))
        raise
    
    try:
        log.info("Setting up middlewares")
        dp.message.middleware(ThrottlingMiddleware(0.05))
        dp.callback_query.middleware(ThrottlingMiddleware(0.05))
        dp.update.middleware(ErrorsMiddleware())
        log.info("Middlewares configured successfully")
    except Exception as e:
        log.error("Failed to configure middlewares", error=str(e))
        raise
    
    try:
        log.info("Including routers")
        dp.include_router(start_router)
        dp.include_router(menu_router)
        dp.include_router(search_router)
        dp.include_router(company_router)
        log.info("All routers included successfully")
    except Exception as e:
        log.error("Failed to include routers", error=str(e))
        raise
    
    try:
        log.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        log.error("Bot polling failed", error=str(e))
        raise


if __name__ == "__main__":
    print("Starting bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (Ctrl+C)")
    except SystemExit:
        print("Bot stopped by system")
    except Exception as e:
        print(f"Bot error: {e}")
        import traceback
        traceback.print_exc()