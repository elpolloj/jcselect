"""Tests for DAO tally line upsert functions."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from jcselect.dao import create_tally_session, update_tally_line
from jcselect.models import AuditLog, Party, Pen, TallyLine, TallySession, User
from sqlmodel import Session, select


class TestCreateTallySession:
    """Test cases for create_tally_session function."""

    def test_create_tally_session_success(self, db_session: Session) -> None:
        """Test successful tally session creation."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        # Create tally session
        session_name = "End of Day Count"
        result = create_tally_session(pen.id, operator.id, session_name, db_session)

        # Verify session was created
        assert result.pen_id == pen.id
        assert result.operator_id == operator.id
        assert result.session_name == session_name
        assert result.started_at is not None
        assert result.completed_at is None
        assert result.total_votes_counted == 0
        assert isinstance(result.started_at, datetime)

        # Verify session in database
        db_session_obj = db_session.get(TallySession, result.id)
        assert db_session_obj is not None
        assert db_session_obj.session_name == session_name

    def test_create_tally_session_creates_audit_log(self, db_session: Session) -> None:
        """Test that audit log is created when creating tally session."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        # Create tally session
        session_name = "End of Day Count"
        result = create_tally_session(pen.id, operator.id, session_name, db_session)

        # Verify audit log was created
        audit_logs = db_session.exec(select(AuditLog)).all()
        assert len(audit_logs) == 1

        audit_log = audit_logs[0]
        assert audit_log.operator_id == operator.id
        assert audit_log.action == "TALLY_CREATED"
        assert audit_log.entity_type == "TallySession"
        assert audit_log.entity_id == result.id
        assert audit_log.old_values is None
        assert audit_log.new_values is not None
        assert audit_log.new_values["session_name"] == session_name

    def test_create_tally_session_pen_not_found_error(
        self, db_session: Session
    ) -> None:
        """Test error when pen not found."""
        # Create operator
        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        # Try to create session for non-existent pen
        non_existent_id = uuid4()
        with pytest.raises(ValueError, match="not found"):
            create_tally_session(
                non_existent_id, operator.id, "Test Session", db_session
            )


class TestUpdateTallyLine:
    """Test cases for update_tally_line function."""

    def test_update_tally_line_create_new(self, db_session: Session) -> None:
        """Test creating new tally line."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        party = Party(name="Test Party", short_code="TP")
        db_session.add(party)
        db_session.flush()

        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=operator.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
        )
        db_session.add(tally_session)
        db_session.flush()

        # Create tally line
        vote_count = 25
        result = update_tally_line(tally_session.id, party.id, vote_count, db_session)

        # Verify tally line was created
        assert result.tally_session_id == tally_session.id
        assert result.party_id == party.id
        assert result.vote_count == vote_count

        # Verify total votes updated in session
        db_session.refresh(tally_session)
        assert tally_session.total_votes_counted == vote_count

    def test_update_tally_line_update_existing(self, db_session: Session) -> None:
        """Test updating existing tally line."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        party = Party(name="Test Party", short_code="TP")
        db_session.add(party)
        db_session.flush()

        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=operator.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
        )
        db_session.add(tally_session)
        db_session.flush()

        # Create initial tally line
        initial_count = 10
        tally_line = TallyLine(
            tally_session_id=tally_session.id,
            party_id=party.id,
            vote_count=initial_count,
        )
        db_session.add(tally_line)
        db_session.flush()

        # Update tally line
        new_count = 25
        result = update_tally_line(tally_session.id, party.id, new_count, db_session)

        # Verify tally line was updated
        assert result.id == tally_line.id  # Same instance
        assert result.vote_count == new_count

        # Verify total votes updated in session
        db_session.refresh(tally_session)
        assert tally_session.total_votes_counted == new_count

    def test_update_tally_line_creates_audit_log(self, db_session: Session) -> None:
        """Test that audit log is created when updating tally line."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        party = Party(name="Test Party", short_code="TP")
        db_session.add(party)
        db_session.flush()

        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=operator.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
        )
        db_session.add(tally_session)
        db_session.flush()

        # Update tally line
        vote_count = 25
        result = update_tally_line(tally_session.id, party.id, vote_count, db_session)

        # Verify audit log was created
        audit_logs = db_session.exec(select(AuditLog)).all()
        assert len(audit_logs) == 1

        audit_log = audit_logs[0]
        assert audit_log.operator_id == operator.id
        assert audit_log.action == "TALLY_UPDATED"
        assert audit_log.entity_type == "TallyLine"
        assert audit_log.entity_id == result.id
        assert audit_log.new_values is not None
        assert audit_log.new_values["vote_count"] == vote_count

    def test_update_tally_line_multiple_parties_total(
        self, db_session: Session
    ) -> None:
        """Test that total votes are calculated correctly with multiple parties."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        party1 = Party(name="Party 1", short_code="P1")
        party2 = Party(name="Party 2", short_code="P2")
        db_session.add_all([party1, party2])
        db_session.flush()

        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=operator.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
        )
        db_session.add(tally_session)
        db_session.flush()

        # Add votes for party 1
        update_tally_line(tally_session.id, party1.id, 15, db_session)
        db_session.refresh(tally_session)
        assert tally_session.total_votes_counted == 15

        # Add votes for party 2
        update_tally_line(tally_session.id, party2.id, 20, db_session)
        db_session.refresh(tally_session)
        assert tally_session.total_votes_counted == 35

        # Update party 1 votes
        update_tally_line(tally_session.id, party1.id, 25, db_session)
        db_session.refresh(tally_session)
        assert tally_session.total_votes_counted == 45  # 25 + 20

    def test_update_tally_line_negative_votes_error(self, db_session: Session) -> None:
        """Test error when vote count is negative."""
        # Create minimal test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        party = Party(name="Test Party", short_code="TP")
        db_session.add(party)
        db_session.flush()

        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=operator.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
        )
        db_session.add(tally_session)
        db_session.flush()

        # Try to set negative vote count
        with pytest.raises(ValueError, match="cannot be negative"):
            update_tally_line(tally_session.id, party.id, -5, db_session)

    def test_update_tally_line_session_not_found_error(
        self, db_session: Session
    ) -> None:
        """Test error when tally session not found."""
        # Create party
        party = Party(name="Test Party", short_code="TP")
        db_session.add(party)
        db_session.flush()

        # Try to update line for non-existent session
        non_existent_id = uuid4()
        with pytest.raises(ValueError, match="TallySession.*not found"):
            update_tally_line(non_existent_id, party.id, 10, db_session)

    def test_update_tally_line_party_not_found_error(self, db_session: Session) -> None:
        """Test error when party not found."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=operator.id,
            session_name="Test Session",
            started_at=datetime.utcnow(),
        )
        db_session.add(tally_session)
        db_session.flush()

        # Try to update line for non-existent party
        non_existent_id = uuid4()
        with pytest.raises(ValueError, match="Party.*not found"):
            update_tally_line(tally_session.id, non_existent_id, 10, db_session)
