"""Sync engine data models and schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChangeOperation(str, Enum):
    """Types of change operations for sync."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class EntityChange(BaseModel):
    """Represents a change to an entity for sync."""

    id: UUID = Field(description="Unique change ID")
    entity_type: str = Field(description="Type of entity (e.g., 'Voter', 'TallySession')")
    entity_id: UUID = Field(description="ID of the changed entity")
    operation: ChangeOperation = Field(description="Type of change operation")
    data: dict[str, Any] = Field(description="Entity data")
    timestamp: datetime = Field(description="When the change occurred")
    retry_count: int = Field(default=0, description="Number of sync retry attempts")


class SyncPushRequest(BaseModel):
    """Request model for pushing changes to server."""

    changes: list[EntityChange] = Field(description="List of changes to push")
    client_timestamp: datetime = Field(description="Client timestamp")


class SyncPushResponse(BaseModel):
    """Response model for push operation."""

    processed_count: int = Field(description="Number of changes successfully processed")
    failed_changes: list[EntityChange] = Field(default=[], description="Changes that failed to process")
    conflicts: list[EntityChange] = Field(default=[], description="Changes with conflicts")
    server_timestamp: datetime = Field(description="Server timestamp")


class SyncPullResponse(BaseModel):
    """Response model for pull operation."""

    changes: list[EntityChange] = Field(description="Changes from server")
    server_timestamp: datetime = Field(description="Server timestamp")
    has_more: bool = Field(default=False, description="Whether more changes are available")
    total_available: int | None = Field(default=None, description="Total changes available")


class PullResult(BaseModel):
    """Result of a pull operation."""

    changes: list[EntityChange] = Field(description="All retrieved changes")
    total_count: int = Field(description="Total number of changes retrieved")


class PushResult(BaseModel):
    """Result of a push operation."""

    processed_count: int = Field(description="Number of changes successfully processed")
    failed_count: int = Field(description="Number of failed changes")
    conflict_count: int = Field(description="Number of conflicts")
