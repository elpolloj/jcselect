"""Tests for enhanced sync queue TallyLine integration."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlmodel import Session

from jcselect.models.sync_schemas import ChangeOperation
from jcselect.models.enums import BallotType
from jcselect.models.tally_line import TallyLine
from jcselect.models.tally_session import TallySession
from jcselect.sync.queue import SyncQueue


@pytest.fixture
def mock_sync_queue(tmp_path):
    """Create a mock sync queue for testing."""
    db_path = tmp_path / "test_sync.db"
    queue = SyncQueue(db_path)
    return queue


@pytest.fixture
def sample_tally_line():
    """Create a sample TallyLine for testing."""
    session_id = uuid.uuid4()
    party_id = uuid.uuid4()
    
    return TallyLine(
        id=uuid.uuid4(),
        tally_session_id=session_id,
        party_id=party_id,
        vote_count=1,
        ballot_type=BallotType.NORMAL,
        ballot_number=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def test_enqueue_tally_line_serialization(mock_sync_queue, sample_tally_line):
    """Test that enqueue_tally_line correctly serializes TallyLine objects."""
    with patch('jcselect.dao.tally_line_to_dict') as mock_to_dict:
        # Mock the serialization function
        expected_data = {
            "id": str(sample_tally_line.id),
            "tally_session_id": str(sample_tally_line.tally_session_id),
            "party_id": str(sample_tally_line.party_id),
            "vote_count": sample_tally_line.vote_count,
            "ballot_type": sample_tally_line.ballot_type.value,
            "ballot_number": sample_tally_line.ballot_number,
            "created_at": sample_tally_line.created_at.isoformat(),
            "updated_at": sample_tally_line.updated_at.isoformat()
        }
        mock_to_dict.return_value = expected_data
        
        # Enqueue the TallyLine
        change = mock_sync_queue.enqueue_tally_line(sample_tally_line, ChangeOperation.CREATE)
        
        # Verify the serialization was called
        mock_to_dict.assert_called_once_with(sample_tally_line)
        
        # Verify the change was created correctly
        assert change.entity_type == "TallyLine"
        assert change.entity_id == sample_tally_line.id
        assert change.operation == ChangeOperation.CREATE
        assert change.data == expected_data


def test_enqueue_tally_line_triggers_fast_sync(mock_sync_queue, sample_tally_line):
    """Test that enqueuing TallyLine triggers fast sync when enabled."""
    with patch('jcselect.dao.tally_line_to_dict') as mock_to_dict, \
         patch.object(mock_sync_queue, '_should_trigger_fast_sync', return_value=True) as mock_should_trigger, \
         patch.object(mock_sync_queue, '_trigger_fast_sync_async') as mock_trigger:
        
        # Mock the serialization
        mock_to_dict.return_value = {"test": "data"}
        
        # Enqueue the TallyLine
        mock_sync_queue.enqueue_tally_line(sample_tally_line, ChangeOperation.CREATE)
        
        # Verify fast sync was triggered
        mock_should_trigger.assert_called_once()
        mock_trigger.assert_called_once()


def test_enqueue_tally_line_no_fast_sync_when_disabled(mock_sync_queue, sample_tally_line):
    """Test that enqueuing TallyLine doesn't trigger fast sync when disabled."""
    with patch('jcselect.dao.tally_line_to_dict') as mock_to_dict, \
         patch.object(mock_sync_queue, '_should_trigger_fast_sync', return_value=False) as mock_should_trigger, \
         patch.object(mock_sync_queue, '_trigger_fast_sync_async') as mock_trigger:
        
        # Mock the serialization
        mock_to_dict.return_value = {"test": "data"}
        
        # Enqueue the TallyLine
        mock_sync_queue.enqueue_tally_line(sample_tally_line, ChangeOperation.CREATE)
        
        # Verify fast sync was not triggered
        mock_should_trigger.assert_called_once()
        mock_trigger.assert_not_called()


