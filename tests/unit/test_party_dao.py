"""Unit tests for party-related DAO helper functions."""
import pytest
from datetime import datetime
from uuid import uuid4

from jcselect.dao import (
    get_parties_for_pen,
    get_candidates_by_party,
    get_or_create_tally_session,
    get_tally_session_counts
)
from jcselect.models import (
    BallotType,
    Party,
    Pen,
    TallyLine,
    TallySession,
    User
)


@pytest.fixture
def sample_data(db_session):
    """Create sample test data for party DAO tests."""
    # Create a user (operator)
    user = User(
        username=f"testoperator_{uuid4().hex[:8]}",
        password_hash="dummy_hash",
        full_name="Test Operator",
        role="operator"
    )
    db_session.add(user)

    # Create a pen
    pen = Pen(
        town_name="Test Town",
        label="Test Pen 123"
    )
    db_session.add(pen)

    # Create multiple parties (Lebanese elections typically have 3+ for testing)
    parties = []
    for i in range(5):  # Create 5 parties to have enough for tests
        party = Party(
            name=f"Test Party {i+1}",
            abbreviation=f"TP{i+1}"
        )
        db_session.add(party)
        parties.append(party)

    db_session.commit()
    for entity in [user, pen] + parties:
        db_session.refresh(entity)

    return {
        "user": user,
        "pen": pen,
        "parties": parties
    }


class TestGetPartiesForPen:
    """Test get_parties_for_pen DAO helper."""

    def test_get_parties_for_pen_success(self, db_session, sample_data):
        """Test successful retrieval of parties for a pen."""
        pen = sample_data["pen"]
        expected_parties = sample_data["parties"]

        parties = get_parties_for_pen(pen.id, db_session)

        assert len(parties) == 5  # Updated to match new fixture
        party_names = [p.name for p in parties]
        expected_names = [p.name for p in expected_parties]
        
        for name in expected_names:
            assert name in party_names

    def test_get_parties_for_pen_invalid_pen(self, db_session):
        """Test get_parties_for_pen with invalid pen ID."""
        invalid_pen_id = uuid4()

        with pytest.raises(ValueError, match=f"Pen with ID {invalid_pen_id} not found"):
            get_parties_for_pen(invalid_pen_id, db_session)

    def test_get_parties_for_pen_empty_database(self, db_session, sample_data):
        """Test get_parties_for_pen when no parties exist."""
        pen = sample_data["pen"]
        
        # Delete all parties
        for party in sample_data["parties"]:
            db_session.delete(party)
        db_session.commit()

        parties = get_parties_for_pen(pen.id, db_session)
        assert len(parties) == 0


class TestGetCandidatesByParty:
    """Test get_candidates_by_party DAO helper."""

    def test_get_candidates_by_party_success(self, db_session, sample_data):
        """Test successful retrieval of candidates for a party."""
        party = sample_data["parties"][0]

        candidates = get_candidates_by_party(party.id, db_session)

        assert len(candidates) == 3  # Mock data returns 3 candidates per party
        
        # Verify structure of candidate data
        for candidate in candidates:
            assert "id" in candidate
            assert "name" in candidate
            assert "order" in candidate
            assert candidate["name"].startswith(party.name)
            assert isinstance(candidate["order"], int)

    def test_get_candidates_by_party_invalid_party(self, db_session):
        """Test get_candidates_by_party with invalid party ID."""
        invalid_party_id = uuid4()

        with pytest.raises(ValueError, match=f"Party with ID {invalid_party_id} not found"):
            get_candidates_by_party(invalid_party_id, db_session)

    def test_get_candidates_by_party_structure(self, db_session, sample_data):
        """Test the structure of returned candidate data."""
        party = sample_data["parties"][0]

        candidates = get_candidates_by_party(party.id, db_session)

        # Verify each candidate has required fields
        for i, candidate in enumerate(candidates):
            assert candidate["id"] == f"{party.id}_candidate_{i+1}"
            assert candidate["name"] == f"{party.name} - Candidate {i+1}"
            assert candidate["order"] == i+1


