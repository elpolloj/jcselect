"""Test tally counting schema migration and model enhancements."""
import pytest
from datetime import datetime
from uuid import uuid4

from sqlmodel import select

from jcselect.models import (
    BallotType,
    TallyLine,
    TallySession,
    User,
    Party,
    Pen
)


@pytest.fixture
def sample_data(db_session):
    """Create sample test data."""
    # Create a user
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        password_hash="dummy_hash",
        full_name="Test User",
        role="operator"
    )
    db_session.add(user)

    # Create a pen
    pen = Pen(
        town_name="Test Town",
        label="Test Pen 123"
    )
    db_session.add(pen)

    # Create multiple parties for testing
    party1 = Party(
        name="Test Party 1",
        abbreviation="TP1"
    )
    party2 = Party(
        name="Test Party 2",
        abbreviation="TP2"
    )
    party3 = Party(
        name="Test Party 3",
        abbreviation="TP3"
    )
    db_session.add(party1)
    db_session.add(party2)
    db_session.add(party3)

    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(pen)
    db_session.refresh(party1)
    db_session.refresh(party2)
    db_session.refresh(party3)

    return {
        "user": user,
        "pen": pen,
        "party1": party1,
        "party2": party2,
        "party3": party3
    }


def test_ballot_type_enum_values():
    """Test BallotType enum has all required values."""
    assert BallotType.NORMAL == "normal"
    assert BallotType.CANCEL == "cancel"
    assert BallotType.WHITE == "white"
    assert BallotType.ILLEGAL == "illegal"
    assert BallotType.BLANK == "blank"

    # Test enum is string-based
    assert isinstance(BallotType.NORMAL, str)


def test_tally_session_new_fields(db_session, sample_data):
    """Test TallySession new fields work correctly."""
    user = sample_data["user"]
    pen = sample_data["pen"]

    # Create TallySession with new fields
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow(),
        ballot_number=5,  # Test ballot_number field
        recounted_at=datetime.utcnow(),  # Test recounted_at field
        recount_operator_id=user.id  # Test recount_operator_id field
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Verify fields are set correctly
    assert tally_session.ballot_number == 5
    assert tally_session.recounted_at is not None
    assert tally_session.recount_operator_id == user.id

    # Test recount_operator relationship
    assert tally_session.recount_operator is not None
    assert tally_session.recount_operator.id == user.id


def test_tally_session_default_values(db_session, sample_data):
    """Test TallySession default values for new fields."""
    user = sample_data["user"]
    pen = sample_data["pen"]

    # Create TallySession without setting new fields
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow()
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Verify default values
    assert tally_session.ballot_number == 0  # Default
    assert tally_session.recounted_at is None  # Default
    assert tally_session.recount_operator_id is None  # Default


def test_tally_line_new_fields(db_session, sample_data):
    """Test TallyLine new fields work correctly."""
    user = sample_data["user"]
    pen = sample_data["pen"]
    party = sample_data["party1"]

    # Create TallySession
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow()
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Create TallyLine with new fields
    tally_line = TallyLine(
        tally_session_id=tally_session.id,
        party_id=party.id,
        vote_count=10,
        ballot_type=BallotType.WHITE,  # Test ballot_type field
        ballot_number=3  # Test ballot_number field
    )
    db_session.add(tally_line)
    db_session.commit()
    db_session.refresh(tally_line)

    # Verify fields are set correctly
    assert tally_line.ballot_type == BallotType.WHITE
    assert tally_line.ballot_number == 3


def test_tally_line_default_ballot_type(db_session, sample_data):
    """Test TallyLine default ballot_type value."""
    user = sample_data["user"]
    pen = sample_data["pen"]
    party = sample_data["party1"]

    # Create TallySession
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow()
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Create TallyLine without setting ballot_type
    tally_line = TallyLine(
        tally_session_id=tally_session.id,
        party_id=party.id,
        vote_count=5
    )
    db_session.add(tally_line)
    db_session.commit()
    db_session.refresh(tally_line)

    # Verify default value
    assert tally_line.ballot_type == BallotType.NORMAL
    assert tally_line.ballot_number is None  # Default


def test_ballot_type_filtering(db_session, sample_data):
    """Test filtering TallyLines by ballot_type."""
    user = sample_data["user"]
    pen = sample_data["pen"]
    party1 = sample_data["party1"]
    party2 = sample_data["party2"]
    party3 = sample_data["party3"]

    # Create TallySession
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow()
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Create multiple TallyLines with different ballot types and parties
    tally_lines = [
        TallyLine(
            tally_session_id=tally_session.id,
            party_id=party1.id,
            vote_count=5,
            ballot_type=BallotType.NORMAL,
            ballot_number=1
        ),
        TallyLine(
            tally_session_id=tally_session.id,
            party_id=party2.id,
            vote_count=2,
            ballot_type=BallotType.WHITE,
            ballot_number=2
        ),
        TallyLine(
            tally_session_id=tally_session.id,
            party_id=party3.id,
            vote_count=1,
            ballot_type=BallotType.CANCEL,
            ballot_number=3
        )
    ]

    for tl in tally_lines:
        db_session.add(tl)
    db_session.commit()

    # Test filtering by ballot_type
    normal_ballots = db_session.exec(
        select(TallyLine).where(TallyLine.ballot_type == BallotType.NORMAL)
    ).all()
    assert len(normal_ballots) == 1

    white_ballots = db_session.exec(
        select(TallyLine).where(TallyLine.ballot_type == BallotType.WHITE)
    ).all()
    assert len(white_ballots) == 1

    # Test filtering by ballot_number
    ballot_1 = db_session.exec(
        select(TallyLine).where(TallyLine.ballot_number == 1)
    ).first()
    assert ballot_1 is not None
    assert ballot_1.ballot_type == BallotType.NORMAL


def test_recount_relationship(db_session, sample_data):
    """Test relationships work correctly for recount operations."""
    user = sample_data["user"]
    pen = sample_data["pen"]

    # Create TallySession with recount
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow(),
        recounted_at=datetime.utcnow(),
        recount_operator_id=user.id
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Refresh user to load relationships
    db_session.refresh(user)

    # Verify bidirectional relationships
    assert tally_session.recount_operator is not None
    assert tally_session.recount_operator.id == user.id


def test_schema_integrity(db_session, sample_data):
    """Test that all new fields maintain data integrity."""
    user = sample_data["user"]
    pen = sample_data["pen"]
    party1 = sample_data["party1"]
    party2 = sample_data["party2"]
    party3 = sample_data["party3"]

    # Test creating a complete tally scenario
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Complete Test Session",
        started_at=datetime.utcnow(),
        ballot_number=10,
        recounted_at=datetime.utcnow(),
        recount_operator_id=user.id
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Create various ballot types with different parties
    ballot_data = [
        (BallotType.NORMAL, party1),
        (BallotType.WHITE, party2),
        (BallotType.CANCEL, party3)
    ]

    for i, (ballot_type, party) in enumerate(ballot_data, 1):
        tally_line = TallyLine(
            tally_session_id=tally_session.id,
            party_id=party.id,
            vote_count=i,
            ballot_type=ballot_type,
            ballot_number=i
        )
        db_session.add(tally_line)

    db_session.commit()

    # Verify all data persisted correctly
    all_lines = db_session.exec(
        select(TallyLine).where(TallyLine.tally_session_id == tally_session.id)
    ).all()

    assert len(all_lines) == 3
    assert {line.ballot_type for line in all_lines} == {BallotType.NORMAL, BallotType.WHITE, BallotType.CANCEL}
    assert all(line.ballot_number is not None for line in all_lines)
