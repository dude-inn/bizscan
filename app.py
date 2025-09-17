# -*- coding: utf-8 -*-
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
from bot.handlers.payment import router as payment_router


async def main():
    settings = load_settings()
    log = setup_logging()
    await init_db(settings.SQLITE_PATH)

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    # Middlewares
    dp.message.middleware(ThrottlingMiddleware(0.05))
    dp.callback_query.middleware(ThrottlingMiddleware(0.05))
    dp.update.middleware(ErrorsMiddleware())

    # Routers
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(search_router)
    dp.include_router(company_router)
    dp.include_router(payment_router)

    log.info("Bot starting (polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        print("Starting bot...")
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped by user")
        pass
    except Exception as e:
        print(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
