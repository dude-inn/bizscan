# -*- coding: utf-8 -*-
from settings import PAYMENTS_ENABLED, PAYMENT_AMOUNT_RUB
from .yookassa_stub import create_payment, check_payment

async def initiate_payment(user_id: int, description: str = "Полный отчёт BizScan"):
    if not PAYMENTS_ENABLED:
        # Симулируем моментальный успех
        return {"ok": True, "payment_id": "stub", "amount": PAYMENT_AMOUNT_RUB}
    # В будущем: реальная интеграция ЮKassa
    p = create_payment(PAYMENT_AMOUNT_RUB, description, {"user_id": user_id})
    return {"ok": p.status == "succeeded", "payment_id": p.id, "amount": p.amount}

async def ensure_payment(payment_id: str):
    if not PAYMENTS_ENABLED:
        return True
    p = check_payment(payment_id)
    return p.status == "succeeded"
