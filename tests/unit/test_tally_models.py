"""Test tally models functionality and constraints."""
import pytest
from datetime import datetime
from uuid import uuid4
from sqlmodel import select, MetaData, Table

from jcselect.models import (
    BallotType,
    TallyLine,
    TallySession,
    User,
    Party,
    Pen
)
from jcselect.dao import tally_line_to_dict


@pytest.fixture
def sample_entities(db_session):
    """Create sample test entities."""
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

    # Create a party
    party = Party(
        name="Test Party",
        abbreviation="TP"
    )
    db_session.add(party)

    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(pen)
    db_session.refresh(party)

    return {
        "user": user,
        "pen": pen,
        "party": party
    }


def test_ballot_type_enum_values():
    """Test BallotType enum has all required values and correct types."""
    # Test all enum values exist
    assert BallotType.NORMAL == "normal"
    assert BallotType.CANCEL == "cancel"
    assert BallotType.WHITE == "white"
    assert BallotType.ILLEGAL == "illegal"
    assert BallotType.BLANK == "blank"

    # Test enum is string-based for database compatibility
    assert isinstance(BallotType.NORMAL, str)
    assert isinstance(BallotType.CANCEL, str)
    
    # Test enum can be compared to strings
    assert BallotType.NORMAL == "normal"
    assert BallotType.WHITE != "invalid"

    # Test all expected values are present
    expected_values = {"normal", "cancel", "white", "illegal", "blank"}
    actual_values = {item.value for item in BallotType}
    assert actual_values == expected_values


def test_tally_session_defaults(db_session, sample_entities):
    """Test TallySession field defaults work correctly."""
    user = sample_entities["user"]
    pen = sample_entities["pen"]

    # Create TallySession with only required fields
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
    assert tally_session.ballot_number == 0  # Default value
    assert tally_session.recounted_at is None  # Default value
    assert tally_session.recount_operator_id is None  # Default value
    assert tally_session.completed_at is None  # Existing default
    assert tally_session.total_votes_counted == 0  # Existing default

    # Test setting non-default values
    tally_session.ballot_number = 5
    tally_session.recounted_at = datetime.utcnow()
    tally_session.recount_operator_id = user.id
    
    db_session.commit()
    db_session.refresh(tally_session)

    assert tally_session.ballot_number == 5
    assert tally_session.recounted_at is not None
    assert tally_session.recount_operator_id == user.id


def test_tally_line_defaults(db_session, sample_entities):
    """Test TallyLine field defaults work correctly."""
    user = sample_entities["user"]
    pen = sample_entities["pen"]
    party = sample_entities["party"]

    # Create TallySession first
    tally_session = TallySession(
        pen_id=pen.id,
        operator_id=user.id,
        session_name="Test Session",
        started_at=datetime.utcnow()
    )
    db_session.add(tally_session)
    db_session.commit()
    db_session.refresh(tally_session)

    # Create TallyLine with only required fields
    tally_line = TallyLine(
        tally_session_id=tally_session.id,
        party_id=party.id,
        vote_count=10
    )
    db_session.add(tally_line)
    db_session.commit()
    db_session.refresh(tally_line)

    # Verify default values
    assert tally_line.ballot_type == BallotType.NORMAL  # Default value
    assert tally_line.ballot_number is None  # Default value
    assert tally_line.vote_count == 10  # Set value

    # Test setting non-default values
    tally_line.ballot_type = BallotType.WHITE
    tally_line.ballot_number = 3
    
    db_session.commit()
    db_session.refresh(tally_line)

    assert tally_line.ballot_type == BallotType.WHITE
    assert tally_line.ballot_number == 3


def test_recount_relationship(db_session, sample_entities):
    """Test relationships work correctly for recount operations."""
    user = sample_entities["user"]
    pen = sample_entities["pen"]

    # Create TallySession with recount fields
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

    # Test forward relationships
    assert tally_session.operator is not None
    assert tally_session.operator.id == user.id
    assert tally_session.recount_operator is not None
    assert tally_session.recount_operator.id == user.id

    # Refresh user to test back relationships
    db_session.refresh(user)

    # Test that relationships are accessible
    # Note: The actual back relationship testing depends on how SQLModel handles the relationships


def test_schema_reflection(db_session):
    """Test schema reflection to verify database structure."""
    # Get metadata from the current database
    metadata = MetaData()
    metadata.reflect(bind=db_session.get_bind())

    # Test TallySession table exists and has new columns
    tally_sessions_table: Table = metadata.tables.get("tally_sessions")
    assert tally_sessions_table is not None

    column_names = [col.name for col in tally_sessions_table.columns]
    assert "ballot_number" in column_names
    assert "recounted_at" in column_names
    assert "recount_operator_id" in column_names

    # Test TallyLine table exists and has new columns
    tally_lines_table: Table = metadata.tables.get("tally_lines")
    assert tally_lines_table is not None

    tally_line_columns = [col.name for col in tally_lines_table.columns]
    assert "ballot_type" in tally_line_columns
    assert "ballot_number" in tally_line_columns


