# -*- coding: utf-8 -*-
import asyncio
import sys
import traceback

print("Test bot starting...")

try:
    from core.config import load_settings
    print("Settings imported")
    
    settings = load_settings()
    print(f"Settings loaded: {settings.BOT_TOKEN[:10]}...")
    
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    print("Aiogram imported")
    
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    print("Bot created")
    
    dp = Dispatcher()
    print("Dispatcher created")
    
    async def test_polling():
        print("Starting polling...")
        await dp.start_polling(bot)
    
    print("Starting asyncio...")
    asyncio.run(test_polling())
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)

