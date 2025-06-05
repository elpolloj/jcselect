"""Health check API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str  # "ok" or "error"
    timestamp: datetime
    database_status: str  # "connected" or "disconnected"
    sync_queue_size: int
    uptime_seconds: float
    version: str = "0.1.0"


class DatabaseHealth(BaseModel):
    """Database health details."""

    status: str
    connection_time_ms: float | None = None
    error_message: str | None = None


class SyncQueueHealth(BaseModel):
    """Sync queue health details."""

    pending_count: int
    retry_count: int
    failed_count: int
    last_sync_timestamp: datetime | None = None
