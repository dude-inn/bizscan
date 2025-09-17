# -*- coding: utf-8 -*-
import aiosqlite
import os

DDL = '''
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS search_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
'''

async def init_db(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(DDL)
        await db.commit()

async def get_conn(path: str):
    return await aiosqlite.connect(path)
