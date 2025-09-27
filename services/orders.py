# -*- coding: utf-8 -*-
"""
Order management service
"""
import time
import json
from typing import Optional, Dict, Any
from decimal import Decimal
from core.logger import get_logger

log = get_logger(__name__)

class OrderService:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def create_order(
        self,
        user_id: int,
        company_inn: str,
        company_name: Optional[str] = None,
        amount: Decimal = None,
    ) -> int:
        """Создать новый заказ"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                cur = await db.execute(
                    "INSERT INTO orders (user_id, company_inn, company_name, amount, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, company_inn, company_name, float(amount), int(time.time()))
                )
                await db.commit()
                order_id = cur.lastrowid
                log.info("Order created", order_id=order_id, user_id=user_id, company_inn=company_inn)
                return order_id
        except Exception as e:
            log.error("Failed to create order", error=str(e), user_id=user_id, company_inn=company_inn)
            raise
    
    async def mark_paid(
        self,
        order_id: int,
        operation_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Отметить заказ как оплаченный"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE orders SET status = 'paid', paid_at = ?, operation_id = ?, metadata = ? WHERE id = ?",
                    (int(time.time()), operation_id, json.dumps(metadata) if metadata else None, order_id)
                )
                await db.commit()
                log.info("Order marked as paid", order_id=order_id, operation_id=operation_id)
                return True
        except Exception as e:
            log.error("Failed to mark order as paid", error=str(e), order_id=order_id)
            return False
    
    async def mark_failed(
        self,
        order_id: int,
        reason: str,
    ) -> bool:
        """Отметить заказ как неудачный"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE orders SET status = 'failed', metadata = ? WHERE id = ?",
                    (json.dumps({"failure_reason": reason}), order_id)
                )
                await db.commit()
                log.info("Order marked as failed", order_id=order_id, reason=reason)
                return True
        except Exception as e:
            log.error("Failed to mark order as failed", error=str(e), order_id=order_id)
            return False
    
    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Получить заказ по ID"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                cur = await db.execute(
                    "SELECT * FROM orders WHERE id = ?",
                    (order_id,)
                )
                row = await cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "company_inn": row[2],
                        "company_name": row[3],
                        "amount": row[4],
                        "status": row[5],
                        "created_at": row[6],
                        "paid_at": row[7],
                        "operation_id": row[8],
                        "metadata": json.loads(row[9]) if row[9] else None,
                    }
                return None
        except Exception as e:
            log.error("Failed to get order", error=str(e), order_id=order_id)
            return None
    
    async def get_user_orders(self, user_id: int, limit: int = 10) -> list:
        """Получить заказы пользователя"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                cur = await db.execute(
                    "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit)
                )
                rows = await cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "user_id": row[1],
                        "company_inn": row[2],
                        "company_name": row[3],
                        "amount": row[4],
                        "status": row[5],
                        "created_at": row[6],
                        "paid_at": row[7],
                        "operation_id": row[8],
                        "metadata": json.loads(row[9]) if row[9] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            log.error("Failed to get user orders", error=str(e), user_id=user_id)
            return []



