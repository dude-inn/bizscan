# -*- coding: utf-8 -*-
import time, json
from typing import Optional
import aiosqlite

class CacheRepository:
    def __init__(self, db_path: str, ttl_minutes: int = 30):
        self.db_path = db_path
        self.ttl = ttl_minutes * 60

    async def _get_db(self):
        return await aiosqlite.connect(self.db_path)

    async def get(self, key: str) -> Optional[str]:
        async with await self._get_db() as db:
            async with db.execute("SELECT value, created_at FROM cache WHERE key=?", (key,)) as cur:
                row = await cur.fetchone()
                if not row: return None
                value, created = row
                if time.time() - created > self.ttl:
                    await db.execute("DELETE FROM cache WHERE key=?", (key,))
                    await db.commit()
                    return None
                return value

    async def set(self, key: str, value: str):
        now = int(time.time())
        async with await self._get_db() as db:
            await db.execute("REPLACE INTO cache(key, value, created_at) VALUES (?, ?, ?)", (key, value, now))
            await db.commit()

    async def get_search(self, key: str) -> Optional[str]:
        async with await self._get_db() as db:
            async with db.execute("SELECT value, created_at FROM search_cache WHERE key=?", (key,)) as cur:
                row = await cur.fetchone()
                if not row: return None
                value, created = row
                if time.time() - created > self.ttl:
                    await db.execute("DELETE FROM search_cache WHERE key=?", (key,))
                    await db.commit()
                    return None
                return value

    async def set_search(self, key: str, value: str):
        now = int(time.time())
        async with await self._get_db() as db:
            await db.execute("REPLACE INTO search_cache(key, value, created_at) VALUES (?, ?, ?)", (key, value, now))
            await db.commit()
