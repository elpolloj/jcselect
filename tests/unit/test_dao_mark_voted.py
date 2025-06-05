"""Tests for DAO mark_voted function."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from jcselect.dao import mark_voted
from jcselect.models import AuditLog, Pen, User, Voter
from sqlmodel import Session, select


class TestMarkVoted:
    """Test cases for mark_voted function."""

    def test_mark_voted_success(self, db_session: Session) -> None:
        """Test successful voter marking."""
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

        voter = Voter(
            pen_id=pen.id,
            voter_number="001",
            full_name="John Doe",
            has_voted=False,
        )
        db_session.add(voter)
        db_session.flush()

        # Mark voter as voted
        result = mark_voted(voter.id, operator.id, db_session)

        # Verify voter was updated
        assert result.has_voted is True
        assert result.voted_at is not None
        assert result.voted_by_operator_id == operator.id
        assert isinstance(result.voted_at, datetime)

        # Verify voter in database
        db_voter = db_session.get(Voter, voter.id)
        assert db_voter is not None
        assert db_voter.has_voted is True
        assert db_voter.voted_at is not None
        assert db_voter.voted_by_operator_id == operator.id

    def test_mark_voted_creates_audit_log(self, db_session: Session) -> None:
        """Test that audit log is created when marking voter."""
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

        voter = Voter(
            pen_id=pen.id,
            voter_number="001",
            full_name="John Doe",
            has_voted=False,
        )
        db_session.add(voter)
        db_session.flush()

        # Mark voter as voted
        mark_voted(voter.id, operator.id, db_session)

        # Verify audit log was created
        audit_logs = db_session.exec(select(AuditLog)).all()
        assert len(audit_logs) == 1

        audit_log = audit_logs[0]
        assert audit_log.operator_id == operator.id
        assert audit_log.action == "VOTER_MARKED"
        assert audit_log.entity_type == "Voter"
        assert audit_log.entity_id == voter.id
        assert audit_log.old_values is not None
        assert audit_log.new_values is not None
        assert audit_log.old_values["has_voted"] is False
        assert audit_log.new_values["has_voted"] is True

    def test_mark_voted_already_voted_error(self, db_session: Session) -> None:
        """Test error when trying to mark already voted voter."""
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

        voter = Voter(
            pen_id=pen.id,
            voter_number="001",
            full_name="John Doe",
            has_voted=True,  # Already voted
            voted_at=datetime.utcnow(),
            voted_by_operator_id=operator.id,
        )
        db_session.add(voter)
        db_session.flush()

        # Try to mark voter as voted again
        with pytest.raises(ValueError, match="has already voted"):
            mark_voted(voter.id, operator.id, db_session)

    def test_mark_voted_voter_not_found_error(self, db_session: Session) -> None:
        """Test error when voter not found."""
        # Create operator
        operator = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator",
        )
        db_session.add(operator)
        db_session.flush()

        # Try to mark non-existent voter
        non_existent_id = uuid4()
        with pytest.raises(ValueError, match="not found"):
            mark_voted(non_existent_id, operator.id, db_session)

    def test_mark_voted_operator_tracking(self, db_session: Session) -> None:
        """Test that operator is properly tracked."""
        # Create test data
        pen = Pen(town_name="TestTown", label="Pen 101")
        db_session.add(pen)
        db_session.flush()

        operator1 = User(
            username="operator1",
            password_hash="hashed_password",
            full_name="Test Operator 1",
        )
        operator2 = User(
            username="operator2",
            password_hash="hashed_password",
            full_name="Test Operator 2",
        )
        db_session.add_all([operator1, operator2])
        db_session.flush()

        voter = Voter(
            pen_id=pen.id,
            voter_number="001",
            full_name="John Doe",
            has_voted=False,
        )
        db_session.add(voter)
        db_session.flush()

        # Mark voter as voted by operator1
        result = mark_voted(voter.id, operator1.id, db_session)

        # Verify correct operator is tracked
        assert result.voted_by_operator_id == operator1.id
        assert result.voted_by_operator_id != operator2.id

        # Verify audit log has correct operator
        audit_log = db_session.exec(select(AuditLog)).first()
        assert audit_log is not None
        assert audit_log.operator_id == operator1.id
