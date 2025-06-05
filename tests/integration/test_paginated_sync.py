"""Integration tests for paginated sync operations."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from jcselect.models.sync_schemas import ChangeOperation, EntityChange, SyncPullResponse
from jcselect.sync.engine import SyncEngine
from jcselect.utils.settings import SyncSettings


@pytest.fixture
def sync_settings():
    """Create sync settings optimized for testing pagination."""
    return SyncSettings(
        sync_api_url="http://test-server.com",
        sync_jwt_secret="test-secret-key-32-characters-long",
        sync_pull_page_size=10,  # Small page size for testing
        sync_max_pull_pages=5,   # Limit for testing
    )


@pytest.fixture
def sync_engine(sync_settings):
    """Create sync engine for testing."""
    with patch('jcselect.sync.engine.sync_queue') as mock_queue:
        engine = SyncEngine(sync_settings, mock_queue)
        return engine


def create_test_changes(count: int, entity_type: str = "Voter") -> list[EntityChange]:
    """Create test changes for pagination testing."""
    changes = []
    for i in range(count):
        change = EntityChange(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=uuid4(),
            operation=ChangeOperation.UPDATE,
            data={"full_name": f"Test {entity_type} {i}"},
            timestamp=datetime(2024, 1, 1, 12, i // 60, i % 60)
        )
        changes.append(change)
    return changes


class TestPaginatedSync:
    """Test cases for paginated sync operations."""

    @pytest.mark.asyncio
    async def test_large_dataset_pull(self, sync_engine):
        """Test pulling large datasets with pagination."""
        # Create 25 changes (more than 2 pages with page_size=10)
        total_changes = 25
        all_changes = create_test_changes(total_changes)
        
        # Mock the API client to return paginated responses
        responses = []
        page_size = sync_engine.settings.sync_pull_page_size
        
        for offset in range(0, total_changes, page_size):
            end_offset = min(offset + page_size, total_changes)
            page_changes = all_changes[offset:end_offset]
            has_more = end_offset < total_changes
            
            response = SyncPullResponse(
                changes=page_changes,
                server_timestamp="2024-01-01T12:00:00",
                has_more=has_more,
                total_available=total_changes
            )
            responses.append(response)
        
        # Mock the API client
        mock_response = Mock()
        response_iter = iter(responses)
        
        def mock_get(*args, **kwargs):
            """Mock API response for paginated pulls."""
            mock_response.json.return_value = next(response_iter).model_dump()
            return mock_response
        
        with patch.object(sync_engine, 'api_client') as mock_api:
            mock_api.get = mock_get
            mock_api.is_authenticated = True
            
            # Mock the queue operations
            sync_engine.queue.enqueue_change = Mock()
            sync_engine.last_sync_timestamp = None
            
            # Perform paginated pull
            await sync_engine.pull_changes_paginated()
            
            # Verify all changes were retrieved through pagination
            expected_calls = (total_changes + page_size - 1) // page_size  # Ceiling division
            assert mock_api.get.call_count == expected_calls
            
            # Verify changes were enqueued
            assert sync_engine.queue.enqueue_change.call_count == total_changes

    @pytest.mark.asyncio
    async def test_dependency_conflict_retry(self, sync_engine):
        """Test dependency conflicts are retried correctly."""
        # Create a TallyLine change that depends on a TallySession
        tally_session_id = uuid4()
        party_id = uuid4()
        
        # TallyLine change (child) - should fail first due to missing TallySession
        tally_line_change = EntityChange(
            id=uuid4(),
            entity_type="TallyLine",
            entity_id=uuid4(),
            operation=ChangeOperation.CREATE,
            data={
                "tally_session_id": str(tally_session_id),
                "party_id": str(party_id),
                "votes": 100
            },
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        # TallySession change (parent) - should succeed
        tally_session_change = EntityChange(
            id=uuid4(),
            entity_type="TallySession",
            entity_id=tally_session_id,
            operation=ChangeOperation.CREATE,
            data={
                "session_name": "Test Session",
                "pen_id": str(uuid4()),
                "operator_id": str(uuid4())
            },
            timestamp=datetime(2024, 1, 1, 12, 0, 1)
        )
        
        # Party change (required for TallyLine)
        party_change = EntityChange(
            id=uuid4(),
            entity_type="Party",
            entity_id=party_id,
            operation=ChangeOperation.CREATE,
            data={"name": "Test Party"},
            timestamp=datetime(2024, 1, 1, 12, 0, 2)
        )
        
        # Mock the queue to return changes in dependency-conflicting order initially
        call_count = 0
        def mock_get_pending():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: return TallyLine first (should cause 409)
                return [tally_line_change]
            elif call_count == 2:
                # Second call: return parent dependencies
                return [party_change, tally_session_change]
            elif call_count == 3:
                # Third call: retry TallyLine (should succeed now)
                return [tally_line_change]
            else:
                # No more changes
                return []
        
        sync_engine.queue.get_pending_changes_ordered.side_effect = mock_get_pending
        
        # Mock successful pushes for properly ordered changes
        push_results = []
        
        async def mock_push_batch(batch):
            """Mock push batch with dependency validation."""
            for change in batch:
                if change.entity_type == "TallyLine":
                    if call_count == 1:
                        # First time TallyLine is pushed without dependencies
                        raise Exception("409 Dependency conflict: missing TallySession")
                    else:
                        # Second time should succeed
                        push_results.append(f"SUCCESS: {change.entity_type}")
                else:
                    # Parent entities always succeed
                    push_results.append(f"SUCCESS: {change.entity_type}")
        
        # Mock dependency conflict handling
        conflict_calls = []
        def mock_handle_conflict(change_id, error):
            conflict_calls.append((change_id, error))
        
        sync_engine.queue.handle_dependency_conflict = mock_handle_conflict
        
        with patch.object(sync_engine, '_push_batch', side_effect=mock_push_batch):
            # First push attempt should fail with dependency conflict
            try:
                await sync_engine.push_changes()
                # Should handle the conflict and mark for retry
            except Exception:
                # Expected for dependency conflict
                pass
            
            # Verify conflict was detected
            assert len(conflict_calls) > 0, "Dependency conflict should have been detected"
            
            # Second push should succeed with proper dependencies
            await sync_engine.push_changes()
            
            # Third push should retry the conflicted change successfully
            await sync_engine.push_changes()
            
            # Verify all entities were eventually pushed successfully
            success_count = len([r for r in push_results if "SUCCESS" in r])
            assert success_count >= 2, f"Expected successful pushes, got: {push_results}"

    @pytest.mark.asyncio
    async def test_pagination_respects_max_pages_limit(self, sync_engine):
        """Test that pagination respects the maximum pages limit."""
        # Set a low max pages limit
        sync_engine.settings.sync_max_pull_pages = 2
        
        # Create many changes (more than max_pages * page_size)
        total_changes = 50
        page_size = sync_engine.settings.sync_pull_page_size
        
        # Mock responses that always indicate more pages available
        def mock_get(*args, **kwargs):
            """Mock API that always returns has_more=True."""
            mock_response = Mock()
            mock_response.json.return_value = {
                "changes": create_test_changes(page_size),
                "server_timestamp": "2024-01-01T12:00:00",
                "has_more": True,  # Always more pages
                "total_available": total_changes
            }
            return mock_response
        
        with patch.object(sync_engine, 'api_client') as mock_api:
            mock_api.get = mock_get
            mock_api.is_authenticated = True
            
            sync_engine.queue.enqueue_change = Mock()
            sync_engine.last_sync_timestamp = None
            
            # Perform paginated pull
            await sync_engine.pull_changes_paginated()
            
            # Should only make max_pull_pages requests despite has_more=True
            assert mock_api.get.call_count == sync_engine.settings.sync_max_pull_pages
            
            # Should have processed max_pages * page_size changes
            expected_changes = sync_engine.settings.sync_max_pull_pages * page_size
            assert sync_engine.queue.enqueue_change.call_count == expected_changes

    @pytest.mark.asyncio
    async def test_pagination_handles_empty_pages(self, sync_engine):
        """Test pagination handles empty pages gracefully."""
        responses = [
            # First page has changes
            SyncPullResponse(
                changes=create_test_changes(5),
                server_timestamp=datetime(2024, 1, 1, 12, 0, 0),
                has_more=True
            ),
            # Second page is empty but indicates more
            SyncPullResponse(
                changes=[],
                server_timestamp=datetime(2024, 1, 1, 12, 0, 1),
                has_more=True
            ),
            # Third page has changes and ends
            SyncPullResponse(
                changes=create_test_changes(3),
                server_timestamp=datetime(2024, 1, 1, 12, 0, 2),
                has_more=False
            ),
        ]
        
        response_iter = iter(responses)
        
        def mock_get(*args, **kwargs):
            mock_response = Mock()
            mock_response.json.return_value = next(response_iter).model_dump()
            return mock_response
        
        with patch.object(sync_engine, 'api_client') as mock_api:
            mock_api.get = mock_get
            mock_api.is_authenticated = True
            
            sync_engine.queue.enqueue_change = Mock()
            sync_engine.last_sync_timestamp = None
            
            # Perform paginated pull
            await sync_engine.pull_changes_paginated()
            
            # Should make all 3 requests
            assert mock_api.get.call_count == 3
            
            # Should have processed 8 total changes (5 + 0 + 3)
            assert sync_engine.queue.enqueue_change.call_count == 8

    @pytest.mark.asyncio
    async def test_pagination_with_large_payload_batching(self, sync_engine):
        """Test that large payloads are properly batched during push."""
        # Create many changes that would exceed payload size
        changes = []
        for i in range(20):
            change = EntityChange(
                id=uuid4(),
                entity_type="Voter",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"full_name": "A" * 500},  # Large data
                timestamp=datetime(2024, 1, 1, 12, i // 60, i % 60)
            )
            changes.append(change)
        
        # Set small payload size to force batching
        sync_engine.settings.sync_max_payload_size = 2048  # 2KB
        
        sync_engine.queue.get_pending_changes_ordered.return_value = changes
        
        # Track batch sizes
        batch_sizes = []
        
        async def mock_push_batch(batch):
            batch_sizes.append(len(batch))
            # Simulate successful push
            return Mock(status_code=200)
        
        with patch.object(sync_engine, '_push_batch', side_effect=mock_push_batch):
            await sync_engine.push_changes()
            
            # Should create multiple batches due to payload size limits
            assert len(batch_sizes) > 1, f"Expected multiple batches, got: {batch_sizes}"
            
            # Total changes should be preserved across batches
            total_pushed = sum(batch_sizes)
            assert total_pushed == len(changes)
            
            # Each batch should be reasonably sized
            for batch_size in batch_sizes:
                assert batch_size > 0, "No empty batches should be created"
                assert batch_size <= 10, "Batches should respect size limits"

    @pytest.mark.asyncio
    async def test_pagination_error_handling(self, sync_engine):
        """Test error handling during paginated operations."""
        # Mock API that fails on second page
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First page succeeds
                mock_response = Mock()
                mock_response.json.return_value = SyncPullResponse(
                    changes=create_test_changes(5),
                    server_timestamp=datetime(2024, 1, 1, 12, 0, 0),
                    has_more=True
                ).model_dump()
                return mock_response
            else:
                # Second page fails
                raise Exception("Network error")
        
        with patch.object(sync_engine, 'api_client') as mock_api:
            mock_api.get = mock_get
            mock_api.is_authenticated = True
            
            sync_engine.queue.enqueue_change = Mock()
            sync_engine.last_sync_timestamp = None
            
            # Should handle the error gracefully
            try:
                await sync_engine.pull_changes_paginated()
            except Exception as e:
                # Error should be propagated but not crash the system
                assert "Network error" in str(e)
            
            # First page should have been processed successfully
            assert sync_engine.queue.enqueue_change.call_count == 5 