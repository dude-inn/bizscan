# -*- coding: utf-8 -*-
"""
Главный файл приложения BizScan Bot
"""
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties

from core.config import load_settings
from core.db import init_db
from core.logger import setup_logging
from services.database import get_db_service
from services.queue import get_queue_manager
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.errors import ErrorsMiddleware

# Set Windows event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Routers
from bot.handlers.start import router as start_router
from bot.handlers.menu import router as menu_router
from bot.handlers.search import router as search_router
from bot.handlers.company import router as company_router
from bot.handlers.report import router as report_router
from bot.handlers.check import router as check_router
from bot.handlers.stats import router as stats_router
from bot.handlers.payment import router as payment_router


async def main():
    """Основная функция запуска бота"""
    # Load settings first to configure logging properly
    settings = load_settings()
    log = setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
    log.info("Starting application initialization")

    bot = None
    db_service = None
    queue_manager = None

    try:
        log.info(
            "Settings loaded successfully",
            bot_token_present=bool(settings.BOT_TOKEN),
            ofdata_key_present=bool(settings.OFDATA_KEY),
            sqlite_path=settings.SQLITE_PATH,
        )
        if not settings.BOT_TOKEN:
            log.error("BOT_TOKEN is not configured")
            raise RuntimeError("BOT_TOKEN is empty. Set it in settings or environment.")
    except Exception as e:
        log.error("Failed to load settings", error=str(e))
        raise

    try:
        log.info(
            "Initializing database",
            database_type=settings.DATABASE_TYPE,
            sqlite_path=settings.SQLITE_PATH,
        )
        # Initialize legacy SQLite database for backward compatibility
        await init_db(settings.SQLITE_PATH)
        # Initialize new database service (PostgreSQL or SQLite)
        db_service = await get_db_service()
        # Initialize queue manager
        queue_manager = await get_queue_manager()
        log.info("Database and queue manager initialized successfully")
    except Exception as e:
        log.error("Failed to initialize database", error=str(e))
        raise

    try:
        log.info("Creating bot instance")
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="Markdown"),
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
        dp.include_router(report_router)
        dp.include_router(check_router)
        dp.include_router(stats_router)
        dp.include_router(payment_router)
        log.info("All routers included successfully")
    except Exception as e:
        log.error("Failed to include routers", error=str(e))
        raise

    # Configure bot command list for the Telegram client
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Запустить бота"),
                BotCommand(command="help", description="Помощь и стоимость отчёта"),
                BotCommand(
                    command="check",
                    description="Проверить компанию: /check <ИНН/ОГРН или название>",
                ),
                BotCommand(command="menu", description="Показать главное меню"),
                BotCommand(command="stats", description="Статистика бота (только для админов)"),
            ]
        )
        log.info("Bot commands configured")
    except Exception as e:
        log.warning("Failed to set bot commands", error=str(e))

    try:
        log.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        log.error("Bot polling failed", error=str(e))
        raise
    finally:
        if bot:
            log.info("Closing bot session...")
            await bot.session.close()
            log.info("Bot session closed")

        if queue_manager:
            try:
                await queue_manager.stop()
                log.info("Queue manager stopped")
            except Exception as e:
                log.error("Failed to stop queue manager", error=str(e))

        if db_service:
            try:
                await db_service.close()
                log.info("Database service closed")
            except Exception as e:
                log.error("Failed to close database service", error=str(e))


if __name__ == "__main__":
    print("Starting bot...")
    exit_code = 0
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (Ctrl+C)")
        exit_code = 130
    except SystemExit as exc:
        print("Bot stopped by system")
        exit_code = exc.code if isinstance(exc.code, int) else exit_code
    except Exception as e:
        print(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    sys.exit(exit_code)
