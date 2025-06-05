"""Unit tests for dependency-ordered sync queue functionality."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from jcselect.models.sync_schemas import ChangeOperation, EntityChange
from jcselect.sync.queue import SyncQueue
from jcselect.utils.settings import sync_settings


@pytest.fixture
def temp_sync_queue():
    """Create a temporary sync queue for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_sync_queue.db"
        with SyncQueue(db_path) as queue:
            yield queue


def test_enqueue_and_fetch_dependency_order(temp_sync_queue):
    """Test that changes are enqueued and fetched in correct dependency order."""
    queue = temp_sync_queue
    
    # Enqueue changes in reverse dependency order to test sorting
    changes_data = [
        ("AuditLog", {"action": "test_audit"}),
        ("TallyLine", {"party_id": str(uuid4()), "vote_count": 10}),
        ("Voter", {"voter_number": "123", "full_name": "Test Voter"}),
        ("TallySession", {"session_name": "Test Session"}),
        ("Pen", {"label": "Test Pen", "town_name": "Test Town"}),
        ("Party", {"name": "Test Party", "abbreviation": "TP"}),
        ("User", {"username": "test_user", "full_name": "Test User"}),
    ]
    
    # Enqueue all changes
    for entity_type, data in changes_data:
        queue.enqueue_change(
            entity_type=entity_type,
            entity_id=uuid4(),
            operation=ChangeOperation.CREATE,
            data=data
        )
    
    # Fetch changes and verify dependency order
    pending_changes = queue.get_pending_changes_ordered()
    
    assert len(pending_changes) == 7
    
    # Verify correct dependency order: User, Party, Pen, TallySession, Voter, TallyLine, AuditLog
    expected_order = ["User", "Party", "Pen", "TallySession", "Voter", "TallyLine", "AuditLog"]
    actual_order = [change.entity_type for change in pending_changes]
    
    assert actual_order == expected_order


def test_retry_backoff_calculation(temp_sync_queue):
    """Test exponential backoff calculation for retry logic."""
    queue = temp_sync_queue
    
    # Test exponential backoff calculation
    retry_0 = queue._calculate_next_retry(0)
    retry_1 = queue._calculate_next_retry(1)
    retry_2 = queue._calculate_next_retry(2)
    retry_3 = queue._calculate_next_retry(3)
    
    now = datetime.utcnow()
    
    # Each retry should be exponentially longer
    base = sync_settings.sync_backoff_base
    
    assert retry_0 > now + timedelta(seconds=base**0 - 1)  # ~1 second
    assert retry_1 > now + timedelta(seconds=base**1 - 1)  # ~2 seconds
    assert retry_2 > now + timedelta(seconds=base**2 - 1)  # ~4 seconds
    assert retry_3 > now + timedelta(seconds=base**3 - 1)  # ~8 seconds
    
    # Test that backoff is capped at max_seconds
    large_retry = queue._calculate_next_retry(20)
    max_backoff = timedelta(seconds=sync_settings.sync_backoff_max_seconds)
    assert large_retry <= now + max_backoff + timedelta(seconds=1)  # Allow 1s tolerance


def test_mark_synced_and_failed(temp_sync_queue):
    """Test marking changes as synced and failed."""
    queue = temp_sync_queue
    
    # Enqueue some test changes
    change1 = queue.enqueue_change("User", uuid4(), ChangeOperation.CREATE, {"username": "user1"})
    change2 = queue.enqueue_change("User", uuid4(), ChangeOperation.UPDATE, {"username": "user2"})
    change3 = queue.enqueue_change("Party", uuid4(), ChangeOperation.CREATE, {"name": "party1"})
    
    # Verify all are pending
    assert queue.get_pending_count() == 3
    assert queue.get_queue_size() == 3
    
    # Mark first two as synced
    queue.mark_synced([str(change1.id), str(change2.id)])
    
    # Verify they're removed from queue
    assert queue.get_pending_count() == 1
    assert queue.get_queue_size() == 1
    
    # Mark the third as failed
    queue.mark_failed(str(change3.id), "Test error", 1)
    
    # Verify it's marked for retry
    assert queue.get_pending_count() == 0
    assert queue.get_retry_count() == 1
    assert queue.get_queue_size() == 1
    
    # Mark it as failed again with max retries
    max_retries = sync_settings.sync_max_retries
    queue.mark_failed(str(change3.id), "Permanent failure", max_retries)
    
    # Verify it's permanently failed
    assert queue.get_retry_count() == 0
    assert queue.get_failed_count() == 1
    assert queue.get_queue_size() == 1


