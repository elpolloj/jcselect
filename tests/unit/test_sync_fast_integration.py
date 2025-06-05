"""Unit tests for fast-sync integration functionality."""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from PySide6.QtCore import QObject, Signal


class MockEntityChange:
    """Mock EntityChange for testing without SQLAlchemy imports."""
    def __init__(self, entity_type: str, entity_id: str):
        self.id = uuid4()
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.operation = "UPDATE"
        self.data = {"test": "data"}
        self.timestamp = datetime.utcnow()


class MockSyncSettings:
    """Mock sync settings for testing."""
    def __init__(self):
        self.sync_backoff_base = 2.0
        self.sync_backoff_max_seconds = 60.0
        self.sync_interval_seconds = 30
        self.sync_pull_page_size = 100
        self.sync_max_pull_pages = 10
        self.max_payload_size = 1000000
        self.sync_api_url = "http://test-sync.example.com"


class MockSyncQueue:
    """Mock sync queue for testing."""
    def get_pending_changes_ordered(self, limit=100):
        return []


class TestSyncEngineSignals:
    """Test Qt signals in sync engine for fast-sync integration."""

    def test_sync_engine_has_qobject_inheritance(self):
        """Test that sync engine properly inherits from QObject without importing full models."""
        # Mock the imports to avoid SQLAlchemy conflicts
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            mock_settings.sync_backoff_base = 2.0
            mock_settings.sync_backoff_max_seconds = 60.0
            
            # Import after mocking to avoid the conflicts
            from src.jcselect.sync.engine import SyncEngine
            
            # Create instance
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            
            # Test QObject inheritance
            assert isinstance(engine, QObject)
            
            # Test required signals exist
            assert hasattr(engine, 'syncCompleted')
            assert hasattr(engine, 'syncStarted')
            assert hasattr(engine, 'syncFailed')
            assert hasattr(engine, 'tallyLineUpdated')
            assert hasattr(engine, 'tallySessionUpdated')
            assert hasattr(engine, 'entityUpdated')
            
            # Test signal types
            assert isinstance(engine.syncCompleted, Signal)
            assert isinstance(engine.syncStarted, Signal)
            assert isinstance(engine.syncFailed, Signal)
            assert isinstance(engine.tallyLineUpdated, Signal)
            assert isinstance(engine.tallySessionUpdated, Signal)
            assert isinstance(engine.entityUpdated, Signal)

    def test_signal_emissions(self):
        """Test that signals can be emitted and connected."""
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            
            from src.jcselect.sync.engine import SyncEngine
            
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            
            # Test signal connection and emission
            sync_completed_calls = []
            tally_updated_calls = []
            
            engine.syncCompleted.connect(lambda: sync_completed_calls.append(True))
            engine.tallyLineUpdated.connect(lambda line_id: tally_updated_calls.append(line_id))
            
            # Emit signals
            engine.syncCompleted.emit()
            engine.tallyLineUpdated.emit("test-line-id")
            
            # Verify signals were received
            assert len(sync_completed_calls) == 1
            assert len(tally_updated_calls) == 1
            assert tally_updated_calls[0] == "test-line-id"

    def test_entity_signal_emission_method(self):
        """Test the _emit_entity_signals method."""
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            
            from src.jcselect.sync.engine import SyncEngine
            
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            
            # Track signal emissions
            tally_line_updated_calls = []
            entity_updated_calls = []
            
            engine.tallyLineUpdated.connect(lambda line_id: tally_line_updated_calls.append(line_id))
            engine.entityUpdated.connect(lambda entity_type, entity_id: entity_updated_calls.append((entity_type, entity_id)))
            
            # Test TallyLine entity change
            change = MockEntityChange("TallyLine", "test-line-123")
            engine._emit_entity_signals(change)
            
            # Verify TallyLine specific signal was emitted
            assert len(tally_line_updated_calls) == 1
            assert tally_line_updated_calls[0] == "test-line-123"
            
            # Verify general entity signal was emitted
            assert len(entity_updated_calls) == 1
            assert entity_updated_calls[0] == ("TallyLine", "test-line-123")


class TestFastSyncTrigger:
    """Test fast sync trigger functionality."""

    @pytest.mark.asyncio
    async def test_trigger_fast_sync_method_exists(self):
        """Test that trigger_fast_sync method exists and works."""
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            
            from src.jcselect.sync.engine import SyncEngine
            
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            
            # Verify method exists
            assert hasattr(engine, 'trigger_fast_sync')
            assert callable(engine.trigger_fast_sync)
            
            # Test that it doesn't crash when engine is not running
            await engine.trigger_fast_sync()
            
            # Should complete without error when engine not running

    @pytest.mark.asyncio
    async def test_trigger_fast_sync_when_running(self):
        """Test trigger_fast_sync when engine is running."""
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            
            from src.jcselect.sync.engine import SyncEngine
            
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            engine._running = True  # Simulate running state
            
            # Mock sync_cycle method
            with patch.object(engine, 'sync_cycle', new_callable=AsyncMock) as mock_sync, \
                 patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                
                await engine.trigger_fast_sync()
                
                # Verify debounce delay (250ms as per spec)
                mock_sleep.assert_called_once_with(0.25)
                mock_sync.assert_called_once()


class TestSyncEngineIntegration:
    """Test sync engine integration with results controller patterns."""

    def test_global_sync_engine_access(self):
        """Test that sync engine can be accessed globally."""
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            
            from src.jcselect.sync.engine import SyncEngine, get_sync_engine, set_sync_engine
            
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            
            # Set as global instance
            set_sync_engine(engine)
            
            # Verify it can be retrieved
            retrieved_engine = get_sync_engine()
            assert retrieved_engine is engine

    def test_results_controller_signal_pattern(self):
        """Test signal pattern that results controller expects."""
        with patch('src.jcselect.sync.engine.SyncSettings') as mock_settings_class, \
             patch('src.jcselect.sync.engine.SyncQueue') as mock_queue_class, \
             patch('src.jcselect.sync.engine.sync_settings') as mock_settings, \
             patch('src.jcselect.sync.engine.sync_queue') as mock_queue:
            
            mock_settings_class.return_value = MockSyncSettings()
            mock_queue_class.return_value = MockSyncQueue()
            
            from src.jcselect.sync.engine import SyncEngine
            
            engine = SyncEngine(MockSyncSettings(), MockSyncQueue())
            
            # This simulates the pattern used in results controller
            sync_completed_calls = []
            tally_line_calls = []
            
            # Connect like results controller does
            if hasattr(engine, 'syncCompleted'):
                engine.syncCompleted.connect(lambda: sync_completed_calls.append(True))
            if hasattr(engine, 'tallyLineUpdated'):
                engine.tallyLineUpdated.connect(lambda line_id: tally_line_calls.append(line_id))
            
            # Test signal emissions
            engine.syncCompleted.emit()
            engine.tallyLineUpdated.emit("line-123")
            
            # Verify results controller would receive these signals
            assert len(sync_completed_calls) == 1
            assert len(tally_line_calls) == 1
            assert tally_line_calls[0] == "line-123" 