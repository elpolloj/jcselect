"""Base SQLModel classes and mixins."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlmodel import Field, SQLModel


class BaseUUIDModel(SQLModel):
    """Base model with UUID primary key."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class TimeStampedMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": func.now()},
    )


# ---------------------------------------------------------
# Soft-delete tombstone support (Sync Engine – Step 1)
# ---------------------------------------------------------
class SoftDeleteMixin(SQLModel, table=False):
    """Mixin for soft delete tombstone fields."""

    deleted_at: datetime | None = Field(
        default=None,
        index=True,
        sa_column_kwargs={"nullable": True},
    )
    deleted_by: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        sa_column_kwargs={"nullable": True},
    )
