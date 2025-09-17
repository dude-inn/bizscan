# -*- coding: utf-8 -*-
from typing import Any, Dict, Literal
from dataclasses import dataclass

@dataclass
class PaymentStub:
    id: str
    status: Literal['pending', 'succeeded', 'canceled'] = 'succeeded'
    amount: int = 0
    description: str = ""

def create_payment(amount: int, description: str, metadata: Dict[str, Any]) -> PaymentStub:
    return PaymentStub(id="stub-payment-id", status="succeeded", amount=amount, description=description)

def check_payment(payment_id: str) -> PaymentStub:
    return PaymentStub(id=payment_id, status="succeeded")