class TestGetOrCreateTallySession:
    """Test get_or_create_tally_session DAO helper."""

    def test_create_new_tally_session(self, db_session, sample_data):
        """Test creating a new tally session."""
        pen = sample_data["pen"]
        user = sample_data["user"]

        tally_session = get_or_create_tally_session(pen.id, user.id, db_session)

        assert tally_session is not None
        assert tally_session.pen_id == pen.id
        assert tally_session.operator_id == user.id
        assert tally_session.session_name == f"Tally Count - {pen.label}"
        assert tally_session.ballot_number == 0
        assert tally_session.started_at is not None
        assert tally_session.completed_at is None

    def test_get_existing_tally_session(self, db_session, sample_data):
        """Test getting an existing active tally session."""
        pen = sample_data["pen"]
        user = sample_data["user"]

        # Create first session
        session1 = get_or_create_tally_session(pen.id, user.id, db_session)
        db_session.commit()

        # Try to get session again
        session2 = get_or_create_tally_session(pen.id, user.id, db_session)

        assert session1.id == session2.id
        assert session1.session_name == session2.session_name

    def test_get_or_create_tally_session_invalid_pen(self, db_session, sample_data):
        """Test get_or_create_tally_session with invalid pen ID."""
        user = sample_data["user"]
        invalid_pen_id = uuid4()

        with pytest.raises(ValueError, match=f"Pen with ID {invalid_pen_id} not found"):
            get_or_create_tally_session(invalid_pen_id, user.id, db_session)

    def test_get_or_create_tally_session_invalid_operator(self, db_session, sample_data):
        """Test get_or_create_tally_session with invalid operator ID."""
        pen = sample_data["pen"]
        invalid_operator_id = uuid4()

        with pytest.raises(ValueError, match=f"Operator with ID {invalid_operator_id} not found"):
            get_or_create_tally_session(pen.id, invalid_operator_id, db_session)

    def test_create_multiple_sessions_different_pens(self, db_session, sample_data):
        """Test creating separate sessions for different pens."""
        user = sample_data["user"]
        
        # Create second pen
        pen2 = Pen(town_name="Test Town 2", label="Test Pen 456")
        db_session.add(pen2)
        db_session.commit()
        db_session.refresh(pen2)

        # Create sessions for both pens
        session1 = get_or_create_tally_session(sample_data["pen"].id, user.id, db_session)
        session2 = get_or_create_tally_session(pen2.id, user.id, db_session)

        assert session1.id != session2.id
        assert session1.pen_id != session2.pen_id

    def test_ignore_completed_sessions(self, db_session, sample_data):
        """Test that completed sessions are ignored when looking for active sessions."""
        pen = sample_data["pen"]
        user = sample_data["user"]

        # Create and complete a session
        completed_session = TallySession(
            pen_id=pen.id,
            operator_id=user.id,
            session_name="Completed Session",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),  # Mark as completed
            ballot_number=0
        )
        db_session.add(completed_session)
        db_session.commit()

        # Create new session (should create new, not return completed one)
        new_session = get_or_create_tally_session(pen.id, user.id, db_session)

        assert new_session.id != completed_session.id
        assert new_session.completed_at is None


