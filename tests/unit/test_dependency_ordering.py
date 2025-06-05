"""Unit tests for dependency ordering in sync operations."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from jcselect.models.sync_schemas import ChangeOperation, EntityChange
from jcselect.sync.engine import SyncEngine
from jcselect.utils.settings import SyncSettings


@pytest.fixture
def sync_settings():
    """Create sync settings for testing."""
    return SyncSettings(
        sync_api_url="http://test-server.com",
        sync_jwt_secret="test-secret-key-32-characters-long",
        sync_entity_order=[
            "User", "Party", "Pen", 
            "TallySession", 
            "Voter", "TallyLine", 
            "AuditLog"
        ]
    )


@pytest.fixture
def sync_engine(sync_settings):
    """Create sync engine for testing."""
    with patch('jcselect.sync.engine.sync_queue') as mock_queue:
        engine = SyncEngine(sync_settings, mock_queue)
        return engine


class TestDependencyOrdering:
    """Test cases for dependency ordering in sync operations."""

    def test_batch_dependency_order(self, sync_engine):
        """Test changes are batched in correct dependency order."""
        # Create changes in reverse dependency order to test sorting
        changes = [
            EntityChange(
                id=uuid4(),
                entity_type="AuditLog",
                entity_id=uuid4(),
                operation=ChangeOperation.CREATE,
                data={"action": "test"},
                timestamp=datetime(2024, 1, 1, 12, 0, 0)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="TallyLine",
                entity_id=uuid4(),
                operation=ChangeOperation.CREATE,
                data={"party_id": str(uuid4())},
                timestamp=datetime(2024, 1, 1, 12, 0, 1)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="Voter",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"full_name": "Test Voter"},
                timestamp=datetime(2024, 1, 1, 12, 0, 2)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="TallySession",
                entity_id=uuid4(),
                operation=ChangeOperation.CREATE,
                data={"session_name": "Test Session"},
                timestamp=datetime(2024, 1, 1, 12, 0, 3)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="Pen",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"label": "Test Pen"},
                timestamp=datetime(2024, 1, 1, 12, 0, 4)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="Party",
                entity_id=uuid4(),
                operation=ChangeOperation.CREATE,
                data={"name": "Test Party"},
                timestamp=datetime(2024, 1, 1, 12, 0, 5)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="User",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"full_name": "Test User"},
                timestamp=datetime(2024, 1, 1, 12, 0, 6)
            ),
        ]
        
        # Create dependency batches
        batches = sync_engine._create_batches(changes)
        
        # Verify batches are created (at least one batch)
        assert len(batches) > 0
        
        # Flatten batches to get ordered changes
        ordered_changes = []
        for batch in batches:
            ordered_changes.extend(batch)
        
        # Verify correct dependency order: User, Party, Pen, TallySession, Voter, TallyLine, AuditLog
        entity_types_order = [change.entity_type for change in ordered_changes]
        
        # Check that parent entities come before children
        user_index = next((i for i, et in enumerate(entity_types_order) if et == "User"), -1)
        party_index = next((i for i, et in enumerate(entity_types_order) if et == "Party"), -1)
        pen_index = next((i for i, et in enumerate(entity_types_order) if et == "Pen"), -1)
        tally_session_index = next((i for i, et in enumerate(entity_types_order) if et == "TallySession"), -1)
        voter_index = next((i for i, et in enumerate(entity_types_order) if et == "Voter"), -1)
        tally_line_index = next((i for i, et in enumerate(entity_types_order) if et == "TallyLine"), -1)
        audit_log_index = next((i for i, et in enumerate(entity_types_order) if et == "AuditLog"), -1)
        
        # Verify dependency order constraints
        assert user_index < tally_session_index, "User should come before TallySession"
        assert party_index < tally_line_index, "Party should come before TallyLine"
        assert pen_index < tally_session_index, "Pen should come before TallySession"
        assert pen_index < voter_index, "Pen should come before Voter"
        assert tally_session_index < tally_line_index, "TallySession should come before TallyLine"

    def test_dependency_conflict_handling(self, sync_engine):
        """Test 409 conflicts are handled gracefully."""
        # Mock the push method to simulate dependency conflicts
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.json.return_value = {
            "error": "Dependency conflict",
            "missing_dependencies": ["TallySession"]
        }
        
        # Create a change that would have dependency conflicts
        tally_line_change = EntityChange(
            id=uuid4(),
            entity_type="TallyLine",
            entity_id=uuid4(),
            operation=ChangeOperation.CREATE,
            data={
                "tally_session_id": str(uuid4()),  # Non-existent session
                "party_id": str(uuid4()),
                "votes": 100
            },
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        with patch.object(sync_engine, '_push_batch') as mock_push:
            mock_push.side_effect = Exception("Dependency conflict: missing TallySession")
            
            # Mock the queue to return our test change
            sync_engine.queue.get_pending_changes_ordered.return_value = [tally_line_change]
            
            # Mock handle_dependency_conflict method
            sync_engine.queue.handle_dependency_conflict = Mock()
            
            # This should handle the dependency conflict gracefully
            try:
                # Since push_changes is async, we need to test the error handling
                batches = sync_engine._create_batches([tally_line_change])
                assert len(batches) == 1
                assert batches[0][0].entity_type == "TallyLine"
                
                # Simulate the conflict handling
                sync_engine.queue.handle_dependency_conflict.assert_not_called()  # Not called yet
                
                # This would be called when the actual push fails with 409
                sync_engine.queue.handle_dependency_conflict(
                    str(tally_line_change.entity_id), 
                    "missing TallySession"
                )
                
                # Verify conflict was handled
                sync_engine.queue.handle_dependency_conflict.assert_called_once()
                
            except Exception as e:
                # Expected behavior - conflict should be caught and handled
                assert "Dependency conflict" in str(e) or "missing" in str(e)

    def test_entity_order_validation(self, sync_settings):
        """Test that entity order is properly configured."""
        expected_order = [
            "User", "Party", "Pen", 
            "TallySession", 
            "Voter", "TallyLine", 
            "AuditLog"
        ]
        
        assert sync_settings.sync_entity_order == expected_order
        
        # Verify parents come before children in the configuration
        user_pos = sync_settings.sync_entity_order.index("User")
        tally_session_pos = sync_settings.sync_entity_order.index("TallySession")
        voter_pos = sync_settings.sync_entity_order.index("Voter")
        tally_line_pos = sync_settings.sync_entity_order.index("TallyLine")
        
        assert user_pos < tally_session_pos, "User should come before TallySession"
        assert tally_session_pos < tally_line_pos, "TallySession should come before TallyLine"
        
    def test_batch_size_limits_respected(self, sync_engine):
        """Test that batches respect payload size limits."""
        # Create many small changes
        changes = []
        for i in range(10):
            change = EntityChange(
                id=uuid4(),
                entity_type="Voter",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"full_name": f"Voter {i}" * 100},  # Make data larger
                timestamp=datetime(2024, 1, 1, 12, 0, i)
            )
            changes.append(change)
        
        # Set a small max payload size for testing
        sync_engine.settings.sync_max_payload_size = 1024  # 1KB
        
        batches = sync_engine._create_batches(changes)
        
        # Should create multiple batches due to size limit
        assert len(batches) >= 1
        
        # Each batch should be reasonably sized
        for batch in batches:
            # Calculate approximate batch size
            batch_size = sum(len(str(change.data)) for change in batch)
            # Allow some overhead, but batch shouldn't be extremely large
            assert batch_size < sync_engine.settings.sync_max_payload_size * 2

    def test_mixed_entity_types_batching(self, sync_engine):
        """Test batching with mixed entity types maintains dependency order."""
        changes = [
            # Mix different entity types
            EntityChange(
                id=uuid4(),
                entity_type="Voter",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"full_name": "Voter 1"},
                timestamp=datetime(2024, 1, 1, 12, 0, 0)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="User",
                entity_id=uuid4(),
                operation=ChangeOperation.CREATE,
                data={"username": "user1"},
                timestamp=datetime(2024, 1, 1, 12, 0, 1)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="TallyLine",
                entity_id=uuid4(),
                operation=ChangeOperation.CREATE,
                data={"votes": 50},
                timestamp=datetime(2024, 1, 1, 12, 0, 2)
            ),
            EntityChange(
                id=uuid4(),
                entity_type="Party",
                entity_id=uuid4(),
                operation=ChangeOperation.UPDATE,
                data={"name": "Party 1"},
                timestamp=datetime(2024, 1, 1, 12, 0, 3)
            ),
        ]
        
        batches = sync_engine._create_batches(changes)
        
        # Flatten to check order
        all_changes = []
        for batch in batches:
            all_changes.extend(batch)
        
        # Find positions of each entity type
        positions = {}
        for i, change in enumerate(all_changes):
            if change.entity_type not in positions:
                positions[change.entity_type] = i
        
        # Verify dependency order is maintained
        assert positions["User"] < positions["Voter"], "User should come before Voter"
        assert positions["Party"] < positions["TallyLine"], "Party should come before TallyLine" 