# -*- coding: utf-8 -*-
"""
Legacy StatsService - now uses DatabaseService for both SQLite and PostgreSQL.
"""
import time
import json
from typing import Dict, List, Optional, Any
from core.logger import get_logger
from services.database import get_db_service

log = get_logger(__name__)

class StatsService:
    """Legacy StatsService that delegates to DatabaseService."""
    
    def __init__(self, db_path: str = None):
        # db_path is kept for backward compatibility but not used
        self.db_path = db_path
    
    async def track_event(self, event_type: str, user_id: int, metadata: Optional[Dict] = None):
        """Track a bot event"""
        try:
            db = await get_db_service()
            await db.track_event(event_type, user_id, metadata)
            log.debug("Event tracked", event_type=event_type, user_id=user_id)
        except Exception as e:
            log.error("Failed to track event", error=str(e), event_type=event_type, user_id=user_id)
    
    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get bot statistics for the last N days"""
        try:
            db = await get_db_service()
            return await db.get_stats(days)
        except Exception as e:
            log.error("Failed to get stats", error=str(e))
            return {
                "period_days": days,
                "total_users": 0,
                "total_searches": 0,
                "total_reports": 0,
                "conversion_rate": 0,
                "daily_stats": [],
                "top_hours": []
            }

    async def get_event_count_today(self, event_type: str) -> int:
        """Get count of events today by type."""
        try:
            db = await get_db_service()
            return await db.get_event_count_today(event_type)
        except Exception as e:
            log.error("Failed to count today's events", error=str(e), event_type=event_type)
            return 0

