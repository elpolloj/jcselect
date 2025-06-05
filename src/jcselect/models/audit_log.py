"""AuditLog entity."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, SoftDeleteMixin

if TYPE_CHECKING:
    from .user import User


class AuditLog(BaseUUIDModel, SoftDeleteMixin, table=True):
    """Audit log for tracking user actions."""

    __tablename__ = "audit_logs"

    # Foreign key
    operator_id: UUID | None = Field(
        default=None, foreign_key="users.id", nullable=True
    )

    # Action details
    action: str = Field(index=True)  # e.g., "VOTER_MARKED", "TALLY_CREATED"
    entity_type: str = Field(index=True)  # e.g., "Voter", "TallySession"
    entity_id: UUID = Field(index=True)

    # Change tracking - explicit types + JSON column mapping
    old_values: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    new_values: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    ip_address: str | None = None
    user_agent: str | None = None

    # Relationships - specify foreign_keys to resolve ambiguity
    operator: User = Relationship(
        back_populates="audit_logs",
        sa_relationship_kwargs={"foreign_keys": "[AuditLog.operator_id]"}
    )