def test_ballot_type_storage_and_retrieval(db_session, sample_entities):
    """Test that BallotType enum values are stored and retrieved correctly."""
    user = sample_entities["user"]
    pen = sample_entities["pen"]
    party = sample_entities["party"]

    # Create additional parties for this test (unique constraint requires different parties)
    parties = [party]
    for i in range(4):  # Create 4 more parties for different ballot types
        additional_party = Party(
            name=f"Test Party {i+2}",
            abbreviation=f"TP{i+2}"
        )
        db_session.add(additional_party)
        parties.append(additional_party)
    
    db_session.commit()
    for p in parties:
        db_session.refresh(p)

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

    # Test storing different ballot types with different parties (due to unique constraint)
    ballot_types = [
        BallotType.NORMAL,
        BallotType.CANCEL,
        BallotType.WHITE,
        BallotType.ILLEGAL,
        BallotType.BLANK
    ]

    tally_lines = []
    for i, ballot_type in enumerate(ballot_types):
        tally_line = TallyLine(
            tally_session_id=tally_session.id,
            party_id=parties[i].id,  # Use different parties due to unique constraint
            vote_count=i + 1,
            ballot_type=ballot_type,
            ballot_number=i + 1
        )
        db_session.add(tally_line)
        tally_lines.append(tally_line)

    db_session.commit()

    # Retrieve and verify
    for tally_line in tally_lines:
        db_session.refresh(tally_line)

    retrieved_types = [line.ballot_type for line in tally_lines]
    assert retrieved_types == ballot_types

    # Test querying by ballot type
    white_ballots = db_session.exec(
        select(TallyLine).where(TallyLine.ballot_type == BallotType.WHITE)
    ).all()
    assert len(white_ballots) == 1
    assert white_ballots[0].ballot_type == BallotType.WHITE


def test_tally_line_to_dict_helper(db_session, sample_entities):
    """Test the tally_line_to_dict helper function."""
    user = sample_entities["user"]
    pen = sample_entities["pen"]
    party = sample_entities["party"]

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

    # Create TallyLine with specific values
    tally_line = TallyLine(
        tally_session_id=tally_session.id,
        party_id=party.id,
        vote_count=5,
        ballot_type=BallotType.WHITE,
        ballot_number=3
    )
    db_session.add(tally_line)
    db_session.commit()
    db_session.refresh(tally_line)

    # Test the helper function
    result = tally_line_to_dict(tally_line)

    # Verify all expected fields are present
    expected_fields = {
        "id", "tally_session_id", "party_id", "vote_count", 
        "ballot_type", "ballot_number", "created_at", "updated_at", 
        "deleted_at", "deleted_by", "timestamp"
    }
    assert set(result.keys()) == expected_fields

    # Verify specific values
    assert result["id"] == str(tally_line.id)
    assert result["tally_session_id"] == str(tally_session.id)
    assert result["party_id"] == str(party.id)
    assert result["vote_count"] == 5
    assert result["ballot_type"] == "white"  # Enum value as string
    assert result["ballot_number"] == 3
    assert result["deleted_at"] is None
    assert result["deleted_by"] is None

    # Verify datetime serialization
    assert isinstance(result["created_at"], str)  # Should be ISO format
    assert isinstance(result["updated_at"], str)  # Should be ISO format


def test_ballot_type_unique_constraint_behavior(db_session, sample_entities):
    """Test that the unique constraint on (tally_session_id, party_id) works as expected."""
    user = sample_entities["user"]
    pen = sample_entities["pen"]
    party = sample_entities["party"]

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

    # Create first TallyLine
    tally_line1 = TallyLine(
        tally_session_id=tally_session.id,
        party_id=party.id,
        vote_count=5,
        ballot_type=BallotType.NORMAL,
        ballot_number=1
    )
    db_session.add(tally_line1)
    db_session.commit()

    # Attempting to create another TallyLine with same session + party should fail
    tally_line2 = TallyLine(
        tally_session_id=tally_session.id,
        party_id=party.id,  # Same party as line1
        vote_count=3,
        ballot_type=BallotType.WHITE,  # Different type, but same session+party
        ballot_number=2
    )
    db_session.add(tally_line2)
    
    # This should raise an IntegrityError due to unique constraint
    with pytest.raises(Exception):  # SQLAlchemy wraps as IntegrityError
        db_session.commit() 