def test_retry_ready_changes(temp_sync_queue):
    """Test fetching changes that are ready for retry."""
    queue = temp_sync_queue
    
    # Enqueue a change
    change = queue.enqueue_change("User", uuid4(), ChangeOperation.CREATE, {"username": "test"})
    
    # Mark it for retry with a future time
    queue.mark_failed(str(change.id), "Test error", 1)
    
    # Should not be ready for retry yet
    retry_ready = queue.get_retry_ready_changes()
    assert len(retry_ready) == 0
    
    # Mark it for retry with a past time (simulate time passing)
    past_time = datetime.utcnow() - timedelta(minutes=1)
    import sqlite3
    with sqlite3.connect(queue.db_path) as conn:
        conn.execute(
            "UPDATE sync_queue SET next_retry_at = ? WHERE id = ?",
            (past_time.isoformat(), str(change.id))
        )
        conn.commit()
    
    # Should now be ready for retry
    retry_ready = queue.get_retry_ready_changes()
    assert len(retry_ready) == 1
    assert retry_ready[0].id == change.id


def test_dependency_conflict_handling(temp_sync_queue):
    """Test handling of dependency conflicts."""
    queue = temp_sync_queue
    
    # Enqueue a change
    change = queue.enqueue_change("TallyLine", uuid4(), ChangeOperation.CREATE, {"vote_count": 5})
    
    # Mark it as having a dependency conflict
    queue.handle_dependency_conflict(str(change.id), "tally_session_id")
    
    # Verify it's marked with dependency conflict status
    import sqlite3
    with sqlite3.connect(queue.db_path) as conn:
        cursor = conn.execute(
            "SELECT status, last_error FROM sync_queue WHERE id = ?",
            (str(change.id),)
        )
        row = cursor.fetchone()
        assert row[0] == "dependency_conflict"
        assert "Missing FK: tally_session_id" in row[1]


def test_limit_respected_in_dependency_order(temp_sync_queue):
    """Test that the limit parameter is respected when fetching dependency-ordered changes."""
    queue = temp_sync_queue
    
    # Enqueue 5 changes of different types
    for i in range(5):
        queue.enqueue_change("User", uuid4(), ChangeOperation.CREATE, {"username": f"user{i}"})
    
    for i in range(3):
        queue.enqueue_change("Party", uuid4(), ChangeOperation.CREATE, {"name": f"party{i}"})
    
    # Request only 6 changes (should get 5 User + 1 Party)
    changes = queue.get_pending_changes_ordered(limit=6)
    assert len(changes) == 6
    
    # Should be 5 Users followed by 1 Party
    user_changes = [c for c in changes if c.entity_type == "User"]
    party_changes = [c for c in changes if c.entity_type == "Party"]
    
    assert len(user_changes) == 5
    assert len(party_changes) == 1


def test_database_persistence(temp_sync_queue):
    """Test that changes persist across queue instances."""
    db_path = temp_sync_queue.db_path
    
    # Enqueue a change in first instance
    change = temp_sync_queue.enqueue_change(
        "User", uuid4(), ChangeOperation.CREATE, {"username": "persistent_user"}
    )
    
    # Create a new queue instance with same database
    new_queue = SyncQueue(db_path)
    
    # Should be able to fetch the change
    changes = new_queue.get_pending_changes_ordered()
    assert len(changes) == 1
    assert changes[0].id == change.id
    assert changes[0].data["username"] == "persistent_user"


def test_queue_statistics(temp_sync_queue):
    """Test queue statistics methods."""
    queue = temp_sync_queue
    
    # Initially empty
    assert queue.get_queue_size() == 0
    assert queue.get_pending_count() == 0
    assert queue.get_retry_count() == 0
    assert queue.get_failed_count() == 0
    
    # Add some changes
    change1 = queue.enqueue_change("User", uuid4(), ChangeOperation.CREATE, {"username": "user1"})
    change2 = queue.enqueue_change("Party", uuid4(), ChangeOperation.CREATE, {"name": "party1"})
    change3 = queue.enqueue_change("Pen", uuid4(), ChangeOperation.CREATE, {"label": "pen1"})
    
    assert queue.get_queue_size() == 3
    assert queue.get_pending_count() == 3
    
    # Mark one as failed for retry
    queue.mark_failed(str(change1.id), "Test error", 1)
    
    assert queue.get_queue_size() == 3
    assert queue.get_pending_count() == 2
    assert queue.get_retry_count() == 1
    
    # Mark one as permanently failed
    queue.mark_failed(str(change2.id), "Permanent error", sync_settings.sync_max_retries)
    
    assert queue.get_queue_size() == 3
    assert queue.get_pending_count() == 1
    assert queue.get_retry_count() == 1
    assert queue.get_failed_count() == 1

    # Mark one as synced (removes from queue)
    queue.mark_synced([str(change3.id)])
    
    assert queue.get_queue_size() == 2
    assert queue.get_pending_count() == 0
    assert queue.get_retry_count() == 1
    assert queue.get_failed_count() == 1 