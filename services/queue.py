# -*- coding: utf-8 -*-
"""
Queue system for managing API requests to Gamma and OFData with rate limiting and quotas.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import json
from core.logger import get_logger

from settings import (
    GAMMA_QUEUE_MAX_WORKERS,
    GAMMA_DAILY_LIMIT,
    GAMMA_RATE_LIMIT_PER_MINUTE,
    OFDATA_QUEUE_MAX_WORKERS,
    OFDATA_RATE_LIMIT_PER_MINUTE,
    OFDATA_RATE_LIMIT_PER_HOUR,
    QUEUE_PROCESS_INTERVAL,
    QUEUE_CLEANUP_INTERVAL,
)

logger = get_logger(__name__)


class TaskType(Enum):
    GAMMA_PDF = "gamma_pdf"
    GAMMA_PPTX = "gamma_pptx"
    OFDATA_COMPANY = "ofdata_company"
    OFDATA_PERSON = "ofdata_person"


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueTask:
    """Represents a task in the queue."""
    id: str
    task_type: TaskType
    payload: Dict[str, Any]
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int, requests_per_hour: int = None):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour or (requests_per_minute * 60)
        self.minute_requests: List[float] = []
        self.hour_requests: List[float] = []
    
    async def acquire(self) -> bool:
        """Acquire permission to make a request. Returns True if allowed."""
        now = time.time()
        
        # Clean old requests
        minute_ago = now - 60
        hour_ago = now - 3600
        
        self.minute_requests = [req_time for req_time in self.minute_requests if req_time > minute_ago]
        self.hour_requests = [req_time for req_time in self.hour_requests if req_time > hour_ago]
        
        # Check limits
        if len(self.minute_requests) >= self.requests_per_minute:
            return False
        if len(self.hour_requests) >= self.requests_per_hour:
            return False
        
        # Record this request
        self.minute_requests.append(now)
        self.hour_requests.append(now)
        return True
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Clean old requests
        self.minute_requests = [req_time for req_time in self.minute_requests if req_time > minute_ago]
        self.hour_requests = [req_time for req_time in self.hour_requests if req_time > hour_ago]
        
        if len(self.minute_requests) >= self.requests_per_minute:
            return 60 - (now - min(self.minute_requests))
        if len(self.hour_requests) >= self.requests_per_hour:
            return 3600 - (now - min(self.hour_requests))
        return 0


class QueueManager:
    """Manages API request queues with rate limiting and quotas."""
    
    def __init__(self):
        self.tasks: Dict[str, QueueTask] = {}
        self.workers: Dict[TaskType, List[asyncio.Task]] = {}
        self.rate_limiters: Dict[TaskType, RateLimiter] = {}
        self.daily_quotas: Dict[TaskType, int] = {}
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Initialize rate limiters
        self.rate_limiters[TaskType.GAMMA_PDF] = RateLimiter(GAMMA_RATE_LIMIT_PER_MINUTE)
        self.rate_limiters[TaskType.GAMMA_PPTX] = RateLimiter(GAMMA_RATE_LIMIT_PER_MINUTE)
        self.rate_limiters[TaskType.OFDATA_COMPANY] = RateLimiter(OFDATA_RATE_LIMIT_PER_MINUTE, OFDATA_RATE_LIMIT_PER_HOUR)
        self.rate_limiters[TaskType.OFDATA_PERSON] = RateLimiter(OFDATA_RATE_LIMIT_PER_MINUTE, OFDATA_RATE_LIMIT_PER_HOUR)
        
        # Initialize daily quotas
        self.daily_quotas[TaskType.GAMMA_PDF] = GAMMA_DAILY_LIMIT
        self.daily_quotas[TaskType.GAMMA_PPTX] = GAMMA_DAILY_LIMIT
        
        # Initialize workers
        self.workers[TaskType.GAMMA_PDF] = []
        self.workers[TaskType.GAMMA_PPTX] = []
        self.workers[TaskType.OFDATA_COMPANY] = []
        self.workers[TaskType.OFDATA_PERSON] = []
        
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the queue manager."""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting queue manager")
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Start workers for each task type
        for task_type in TaskType:
            max_workers = self._get_max_workers(task_type)
            for i in range(max_workers):
                worker = asyncio.create_task(self._worker(task_type, i))
                self.workers[task_type].append(worker)
        
        logger.info("Queue manager started", workers={
            task_type.value: len(workers) for task_type, workers in self.workers.items()
        })
    
    async def stop(self):
        """Stop the queue manager."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping queue manager")
        
        # Cancel all workers
        for workers in self.workers.values():
            for worker in workers:
                worker.cancel()
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Wait for workers to finish
        for workers in self.workers.values():
            await asyncio.gather(*workers, return_exceptions=True)
        
        if self._cleanup_task:
            await asyncio.gather(self._cleanup_task, return_exceptions=True)
        
        logger.info("Queue manager stopped")
    
    def _get_max_workers(self, task_type: TaskType) -> int:
        """Get maximum workers for task type."""
        if task_type in [TaskType.GAMMA_PDF, TaskType.GAMMA_PPTX]:
            return GAMMA_QUEUE_MAX_WORKERS
        elif task_type in [TaskType.OFDATA_COMPANY, TaskType.OFDATA_PERSON]:
            return OFDATA_QUEUE_MAX_WORKERS
        return 1
    
    async def add_task(self, task_type: TaskType, payload: Dict[str, Any], 
                      callback: Optional[Callable] = None) -> str:
        """Add a task to the queue."""
        task_id = f"{task_type.value}_{int(time.time() * 1000)}_{len(self.tasks)}"
        
        # Check daily quota
        if not await self._check_daily_quota(task_type):
            raise Exception(f"Daily quota exceeded for {task_type.value}")
        
        task = QueueTask(
            id=task_id,
            task_type=task_type,
            payload=payload,
            callback=callback
        )
        
        self.tasks[task_id] = task
        logger.info("Task added to queue", task_id=task_id, task_type=task_type.value)
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
            task.status = TaskStatus.CANCELLED
            logger.info("Task cancelled", task_id=task_id)
            return True
        
        return False
    
    async def _check_daily_quota(self, task_type: TaskType) -> bool:
        """Check if daily quota allows this task type."""
        # Reset daily quotas at midnight
        now = datetime.now()
        if now >= self.daily_reset_time + timedelta(days=1):
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            for quota_type in self.daily_quotas:
                self.daily_quotas[quota_type] = GAMMA_DAILY_LIMIT if quota_type in [TaskType.GAMMA_PDF, TaskType.GAMMA_PPTX] else 999999
        
        # Check quota
        quota = self.daily_quotas.get(task_type, 999999)
        if quota <= 0:
            return False
        
        # Decrease quota
        self.daily_quotas[task_type] -= 1
        return True
    
    async def _worker(self, task_type: TaskType, worker_id: int):
        """Worker coroutine for processing tasks."""
        logger.info("Worker started", task_type=task_type.value, worker_id=worker_id)
        
        while self._running:
            try:
                # Find pending task of this type
                task = None
                for t in self.tasks.values():
                    if t.task_type == task_type and t.status == TaskStatus.PENDING:
                        task = t
                        break
                
                if not task:
                    await asyncio.sleep(QUEUE_PROCESS_INTERVAL)
                    continue
                
                # Check rate limit
                rate_limiter = self.rate_limiters.get(task_type)
                if rate_limiter:
                    if not await rate_limiter.acquire():
                        wait_time = rate_limiter.get_wait_time()
                        logger.debug("Rate limit reached, waiting", task_type=task_type.value, wait_time=wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                
                # Process task
                await self._process_task(task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker error", task_type=task_type.value, worker_id=worker_id, error=str(e))
                await asyncio.sleep(1)
        
        logger.info("Worker stopped", task_type=task_type.value, worker_id=worker_id)
    
    async def _process_task(self, task: QueueTask):
        """Process a single task."""
        task.status = TaskStatus.PROCESSING
        task.started_at = time.time()
        
        logger.info("Processing task", task_id=task.id, task_type=task.task_type.value)
        
        try:
            # Import handlers dynamically to avoid circular imports
            if task.task_type in [TaskType.GAMMA_PDF, TaskType.GAMMA_PPTX]:
                from services.export.gamma_exporter import generate_pdf_from_report_text, generate_pptx_from_report_text
                
                if task.task_type == TaskType.GAMMA_PDF:
                    result = await asyncio.to_thread(
                        generate_pdf_from_report_text,
                        **task.payload
                    )
                elif task.task_type == TaskType.GAMMA_PPTX:
                    result = await asyncio.to_thread(
                        generate_pptx_from_report_text,
                        **task.payload
                    )
            elif task.task_type == TaskType.OFDATA_COMPANY:
                from services.report.ofdata_client import OFDataClient
                client = OFDataClient()
                result = await client.get_company_data(task.payload["inn"])
            elif task.task_type == TaskType.OFDATA_PERSON:
                from services.report.ofdata_client import OFDataClient
                client = OFDataClient()
                result = await client.get_person(task.payload["inn"])
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            
            logger.info("Task completed", task_id=task.id, task_type=task.task_type.value)
            
            # Call callback if provided
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(task)
                    else:
                        task.callback(task)
                except Exception as e:
                    logger.error("Callback error", task_id=task.id, error=str(e))
            
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                logger.warning("Task failed, retrying", task_id=task.id, retry_count=task.retry_count, error=str(e))
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                logger.error("Task failed permanently", task_id=task.id, error=str(e))
    
    async def _cleanup_loop(self):
        """Cleanup old completed tasks."""
        while self._running:
            try:
                await asyncio.sleep(QUEUE_CLEANUP_INTERVAL)
                
                # Remove old completed/failed tasks (older than 1 hour)
                cutoff_time = time.time() - 3600
                to_remove = []
                
                for task_id, task in self.tasks.items():
                    if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                        and task.completed_at and task.completed_at < cutoff_time):
                        to_remove.append(task_id)
                
                for task_id in to_remove:
                    del self.tasks[task_id]
                
                if to_remove:
                    logger.info("Cleaned up old tasks", count=len(to_remove))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error", error=str(e))


# Global queue manager instance
queue_manager = QueueManager()


async def get_queue_manager() -> QueueManager:
    """Get queue manager instance."""
    if not queue_manager._running:
        await queue_manager.start()
    return queue_manager
