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
    from core.logger import setup_logging
    log = setup_logging()
    
    try:
        log.info("Initializing database", db_path=path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        log.info("Database directory created", directory=os.path.dirname(path))
    except Exception as e:
        log.error("Failed to create database directory", error=str(e))
        raise
    
    try:
        log.info("Connecting to database")
        async with aiosqlite.connect(path) as db:
            log.info("Database connection established")
            log.info("Executing DDL script")
            await db.executescript(DDL)
            log.info("DDL script executed successfully")
            await db.commit()
            log.info("Database transaction committed")
        log.info("Database initialization completed successfully")
    except Exception as e:
        log.error("Failed to initialize database", error=str(e))
        raise

async def get_conn(path: str):
    return await aiosqlite.connect(path)
