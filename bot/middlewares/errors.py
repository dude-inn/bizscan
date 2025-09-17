# -*- coding: utf-8 -*-
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Dict, Any, Callable, Awaitable
import logging

class ErrorsMiddleware(BaseMiddleware):
    async def __call__(self,
                       handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        try:
            # Логируем все входящие обновления
            if hasattr(event, 'callback_query') and event.callback_query:
                logging.debug(f"Callback query received: {event.callback_query.data}, user_id: {event.callback_query.from_user.id}")
            return await handler(event, data)
        except Exception as e:
            logging.exception("Unhandled bot error")
            # Падаем мягко: пробрасываем
            raise
