"""Unit tests for results DAO functions."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from jcselect.dao_results import (
    calculate_winners,
    get_pen_completion_status,
    get_pen_voter_turnout,
    get_totals_by_candidate,
    get_totals_by_party,
)
from jcselect.models import Party, Pen, TallyLine, TallySession, User, Voter
from jcselect.models.enums import BallotType
from sqlalchemy import text
from sqlmodel import Session


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


class TestTotalsByParty:
    """Test get_totals_by_party function."""

    def test_totals_by_party_all_pens(self, db_session: Session, setup_view):
        """Test party totals across all pens."""
        # Create test data
        pen1 = Pen(id=uuid.uuid4(), town_name="Town 1", label="Pen 1")
        pen2 = Pen(id=uuid.uuid4(), town_name="Town 2", label="Pen 2")
        party1 = Party(
            id=uuid.uuid4(),
            name="Party A",
            short_code="PA",
            display_order=1,
            is_active=True
        )
        party2 = Party(
            id=uuid.uuid4(),
            name="Party B",
            short_code="PB",
            display_order=2,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen1, pen2, party1, party2, user])
        db_session.commit()

        # Create tally sessions
        session1 = TallySession(
            id=uuid.uuid4(),
            pen_id=pen1.id,
            operator_id=user.id,
            session_name="Session 1",
            started_at=datetime.utcnow(),
            total_votes_counted=100
        )
        session2 = TallySession(
            id=uuid.uuid4(),
            pen_id=pen2.id,
            operator_id=user.id,
            session_name="Session 2",
            started_at=datetime.utcnow(),
            total_votes_counted=150
        )

        db_session.add_all([session1, session2])
        db_session.commit()

        # Create tally lines
        candidate1_id = uuid.uuid4()
        candidate2_id = uuid.uuid4()
        candidate3_id = uuid.uuid4()

        # Party A candidates across both pens
        tally1 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session1.id,
            party_id=party1.id,
            candidate_id=candidate1_id,
            vote_count=50,
            ballot_type=BallotType.NORMAL
        )
        tally2 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session2.id,
            party_id=party1.id,
            candidate_id=candidate2_id,
            vote_count=75,
            ballot_type=BallotType.NORMAL
        )

        # Party B candidate
        tally3 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session1.id,
            party_id=party2.id,
            candidate_id=candidate3_id,
            vote_count=25,
            ballot_type=BallotType.NORMAL
        )

        db_session.add_all([tally1, tally2, tally3])
        db_session.commit()

        # Test function
        party_totals = get_totals_by_party(session=db_session)

        # Verify results
        assert len(party_totals) == 2

        # Party A should have more votes (125 total)
        party_a_result = next(p for p in party_totals if p["party_name"] == "Party A")
        assert party_a_result["total_votes"] == 125
        assert party_a_result["candidate_count"] == 2

        # Party B should have fewer votes (25 total)
        party_b_result = next(p for p in party_totals if p["party_name"] == "Party B")
        assert party_b_result["total_votes"] == 25
        assert party_b_result["candidate_count"] == 1

    def test_totals_by_party_pen_filter(self, db_session: Session, setup_view):
        """Test party totals filtered by specific pen."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Test Pen")
        party = Party(
            id=uuid.uuid4(),
            name="Test Party",
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen, party, user])
        db_session.commit()

        # Create tally session
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

        # Create tally line
        tally = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=uuid.uuid4(),
            vote_count=30,
            ballot_type=BallotType.NORMAL
        )
        db_session.add(tally)
        db_session.commit()

        # Test function with pen filter
        party_totals = get_totals_by_party(pen_id=str(pen.id), session=db_session)

        # Verify results
        assert len(party_totals) == 1
        assert party_totals[0]["party_name"] == "Test Party"
        assert party_totals[0]["total_votes"] == 30

    def test_totals_by_party_ignores_soft_deleted(self, db_session: Session, setup_view):
        """Test that soft-deleted records are excluded."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Test Pen")
        party = Party(
            id=uuid.uuid4(),
            name="Test Party",
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen, party, user])
        db_session.commit()

        # Create tally session
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

        # Create active and soft-deleted tally lines
        active_tally = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=uuid.uuid4(),
            vote_count=30,
            ballot_type=BallotType.NORMAL
        )

        deleted_tally = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=uuid.uuid4(),
            vote_count=20,
            ballot_type=BallotType.NORMAL,
            deleted_at=datetime.utcnow()
        )

        db_session.add_all([active_tally, deleted_tally])
        db_session.commit()

        # Test function
        party_totals = get_totals_by_party(session=db_session)

        # Should only count active records
        assert len(party_totals) == 1
        assert party_totals[0]["total_votes"] == 30  # Not 50


class TestTotalsByCandidate:
    """Test get_totals_by_candidate function."""

    def test_totals_by_candidate_pen_filter(self, db_session: Session, setup_view):
        """Test candidate totals with pen filtering."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Test Pen")
        party = Party(
            id=uuid.uuid4(),
            name="Test Party",
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen, party, user])
        db_session.commit()

        # Create tally session
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

        # Create tally lines for different candidates
        candidate1_id = uuid.uuid4()
        candidate2_id = uuid.uuid4()

        tally1 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=candidate1_id,
            vote_count=30,
            ballot_type=BallotType.NORMAL
        )

        tally2 = TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session.id,
            party_id=party.id,
            candidate_id=candidate2_id,
            vote_count=15,
            ballot_type=BallotType.NORMAL
        )

        db_session.add_all([tally1, tally2])
        db_session.commit()

        # Test function
        candidate_totals = get_totals_by_candidate(pen_id=str(pen.id), session=db_session)

        # Verify results (sorted by votes DESC)
        assert len(candidate_totals) == 2
        assert candidate_totals[0]["total_votes"] == 30
        assert candidate_totals[1]["total_votes"] == 15
        assert all(c["party_name"] == "Test Party" for c in candidate_totals)


