"""Data Transfer Objects for UI layer communication."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class VoterDTO:
    """Data transfer object for voter information in the UI layer."""

    id: str
    voter_number: str
    full_name: str
    father_name: str | None
    mother_name: str | None
    pen_label: str
    has_voted: bool
    voted_at: datetime | None
    voted_by_operator: str | None

    @property
    def display_name(self) -> str:
        """Formatted name for UI display."""
        if self.father_name:
            return f"{self.full_name} ({self.father_name})"
        return self.full_name

    @property
    def search_text(self) -> str:
        """Concatenated searchable text for fuzzy search."""
        parts = [
            self.voter_number,
            self.full_name,
        ]

        if self.father_name:
            parts.append(self.father_name)

        if self.mother_name:
            parts.append(self.mother_name)

        return " ".join(parts).lower()


@dataclass
class SearchResultDTO:
    """Data transfer object for search results with metadata."""

    voters: list[VoterDTO]
    total_count: int
    search_query: str
    execution_time_ms: int
