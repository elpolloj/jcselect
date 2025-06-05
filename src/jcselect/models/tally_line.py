"""TallyLine (Dynamic Votes per Party) entity."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship

from .base import BaseUUIDModel, SoftDeleteMixin, TimeStampedMixin
from .enums import BallotType

if TYPE_CHECKING:
    from .party import Party
    from .tally_session import TallySession


class TallyLine(BaseUUIDModel, TimeStampedMixin, SoftDeleteMixin, table=True):
    """Vote count per party in a tally session."""

    __tablename__ = "tally_lines"
    __table_args__ = (
        UniqueConstraint("tally_session_id", "party_id", "candidate_id", name="uq_tally_session_party_candidate"),
    )

    # Foreign keys
    tally_session_id: UUID = Field(foreign_key="tally_sessions.id", index=True)
    party_id: UUID = Field(foreign_key="parties.id", index=True)
    candidate_id: UUID | None = Field(default=None, index=True)  # Candidate within party (nullable for party-only votes)

    # Vote count
    vote_count: int = Field(default=0)

    # Tally counting enhancements
    ballot_type: BallotType = Field(default=BallotType.NORMAL, index=True)  # Type of ballot
    ballot_number: int | None = Field(default=None, index=True)  # Ballot sequence number

    # Relationships
    tally_session: TallySession = Relationship(back_populates="tally_lines")
    party: Party = Relationship(back_populates="tally_lines")
