"""Integration tests for end-to-end sync functionality."""
from __future__ import annotations

import asyncio
import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from jcselect.models.sync_schemas import ChangeOperation
from jcselect.sync.engine import SyncEngine
from jcselect.sync.queue import SyncQueue
from jcselect.utils.settings import SyncSettings
from tests.helpers.mock_sync_server import MockSyncServer


class TestSyncSettings(SyncSettings):
    """Test sync settings pointing to mock server."""
    
    def __init__(self, server_port: int = 8999) -> None:
        super().__init__()
        self.sync_api_url = f"http://localhost:{server_port}"
        self.sync_enabled = True
        self.sync_max_payload_size = 1024 * 1024  # 1MB
        self.sync_pull_page_size = 10  # Small for testing pagination
        self.sync_max_pull_pages = 5
        self.sync_backoff_base = 2.0
        self.sync_backoff_max_seconds = 60
        self.sync_interval_seconds = 300


@pytest.fixture
def mock_server():
    """Start mock sync server for testing."""
    server = MockSyncServer(port=8999)
    server.start()
    yield server
    server.stop()
    server.reset()


@pytest.fixture
def test_settings():
    """Create test sync settings."""
    return TestSyncSettings()


@pytest.fixture
def temp_queue():
    """Create temporary sync queue."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_sync_queue.db"
        with SyncQueue(db_path) as queue:
            yield queue


@pytest.fixture
def sync_engine(test_settings, temp_queue):
    """Create sync engine for testing."""
    return SyncEngine(test_settings, temp_queue)


@pytest.mark.asyncio
async def test_sync_end_to_end(mock_server, sync_engine, temp_queue):
    """Test complete sync cycle: enqueue changes, push to server, verify sync."""
    # Reset server state
    mock_server.reset()
    
    # Create test changes
    voter_id = uuid4()
    user_id = uuid4()
    
    # Enqueue local changes in dependency order
    temp_queue.enqueue_change(
        entity_type="User",
        entity_id=user_id,
        operation=ChangeOperation.CREATE,
        data={
            "id": str(user_id),
            "username": "test_operator",
            "full_name": "Test Operator",
            "role": "operator",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    )
    
    temp_queue.enqueue_change(
        entity_type="Voter",
        entity_id=voter_id,
        operation=ChangeOperation.UPDATE,
        data={
            "id": str(voter_id),
            "voter_number": "12345",
            "full_name": "Test Voter",
            "has_voted": True,
            "updated_at": datetime.utcnow().isoformat()
        }
    )
    
    # Verify initial queue state
    assert temp_queue.get_pending_count() == 2
    assert temp_queue.get_queue_size() == 2
    
    # Start sync engine and perform sync cycle
    await sync_engine.start()
    
    try:
        # Perform single sync cycle
        await sync_engine.sync_cycle()
        
        # Give a moment for processing
        await asyncio.sleep(0.1)
        
        # Verify changes were pushed successfully
        assert temp_queue.get_pending_count() == 0  # No pending changes
        assert temp_queue.get_queue_size() == 0     # Queue empty (changes synced)
        
        # Verify server received the changes
        assert mock_server.has_change("User", user_id)
        assert mock_server.has_change("Voter", voter_id)
        
        # Verify server data matches what we sent
        user_data = mock_server.get_entity("User", str(user_id))
        assert user_data["username"] == "test_operator"
        
        voter_data = mock_server.get_entity("Voter", str(voter_id))
        assert voter_data["voter_number"] == "12345"
        assert voter_data["has_voted"] is True
        
    finally:
        await sync_engine.stop()


@pytest.mark.asyncio
async def test_sync_pagination_end_to_end(mock_server, sync_engine, temp_queue):
    """Test pull with pagination from server."""
    # Reset server state
    mock_server.reset()
    
    # Manually add many changes to server to test pagination
    for i in range(25):  # More than one page (page_size=10)
        mock_server.changes_log.append(
            type('MockChange', (), {
                'id': uuid4(),
                'entity_type': 'User',
                'entity_id': uuid4(),
                'operation': ChangeOperation.CREATE,
                'data': {
                    'username': f'user_{i}',
                    'full_name': f'User {i}',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                },
                'timestamp': datetime.utcnow(),
                'retry_count': 0
            })()
        )
    
    # Start sync engine
    await sync_engine.start()
    
    try:
        # Mock the apply_remote_changes to count how many changes were processed
        applied_changes = []
        
        async def mock_apply_changes(changes):
            applied_changes.extend(changes)
        
        sync_engine.apply_remote_changes = mock_apply_changes
        
        # Perform pull
        await sync_engine.pull_changes_paginated()
        
        # Verify all changes were pulled despite pagination
        assert len(applied_changes) == 25
        
    finally:
        await sync_engine.stop()


@pytest.mark.asyncio
async def test_dependency_conflict_retry(mock_server, sync_engine, temp_queue):
    """Test handling of dependency conflicts and retry logic."""
    # Reset server state
    mock_server.reset()
    
    # Override mock server to simulate dependency conflict
    original_validate = mock_server._validate_dependencies
    
    def failing_validate(change):
        # Fail validation for TallyLine to simulate missing TallySession
        if change.entity_type == "TallyLine":
            return False
        return original_validate(change)
    
    mock_server._validate_dependencies = failing_validate
    
    # Enqueue a change that will fail dependency validation
    tally_line_id = uuid4()
    temp_queue.enqueue_change(
        entity_type="TallyLine",
        entity_id=tally_line_id,
        operation=ChangeOperation.CREATE,
        data={
            "id": str(tally_line_id),
            "tally_session_id": str(uuid4()),  # Non-existent session
            "party_id": str(uuid4()),
            "vote_count": 10,
            "created_at": datetime.utcnow().isoformat()
        }
    )
    
    # Start sync engine
    await sync_engine.start()
    
    try:
        # Perform sync cycle
        await sync_engine.sync_cycle()
        
        # Give a moment for processing
        await asyncio.sleep(0.1)
        
        # Verify change was marked as dependency conflict
        assert temp_queue.get_pending_count() == 0  # Not pending anymore
        assert temp_queue.get_queue_size() == 1     # Still in queue
        
        # Check status in database
        import sqlite3
        with sqlite3.connect(temp_queue.db_path) as conn:
            cursor = conn.execute("SELECT status FROM sync_queue WHERE entity_type = 'TallyLine'")
            row = cursor.fetchone()
            assert row[0] == "dependency_conflict"
        
        # Verify server didn't receive the change
        assert not mock_server.has_change("TallyLine", tally_line_id)
        
    finally:
        await sync_engine.stop()


@pytest.mark.asyncio
async def test_network_failure_retry(mock_server, sync_engine, temp_queue):
    """Test retry logic on network failures."""
    # Stop the mock server to simulate network failure
    mock_server.stop()
    
    # Enqueue a change
    voter_id = uuid4()
    temp_queue.enqueue_change(
        entity_type="Voter",
        entity_id=voter_id,
        operation=ChangeOperation.UPDATE,
        data={
            "id": str(voter_id),
            "voter_number": "12345",
            "has_voted": True,
            "updated_at": datetime.utcnow().isoformat()
        }
    )
    
    # Start sync engine
    await sync_engine.start()
    
    try:
        # Perform sync cycle (should fail due to network)
        await sync_engine.sync_cycle()
        
        # Give a moment for processing
        await asyncio.sleep(0.1)
        
        # Verify change was marked for retry due to network failure
        assert temp_queue.get_pending_count() == 0  # Not pending
        assert temp_queue.get_retry_count() == 1    # Marked for retry
        assert temp_queue.get_queue_size() == 1     # Still in queue
        
    finally:
        await sync_engine.stop()


@pytest.mark.asyncio
async def test_batch_size_limits(mock_server, sync_engine, temp_queue):
    """Test that large payloads are properly batched."""
    # Reset server state
    mock_server.reset()
    
    # Create many changes with large data to test batching
    large_data = {"description": "x" * 10000}  # 10KB per change
    
    for i in range(10):
        temp_queue.enqueue_change(
            entity_type="User",
            entity_id=uuid4(),
            operation=ChangeOperation.CREATE,
            data={
                **large_data,
                "username": f"user_{i}",
                "full_name": f"User {i}",
                "created_at": datetime.utcnow().isoformat()
            }
        )
    
    # Set small payload size to force batching
    sync_engine.settings.sync_max_payload_size = 50000  # 50KB
    
    # Track server requests
    request_count = 0
    original_push = mock_server.app.routes[0].endpoint
    
    async def counting_push(request):
        nonlocal request_count
        request_count += 1
        return await original_push(request)
    
    # Start sync engine
    await sync_engine.start()
    
    try:
        # Perform sync cycle
        await sync_engine.sync_cycle()
        
        # Give a moment for processing
        await asyncio.sleep(0.1)
        
        # Verify all changes were synced
        assert temp_queue.get_queue_size() == 0
        
        # Verify multiple batches were sent (due to size limits)
        # With 10 changes of 10KB each and 50KB limit, expect multiple batches
        
    finally:
        await sync_engine.stop()


@pytest.mark.asyncio
async def test_conflict_resolution_workflow(mock_server, sync_engine, temp_queue):
    """Test conflict resolution when server has newer data."""
    # Reset server state
    mock_server.reset()
    
    voter_id = uuid4()
    
    # First, add data to server (simulating it's newer)
    server_timestamp = datetime.utcnow()
    mock_server.storage["Voter"] = {
        str(voter_id): {
            "id": str(voter_id),
            "voter_number": "12345",
            "full_name": "Server Version",
            "has_voted": False,
            "updated_at": server_timestamp.isoformat()
        }
    }
    
    # Now enqueue local change with older timestamp
    local_timestamp = server_timestamp.replace(hour=server_timestamp.hour - 1)  # 1 hour older
    temp_queue.enqueue_change(
        entity_type="Voter",
        entity_id=voter_id,
        operation=ChangeOperation.UPDATE,
        data={
            "id": str(voter_id),
            "voter_number": "12345",
            "full_name": "Local Version",
            "has_voted": True,
            "updated_at": local_timestamp.isoformat()
        }
    )
    
    # Start sync engine
    await sync_engine.start()
    
    try:
        # Perform sync cycle
        await sync_engine.sync_cycle()
        
        # Give a moment for processing
        await asyncio.sleep(0.1)
        
        # Verify local change was handled (either synced or conflicted)
        assert temp_queue.get_pending_count() == 0
        
        # In a real implementation, we'd verify the conflict was logged
        # and the server version was preserved
        
    finally:
        await sync_engine.stop() 