"""Unit tests for sync engine functionality."""
from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import Response

from jcselect.models.sync_schemas import (
    ChangeOperation,
    EntityChange,
    SyncPullResponse,
    SyncPushResponse,
)
from jcselect.sync.engine import BackoffStrategy, SyncEngine
from jcselect.sync.queue import SyncQueue
from jcselect.utils.settings import SyncSettings


@pytest.fixture
def mock_settings():
    """Create mock sync settings for testing."""
    settings = MagicMock(spec=SyncSettings)
    settings.sync_api_url = "http://localhost:8999"
    settings.sync_max_payload_size = 1024 * 1024  # 1MB
    settings.sync_pull_page_size = 100
    settings.sync_max_pull_pages = 10
    settings.sync_backoff_base = 2.0
    settings.sync_backoff_max_seconds = 300
    settings.sync_interval_seconds = 300
    return settings


@pytest.fixture
def temp_queue():
    """Create a temporary sync queue for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_sync_queue.db"
        with SyncQueue(db_path) as queue:
            yield queue


@pytest.fixture
def sync_engine(mock_settings, temp_queue):
    """Create sync engine with mocked dependencies."""
    return SyncEngine(mock_settings, temp_queue)


@pytest.fixture
def sample_change():
    """Create a sample entity change for testing."""
    return EntityChange(
        id=uuid4(),
        entity_type="Voter",
        entity_id=uuid4(),
        operation=ChangeOperation.UPDATE,
        data={"voter_number": "123", "has_voted": True},
        timestamp=datetime.utcnow(),
        retry_count=0
    )


def test_backoff_delay_growth():
    """Test that backoff delay grows exponentially."""
    backoff = BackoffStrategy(base=2.0, max_delay=300.0)
    
    # Test exponential growth
    delay_0 = backoff.calculate_delay(0)
    delay_1 = backoff.calculate_delay(1)
    delay_2 = backoff.calculate_delay(2)
    delay_3 = backoff.calculate_delay(3)
    
    assert delay_0 == 1.0  # 2^0
    assert delay_1 == 2.0  # 2^1
    assert delay_2 == 4.0  # 2^2
    assert delay_3 == 8.0  # 2^3
    
    # Test max delay cap
    large_delay = backoff.calculate_delay(20)
    assert large_delay == 300.0  # Capped at max_delay


@pytest.mark.asyncio
async def test_push_success_marks_synced(sync_engine, temp_queue, sample_change):
    """Test that successful push marks changes as synced."""
    # Add change to queue
    temp_queue.enqueue_change(
        sample_change.entity_type,
        sample_change.entity_id,
        sample_change.operation,
        sample_change.data
    )
    
    # Mock successful HTTP response
    mock_response = Response(
        status_code=200,
        json={
            "processed_count": 1,
            "failed_changes": [],
            "conflicts": [],
            "server_timestamp": datetime.utcnow().isoformat()
        }
    )
    
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    sync_engine._client = mock_client
    
    # Execute push
    await sync_engine.push_changes()
    
    # Verify queue is empty (changes marked as synced)
    assert temp_queue.get_pending_count() == 0
    assert temp_queue.get_queue_size() == 0
    
    # Verify HTTP call was made
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_dependency_conflict_requeues(sync_engine, temp_queue, sample_change):
    """Test that dependency conflicts requeue changes."""
    # Add change to queue
    temp_queue.enqueue_change(
        sample_change.entity_type,
        sample_change.entity_id,
        sample_change.operation,
        sample_change.data
    )
    
    # Mock 409 dependency conflict response
    mock_response = Response(status_code=409, text="Dependency conflict")
    
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    sync_engine._client = mock_client
    
    # Execute push
    await sync_engine.push_changes()
    
    # Verify change is still in queue but marked for dependency conflict
    assert temp_queue.get_pending_count() == 0  # No longer pending
    assert temp_queue.get_queue_size() == 1     # Still in queue
    
    # Check the change status in database
    import sqlite3
    with sqlite3.connect(temp_queue.db_path) as conn:
        cursor = conn.execute("SELECT status FROM sync_queue LIMIT 1")
        row = cursor.fetchone()
        assert row[0] == "dependency_conflict"


@pytest.mark.asyncio
async def test_push_failure_marks_failed(sync_engine, temp_queue, sample_change):
    """Test that push failures mark changes for retry."""
    # Add change to queue
    temp_queue.enqueue_change(
        sample_change.entity_type,
        sample_change.entity_id,
        sample_change.operation,
        sample_change.data
    )
    
    # Mock server error response
    mock_response = Response(status_code=500, text="Internal server error")
    
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    sync_engine._client = mock_client
    
    # Execute push
    await sync_engine.push_changes()
    
    # Verify change is marked for retry
    assert temp_queue.get_pending_count() == 0  # No longer pending
    assert temp_queue.get_retry_count() == 1    # Marked for retry
    assert temp_queue.get_queue_size() == 1     # Still in queue


@pytest.mark.asyncio
async def test_pull_pagination_applies_changes(sync_engine):
    """Test that pull respects pagination and applies changes."""
    # Mock paginated pull responses
    page1_response = Response(
        status_code=200,
        json={
            "changes": [
                {
                    "id": str(uuid4()),
                    "entity_type": "User",
                    "entity_id": str(uuid4()),
                    "operation": "CREATE",
                    "data": {"username": "testuser1", "full_name": "Test User 1"},
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_count": 0
                }
            ],
            "server_timestamp": datetime.utcnow().isoformat(),
            "has_more": True
        }
    )
    
    page2_response = Response(
        status_code=200,
        json={
            "changes": [
                {
                    "id": str(uuid4()),
                    "entity_type": "User", 
                    "entity_id": str(uuid4()),
                    "operation": "CREATE",
                    "data": {"username": "testuser2", "full_name": "Test User 2"},
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_count": 0
                }
            ],
            "server_timestamp": datetime.utcnow().isoformat(),
            "has_more": False
        }
    )
    
    mock_client = AsyncMock()
    mock_client.get.side_effect = [page1_response, page2_response]
    sync_engine._client = mock_client
    
    # Mock apply_remote_changes to avoid database operations
    sync_engine.apply_remote_changes = AsyncMock()
    
    # Execute pull
    await sync_engine.pull_changes_paginated()
    
    # Verify both pages were fetched
    assert mock_client.get.call_count == 2
    
    # Verify changes were applied
    sync_engine.apply_remote_changes.assert_called_once()
    applied_changes = sync_engine.apply_remote_changes.call_args[0][0]
    assert len(applied_changes) == 2  # Both changes applied


@pytest.mark.asyncio
async def test_pull_respects_page_limits(sync_engine, mock_settings):
    """Test that pull respects max pages limit."""
    # Set low page limit for testing
    mock_settings.sync_max_pull_pages = 2
    
    # Mock responses that always have more pages
    mock_response = Response(
        status_code=200,
        json={
            "changes": [
                {
                    "id": str(uuid4()),
                    "entity_type": "User",
                    "entity_id": str(uuid4()),
                    "operation": "CREATE",
                    "data": {"username": "testuser"},
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_count": 0
                }
            ],
            "server_timestamp": datetime.utcnow().isoformat(),
            "has_more": True  # Always more pages
        }
    )
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    sync_engine._client = mock_client
    
    # Mock apply_remote_changes
    sync_engine.apply_remote_changes = AsyncMock()
    
    # Execute pull
    await sync_engine.pull_changes_paginated()
    
    # Should only fetch max_pull_pages (2) despite has_more=True
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_batch_creation_respects_payload_size(sync_engine, temp_queue):
    """Test that batching respects payload size limits."""
    # Create changes with large data
    large_data = {"description": "x" * 1000}  # 1KB data
    
    # Add multiple changes to queue
    for i in range(5):
        temp_queue.enqueue_change(
            "User",
            uuid4(),
            ChangeOperation.CREATE,
            {**large_data, "username": f"user{i}"}
        )
    
    # Set small payload size to force multiple batches
    sync_engine.settings.sync_max_payload_size = 2000  # 2KB limit
    
    # Get pending changes and create batches
    changes = temp_queue.get_pending_changes_ordered()
    batches = sync_engine._create_batches(changes)
    
    # Should create multiple batches due to size limit
    assert len(batches) > 1
    
    # Each batch should respect size limit
    for batch in batches:
        batch_size = sum(len(str(change.data)) for change in batch)
        assert batch_size <= sync_engine.settings.sync_max_payload_size + 1000  # Allow some overhead


@pytest.mark.asyncio
async def test_start_stop_engine(sync_engine):
    """Test sync engine start and stop functionality."""
    # Start engine
    await sync_engine.start()
    assert sync_engine._running is True
    assert sync_engine._client is not None
    assert sync_engine._sync_task is not None
    
    # Stop engine
    await sync_engine.stop()
    assert sync_engine._running is False
    assert sync_engine._client is None


@pytest.mark.asyncio
async def test_conflict_resolution_last_write_wins(sync_engine):
    """Test conflict resolution using last-write-wins."""
    # Create a mock local entity with older timestamp
    local_entity = MagicMock()
    local_entity.updated_at = datetime.utcnow() - timedelta(hours=1)
    local_entity.username = "old_value"
    
    # Create remote change with newer timestamp
    remote_change = EntityChange(
        id=uuid4(),
        entity_type="User",
        entity_id=uuid4(),
        operation=ChangeOperation.UPDATE,
        data={"username": "new_value", "updated_at": datetime.utcnow().isoformat()},
        timestamp=datetime.utcnow(),  # Newer timestamp
        retry_count=0
    )
    
    # Mock session and audit log creation
    mock_session = MagicMock()
    
    with patch('jcselect.sync.engine.create_audit_log') as mock_audit:
        await sync_engine._resolve_conflict(local_entity, remote_change, mock_session)
        
        # Verify remote change wins (newer timestamp)
        assert local_entity.username == "new_value"
        mock_audit.assert_called_once()


@pytest.mark.asyncio 
async def test_network_error_handling(sync_engine, temp_queue, sample_change):
    """Test handling of network errors during sync."""
    # Add change to queue
    temp_queue.enqueue_change(
        sample_change.entity_type,
        sample_change.entity_id,
        sample_change.operation,
        sample_change.data
    )
    
    # Mock network error
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Network timeout")
    sync_engine._client = mock_client
    
    # Execute push (should not raise exception)
    await sync_engine.push_changes()
    
    # Verify change is marked for retry
    assert temp_queue.get_retry_count() == 1


@pytest.mark.asyncio
async def test_empty_queue_push(sync_engine, temp_queue):
    """Test push with empty queue."""
    # Ensure queue is empty
    temp_queue.clear()
    
    mock_client = AsyncMock()
    sync_engine._client = mock_client
    
    # Execute push
    await sync_engine.push_changes()
    
    # No HTTP calls should be made
    mock_client.post.assert_not_called() 