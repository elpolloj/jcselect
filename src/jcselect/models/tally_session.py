"""TallySession (Counting Event) entity."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, SoftDeleteMixin, TimeStampedMixin

if TYPE_CHECKING:
    from .pen import Pen
    from .tally_line import TallyLine
    from .user import User


class TallySession(BaseUUIDModel, TimeStampedMixin, SoftDeleteMixin, table=True):
    """Counting session entity."""

    __tablename__ = "tally_sessions"

    # Foreign keys
    pen_id: UUID = Field(foreign_key="pens.id", index=True)
    operator_id: UUID = Field(foreign_key="users.id", index=True)

    # Session information
    session_name: str  # e.g., "End of Day Count"
    started_at: datetime
    completed_at: datetime | None = None
    total_votes_counted: int = Field(default=0)
    notes: str | None = None

    # Tally counting enhancements
    ballot_number: int = Field(default=0)  # Current ballot number being processed
    recounted_at: datetime | None = None   # When recount was performed
    recount_operator_id: UUID | None = Field(
        foreign_key="users.id",
        default=None,
        index=True
    )  # Who performed the recount

    # Relationships
    pen: Pen = Relationship(back_populates="tally_sessions")
    operator: User = Relationship(
        back_populates="tally_sessions",
        sa_relationship_kwargs={"foreign_keys": "[TallySession.operator_id]"}
    )
    recount_operator: User = Relationship(
        back_populates="recounted_tally_sessions",
        sa_relationship_kwargs={"foreign_keys": "[TallySession.recount_operator_id]"}
    )
    tally_lines: TallyLine = Relationship(back_populates="tally_session")
