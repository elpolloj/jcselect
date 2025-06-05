"""Unit tests for results schema and models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session, select

from jcselect.models import (
    CandidateTotal,
    Party,
    Pen,
    ResultAggregate,
    TallyLine,
    TallySession,
    User,
    WinnerEntry,
)
from jcselect.models.enums import BallotType
from jcselect.models.results import PartyTotal


@pytest.fixture
def setup_view(db_session: Session):
    """Create the v_results_aggregate view in the test database."""
    db_session.execute(text("""
        CREATE VIEW IF NOT EXISTS v_results_aggregate AS
        SELECT
            ts.pen_id,
            tl.party_id,
            tl.candidate_id,
            tl.ballot_type,
            SUM(CASE WHEN tl.deleted_at IS NULL THEN tl.vote_count ELSE 0 END) AS votes,
            COUNT(CASE WHEN tl.deleted_at IS NULL THEN tl.id ELSE NULL END) AS ballot_count,
            MAX(tl.updated_at) AS last_updated
        FROM tally_lines tl
        JOIN tally_sessions ts ON tl.tally_session_id = ts.id
        WHERE ts.deleted_at IS NULL
        GROUP BY ts.pen_id, tl.party_id, tl.candidate_id, tl.ballot_type
    """))
    db_session.commit()


class TestResultsView:
    """Test the v_results_aggregate database view."""

    def test_view_exists(self, db_session: Session, setup_view):
        """Test that the v_results_aggregate view exists and has correct columns."""
        # Try to query the view
        result = db_session.execute(text("SELECT * FROM v_results_aggregate LIMIT 0"))
        columns = list(result.keys())
        
        # Verify expected columns exist
        expected_columns = {
            'pen_id', 'party_id', 'candidate_id', 'ballot_type', 
            'votes', 'ballot_count', 'last_updated'
        }
        actual_columns = set(columns)
        
        assert expected_columns.issubset(actual_columns), (
            f"Missing columns: {expected_columns - actual_columns}"
        )

    def test_view_aggregation_logic(self, db_session: Session, setup_view):
        """Test that the view correctly aggregates tally line data."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Pen 1")
        party1 = Party(
            id=uuid.uuid4(), 
            name="Test Party 1", 
            short_code="TP1",
            display_order=1,
            is_active=True
        )
        party2 = Party(
            id=uuid.uuid4(), 
            name="Test Party 2", 
            short_code="TP2",
            display_order=2,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="test_operator",
            password_hash="hashed",
            full_name="Test Operator", 
            role="operator",
            is_active=True
        )
        
        db_session.add_all([pen, party1, party2, user])
        db_session.commit()
        
        # Create tally session
        session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
            total_votes_counted=100
        )
        db_session.add(session)
        db_session.commit()
        
        # Create tally lines with different scenarios
        candidate1_id = uuid.uuid4()
        candidate2_id = uuid.uuid4()
        
        # Normal ballot for candidate 1 in party 1
        tally1 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party1.id,
            candidate_id=candidate1_id,
            vote_count=25,
            ballot_type=BallotType.NORMAL
        )
        
        # Normal ballot for candidate 2 in party 2
        tally2 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party2.id,
            candidate_id=candidate2_id,
            vote_count=15,
            ballot_type=BallotType.NORMAL
        )
        
        # Soft-deleted ballot (should be excluded)
        tally3 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party1.id,
            candidate_id=uuid.uuid4(),  # Different candidate to avoid constraint violation
            vote_count=10,
            ballot_type=BallotType.NORMAL,
            deleted_at=datetime.utcnow()
        )
        
        db_session.add_all([tally1, tally2, tally3])
        db_session.commit()
        
        # Query the view
        view_results = db_session.execute(
            text("""
                SELECT pen_id, party_id, candidate_id, ballot_type, votes, ballot_count
                FROM v_results_aggregate
                WHERE pen_id = :pen_id
                ORDER BY votes DESC
            """),
            {"pen_id": pen.id.hex}  # Use hex format without hyphens
        ).fetchall()
        
        # Should have 2 results (non-deleted candidates only)
        non_deleted_results = [r for r in view_results if r[4] > 0]  # votes > 0
        assert len(non_deleted_results) == 2
        
        # Check candidate totals
        votes_list = [r[4] for r in non_deleted_results]
        assert 25 in votes_list  # candidate 1 votes
        assert 15 in votes_list  # candidate 2 votes
        
        # Check ballot counts
        ballot_counts = [r[5] for r in non_deleted_results]
        assert all(count == 1 for count in ballot_counts)  # Each candidate should have 1 ballot

    def test_view_handles_soft_deleted_sessions(self, db_session: Session, setup_view):
        """Test that the view excludes results from soft-deleted sessions."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Pen 1")
        party = Party(
            id=uuid.uuid4(), 
            name="Test Party", 
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="test_operator",
            password_hash="hashed",
            full_name="Test Operator", 
            role="operator",
            is_active=True
        )
        
        db_session.add_all([pen, party, user])
        db_session.commit()
        
        # Create soft-deleted session
        session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Deleted Session",
            started_at=datetime.utcnow(),
            total_votes_counted=50,
            deleted_at=datetime.utcnow()  # Soft deleted
        )
        db_session.add(session)
        db_session.commit()
        
        # Create tally line in deleted session
        tally = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=uuid.uuid4(),
            vote_count=25,
            ballot_type=BallotType.NORMAL
        )
        db_session.add(tally)
        db_session.commit()
        
        # Query the view - should return no results
        view_results = db_session.execute(
            text("SELECT COUNT(*) FROM v_results_aggregate WHERE pen_id = :pen_id"),
            {"pen_id": pen.id.hex}  # Use hex format without hyphens
        ).scalar()
        
        assert view_results == 0


class TestResultAggregateModel:
    """Test the ResultAggregate SQLModel class."""

    def test_result_aggregate_model_fields(self):
        """Test that ResultAggregate model has correct field types."""
        # Create a mock result aggregate
        aggregate = ResultAggregate(
            pen_id=uuid.uuid4(),
            party_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            ballot_type="normal",
            votes=100,
            ballot_count=5,
            last_updated=datetime.utcnow()
        )
        
        # Test field types
        assert isinstance(aggregate.pen_id, uuid.UUID)
        assert isinstance(aggregate.party_id, uuid.UUID)
        assert isinstance(aggregate.candidate_id, uuid.UUID)
        assert isinstance(aggregate.ballot_type, str)
        assert isinstance(aggregate.votes, int)
        assert isinstance(aggregate.ballot_count, int)
        assert isinstance(aggregate.last_updated, datetime)

    def test_result_aggregate_nullable_fields(self):
        """Test that nullable fields work correctly."""
        # Create aggregate with null candidate and party (special ballot)
        aggregate = ResultAggregate(
            pen_id=uuid.uuid4(),
            party_id=None,
            candidate_id=None,
            ballot_type="invalid",
            votes=5,
            ballot_count=1,
            last_updated=datetime.utcnow()
        )
        
        assert aggregate.party_id is None
        assert aggregate.candidate_id is None


class TestResultsModels:
    """Test the Pydantic results models."""

    def test_party_total_model(self):
        """Test PartyTotal model validation and defaults."""
        party_total = PartyTotal(
            party_id="party-123",
            party_name="Test Party",
            total_votes=150,
            candidate_count=3
        )
        
        assert party_total.party_id == "party-123"
        assert party_total.party_name == "Test Party"
        assert party_total.total_votes == 150
        assert party_total.candidate_count == 3
        assert party_total.pen_breakdown == {}  # Default empty dict

    def test_party_total_with_breakdown(self):
        """Test PartyTotal with pen breakdown data."""
        party_total = PartyTotal(
            party_id="party-123",
            party_name="Test Party",
            total_votes=150,
            candidate_count=3,
            pen_breakdown={"pen-1": 75, "pen-2": 75}
        )
        
        assert party_total.pen_breakdown == {"pen-1": 75, "pen-2": 75}
        assert sum(party_total.pen_breakdown.values()) == party_total.total_votes

    def test_candidate_total_model(self):
        """Test CandidateTotal model validation."""
        candidate_total = CandidateTotal(
            candidate_id="candidate-456",
            candidate_name="John Doe",
            party_id="party-123",
            party_name="Test Party",
            total_votes=75,
            pen_breakdown={"pen-1": 40, "pen-2": 35}
        )
        
        assert candidate_total.candidate_id == "candidate-456"
        assert candidate_total.candidate_name == "John Doe"
        assert candidate_total.party_id == "party-123"
        assert candidate_total.party_name == "Test Party"
        assert candidate_total.total_votes == 75
        assert candidate_total.pen_breakdown == {"pen-1": 40, "pen-2": 35}

    def test_winner_entry_model(self):
        """Test WinnerEntry model validation."""
        winner = WinnerEntry(
            candidate_id="candidate-456",
            candidate_name="John Doe",
            party_name="Test Party",
            total_votes=150,
            rank=1,
            is_elected=True
        )
        
        assert winner.candidate_id == "candidate-456"
        assert winner.candidate_name == "John Doe"
        assert winner.party_name == "Test Party"
        assert winner.total_votes == 150
        assert winner.rank == 1
        assert winner.is_elected is True

    def test_winner_entry_not_elected(self):
        """Test WinnerEntry for non-elected candidate."""
        runner_up = WinnerEntry(
            candidate_id="candidate-789",
            candidate_name="Jane Smith",
            party_name="Other Party",
            total_votes=75,
            rank=4,
            is_elected=False
        )
        
        assert runner_up.rank == 4
        assert runner_up.is_elected is False


class TestSchemaIntegration:
    """Test integration between schema and models."""

    def test_tally_line_candidate_id_field(self, db_session: Session):
        """Test that TallyLine model includes the new candidate_id field."""
        # Create required dependencies
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Pen 1")
        party = Party(
            id=uuid.uuid4(), 
            name="Test Party", 
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="test_operator",
            password_hash="hashed",
            full_name="Test Operator", 
            role="operator",
            is_active=True
        )
        
        db_session.add_all([pen, party, user])
        db_session.commit()
        
        session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
            total_votes_counted=50
        )
        db_session.add(session)
        db_session.commit()
        
        # Create tally line with candidate_id
        candidate_id = uuid.uuid4()
        tally = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=candidate_id,
            vote_count=25,
            ballot_type=BallotType.NORMAL
        )
        
        db_session.add(tally)
        db_session.commit()
        
        # Query back and verify candidate_id is stored
        retrieved = db_session.get(TallyLine, tally.id)
        assert retrieved is not None
        assert retrieved.candidate_id == candidate_id

    def test_tally_line_nullable_candidate_id(self, db_session: Session):
        """Test that candidate_id can be null for party-only votes."""
        # Create required dependencies
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Pen 1")
        party = Party(
            id=uuid.uuid4(), 
            name="Test Party", 
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="test_operator",
            password_hash="hashed",
            full_name="Test Operator", 
            role="operator",
            is_active=True
        )
        
        db_session.add_all([pen, party, user])
        db_session.commit()
        
        session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
            total_votes_counted=50
        )
        db_session.add(session)
        db_session.commit()
        
        # Create tally line without candidate_id (party-only vote)
        tally = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=None,  # Explicitly null
            vote_count=25,
            ballot_type=BallotType.NORMAL
        )
        
        db_session.add(tally)
        db_session.commit()
        
        # Query back and verify candidate_id is null
        retrieved = db_session.get(TallyLine, tally.id)
        assert retrieved is not None
        assert retrieved.candidate_id is None 