class TestCalculateWinners:
    """Test calculate_winners function."""

    def test_calculate_winners_default_seats(self, db_session: Session, setup_view):
        """Test winner calculation with default 3 seats."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Test Pen")
        party = Party(
            id=uuid.uuid4(),
            name="Test Party",
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen, party, user])
        db_session.commit()

        # Create tally session
        session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
            total_votes_counted=200
        )
        db_session.add(session)
        db_session.commit()

        # Create 5 candidates with different vote counts
        candidates = []
        vote_counts = [100, 80, 60, 40, 20]  # Top 3 should be elected

        for votes in vote_counts:
            candidate_id = uuid.uuid4()
            tally = TallyLine(
                id=uuid.uuid4(),
                tally_session_id=session.id,
                party_id=party.id,
                candidate_id=candidate_id,
                vote_count=votes,
                ballot_type=BallotType.NORMAL
            )
            candidates.append(tally)

        db_session.add_all(candidates)
        db_session.commit()

        # Test function
        winners = calculate_winners(session=db_session)

        # Verify results
        assert len(winners) == 5

        # Check top 3 are elected
        for i in range(3):
            assert winners[i]["is_elected"] is True
            assert winners[i]["rank"] == i + 1

        # Check bottom 2 are not elected
        for i in range(3, 5):
            assert winners[i]["is_elected"] is False
            assert winners[i]["rank"] == i + 1

        # Check vote ordering (descending)
        vote_sequence = [w["total_votes"] for w in winners]
        assert vote_sequence == sorted(vote_sequence, reverse=True)


class TestPenCompletionStatus:
    """Test get_pen_completion_status function."""

    def test_pen_completion_status_true_false(self, db_session: Session):
        """Test pen completion status for complete and incomplete pens."""
        # Create test data
        pen_complete = Pen(id=uuid.uuid4(), town_name="Complete Town", label="Complete Pen")
        pen_incomplete = Pen(id=uuid.uuid4(), town_name="Incomplete Town", label="Incomplete Pen")
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen_complete, pen_incomplete, user])
        db_session.commit()

        # Add voters to pens
        # Complete pen has 2 voters
        for i in range(2):
            voter = Voter(
                id=uuid.uuid4(),
                pen_id=pen_complete.id,
                voter_number=f"V{i+1}",
                full_name=f"Test Voter{i+1}",
                has_voted=False
            )
            db_session.add(voter)

        # Incomplete pen has 3 voters
        for i in range(3):
            voter = Voter(
                id=uuid.uuid4(),
                pen_id=pen_incomplete.id,
                voter_number=f"V{i+1}",
                full_name=f"Test Voter{i+1}",
                has_voted=False
            )
            db_session.add(voter)

        db_session.commit()

        # Create complete session (ballot_number >= voter_count)
        complete_session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen_complete.id,
            operator_id=user.id,
            session_name="Complete Session",
            started_at=datetime.utcnow(),
            ballot_number=2  # Equals voter count
        )

        # Create incomplete session (ballot_number < voter_count)
        incomplete_session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen_incomplete.id,
            operator_id=user.id,
            session_name="Incomplete Session",
            started_at=datetime.utcnow(),
            ballot_number=1  # Less than voter count (3)
        )

        db_session.add_all([complete_session, incomplete_session])
        db_session.commit()

        # Test function
        assert get_pen_completion_status(str(pen_complete.id), session=db_session) is True
        assert get_pen_completion_status(str(pen_incomplete.id), session=db_session) is False

        # Test with non-existent pen
        assert get_pen_completion_status(str(uuid.uuid4()), session=db_session) is False


class TestPenVoterTurnout:
    """Test get_pen_voter_turnout function."""

    def test_pen_voter_turnout_calculation(self, db_session: Session):
        """Test voter turnout calculation with different ballot types."""
        # Create test data
        pen = Pen(id=uuid.uuid4(), town_name="Test Town", label="Test Pen")
        party = Party(
            id=uuid.uuid4(),
            name="Test Party",
            short_code="TP",
            display_order=1,
            is_active=True
        )
        user = User(
            id=uuid.uuid4(),
            username="operator",
            password_hash="hashed",
            full_name="Test Operator",
            role="operator",
            is_active=True
        )

        db_session.add_all([pen, party, user])
        db_session.commit()

        # Create tally session
        session = TallySession(
            id=uuid.uuid4(),
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Test Session",
            started_at=datetime.utcnow()
        )
        db_session.add(session)
        db_session.commit()

        # Create tally lines with different ballot types
        tallies = [
            TallyLine(
                id=uuid.uuid4(),
                tally_session_id=session.id,
                party_id=party.id,
                candidate_id=uuid.uuid4(),
                vote_count=50,
                ballot_type=BallotType.NORMAL
            ),
            TallyLine(
                id=uuid.uuid4(),
                tally_session_id=session.id,
                party_id=party.id,
                candidate_id=None,
                vote_count=5,
                ballot_type=BallotType.WHITE
            ),
            TallyLine(
                id=uuid.uuid4(),
                tally_session_id=session.id,
                party_id=party.id,
                candidate_id=None,
                vote_count=3,
                ballot_type=BallotType.CANCEL
            ),
            TallyLine(
                id=uuid.uuid4(),
                tally_session_id=session.id,
                party_id=party.id,
                candidate_id=None,
                vote_count=2,
                ballot_type=BallotType.ILLEGAL
            ),
            TallyLine(
                id=uuid.uuid4(),
                tally_session_id=session.id,
                party_id=party.id,
                candidate_id=None,
                vote_count=1,
                ballot_type=BallotType.BLANK
            )
        ]

        db_session.add_all(tallies)
        db_session.commit()

        # Test function
        turnout = get_pen_voter_turnout(str(pen.id), session=db_session)

        # Verify results
        expected = {
            "total_ballots": 61,  # 50+5+3+2+1
            "white": 5,
            "cancel": 3,
            "illegal": 2,
            "blank": 1
        }

        assert turnout == expected
