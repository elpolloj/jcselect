"""Unit tests for soft delete DAO functionality."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func
from sqlmodel import Session

from jcselect.dao import get_active_voters, soft_delete_tally_session, soft_delete_voter
from jcselect.models import AuditLog, Pen, TallySession, User, Voter
from jcselect.models.sync_schemas import ChangeOperation
from jcselect.sync.queue import sync_queue
from jcselect.utils.db import get_session


@pytest.fixture
def setup_test_data():
    """Set up test data for soft delete tests."""
    # Generate unique identifiers for this test run
    test_id = str(uuid4())[:8]
    
    with get_session() as session:
        # Create test pen with unique name
        pen = Pen(town_name=f"Test-Town-{test_id}", label=f"Pen-{test_id}")
        session.add(pen)
        session.flush()
        
        # Create test user (operator) with unique username
        user = User(
            username=f"test_operator_{test_id}",
            password_hash="dummy_hash",
            full_name=f"Test Operator {test_id}",
            role="operator"
        )
        session.add(user)
        session.flush()
        
        # Create test voter with unique number
        voter = Voter(
            pen_id=pen.id,
            voter_number=f"123-{test_id}",
            full_name=f"Test Voter {test_id}",
            father_name=f"Test Father {test_id}"
        )
        session.add(voter)
        session.flush()
        
        # Create test tally session with unique name
        tally_session = TallySession(
            pen_id=pen.id,
            operator_id=user.id,
            session_name=f"Test Session {test_id}",
            started_at=func.now()
        )
        session.add(tally_session)
        session.commit()
        
        yield {
            "pen": pen,
            "user": user,
            "voter": voter,
            "tally_session": tally_session
        }
        
        # Cleanup after test (optional - helps with repeated test runs)
        try:
            session.delete(tally_session)
            session.delete(voter)
            session.delete(user)
            session.delete(pen)
            session.commit()
        except Exception:
            # If cleanup fails, it's not critical
            session.rollback()


def test_soft_delete_voter_success(setup_test_data):
    """Test successful voter soft delete."""
    data = setup_test_data
    voter_id = data["voter"].id
    operator_id = data["user"].id
    
    # Clear any existing queue items
    sync_queue.clear()
    
    with get_session() as session:
        # Act
        soft_delete_voter(voter_id, operator_id, session)
        session.commit()
        
        # Assert voter is soft deleted
        updated_voter = session.get(Voter, voter_id)
        assert updated_voter is not None
        assert updated_voter.deleted_at is not None
        assert updated_voter.deleted_by == operator_id
        assert updated_voter.has_voted is False  # Should be untouched
        
        # Assert audit log created
        audit_logs = session.query(AuditLog).filter_by(
            entity_type="Voter",
            entity_id=voter_id,
            action="VOTER_DELETED"
        ).all()
        assert len(audit_logs) == 1
        audit_log = audit_logs[0]
        assert audit_log.operator_id == operator_id
        assert audit_log.old_values["deleted_at"] is None
        assert audit_log.new_values["deleted_by"] == str(operator_id)
        
        # Assert sync queue contains the change
        pending_changes = sync_queue.get_pending_changes_ordered()
        assert len(pending_changes) == 1
        change = pending_changes[0]
        assert change.entity_type == "Voter"
        assert change.entity_id == voter_id
        assert change.operation == ChangeOperation.UPDATE


def test_soft_delete_voter_not_found():
    """Test soft delete with non-existent voter."""
    non_existent_id = uuid4()
    operator_id = uuid4()
    
    with get_session() as session:
        with pytest.raises(ValueError, match=f"Voter with ID {non_existent_id} not found"):
            soft_delete_voter(non_existent_id, operator_id, session)


def test_soft_delete_voter_already_deleted(setup_test_data):
    """Test soft delete with already deleted voter."""
    data = setup_test_data
    voter_id = data["voter"].id
    operator_id = data["user"].id
    
    with get_session() as session:
        # First deletion
        soft_delete_voter(voter_id, operator_id, session)
        session.commit()
        
        # Attempt second deletion
        with pytest.raises(ValueError, match="is already deleted"):
            soft_delete_voter(voter_id, operator_id, session)


def test_soft_delete_tally_session_success(setup_test_data):
    """Test successful tally session soft delete."""
    data = setup_test_data
    ts_id = data["tally_session"].id
    operator_id = data["user"].id
    
    # Clear any existing queue items
    sync_queue.clear()
    
    with get_session() as session:
        # Act
        soft_delete_tally_session(ts_id, operator_id, session)
        session.commit()
        
        # Assert tally session is soft deleted
        updated_ts = session.get(TallySession, ts_id)
        assert updated_ts is not None
        assert updated_ts.deleted_at is not None
        assert updated_ts.deleted_by == operator_id
        
        # Assert audit log created
        audit_logs = session.query(AuditLog).filter_by(
            entity_type="TallySession",
            entity_id=ts_id,
            action="TALLYSESSION_DELETED"
        ).all()
        assert len(audit_logs) == 1
        
        # Assert sync queue contains the change
        pending_changes = sync_queue.get_pending_changes_ordered()
        assert len(pending_changes) == 1
        change = pending_changes[0]
        assert change.entity_type == "TallySession"
        assert change.entity_id == ts_id
        assert change.operation == ChangeOperation.UPDATE


def test_get_active_voters_excludes_deleted(setup_test_data):
    """Test that get_active_voters excludes soft-deleted records."""
    data = setup_test_data
    pen_id = data["pen"].id
    voter_id = data["voter"].id
    operator_id = data["user"].id
    
    with get_session() as session:
        # Before deletion - voter should be included
        active_voters_before = get_active_voters(pen_id, session)
        assert len(active_voters_before) == 1
        assert active_voters_before[0].id == voter_id
        
        # Soft delete the voter
        soft_delete_voter(voter_id, operator_id, session)
        session.commit()
        
        # After deletion - voter should be excluded
        active_voters_after = get_active_voters(pen_id, session)
        assert len(active_voters_after) == 0
        assert voter_id not in [v.id for v in active_voters_after]


def test_get_active_voters_pen_not_found():
    """Test get_active_voters with non-existent pen."""
    non_existent_pen_id = uuid4()
    
    with get_session() as session:
        with pytest.raises(ValueError, match=f"Pen with ID {non_existent_pen_id} not found"):
            get_active_voters(non_existent_pen_id, session)


def test_sync_queue_integration(setup_test_data):
    """Test that soft delete operations are properly enqueued for sync."""
    data = setup_test_data
    voter_id = data["voter"].id
    operator_id = data["user"].id
    
    # Clear sync queue before test
    sync_queue.clear()
    initial_queue_size = sync_queue.get_queue_size()
    assert initial_queue_size == 0
    
    with get_session() as session:
        # Perform soft delete
        soft_delete_voter(voter_id, operator_id, session)
        session.commit()
        
        # Verify sync queue contains the change
        final_queue_size = sync_queue.get_queue_size()
        assert final_queue_size == 1
        
        pending_changes = sync_queue.get_pending_changes_ordered()
        change = pending_changes[0]
        assert change.entity_type == "Voter"
        assert change.entity_id == voter_id
        assert change.operation == ChangeOperation.UPDATE
        assert "deleted_at" in change.data
        assert "deleted_by" in change.data
        assert change.data["deleted_by"] == str(operator_id)


def test_entity_to_dict_conversion(setup_test_data):
    """Test that entity data is properly converted to dictionary for sync."""
    from jcselect.dao import _entity_to_dict
    
    data = setup_test_data
    voter = data["voter"]
    
    # Convert voter to dict
    voter_dict = _entity_to_dict(voter)
    
    # Assert all expected fields are present
    expected_fields = [
        "id", "pen_id", "voter_number", "full_name", "father_name", 
        "has_voted", "created_at", "updated_at", "deleted_at", "deleted_by"
    ]
    
    for field in expected_fields:
        assert field in voter_dict
    
    # Assert UUID fields are converted to strings
    assert isinstance(voter_dict["id"], str)
    assert isinstance(voter_dict["pen_id"], str)
    
    # Assert datetime fields are converted to ISO format
    assert isinstance(voter_dict["created_at"], str)
    assert isinstance(voter_dict["updated_at"], str) 