# -*- coding: utf-8 -*-
"""
Система кэширования для провайдеров данных
"""
import json
import asyncio
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite
from pydantic import BaseModel

from core.logger import setup_logging

log = setup_logging()


class CacheConfig(BaseModel):
    """Конфигурация кэша"""
    db_path: str = "data/cache.db"
    default_ttl_hours: int = 24


class CacheService:
    """Сервис кэширования"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._db_path = Path(config.db_path)
        self._db_path.parent.mkdir(exist_ok=True)
    
    async def _get_connection(self) -> aiosqlite.Connection:
        """Получает соединение с БД"""
        conn = await aiosqlite.connect(self._db_path)
        
        # Создаем таблицу если не существует
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                ttl_hours INTEGER NOT NULL
            )
        """)
        await conn.commit()
        
        return conn
    
    async def get(self, key: str) -> Optional[Any]:
        """Получает значение из кэша"""
        try:
            conn = await self._get_connection()
            try:
                cursor = await conn.execute(
                    "SELECT value, created_at, ttl_hours FROM cache WHERE key = ?",
                    (key,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                value, created_at, ttl_hours = row
                created_time = datetime.fromtimestamp(created_at)
                
                # Проверяем, не истек ли TTL
                if datetime.now() - created_time > timedelta(hours=ttl_hours):
                    await self.delete(key)
                    return None
                
                return json.loads(value)
            finally:
                await conn.close()
                
        except Exception as e:
            log.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl_hours: Optional[int] = None) -> bool:
        """Сохраняет значение в кэш"""
        try:
            ttl = ttl_hours or self.config.default_ttl_hours
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            
            conn = await self._get_connection()
            try:
                await conn.execute("""
                    INSERT OR REPLACE INTO cache (key, value, created_at, ttl_hours)
                    VALUES (?, ?, ?, ?)
                """, (key, serialized, int(datetime.now().timestamp()), ttl))
                await conn.commit()
            finally:
                await conn.close()
            
            return True
            
        except Exception as e:
            log.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Удаляет значение из кэша"""
        try:
            conn = await self._get_connection()
            try:
                await conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                await conn.commit()
            finally:
                await conn.close()
            return True
            
        except Exception as e:
            log.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def clear_expired(self) -> int:
        """Очищает истекшие записи"""
        try:
            conn = await self._get_connection()
            try:
                cursor = await conn.execute("""
                    DELETE FROM cache 
                    WHERE datetime(created_at, '+' || ttl_hours || ' hours') < datetime('now')
                """)
                await conn.commit()
                return cursor.rowcount
            finally:
                await conn.close()
                
        except Exception as e:
            log.error("Cache clear_expired failed", error=str(e))
            return 0


# Глобальный экземпляр кэша
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Получает глобальный экземпляр кэша"""
    global _cache_service
    if _cache_service is None:
        config = CacheConfig()
        _cache_service = CacheService(config)
    return _cache_service


async def get_cached(key: str) -> Optional[Any]:
    """Получает значение из кэша"""
    return await get_cache_service().get(key)


async def set_cached(key: str, value: Any, ttl_hours: Optional[int] = None) -> bool:
    """Сохраняет значение в кэш"""
    return await get_cache_service().set(key, value, ttl_hours)


async def clear_cache(key: str) -> bool:
    """Очищает кэш по ключу"""
    return await get_cache_service().delete(key)
