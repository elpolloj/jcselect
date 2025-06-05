"""Sync API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from jcselect.models.sync_schemas import EntityChange


class SyncPushRequest(BaseModel):
    """Request schema for pushing changes to server."""

    changes: list[EntityChange]
    client_timestamp: datetime


class SyncPushResponse(BaseModel):
    """Response schema for push requests."""

    processed_count: int
    failed_changes: list[EntityChange]
    conflicts: list[EntityChange]
    server_timestamp: datetime


class SyncPullResponse(BaseModel):
    """Response schema for pull requests."""

    changes: list[EntityChange]
    server_timestamp: datetime
    has_more: bool
    total_available: int | None = None


class SyncStatsResponse(BaseModel):
    """Sync statistics response."""

    pending_push_count: int
    last_successful_sync: datetime | None
    sync_enabled: bool
