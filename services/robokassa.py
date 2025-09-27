# -*- coding: utf-8 -*-
"""
Robokassa payment integration
"""
import hashlib
import hmac
from urllib.parse import urlencode, quote_plus
from decimal import Decimal
from typing import Optional, Dict, Any
from core.logger import get_logger

log = get_logger(__name__)

def _md5_hex(s: str) -> str:
    """MD5 hash in hex format"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()

class RobokassaService:
    def __init__(self, settings):
        self.settings = settings
    
    def build_payment_url(
        self,
        inv_id: int,
        amount: Decimal,
        description: str,
        email: Optional[str] = None,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Формирует ссылку на оплату Robokassa.
        Подпись: MD5(MerchantLogin:OutSum:InvId:Password1)
        """
        login = self.settings.ROBOKASSA_MERCHANT_LOGIN
        out_sum = f"{amount:.2f}"

        # Доп. параметры (все начинающиеся с 'shp_') попадут в подпись и вернутся в колбеках
        shp = {}
        if extra_params:
            shp = {k: v for k, v in extra_params.items() if k.startswith("shp_")}

        base_sign_str = f"{login}:{out_sum}:{inv_id}:{self.settings.ROBOKASSA_PASSWORD1}"
        # Порядок включения shp_* в подпись — по имени, отсортируй по ключу
        if shp:
            for k in sorted(shp.keys()):
                base_sign_str += f":{k}={shp[k]}"

        signature_value = _md5_hex(base_sign_str)

        query = {
            "MerchantLogin": login,
            "OutSum": out_sum,
            "InvId": inv_id,
            "Description": description,
            "SignatureValue": signature_value,
            "Email": email or "",
            "SuccessURL": self.settings.SUCCESS_URL,
            "FailURL": self.settings.FAIL_URL,
        }
        if self.settings.ROBOKASSA_IS_TEST:
            query["IsTest"] = 1
        query.update(shp)

        return f"{self.settings.ROBOKASSA_BASE_URL}?{urlencode(query, quote_via=quote_plus)}"

    def verify_result_signature(
        self,
        merchant_login: str,
        out_sum: str,
        inv_id: str,
        signature_value: str,
        shp: Dict[str, str],
    ) -> bool:
        """
        Проверяем подпись уведомления на ResultURL:
        MD5(OutSum:InvId:Password2[:shp_*])
        """
        sign_str = f"{out_sum}:{inv_id}:{self.settings.ROBOKASSA_PASSWORD2}"
        if shp:
            for k in sorted(shp.keys()):
                sign_str += f":{k}={shp[k]}"
        expected = _md5_hex(sign_str)
        return expected.lower() == (signature_value or "").lower()

    async def refund_payment(
        self,
        operation_id: str,
        amount: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Возврат платежа через Robokassa API
        """
        import httpx
        
        payload = {
            "RoboxPartnerId": self.settings.ROBOKASSA_PARTNER_ID,
            "OperationId": operation_id,
            "Amount": amount,
            "Reason": reason,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(self.settings.ROBOKASSA_REFUND_URL, json=payload)
                r.raise_for_status()
                data = r.json()
                log.info("Refund successful", operation_id=operation_id, amount=amount, response=data)
                return data
        except Exception as e:
            log.error("Refund failed", error=str(e), operation_id=operation_id, amount=amount)
            raise



