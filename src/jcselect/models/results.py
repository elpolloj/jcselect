"""Results and aggregation models for live results and winner calculation."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import SQLModel


class ResultAggregate(SQLModel, table=False):
    """Aggregated voting results view.

    Maps to the v_results_aggregate database view for efficient
    querying of vote totals across pens, parties, and candidates.
    """

    pen_id: UUID
    party_id: UUID | None = None  # NULL for special ballots
    candidate_id: UUID | None = None
    ballot_type: str
    votes: int
    ballot_count: int
    last_updated: datetime


class PartyTotal(BaseModel):
    """Party-level vote totals.

    Used for aggregating results by party across all candidates,
    with optional breakdown by pen for detailed analysis.
    """

    party_id: str
    party_name: str
    total_votes: int
    candidate_count: int
    pen_breakdown: dict[str, int] = {}


class CandidateTotal(BaseModel):
    """Candidate-level vote totals.

    Individual candidate results with party context and
    optional pen-level breakdown for detailed analysis.
    """

    candidate_id: str
    candidate_name: str
    party_id: str
    party_name: str
    total_votes: int
    pen_breakdown: dict[str, int] = {}


class WinnerEntry(BaseModel):
    """Winner calculation result.

    Represents a candidate's final position in the election
    with ranking and elected status based on vote count.
    """

    candidate_id: str
    candidate_name: str
    party_name: str
    total_votes: int
    rank: int
    is_elected: bool
