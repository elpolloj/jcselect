"""Health check API routes."""
from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter, Depends
from loguru import logger
from sqlmodel import Session, text

from jcselect.api.dependencies import get_db
from jcselect.api.schemas.health_schemas import (
    DatabaseHealth,
    HealthResponse,
    SyncQueueHealth,
)
from jcselect.sync.queue import sync_queue

router = APIRouter(prefix="/health", tags=["Health"])

# Track server start time for uptime calculation
_server_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Comprehensive health check endpoint.

    Args:
        db: Database session

    Returns:
        Server health status
    """
    # Check database connectivity
    db_status = "disconnected"
    try:
        # Simple query to test database connection
        db.exec(text("SELECT 1")).first()
        db_status = "connected"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")

    # Get sync queue size
    queue_size = 0
    try:
        queue_size = sync_queue.get_queue_size()
    except Exception as e:
        logger.warning(f"Sync queue health check failed: {e}")

    # Calculate uptime
    uptime_seconds = time.time() - _server_start_time

    # Overall status
    overall_status = "ok" if db_status == "connected" else "error"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database_status=db_status,
        sync_queue_size=queue_size,
        uptime_seconds=uptime_seconds
    )


@router.get("/database", response_model=DatabaseHealth)
async def database_health(db: Session = Depends(get_db)) -> DatabaseHealth:
    """
    Detailed database health check.

    Args:
        db: Database session

    Returns:
        Database health details
    """
    start_time = time.time()
    error_message = None
    status = "disconnected"

    try:
        # Test database connection with a simple query
        db.exec(text("SELECT 1")).first()
        status = "connected"
    except Exception as e:
        error_message = str(e)
        logger.warning(f"Database health check failed: {e}")

    connection_time_ms = (time.time() - start_time) * 1000

    return DatabaseHealth(
        status=status,
        connection_time_ms=connection_time_ms if status == "connected" else None,
        error_message=error_message
    )


@router.get("/sync-queue", response_model=SyncQueueHealth)
async def sync_queue_health() -> SyncQueueHealth:
    """
    Sync queue health and statistics.

    Returns:
        Sync queue health details
    """
    try:
        pending_count = sync_queue.get_pending_count()
        retry_count = sync_queue.get_retry_count()
        failed_count = sync_queue.get_failed_count()

        return SyncQueueHealth(
            pending_count=pending_count,
            retry_count=retry_count,
            failed_count=failed_count,
            last_sync_timestamp=None  # Would be tracked in a real implementation
        )
    except Exception as e:
        logger.error(f"Sync queue health check failed: {e}")
        return SyncQueueHealth(
            pending_count=0,
            retry_count=0,
            failed_count=0,
            last_sync_timestamp=None
        )