def test_trigger_fast_sync_creates_task():
    """Test that trigger_fast_sync creates an async task when event loop is running."""
    mock_queue = Mock()
    
    with patch('asyncio.get_event_loop') as mock_get_loop, \
         patch('asyncio.create_task') as mock_create_task:
        
        # Mock event loop
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop
        
        # Call trigger_fast_sync
        mock_queue.trigger_fast_sync = SyncQueue.trigger_fast_sync.__get__(mock_queue)
        mock_queue.trigger_fast_sync()
        
        # Verify task creation
        mock_create_task.assert_called_once()


def test_should_trigger_fast_sync_settings():
    """Test _should_trigger_fast_sync respects settings."""
    mock_queue = Mock()
    
    with patch('jcselect.utils.settings.sync_settings') as mock_settings:
        # Test when both sync_enabled and sync_fast_tally_enabled are True
        mock_settings.sync_enabled = True
        mock_settings.sync_fast_tally_enabled = True
        
        result = SyncQueue._should_trigger_fast_sync(mock_queue)
        assert result is True
        
        # Test when sync_enabled is False
        mock_settings.sync_enabled = False
        mock_settings.sync_fast_tally_enabled = True
        
        result = SyncQueue._should_trigger_fast_sync(mock_queue)
        assert result is False
        
        # Test when sync_fast_tally_enabled is False
        mock_settings.sync_enabled = True
        mock_settings.sync_fast_tally_enabled = False
        
        result = SyncQueue._should_trigger_fast_sync(mock_queue)
        assert result is False


def test_enqueue_tally_line_update_operation(mock_sync_queue, sample_tally_line):
    """Test enqueuing TallyLine with UPDATE operation for recount."""
    # Simulate a recount scenario
    sample_tally_line.deleted_at = datetime.utcnow()
    sample_tally_line.deleted_by = uuid.uuid4()
    
    with patch('jcselect.dao.tally_line_to_dict') as mock_to_dict:
        # Mock serialization to include deletion fields
        expected_data = {
            "id": str(sample_tally_line.id),
            "tally_session_id": str(sample_tally_line.tally_session_id),
            "party_id": str(sample_tally_line.party_id),
            "vote_count": sample_tally_line.vote_count,
            "ballot_type": sample_tally_line.ballot_type.value,
            "ballot_number": sample_tally_line.ballot_number,
            "deleted_at": sample_tally_line.deleted_at.isoformat(),
            "deleted_by": str(sample_tally_line.deleted_by)
        }
        mock_to_dict.return_value = expected_data
        
        # Enqueue the updated TallyLine
        change = mock_sync_queue.enqueue_tally_line(sample_tally_line, ChangeOperation.UPDATE)
        
        # Verify the change was created correctly
        assert change.entity_type == "TallyLine"
        assert change.entity_id == sample_tally_line.id
        assert change.operation == ChangeOperation.UPDATE
        assert change.data == expected_data
        assert "deleted_at" in change.data


def test_fast_sync_cycle_async():
    """Test the async fast sync cycle functionality."""
    mock_queue = Mock()
    
    with patch('jcselect.sync.engine.get_sync_engine') as mock_get_engine:
        # Mock sync engine
        mock_engine = AsyncMock()
        mock_get_engine.return_value = mock_engine
        
        # Test the async fast sync cycle
        import asyncio
        
        async def test_cycle():
            await SyncQueue._fast_sync_cycle(mock_queue)
        
        # Run the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_cycle())
        finally:
            loop.close()
        
        # Verify sync engine was called
        mock_engine.sync_cycle.assert_called_once()


def test_enqueue_change_with_ballot_type_and_number(mock_sync_queue):
    """Test that enqueue_change accepts ballot_type and ballot_number in data."""
    entity_id = uuid.uuid4()
    data = {
        "id": str(entity_id),
        "vote_count": 1,
        "ballot_type": BallotType.WHITE.value,
        "ballot_number": 5,
        "tally_session_id": str(uuid.uuid4()),
        "party_id": str(uuid.uuid4())
    }
    
    # Enqueue change with ballot type and number
    change = mock_sync_queue.enqueue_change("TallyLine", entity_id, ChangeOperation.CREATE, data)
    
    # Verify the data was preserved
    assert change.data["ballot_type"] == BallotType.WHITE.value
    assert change.data["ballot_number"] == 5
    assert change.entity_type == "TallyLine"
    assert change.operation == ChangeOperation.CREATE 