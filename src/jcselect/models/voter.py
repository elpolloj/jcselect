"""Voter entity (≈ legacy mlist)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, SoftDeleteMixin, TimeStampedMixin

if TYPE_CHECKING:
    from .pen import Pen
    from .user import User


class Voter(BaseUUIDModel, TimeStampedMixin, SoftDeleteMixin, table=True):
    """Voter entity."""

    __tablename__ = "voters"

    # Foreign keys
    pen_id: UUID = Field(foreign_key="pens.id", index=True)
    voted_by_operator_id: UUID | None = Field(
        foreign_key="users.id", default=None, index=True
    )

    # Voter information
    voter_number: str = Field(index=True)  # unique within pen
    full_name: str
    father_name: str | None = None
    mother_name: str | None = None
    birth_year: int | None = None
    gender: str | None = None  # M/F

    # Voting status
    has_voted: bool = Field(default=False, index=True)
    voted_at: datetime | None = None

    # Relationships
    pen: Pen = Relationship(back_populates="voters")
    voted_by_operator: User = Relationship(
        back_populates="voted_voters",
        sa_relationship_kwargs={"foreign_keys": "[Voter.voted_by_operator_id]"}
    )
