# -*- coding: utf-8 -*-
import aiosqlite
import os

DDL = '''
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    ttl_hours INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS search_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS bot_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_bot_stats_event_type ON bot_stats(event_type);
CREATE INDEX IF NOT EXISTS idx_bot_stats_user_id ON bot_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_stats_timestamp ON bot_stats(timestamp);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_inn TEXT NOT NULL,
    company_name TEXT,
    amount DECIMAL(10,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    paid_at INTEGER,
    operation_id TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
'''

async def init_db(path: str):
    from core.logger import get_logger
    log = get_logger(__name__)
    
    try:
        log.info("Initializing database", db_path=path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        log.debug("Database directory ensured", directory=os.path.dirname(path))
    except Exception as e:
        log.error("Failed to create database directory", error=str(e))
        raise
    
    try:
        log.debug("Connecting to database")
        async with aiosqlite.connect(path) as db:
            log.debug("Database connection established")
            # Attempt lightweight migration: add ttl_hours if missing
            try:
                cur = await db.execute("PRAGMA table_info(cache)")
                cols = await cur.fetchall()
                col_names = {row[1] for row in cols}
                if "ttl_hours" not in col_names:
                    await db.execute("ALTER TABLE cache ADD COLUMN ttl_hours INTEGER NOT NULL DEFAULT 24")
                    log.info("Migrated cache table: added ttl_hours column")
                    await db.commit()
            except Exception as e:
                # Suppress "duplicate column name" error specifically
                if "duplicate column name" in str(e).lower():
                    log.info("Column ttl_hours already exists, skipping migration")
                else:
                    # ignore other errors; DDL below will create table if absent
                    log.warning("Migration error (non-critical)", error=str(e))
                pass
            
            log.debug("Executing DDL script")
            await db.executescript(DDL)
            log.debug("DDL script executed successfully")
            await db.commit()
            log.debug("Database transaction committed")
        log.info("Database initialized", db_path=path)
    except Exception as e:
        log.error("Failed to initialize database", error=str(e))
        raise

async def get_conn(path: str):
    return await aiosqlite.connect(path)
