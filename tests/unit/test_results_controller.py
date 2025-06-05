"""Unit tests for ResultsController."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jcselect.controllers.results_controller import ResultsController
from jcselect.models import Party, Pen, TallyLine, TallySession, User, Voter
from jcselect.models.enums import BallotType
from PySide6.QtCore import QDateTime
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QSignalSpy, QTest
from sqlmodel import Session
from sqlalchemy import text


@pytest.fixture
def setup_view(db_session: Session):
    """Create the v_results_aggregate view in the test database."""
    db_session.execute(text("""
        CREATE VIEW IF NOT EXISTS v_results_aggregate AS
        SELECT
            ts.pen_id,
            tl.party_id,
            tl.candidate_id,
            tl.ballot_type,
            SUM(CASE WHEN tl.deleted_at IS NULL THEN tl.vote_count ELSE 0 END) AS votes,
            COUNT(CASE WHEN tl.deleted_at IS NULL THEN tl.id ELSE NULL END) AS ballot_count,
            MAX(tl.updated_at) AS last_updated
        FROM tally_lines tl
        JOIN tally_sessions ts ON tl.tally_session_id = ts.id
        WHERE ts.deleted_at IS NULL
        GROUP BY ts.pen_id, tl.party_id, tl.candidate_id, tl.ballot_type
    """))
    db_session.commit()


@pytest.fixture
def results_controller(qapp):
    """Create a ResultsController instance for testing."""
    controller = ResultsController()
    return controller


@pytest.fixture
def sample_data(db_session: Session, setup_view):
    """Create sample data for testing."""
    # Create test pens
    pen1 = Pen(id=uuid.uuid4(), town_name="Town A", label="Pen 1")
    pen2 = Pen(id=uuid.uuid4(), town_name="Town B", label="Pen 2")
    
    # Create test parties
    party1 = Party(
        id=uuid.uuid4(),
        name="Party Alpha",
        short_code="PA",
        display_order=1,
        is_active=True
    )
    party2 = Party(
        id=uuid.uuid4(),
        name="Party Beta",
        short_code="PB",
        display_order=2,
        is_active=True
    )
    
    # Create test user
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        password_hash="hashed",
        full_name="Test User",
        role="operator",
        is_active=True
    )
    
    db_session.add_all([pen1, pen2, party1, party2, user])
    db_session.commit()
    
    # Create test voters
    voters = []
    for i in range(5):
        voter = Voter(
            id=uuid.uuid4(),
            pen_id=pen1.id,
            voter_number=f"V{i+1}",
            full_name=f"Test Voter {i+1}",
            has_voted=False
        )
        voters.append(voter)
        
    db_session.add_all(voters)
    db_session.commit()
    
    # Create tally sessions
    session1 = TallySession(
        id=uuid.uuid4(),
        pen_id=pen1.id,
        operator_id=user.id,
        session_name="Session 1",
        started_at=datetime.utcnow(),
        ballot_number=3
    )
    session2 = TallySession(
        id=uuid.uuid4(),
        pen_id=pen2.id,
        operator_id=user.id,
        session_name="Session 2",
        started_at=datetime.utcnow(),
        ballot_number=2
    )
    
    db_session.add_all([session1, session2])
    db_session.commit()
    
    # Create tally lines
    candidate1_id = uuid.uuid4()
    candidate2_id = uuid.uuid4()
    candidate3_id = uuid.uuid4()
    
    tallies = [
        TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session1.id,
            party_id=party1.id,
            candidate_id=candidate1_id,
            vote_count=100,
            ballot_type=BallotType.NORMAL
        ),
        TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session1.id,
            party_id=party2.id,
            candidate_id=candidate2_id,
            vote_count=75,
            ballot_type=BallotType.NORMAL
        ),
        TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session2.id,
            party_id=party1.id,
            candidate_id=candidate3_id,
            vote_count=50,
            ballot_type=BallotType.NORMAL
        ),
        # Add special ballot types
        TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session1.id,
            party_id=party1.id,
            candidate_id=None,
            vote_count=5,
            ballot_type=BallotType.WHITE
        ),
        TallyLine(
            id=uuid.uuid4(),
            tally_session_id=session1.id,
            party_id=party1.id,
            candidate_id=None,
            vote_count=2,
            ballot_type=BallotType.CANCEL
        )
    ]
    
    db_session.add_all(tallies)
    db_session.commit()
    
    return {
        "pens": [pen1, pen2],
        "parties": [party1, party2],
        "user": user,
        "voters": voters,
        "sessions": [session1, session2],
        "tallies": tallies,
        "candidates": [candidate1_id, candidate2_id, candidate3_id]
    }


class TestResultsController:
    """Test ResultsController basic functionality."""

    def test_initialization(self, results_controller):
        """Test controller initializes with default values."""
        # Check initial property values
        assert results_controller.partyTotals == []
        assert results_controller.candidateTotals == []
        assert results_controller.winners == []
        assert results_controller.selectedPenId == ""
        assert results_controller.showAllPens is True
        assert results_controller.selectedPartyId == ""
        assert results_controller.isSyncing is False
        assert results_controller.totalBallots == 0
        assert results_controller.completionPercent == 0.0
        assert isinstance(results_controller.lastUpdated, QDateTime)

    @patch('jcselect.controllers.results_controller.get_totals_by_party')
    @patch('jcselect.controllers.results_controller.get_totals_by_candidate')
    @patch('jcselect.controllers.results_controller.get_pen_voter_turnout')
    @patch('jcselect.controllers.results_controller.get_pen_completion_status')
    def test_refresh_data_populates_properties(
        self, 
        mock_completion, 
        mock_turnout, 
        mock_get_candidates, 
        mock_get_parties, 
        results_controller
    ):
        """Test that refreshData populates properties correctly."""
        # Mock return data
        mock_parties = [
            {"party_id": "123", "party_name": "Test Party", "total_votes": 100, "candidate_count": 2}
        ]
        mock_candidates = [
            {"candidate_id": "456", "candidate_name": "Test Candidate", "party_name": "Test Party", "total_votes": 50}
        ]
        
        mock_get_parties.return_value = mock_parties
        mock_get_candidates.return_value = mock_candidates
        mock_turnout.return_value = {"total_ballots": 50}
        mock_completion.return_value = True
        
        # Set up signal spy
        spy = QSignalSpy(results_controller.dataRefreshed)
        
        # Call refresh
        results_controller.refreshData()
        
        # Verify data was populated
        assert results_controller.partyTotals == mock_parties
        assert results_controller.candidateTotals == mock_candidates
        
        # Verify signal was emitted
        assert spy.count() == 1

    def test_pen_filter_changes_results(self, results_controller, sample_data):
        """Test that changing pen filter updates results."""
        pen_id = str(sample_data["pens"][0].id)
        
        # Set up signal spy
        spy = QSignalSpy(results_controller.penFilterChanged)
        
        # Change pen filter
        results_controller.setPenFilter(pen_id)
        
        # Verify filter was updated
        assert results_controller.selectedPenId == pen_id
        assert results_controller.showAllPens is False
        
        # Verify signal was emitted
        assert spy.count() == 1

    @patch('jcselect.controllers.results_controller.calculate_winners')
    def test_calculate_winners_ranking(self, mock_calculate_winners, results_controller, sample_data):
        """Test winner calculation and ranking."""
        # Mock return data
        mock_winners = [
            {"rank": 1, "candidate_name": "Winner 1", "total_votes": 100, "is_elected": True},
            {"rank": 2, "candidate_name": "Winner 2", "total_votes": 75, "is_elected": True},
            {"rank": 3, "candidate_name": "Winner 3", "total_votes": 50, "is_elected": True},
        ]
        mock_calculate_winners.return_value = mock_winners
        
        # Set up signal spy
        spy = QSignalSpy(results_controller.winnersCalculated)
        
        # Calculate winners
        results_controller.calculateWinners()
        
        # Verify signal was emitted
        assert spy.count() == 1
        
        # Verify winners property is populated
        winners = results_controller.winners
        assert isinstance(winners, list)
        assert winners == mock_winners
        
        # Check that winners are properly ranked (votes descending)
        if len(winners) > 1:
            for i in range(len(winners) - 1):
                assert winners[i]["total_votes"] >= winners[i + 1]["total_votes"]
                assert winners[i]["rank"] == i + 1

    @patch('jcselect.controllers.results_controller.get_session')
    def test_load_available_pens(self, mock_get_session, results_controller, sample_data, db_session):
        """Test loading available pens."""
        # Use the test database session
        mock_get_session.return_value.__enter__.return_value = db_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Set up signal spy
        spy = QSignalSpy(results_controller.pensLoaded)
        
        # Load pens
        results_controller.loadAvailablePens()
        
        # Verify signal was emitted
        assert spy.count() == 1
        
        # Verify pens were loaded
        pens = results_controller.availablePens
        assert isinstance(pens, list)
        assert len(pens) == 2  # From sample data
        
        # Check pen data structure
        if pens:
            pen = pens[0]
            assert "id" in pen
            assert "label" in pen
            assert "town_name" in pen
            assert "display_name" in pen

    @patch('jcselect.utils.export.export_results_csv')
    def test_csv_export_success(self, mock_export_csv, results_controller, tmp_path):
        """Test successful CSV export."""
        mock_export_csv.return_value = True
        
        # Set up signal spies
        success_spy = QSignalSpy(results_controller.exportCompleted)
        fail_spy = QSignalSpy(results_controller.exportFailed)
        
        # Trigger export
        results_controller.exportCsv()
        
        # Verify success signal emitted
        assert success_spy.count() == 1
        assert fail_spy.count() == 0
        
        # Verify export function was called
        mock_export_csv.assert_called_once()

    @patch('jcselect.utils.export.export_results_csv')
    def test_csv_export_failure(self, mock_export_csv, results_controller):
        """Test CSV export failure handling."""
        mock_export_csv.return_value = False
        
        # Set up signal spies
        success_spy = QSignalSpy(results_controller.exportCompleted)
        fail_spy = QSignalSpy(results_controller.exportFailed)
        
        # Trigger export
        results_controller.exportCsv()
        
        # Verify failure signal emitted
        assert success_spy.count() == 0
        assert fail_spy.count() == 1

    @patch('jcselect.utils.export.export_results_pdf')
    def test_pdf_export_success(self, mock_export_pdf, results_controller):
        """Test successful PDF export."""
        mock_export_pdf.return_value = True
        
        # Set up signal spies
        success_spy = QSignalSpy(results_controller.exportCompleted)
        fail_spy = QSignalSpy(results_controller.exportFailed)
        
        # Trigger export
        results_controller.exportPdf()
        
        # Verify success signal emitted
        assert success_spy.count() == 1
        assert fail_spy.count() == 0

    def test_party_filter_changes(self, results_controller):
        """Test party filter changes."""
        party_id = "test_party_123"
        
        # Set up signal spy
        spy = QSignalSpy(results_controller.partyFilterChanged)
        
        # Change party filter
        results_controller.setPartyFilter(party_id)
        
        # Verify filter was updated
        assert results_controller.selectedPartyId == party_id
        
        # Verify signal was emitted
        assert spy.count() == 1

    def test_error_handling(self, results_controller):
        """Test error handling in data operations."""
        # Set up signal spy for errors
        error_spy = QSignalSpy(results_controller.errorOccurred)
        
        # Mock database error by patching get_session to raise exception
        with patch('jcselect.controllers.results_controller.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")
            
            # Trigger refresh - should handle error gracefully
            results_controller.refreshData()
            
            # Verify error signal was emitted
            assert error_spy.count() == 1


class TestSyncIntegration:
    """Test fast-sync integration."""

    def test_sync_completed_triggers_refresh(self, results_controller):
        """Test that sync completion triggers auto-refresh."""
        # Set up signal spy
        refresh_spy = QSignalSpy(results_controller.dataRefreshed)
        
        # Mock the refresh timer to fire immediately for testing
        with patch.object(results_controller._refresh_timer, 'start') as mock_start:
            # Simulate sync completion
            results_controller._on_sync_completed()
            
            # Verify timer was started with correct delay
            mock_start.assert_called_with(250)
            
            # Verify syncing status was updated
            assert results_controller.isSyncing is False

    def test_tally_line_updated_triggers_refresh(self, results_controller):
        """Test that tally line updates trigger auto-refresh."""
        tally_line_id = "test_tally_123"
        
        # Mock the refresh timer
        with patch.object(results_controller._refresh_timer, 'start') as mock_start:
            # Simulate tally line update
            results_controller._on_tally_updated(tally_line_id)
            
            # Verify timer was started with correct delay
            mock_start.assert_called_with(250)
            
            # Verify syncing status was updated
            assert results_controller.isSyncing is True

    def test_sync_engine_connection(self, results_controller):
        """Test connection to sync engine signals."""
        # Create a fake sync engine
        fake_sync_engine = MagicMock()
        fake_sync_engine.syncCompleted = MagicMock()
        fake_sync_engine.tallyLineUpdated = MagicMock()
        
        # Mock get_sync_engine to return our fake engine
        with patch('jcselect.sync.engine.get_sync_engine') as mock_get_engine:
            mock_get_engine.return_value = fake_sync_engine
            
            # Create new controller to test connection
            test_controller = ResultsController()
            
            # Verify signals were connected
            fake_sync_engine.syncCompleted.connect.assert_called_once()
            fake_sync_engine.tallyLineUpdated.connect.assert_called_once()


class TestPropertyBinding:
    """Test QML property binding functionality."""

    def test_qml_property_access(self, results_controller):
        """Test that properties can be accessed via Qt property system."""        
        # Test that properties are accessible
        assert results_controller.property("partyTotals") == []
        assert results_controller.property("candidateTotals") == []
        assert results_controller.property("winners") == []
        assert results_controller.property("selectedPenId") == ""
        assert results_controller.property("showAllPens") is True
        
        # Test property setting
        results_controller.setProperty("selectedPenId", "test_pen_123")
        assert results_controller.selectedPenId == "test_pen_123"

    def test_signal_emission(self, results_controller):
        """Test that all signals can be emitted correctly."""
        # Test each signal
        signals_to_test = [
            results_controller.dataRefreshed,
            results_controller.winnersCalculated,
            results_controller.pensLoaded,
            results_controller.penFilterChanged,
            results_controller.partyFilterChanged,
            results_controller.syncStatusChanged,
            results_controller.exportCompleted,
            results_controller.exportFailed,
            results_controller.errorOccurred
        ]
        
        for signal in signals_to_test:
            spy = QSignalSpy(signal)
            
            # Emit signal with appropriate arguments
            if signal in [results_controller.exportCompleted, results_controller.exportFailed, results_controller.errorOccurred]:
                signal.emit("test_message")
            else:
                signal.emit()
            
            assert spy.count() == 1 