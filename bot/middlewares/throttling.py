# -*- coding: utf-8 -*-
import asyncio
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Dict, Any, Callable, Awaitable

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, delay: float = 0.2):
        super().__init__()
        self.delay = delay

    async def __call__(self,
                       handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        await asyncio.sleep(self.delay)
        return await handler(event, data)
