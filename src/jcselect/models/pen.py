"""Pen (Polling Booth) entity."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, TimeStampedMixin

if TYPE_CHECKING:
    from .tally_session import TallySession
    from .voter import Voter


class Pen(BaseUUIDModel, TimeStampedMixin, table=True):
    """Polling booth entity."""

    __tablename__ = "pens"

    town_name: str = Field(index=True)
    label: str = Field(index=True)  # e.g., "Pen 101"

    # Relationships
    voters: Voter = Relationship(back_populates="pen")
    tally_sessions: TallySession = Relationship(back_populates="pen")
