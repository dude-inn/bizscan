# -*- coding: utf-8 -*-
"""
Robokassa callbacks handling
"""
from fastapi import APIRouter, Request, HTTPException, Response
from decimal import Decimal
import hashlib
from core.logger import get_logger
from services.robokassa import RobokassaService
from core.config import load_settings

router = APIRouter(prefix="/robokassa", tags=["robokassa"])
log = get_logger(__name__)

settings = load_settings()
robokassa = RobokassaService(settings)

@router.post("/result")
@router.get("/result")
async def result(request: Request):
    """
    Robokassa шлёт сюда подтверждение платежа.
    Надо:
    - проверить подпись;
    - пометить заказ как оплаченный;
    - вернуть строго 'OK{InvId}' (без лишних пробелов/символов).
    """
    try:
        data = dict((await request.form()) if request.method == "POST" else request.query_params)
        merchant_login = data.get("MerchantLogin")
        out_sum = data.get("OutSum")
        inv_id = data.get("InvId")
        signature_value = data.get("SignatureValue")

        # соберём все shp_* (они участвуют в подписи, если использовали при инициации)
        shp = {k: v for k, v in data.items() if k.startswith("shp_")}

        if not robokassa.verify_result_signature(merchant_login, out_sum, inv_id, signature_value, shp):
            log.error("Bad signature", merchant_login=merchant_login, inv_id=inv_id)
            raise HTTPException(status_code=400, detail="Bad signature")

        # Отмечаем заказ как оплаченный
        from services.orders import OrderService
        order_service = OrderService(settings.SQLITE_PATH)
        
        await order_service.mark_paid(
            order_id=int(inv_id),
            operation_id=inv_id,  # Используем inv_id как operation_id
            metadata={"amount": out_sum, "merchant_login": merchant_login}
        )
        
        log.info("Payment confirmed", inv_id=inv_id, amount=out_sum)
        return Response(content=f"OK{inv_id}", media_type="text/plain")
        
    except Exception as e:
        log.error("Result callback failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")

@router.get("/success")
async def success(request: Request):
    """
    Пользователь вернулся после успешной оплаты (страница для клиента).
    """
    return {"status": "success", "message": "Оплата прошла успешно. Отчёт будет отправлен в боте."}

@router.get("/fail")
async def fail(request: Request):
    """
    Пользователь вернулся после неудачной оплаты.
    """
    return {"status": "fail", "message": "Оплата не завершена или отменена."}
