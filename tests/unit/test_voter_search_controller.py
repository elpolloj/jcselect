"""Unit tests for VoterSearchController."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from PySide6.QtCore import QTimer, QObject
from PySide6.QtTest import QTest

from jcselect.controllers.voter_search_controller import VoterSearchController
from jcselect.models import Voter, Pen, User
from jcselect.models.dto import VoterDTO


@pytest.fixture
def controller():
    """Create a VoterSearchController instance for testing."""
    return VoterSearchController()


@pytest.fixture
def sample_voter():
    """Create a sample voter for testing."""
    return Voter(
        id=uuid4(),
        voter_number="12345",
        full_name="أحمد محمد علي",
        father_name="محمد",
        mother_name="فاطمة",
        pen_id=uuid4(),
        has_voted=False,
        voted_at=None,
        voted_by_operator_id=None
    )


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


class TestVoterSearchController:
    """Test cases for VoterSearchController."""

    def test_initialization(self, controller):
        """Test controller initializes with correct default values."""
        assert controller._search_query == ""
        assert controller._selected_voter is None
        assert controller._search_results == []
        assert controller._is_loading is False
        assert controller._error_message == ""
        assert controller._debounce_delay_ms == 300

    def test_setSearchQuery_debounces_and_emitsResults(self, controller, qtbot):
        """Test that setSearchQuery debounces and emits search results."""
        # Mock the search method
        controller._perform_search = Mock()
        
        # Track signal emissions
        search_query_changed = []
        controller.searchQueryChanged.connect(lambda: search_query_changed.append(True))
        
        # Set search query
        controller.setSearchQuery("test query")
        
        # Verify query was set and signal emitted
        assert controller._search_query == "test query"
        assert len(search_query_changed) == 1
        
        # Verify search hasn't been called yet (debounced)
        controller._perform_search.assert_not_called()
        
        # Wait for debounce timer
        qtbot.wait(350)  # Wait longer than debounce delay
        
        # Verify search was called after debounce
        controller._perform_search.assert_called_once()

    def test_setSearchQuery_empty_clears_results(self, controller):
        """Test that empty search query clears results immediately."""
        # Set some initial results
        controller._set_search_results([Mock()])
        controller._set_is_loading(True)
        
        # Set empty query
        controller.setSearchQuery("")
        
        # Verify results cleared and loading stopped
        assert controller._search_results == []
        assert controller._is_loading is False

    def test_selectVoter_updates_selectedVoter(self, controller, sample_voter_dto):
        """Test that selectVoter updates the selected voter."""
        # Add voter to search results
        controller._set_search_results([sample_voter_dto])
        
        # Track signal emissions
        selected_voter_changed = []
        controller.selectedVoterChanged.connect(lambda: selected_voter_changed.append(True))
        
        # Select the voter
        controller.selectVoter(sample_voter_dto.id)
        
        # Verify voter was selected and signal emitted
        assert controller._selected_voter == sample_voter_dto
        assert len(selected_voter_changed) == 1

    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_selectVoter_not_in_results_queries_database(self, mock_get_session, controller, sample_voter):
        """Test that selectVoter queries database when voter not in current results."""
        # Setup mock session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.get.return_value = sample_voter
        
        # Mock the conversion to DTO
        controller._convert_voter_to_dto = Mock(return_value=Mock(id=str(sample_voter.id)))
        
        # Select voter not in results
        controller.selectVoter(str(sample_voter.id))
        
        # Verify database was queried
        mock_session.get.assert_called_once_with(Voter, UUID(str(sample_voter.id)))

    @patch('jcselect.controllers.voter_search_controller.mark_voted')
    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_markVoterAsVoted_success_emits_voterMarkedSuccessfully(
        self, mock_get_session, mock_mark_voted, controller, sample_voter, sample_voter_dto
    ):
        """Test successful voter marking emits voterMarkedSuccessfully signal."""
        # Setup mocks
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        updated_voter = sample_voter
        updated_voter.has_voted = True
        updated_voter.voted_at = datetime.now()
        mock_mark_voted.return_value = updated_voter
        
        controller._convert_voter_to_dto = Mock(return_value=sample_voter_dto)
        controller._set_selected_voter(sample_voter_dto)
        controller._set_search_results([sample_voter_dto])
        
        # Track signal emissions
        success_signals = []
        controller.voterMarkedSuccessfully.connect(lambda name: success_signals.append(name))
        
        operator_id = str(uuid4())
        
        # Mark voter as voted
        controller.markVoterAsVoted(sample_voter_dto.id, operator_id)
        
        # Verify success signal was emitted
        assert len(success_signals) == 1
        assert success_signals[0] == updated_voter.full_name
        
        # Verify DAO was called correctly
        mock_mark_voted.assert_called_once_with(
            UUID(sample_voter_dto.id), UUID(operator_id), mock_session
        )

    @patch('jcselect.controllers.voter_search_controller.mark_voted')
    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_markVoterAsVoted_failure_emits_operationFailed(
        self, mock_get_session, mock_mark_voted, controller, sample_voter_dto
    ):
        """Test failed voter marking emits operationFailed signal."""
        # Setup mocks to raise exception
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_mark_voted.side_effect = ValueError("Voter already voted")
        
        # Track signal emissions
        failure_signals = []
        controller.operationFailed.connect(lambda msg: failure_signals.append(msg))
        
        operator_id = str(uuid4())
        
        # Attempt to mark voter as voted
        controller.markVoterAsVoted(sample_voter_dto.id, operator_id)
        
        # Verify failure signal was emitted
        assert len(failure_signals) == 1
        assert "already voted" in failure_signals[0].lower()

    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_refreshSearch_reruns_search(self, mock_get_session, controller):
        """Test that refreshSearch re-executes the current search."""
        # Set a search query
        controller._set_search_query("test query")
        
        # Mock the database session and results
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.exec.return_value.all.return_value = []
        
        # Mock the query builder
        controller._build_search_query = Mock(return_value=Mock())
        
        # Call refreshSearch
        controller.refreshSearch()
        
        # Verify search was performed
        controller._build_search_query.assert_called_once_with("test query")

    def test_normalize_arabic_text(self, controller):
        """Test Arabic text normalization functionality."""
        test_cases = [
            ("أحمد", "احمد"),  # hamza above to regular alef
            ("إبراهيم", "ابراهيم"),  # hamza below to regular alef
            ("آمنة", "امنه"),  # madda above + teh marbuta
            ("مُحَمَّد", "محمد"),  # with diacritics
            ("أحمَدّـــ", "احمد"),  # complex: hamza + diacritics + tatweel
            ("", ""),  # empty string
        ]
        
        for input_text, expected in test_cases:
            result = controller._normalize_arabic_text(input_text)
            assert result == expected, f"Failed for '{input_text}': expected '{expected}', got '{result}'"

    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_build_search_query_creates_proper_sql(self, mock_get_session, controller):
        """Test that _build_search_query creates proper SQLModel query."""
        query = controller._build_search_query("test")
        
        # Verify query object was created (basic check)
        assert query is not None
        
        # Test with Arabic text
        arabic_query = controller._build_search_query("أحمد")
        assert arabic_query is not None

    def test_convert_voter_to_dto(self, controller, sample_voter):
        """Test conversion from Voter model to VoterDTO."""
        # Create mock session
        mock_session = Mock()
        mock_session.get.return_value = None  # No operator
        
        # Test with pen relationship (mock it properly)
        with patch.object(sample_voter, 'pen') as mock_pen:
            mock_pen.label = "Test Pen"
            
            # Convert to DTO
            dto = controller._convert_voter_to_dto(sample_voter, mock_session)
            
            # Verify DTO properties
            assert dto.id == str(sample_voter.id)
            assert dto.voter_number == sample_voter.voter_number
            assert dto.full_name == sample_voter.full_name
            assert dto.father_name == sample_voter.father_name
            assert dto.mother_name == sample_voter.mother_name
            assert dto.pen_label == "Test Pen"
            assert dto.has_voted == sample_voter.has_voted
            assert dto.voted_at == sample_voter.voted_at
            assert dto.voted_by_operator is None

    def test_clearSelection(self, controller, sample_voter_dto):
        """Test that clearSelection clears the selected voter."""
        # Set a selected voter
        controller._set_selected_voter(sample_voter_dto)
        assert controller._selected_voter == sample_voter_dto
        
        # Clear selection
        controller.clearSelection()
        
        # Verify selection was cleared
        assert controller._selected_voter is None

    def test_property_getters_and_setters(self, controller, sample_voter_dto):
        """Test property getters and setters work correctly."""
        # Test search query
        controller._set_search_query("test")
        assert controller._get_search_query() == "test"
        
        # Test selected voter
        controller._set_selected_voter(sample_voter_dto)
        selected = controller._get_selected_voter()
        assert selected["id"] == sample_voter_dto.id
        assert selected["fullName"] == sample_voter_dto.full_name
        
        # Test search results
        controller._set_search_results([sample_voter_dto])
        results = controller._get_search_results()
        assert len(results) == 1
        assert results[0]["id"] == sample_voter_dto.id
        
        # Test loading state
        controller._set_is_loading(True)
        assert controller._get_is_loading() is True
        
        # Test error message
        controller._set_error_message("Test error")
        assert controller._get_error_message() == "Test error"

    def test_signal_emissions(self, controller, qtbot):
        """Test that property changes emit the correct signals."""
        # Track signal emissions
        signals_emitted = []
        
        controller.searchQueryChanged.connect(lambda: signals_emitted.append("searchQuery"))
        controller.selectedVoterChanged.connect(lambda: signals_emitted.append("selectedVoter"))
        controller.searchResultsChanged.connect(lambda: signals_emitted.append("searchResults"))
        controller.isLoadingChanged.connect(lambda: signals_emitted.append("isLoading"))
        controller.errorMessageChanged.connect(lambda: signals_emitted.append("errorMessage"))
        
        # Change properties to trigger signals
        controller._set_search_query("test")
        controller._set_selected_voter(None)
        controller._set_search_results([])
        controller._set_is_loading(True)
        controller._set_error_message("error")
        
        # Process Qt events to ensure signals are emitted
        qtbot.wait(10)
        
        # Verify signals were emitted (at least some of them)
        assert len(signals_emitted) >= 3, f"Expected signals to be emitted, got: {signals_emitted}"
        assert "searchQuery" in signals_emitted, "searchQuery signal should be emitted"

    def test_error_handling_empty_search(self, controller):
        """Test error handling for empty search validation."""
        error_signals = []
        controller.operationFailed.connect(lambda msg: error_signals.append(msg))
        
        # Test empty search query validation (after Enter key)
        controller.setSearchQuery("")
        controller.refreshSearch()  # This should trigger error for empty query
        
        # Verify error was emitted
        assert len(error_signals) == 1
        assert "search term" in error_signals[0].lower()

    def test_search_timeout_warning(self, controller):
        """Test search timeout warning when search takes too long."""
        # Mock slow search by setting very low timeout threshold
        controller._search_timeout_threshold_ms = 1  # 1ms threshold
        
        error_signals = []
        controller.operationFailed.connect(lambda msg: error_signals.append(msg))
        
        # Set search query to trigger search
        controller._set_search_query("test")
        controller._perform_search()
        
        # Should emit timeout warning
        assert len(error_signals) >= 1
        timeout_error = any("too long" in msg.lower() for msg in error_signals)
        assert timeout_error, "Should emit timeout warning for slow search"

    def test_database_connection_error_handling(self, controller):
        """Test database connection error handling."""
        with patch('jcselect.controllers.voter_search_controller.get_session') as mock_get_session:
            mock_get_session.side_effect = ConnectionError("Database unavailable")
            
            error_signals = []
            controller.operationFailed.connect(lambda msg: error_signals.append(msg))
            
            # Attempt search with database error
            controller._set_search_query("test")
            controller._perform_search()
            
            # Should emit database connection error
            assert len(error_signals) == 1
            assert "database" in error_signals[0].lower() or "connection" in error_signals[0].lower()

    def test_vote_marking_conflict_error(self, controller, sample_voter_dto):
        """Test vote marking conflict error (voter already voted)."""
        # Set up voter as already voted
        sample_voter_dto.has_voted = True
        controller._set_selected_voter(sample_voter_dto)
        
        error_signals = []
        controller.operationFailed.connect(lambda msg: error_signals.append(msg))
        
        # Attempt to mark already voted voter
        controller.markVoterAsVoted(sample_voter_dto.id, str(uuid4()))
        
        # Should emit conflict error
        assert len(error_signals) == 1
        assert "already voted" in error_signals[0].lower()

    def test_focus_search_bar_signal(self, controller):
        """Test that focusSearchBar emits the correct signal."""
        focus_signals = []
        controller.searchBarFocusRequested.connect(lambda: focus_signals.append(True))
        
        # Call focusSearchBar
        controller.focusSearchBar()
        
        # Verify signal was emitted
        assert len(focus_signals) == 1

    def test_error_clearing_on_selection_change(self, controller, sample_voter_dto):
        """Test that errors are cleared when selection changes."""
        # Set an error
        controller._set_error_message("Test error")
        assert controller._error_message == "Test error"
        
        # Clear selection (should clear error)
        controller.clearSelection()
        assert controller._error_message == ""

    def test_performance_metrics_initialization(self, controller):
        """Test that performance metrics are properly initialized."""
        assert controller.lastSearchTimeMs == 0.0
        assert controller.lastMarkTimeMs == 0.0
        assert controller.avgSearchTimeMs == 0.0
        assert controller.avgMarkTimeMs == 0.0
        assert controller.totalSearches == 0
        assert controller.totalMarks == 0

    def test_search_performance_recording(self, controller):
        """Test that search performance is properly recorded."""
        # Mock the database to avoid actual query
        with patch('jcselect.controllers.voter_search_controller.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = []
            
            # Set a search query and perform search
            controller._set_search_query("test")
            controller._perform_search()
            
            # Verify performance metrics were recorded
            assert controller.lastSearchTimeMs > 0
            assert controller.totalSearches == 1
            assert controller.avgSearchTimeMs > 0

    def test_mark_performance_recording(self, controller, sample_voter_dto):
        """Test that mark performance is properly recorded."""
        # Mock the database operations
        with patch('jcselect.controllers.voter_search_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.voter_search_controller.mark_voted') as mock_mark_voted:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Create a mock updated voter
            mock_voter = Mock()
            mock_voter.voter_number = "12345"
            mock_voter.full_name = "Test Voter"
            mock_mark_voted.return_value = mock_voter
            
            controller._convert_voter_to_dto = Mock(return_value=sample_voter_dto)
            
            # Mark voter as voted
            controller.markVoterAsVoted(sample_voter_dto.id, str(uuid4()))
            
            # Verify performance metrics were recorded
            assert controller.lastMarkTimeMs > 0
            assert controller.totalMarks == 1
            assert controller.avgMarkTimeMs > 0

    def test_performance_metric_signal_emission(self, controller):
        """Test that performance metric changes emit signals."""
        signals_emitted = []
        controller.performanceMetricChanged.connect(lambda: signals_emitted.append(True))
        
        # Update performance metrics
        controller._set_last_search_time_ms(150.0)
        controller._set_last_mark_time_ms(250.0)
        
        # Verify signals were emitted
        assert len(signals_emitted) == 2

    def test_reset_performance_metrics(self, controller):
        """Test that performance metrics can be reset."""
        # Set some performance data
        controller._set_last_search_time_ms(100.0)
        controller._set_last_mark_time_ms(200.0)
        controller._total_searches = 5
        controller._total_marks = 3
        controller._avg_search_time_ms = 120.0
        controller._avg_mark_time_ms = 180.0
        
        # Reset metrics
        controller.resetPerformanceMetrics()
        
        # Verify all metrics are reset
        assert controller.lastSearchTimeMs == 0.0
        assert controller.lastMarkTimeMs == 0.0
        assert controller.totalSearches == 0
        assert controller.totalMarks == 0
        assert controller.avgSearchTimeMs == 0.0
        assert controller.avgMarkTimeMs == 0.0

    def test_performance_averaging(self, controller):
        """Test that performance averaging works correctly."""
        # Simulate multiple searches with known times
        controller._record_search_performance(100.0)
        assert controller.avgSearchTimeMs == 100.0
        assert controller.totalSearches == 1
        
        controller._record_search_performance(200.0)
        assert controller.avgSearchTimeMs == 150.0  # (100 + 200) / 2
        assert controller.totalSearches == 2
        
        controller._record_search_performance(300.0)
        assert controller.avgSearchTimeMs == 200.0  # (100 + 200 + 300) / 3
        assert controller.totalSearches == 3

    @patch('jcselect.controllers.voter_search_controller.soft_delete_voter')
    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_softDeleteVoter_success_emits_voterDeletedSuccessfully(
        self, mock_get_session, mock_soft_delete_voter, controller, sample_voter_dto
    ):
        """Test successful voter soft delete emits voterDeletedSuccessfully signal."""
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
        mock_soft_delete_voter.assert_called_once_with(
            UUID(voter_id), UUID(operator_id), mock_session
        )
        
        # Verify refreshSearch was called
        controller.refreshSearch.assert_called_once()

    @patch('jcselect.controllers.voter_search_controller.soft_delete_voter')
    @patch('jcselect.controllers.voter_search_controller.get_session')
    def test_softDeleteVoter_failure_emits_operationFailed(
        self, mock_get_session, mock_soft_delete_voter, controller, sample_voter_dto
    ):
        """Test failed voter soft delete emits operationFailed signal."""
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