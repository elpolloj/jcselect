"""Unit tests for soft delete functionality."""
from __future__ import annotations

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlmodel import Session

from jcselect.controllers.voter_search_controller import VoterSearchController
from jcselect.dao import soft_delete_voter
from jcselect.models import Voter
from jcselect.models.dto import VoterDTO


@pytest.fixture
def controller():
    """Create a VoterSearchController instance for testing."""
    return VoterSearchController()


@pytest.fixture
def sample_voter_dto():
    """Create a sample VoterDTO for testing."""
    return VoterDTO(
        id=str(uuid4()),
        voter_number="12345",
        full_name="أحمد محمد علي",
        father_name="محمد",
        mother_name="فاطمة",
        pen_label="Pen A",
        has_voted=False,
        voted_at=None,
        voted_by_operator=None
    )


class TestSoftDeletes:
    """Test cases for soft delete functionality."""

    def test_soft_delete_voter(self):
        """Test voter soft delete functionality."""
        voter_id = uuid4()
        operator_id = uuid4()
        
        # Mock the voter and session
        mock_voter = Mock()
        mock_voter.id = voter_id
        mock_voter.voter_number = "12345"
        mock_voter.deleted_at = None
        mock_voter.deleted_by = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_voter
        
        with patch('jcselect.utils.db.get_session') as mock_get_session, \
             patch('jcselect.dao.sync_queue') as mock_sync_queue, \
             patch('jcselect.dao.datetime') as mock_datetime, \
             patch('jcselect.dao._entity_to_dict') as mock_entity_to_dict:
            
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_now = Mock()
            mock_datetime.utcnow.return_value = mock_now
            mock_entity_to_dict.return_value = {"id": str(voter_id), "deleted_at": None}
            
            # Call soft_delete_voter
            soft_delete_voter(voter_id, operator_id, mock_session)
            
            # Verify voter was marked as deleted
            assert mock_voter.deleted_at == mock_now
            assert mock_voter.deleted_by == operator_id
            assert mock_voter.updated_at == mock_now
            
            # Verify session operations
            mock_session.add.assert_called_with(mock_voter)
            mock_session.flush.assert_called()
            
            # Verify sync queue was updated
            mock_sync_queue.enqueue_change.assert_called()

    def test_search_excludes_deleted(self, controller):
        """Test search results exclude soft-deleted records."""
        # Test that _build_search_query includes the soft delete filter
        query = controller._build_search_query("test")
        query_str = str(query)
        
        # The query should contain the soft delete exclusion filter
        assert "deleted_at IS NULL" in query_str or "deleted_at.is_(None)" in query_str
        
        # Verify the query is properly constructed
        assert "SELECT" in query_str
        assert "voters" in query_str.lower()

    @patch('jcselect.controllers.voter_search_controller.soft_delete_voter')
    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_soft_delete_voter_controller_success(
        self, mock_get_session, mock_soft_delete_voter, controller, sample_voter_dto
    ):
        """Test successful voter soft delete through controller."""
        # Setup mocks
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Track signal emissions
        success_signals = []
        controller.voterDeletedSuccessfully.connect(lambda voter_id: success_signals.append(voter_id))
        
        # Mock refreshSearch to avoid actual search
        controller.refreshSearch = Mock()
        
        voter_id = sample_voter_dto.id
        operator_id = str(uuid4())
        
        # Soft delete voter
        controller.softDeleteVoter(voter_id, operator_id)
        
        # Verify success signal was emitted
        assert len(success_signals) == 1
        assert success_signals[0] == voter_id
        
        # Verify DAO was called correctly
        mock_soft_delete_voter.assert_called_once()
        
        # Verify refreshSearch was called
        controller.refreshSearch.assert_called_once()

    @patch('jcselect.controllers.voter_search_controller.soft_delete_voter')
    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_soft_delete_voter_controller_failure(
        self, mock_get_session, mock_soft_delete_voter, controller, sample_voter_dto
    ):
        """Test failed voter soft delete through controller."""
        # Setup mocks to raise exception
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_soft_delete_voter.side_effect = ValueError("Voter already deleted")
        
        # Track signal emissions
        failure_signals = []
        controller.operationFailed.connect(lambda msg: failure_signals.append(msg))
        
        voter_id = sample_voter_dto.id
        operator_id = str(uuid4())
        
        # Attempt to soft delete voter
        controller.softDeleteVoter(voter_id, operator_id)
        
        # Verify failure signal was emitted
        assert len(failure_signals) == 1
        assert "Delete failed" in failure_signals[0]
        assert "already deleted" in failure_signals[0]

    def test_soft_delete_preserves_other_data(self):
        """Test that soft delete only modifies delete-related fields."""
        voter_id = uuid4()
        operator_id = uuid4()
        
        # Mock a voter with existing data
        mock_voter = Mock()
        mock_voter.id = voter_id
        mock_voter.voter_number = "12345"
        mock_voter.full_name = "Test Voter"
        mock_voter.has_voted = True  # Should be preserved
        mock_voter.voted_at = "2024-01-01T12:00:00"  # Should be preserved
        mock_voter.deleted_at = None
        mock_voter.deleted_by = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_voter
        
        with patch('jcselect.utils.db.get_session') as mock_get_session, \
             patch('jcselect.dao.sync_queue'), \
             patch('jcselect.dao.datetime') as mock_datetime, \
             patch('jcselect.dao._entity_to_dict') as mock_entity_to_dict:
            
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_now = Mock()
            mock_datetime.utcnow.return_value = mock_now
            mock_entity_to_dict.return_value = {"id": str(voter_id), "deleted_at": None}
            
            # Store original values
            original_has_voted = mock_voter.has_voted
            original_voted_at = mock_voter.voted_at
            original_full_name = mock_voter.full_name
            
            # Call soft_delete_voter
            soft_delete_voter(voter_id, operator_id, mock_session)
            
            # Verify delete fields were set
            assert mock_voter.deleted_at == mock_now
            assert mock_voter.deleted_by == operator_id
            
            # Verify other fields were preserved
            assert mock_voter.has_voted == original_has_voted
            assert mock_voter.voted_at == original_voted_at
            assert mock_voter.full_name == original_full_name

    def test_soft_delete_voter_not_found(self):
        """Test soft delete with non-existent voter."""
        voter_id = uuid4()
        operator_id = uuid4()
        
        mock_session = Mock()
        mock_session.get.return_value = None  # Voter not found
        
        with patch('jcselect.utils.db.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Should raise ValueError for not found
            with pytest.raises(ValueError, match=f"Voter with ID {voter_id} not found"):
                soft_delete_voter(voter_id, operator_id, mock_session)

    def test_soft_delete_voter_already_deleted(self):
        """Test soft delete with already deleted voter."""
        voter_id = uuid4()
        operator_id = uuid4()
        
        # Mock an already deleted voter
        mock_voter = Mock()
        mock_voter.id = voter_id
        mock_voter.voter_number = "12345"
        mock_voter.deleted_at = "2024-01-01T10:00:00"  # Already deleted
        mock_voter.deleted_by = uuid4()
        
        mock_session = Mock()
        mock_session.get.return_value = mock_voter
        
        with patch('jcselect.utils.db.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Should raise ValueError for already deleted
            with pytest.raises(ValueError, match="is already deleted"):
                soft_delete_voter(voter_id, operator_id, mock_session)

    def test_soft_delete_creates_audit_trail(self):
        """Test that soft delete creates proper audit log entries."""
        voter_id = uuid4()
        operator_id = uuid4()
        
        mock_voter = Mock()
        mock_voter.id = voter_id
        mock_voter.voter_number = "12345"
        mock_voter.deleted_at = None
        mock_voter.deleted_by = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_voter
        
        with patch('jcselect.utils.db.get_session') as mock_get_session, \
             patch('jcselect.dao.sync_queue'), \
             patch('jcselect.dao.datetime') as mock_datetime, \
             patch('jcselect.dao.AuditLog') as mock_audit_log, \
             patch('jcselect.dao._entity_to_dict') as mock_entity_to_dict:
            
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_now = Mock()
            mock_datetime.utcnow.return_value = mock_now
            mock_entity_to_dict.return_value = {"id": str(voter_id), "deleted_at": None}
            
            # Call soft_delete_voter
            soft_delete_voter(voter_id, operator_id, mock_session)
            
            # Verify audit log was created
            mock_audit_log.assert_called_once()
            call_args = mock_audit_log.call_args[1]  # Get keyword arguments
            
            assert call_args["operator_id"] == operator_id
            assert call_args["action"] == "VOTER_DELETED"
            assert call_args["entity_type"] == "Voter"
            assert call_args["entity_id"] == voter_id
            assert "deleted_at" in call_args["old_values"]
            assert "deleted_by" in call_args["new_values"]

    def test_soft_delete_syncs_changes(self):
        """Test that soft delete operations are queued for sync."""
        voter_id = uuid4()
        operator_id = uuid4()
        
        mock_voter = Mock()
        mock_voter.id = voter_id
        mock_voter.voter_number = "12345"
        mock_voter.deleted_at = None
        mock_voter.deleted_by = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_voter
        
        with patch('jcselect.utils.db.get_session') as mock_get_session, \
             patch('jcselect.dao.sync_queue') as mock_sync_queue, \
             patch('jcselect.dao.datetime') as mock_datetime, \
             patch('jcselect.dao._entity_to_dict') as mock_entity_to_dict:
            
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_now = Mock()
            mock_datetime.utcnow.return_value = mock_now
            mock_entity_to_dict.return_value = {"id": str(voter_id), "deleted_at": "2024-01-01T12:00:00"}
            
            # Call soft_delete_voter
            soft_delete_voter(voter_id, operator_id, mock_session)
            
            # Verify sync queue was called
            mock_sync_queue.enqueue_change.assert_called_once()
            call_args = mock_sync_queue.enqueue_change.call_args[0]  # Get positional arguments
            
            assert call_args[0] == "Voter"  # entity_type
            assert call_args[1] == voter_id  # entity_id
            assert call_args[2].value == "UPDATE"  # operation (should be UPDATE not DELETE)

    def test_soft_delete_ui_integration(self, controller):
        """Test that UI properly integrates soft delete functionality."""
        # Verify the controller has the softDeleteVoter method
        assert hasattr(controller, 'softDeleteVoter')
        assert callable(getattr(controller, 'softDeleteVoter'))
        
        # Verify the controller has the required signals
        assert hasattr(controller, 'voterDeletedSuccessfully')
        assert hasattr(controller, 'operationFailed')
        
        # Verify search query excludes soft-deleted records
        query = controller._build_search_query("test")
        query_str = str(query)
        
        # Should contain soft delete filter
        assert "deleted_at" in query_str
        # Should be checking for NULL/None values
        assert ("IS NULL" in query_str or "is_(None)" in query_str) 