# -*- coding: utf-8 -*-
"""
Database service with SQLAlchemy ORM support for both SQLite and PostgreSQL.
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text, JSON, Index
from core.logger import get_logger

from settings import DATABASE_URL, DATABASE_TYPE

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class BotStats(Base):
    """Bot statistics tracking table."""
    __tablename__ = "bot_stats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    event_metadata: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Indexes for better performance
    __table_args__ = (
        Index('idx_bot_stats_event_type', 'event_type'),
        Index('idx_bot_stats_user_id', 'user_id'),
        Index('idx_bot_stats_timestamp', 'timestamp'),
        Index('idx_bot_stats_event_timestamp', 'event_type', 'timestamp'),
    )


class DatabaseService:
    """Database service with async SQLAlchemy support."""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing database", url=self.database_url, type=DATABASE_TYPE)
            
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            self._initialized = False
            logger.info("Database connections closed")
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self._initialized:
            await self.initialize()
        return self.session_factory()
    
    async def track_event(self, event_type: str, user_id: int, metadata: Optional[Dict] = None):
        """Track a bot event."""
        try:
            import json
            import time
            
            async with (await self.get_session()) as session:
                stats = BotStats(
                    event_type=event_type,
                    user_id=user_id,
                    timestamp=int(time.time()),
                    event_metadata=json.dumps(metadata) if metadata else None
                )
                session.add(stats)
                await session.commit()
                
                logger.debug("Event tracked", event_type=event_type, user_id=user_id)
                
        except Exception as e:
            logger.error("Failed to track event", error=str(e), event_type=event_type, user_id=user_id)
    
    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get bot statistics for the last N days."""
        try:
            import time
            from sqlalchemy import func, text
            
            cutoff_time = int(time.time()) - (days * 24 * 60 * 60)
            
            async with (await self.get_session()) as session:
                # Total unique users
                result = await session.execute(
                    text("SELECT COUNT(DISTINCT user_id) FROM bot_stats WHERE timestamp >= :cutoff"),
                    {"cutoff": cutoff_time}
                )
                total_users = result.scalar() or 0
                
                # Total searches
                result = await session.execute(
                    text("SELECT COUNT(*) FROM bot_stats WHERE event_type = 'search' AND timestamp >= :cutoff"),
                    {"cutoff": cutoff_time}
                )
                total_searches = result.scalar() or 0
                
                # Total successful reports
                result = await session.execute(
                    text("SELECT COUNT(*) FROM bot_stats WHERE event_type = 'report_success' AND timestamp >= :cutoff"),
                    {"cutoff": cutoff_time}
                )
                total_reports = result.scalar() or 0
                
                # Daily aggregates (using database-specific date functions)
                if DATABASE_TYPE == "postgresql":
                    daily_query = text("""
                        SELECT 
                            DATE(to_timestamp(timestamp)) as date,
                            COUNT(DISTINCT user_id) as unique_users,
                            COUNT(CASE WHEN event_type = 'search' THEN 1 END) as searches,
                            COUNT(CASE WHEN event_type = 'report_success' THEN 1 END) as reports
                        FROM bot_stats 
                        WHERE timestamp >= :cutoff
                        GROUP BY DATE(to_timestamp(timestamp))
                        ORDER BY date DESC
                        LIMIT 7
                    """)
                else:  # SQLite
                    daily_query = text("""
                        SELECT 
                            DATE(datetime(timestamp, 'unixepoch')) as date,
                            COUNT(DISTINCT user_id) as unique_users,
                            COUNT(CASE WHEN event_type = 'search' THEN 1 END) as searches,
                            COUNT(CASE WHEN event_type = 'report_success' THEN 1 END) as reports
                        FROM bot_stats 
                        WHERE timestamp >= :cutoff
                        GROUP BY DATE(datetime(timestamp, 'unixepoch'))
                        ORDER BY date DESC
                        LIMIT 7
                    """)
                
                result = await session.execute(daily_query, {"cutoff": cutoff_time})
                daily_stats = [{"date": row[0], "unique_users": row[1], "searches": row[2], "reports": row[3]} for row in result.fetchall()]
                
                # Top hours of usage
                if DATABASE_TYPE == "postgresql":
                    hours_query = text("""
                        SELECT 
                            EXTRACT(hour FROM to_timestamp(timestamp)) as hour,
                            COUNT(*) as count
                        FROM bot_stats 
                        WHERE timestamp >= :cutoff
                        GROUP BY EXTRACT(hour FROM to_timestamp(timestamp))
                        ORDER BY count DESC
                        LIMIT 5
                    """)
                else:  # SQLite
                    hours_query = text("""
                        SELECT 
                            strftime('%H', datetime(timestamp, 'unixepoch')) as hour,
                            COUNT(*) as count
                        FROM bot_stats 
                        WHERE timestamp >= :cutoff
                        GROUP BY strftime('%H', datetime(timestamp, 'unixepoch'))
                        ORDER BY count DESC
                        LIMIT 5
                    """)
                
                result = await session.execute(hours_query, {"cutoff": cutoff_time})
                top_hours = [{"hour": int(row[0]), "count": row[1]} for row in result.fetchall()]
                
                # Conversion rate
                conversion_rate = (total_reports / total_searches * 100) if total_searches > 0 else 0
                
                return {
                    "period_days": days,
                    "total_users": total_users,
                    "total_searches": total_searches,
                    "total_reports": total_reports,
                    "conversion_rate": round(conversion_rate, 2),
                    "daily_stats": daily_stats,
                    "top_hours": top_hours
                }
                
        except Exception as e:
            logger.error("Failed to get stats", error=str(e))
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
            import datetime as _dt
            from sqlalchemy import text
            
            start_of_day = _dt.datetime.combine(_dt.date.today(), _dt.time.min)
            cutoff = int(start_of_day.timestamp())
            
            async with (await self.get_session()) as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM bot_stats WHERE event_type = :event_type AND timestamp >= :cutoff"),
                    {"event_type": event_type, "cutoff": cutoff}
                )
                return result.scalar() or 0
                
        except Exception as e:
            logger.error("Failed to count today's events", error=str(e), event_type=event_type)
            return 0


# Global database service instance
db_service = DatabaseService()


async def get_db_service() -> DatabaseService:
    """Get database service instance."""
    if not db_service._initialized:
        await db_service.initialize()
    return db_service




