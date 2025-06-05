"""Party (Candidates/Parties) entity."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, SoftDeleteMixin, TimeStampedMixin

if TYPE_CHECKING:
    from .tally_line import TallyLine


class Party(BaseUUIDModel, TimeStampedMixin, SoftDeleteMixin, table=True):
    """Political party/candidate entity."""

    __tablename__ = "parties"

    name: str = Field(unique=True, index=True)
    short_code: str | None = None  # e.g., "LF", "FPM"
    display_order: int = Field(default=0, index=True)
    is_active: bool = Field(default=True, index=True)

    # Relationships
    tally_lines: TallyLine = Relationship(back_populates="party")