class TestGetTallySessionCounts:
    """Test get_tally_session_counts DAO helper."""

    def test_get_counts_empty_session(self, db_session, sample_data):
        """Test getting counts for a session with no tally lines."""
        pen = sample_data["pen"]
        user = sample_data["user"]

        tally_session = get_or_create_tally_session(pen.id, user.id, db_session)
        db_session.commit()

        counts = get_tally_session_counts(tally_session.id, db_session)

        expected_counts = {
            "total_votes": 0,
            "total_counted": 0,
            "total_candidates": 0,
            "total_white": 0,
            "total_illegal": 0,
            "total_cancel": 0,
            "total_blank": 0,
        }
        assert counts == expected_counts

    def test_get_counts_with_candidate_votes(self, db_session, sample_data):
        """Test getting counts for a session with candidate votes."""
        pen = sample_data["pen"]
        user = sample_data["user"]
        parties = sample_data["parties"]

        tally_session = get_or_create_tally_session(pen.id, user.id, db_session)
        
        # Add some candidate votes - use first 3 parties to avoid constraint issues
        for i, party in enumerate(parties[:3]):
            tally_line = TallyLine(
                tally_session_id=tally_session.id,
                party_id=party.id,
                vote_count=i + 1,  # 1, 2, 3 votes respectively
                ballot_type=BallotType.NORMAL,
                ballot_number=i + 1
            )
            db_session.add(tally_line)
        
        db_session.commit()

        counts = get_tally_session_counts(tally_session.id, db_session)

        assert counts["total_votes"] == 6  # 1 + 2 + 3
        assert counts["total_counted"] == 6
        assert counts["total_candidates"] == 6
        assert counts["total_white"] == 0
        assert counts["total_illegal"] == 0

    def test_get_counts_with_special_ballots(self, db_session, sample_data):
        """Test getting counts for a session with special ballot types."""
        pen = sample_data["pen"]
        user = sample_data["user"]
        parties = sample_data["parties"]

        tally_session = get_or_create_tally_session(pen.id, user.id, db_session)
        
        # Add special ballot types using different parties to avoid unique constraint
        special_ballots = [
            (BallotType.WHITE, 2, parties[0]),
            (BallotType.ILLEGAL, 1, parties[1]),
            (BallotType.CANCEL, 3, parties[2]),
            (BallotType.BLANK, 1, parties[3])
        ]
        
        for ballot_type, count, party in special_ballots:
            tally_line = TallyLine(
                tally_session_id=tally_session.id,
                party_id=party.id,  # Use different parties to avoid constraint
                vote_count=count,
                ballot_type=ballot_type,
                ballot_number=1
            )
            db_session.add(tally_line)
        
        db_session.commit()

        counts = get_tally_session_counts(tally_session.id, db_session)

        assert counts["total_votes"] == 7  # 2 + 1 + 3 + 1
        assert counts["total_counted"] == 7
        assert counts["total_candidates"] == 0
        assert counts["total_white"] == 2
        assert counts["total_illegal"] == 1
        assert counts["total_cancel"] == 3
        assert counts["total_blank"] == 1

    def test_get_counts_with_mixed_ballots(self, db_session, sample_data):
        """Test getting counts for a session with both candidate and special ballots."""
        pen = sample_data["pen"]
        user = sample_data["user"]
        parties = sample_data["parties"]

        tally_session = get_or_create_tally_session(pen.id, user.id, db_session)
        
        # Add candidate votes using first 3 parties
        for party in parties[:3]:
            tally_line = TallyLine(
                tally_session_id=tally_session.id,
                party_id=party.id,
                vote_count=2,
                ballot_type=BallotType.NORMAL,
                ballot_number=1
            )
            db_session.add(tally_line)
        
        # Add white ballots using the 4th party
        white_line = TallyLine(
            tally_session_id=tally_session.id,
            party_id=parties[3].id,  # Use different party to avoid constraint
            vote_count=1,
            ballot_type=BallotType.WHITE,
            ballot_number=2
        )
        db_session.add(white_line)
        
        db_session.commit()

        counts = get_tally_session_counts(tally_session.id, db_session)

        assert counts["total_votes"] == 7  # 6 candidate + 1 white
        assert counts["total_counted"] == 7
        assert counts["total_candidates"] == 6
        assert counts["total_white"] == 1

    def test_get_counts_excludes_soft_deleted(self, db_session, sample_data):
        """Test that soft-deleted tally lines are excluded from counts."""
        pen = sample_data["pen"]
        user = sample_data["user"]
        parties = sample_data["parties"]

        tally_session = get_or_create_tally_session(pen.id, user.id, db_session)
        
        # Add active tally line
        active_line = TallyLine(
            tally_session_id=tally_session.id,
            party_id=parties[0].id,
            vote_count=3,
            ballot_type=BallotType.NORMAL,
            ballot_number=1
        )
        db_session.add(active_line)
        
        # Add soft-deleted tally line using different party
        deleted_line = TallyLine(
            tally_session_id=tally_session.id,
            party_id=parties[1].id,  # Use different party to avoid constraint
            vote_count=5,
            ballot_type=BallotType.NORMAL,
            ballot_number=2,
            deleted_at=datetime.utcnow(),
            deleted_by=user.id
        )
        db_session.add(deleted_line)
        
        db_session.commit()

        counts = get_tally_session_counts(tally_session.id, db_session)

        # Should only count the active line
        assert counts["total_votes"] == 3
        assert counts["total_candidates"] == 3

    def test_get_counts_invalid_session(self, db_session):
        """Test get_tally_session_counts with invalid session ID."""
        invalid_session_id = uuid4()

        with pytest.raises(ValueError, match=f"TallySession with ID {invalid_session_id} not found"):
            get_tally_session_counts(invalid_session_id, db_session) 