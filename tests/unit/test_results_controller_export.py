"""Tests for ResultsController export functionality."""

import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QSignalSpy

from src.jcselect.controllers.results_controller import ResultsController


class TestResultsControllerExport:
    """Test suite for ResultsController export methods."""

    @pytest.fixture
    def results_controller(self):
        """Create a ResultsController instance for testing."""
        # Mock the dependencies to avoid database calls
        with patch.object(ResultsController, '_connect_sync_signals'), \
             patch.object(ResultsController, 'loadAvailablePens'), \
             patch.object(ResultsController, 'refreshData'):
            controller = ResultsController()
            
            # Stop any automatic timers to avoid interference
            if hasattr(controller, '_new_results_timer') and controller._new_results_timer:
                controller._new_results_timer.stop()
            if hasattr(controller, '_refresh_timer') and controller._refresh_timer:
                controller._refresh_timer.stop()
                
            # Set up sample data
            controller._party_totals = [
                {"party_name": "حزب التقدم", "total_votes": 1250, "candidate_count": 5},
                {"party_name": "حزب الوحدة", "total_votes": 980, "candidate_count": 4}
            ]
            controller._candidate_totals = [
                {"candidate_name": "أحمد علي", "party_name": "حزب التقدم", "total_votes": 450, "rank": 1},
                {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 380, "rank": 2}
            ]
            controller._winners = [
                {"candidate_name": "أحمد علي", "party_name": "حزب التقدم", "total_votes": 450, "rank": 1, "is_elected": True}
            ]
            
            return controller

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file path for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            yield tmp.name
        # Cleanup
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def mock_qfiledialog(self):
        """Mock QFileDialog for testing."""
        with patch('PySide6.QtWidgets.QFileDialog') as mock_dialog:
            yield mock_dialog

    @pytest.fixture 
    def mock_qapplication(self):
        """Mock QApplication for testing."""
        with patch('PySide6.QtWidgets.QApplication') as mock_app:
            mock_instance = Mock()
            mock_instance.activeWindow.return_value = None
            mock_app.instance.return_value = mock_instance
            yield mock_app

    def test_export_csv_success(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test successful CSV export."""
        # Setup mocks
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module to replace the entire jcselect.utils.export module
        mock_export_module = MagicMock()
        mock_export_module.export_party_totals_csv.return_value = True
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        # Patch the module import inside the exportCsv method
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportCsv()
            
            # Verify file dialog was called
            mock_qfiledialog.getSaveFileName.assert_called_once()
            
            # Verify export function was called
            mock_export_module.export_party_totals_csv.assert_called_once_with(
                results_controller._party_totals, temp_file
            )
            
            # Verify signals
            assert export_completed_spy.count() == 1
            assert export_failed_spy.count() == 0
            # Access signal arguments using QSignalSpy methods
            signal_data = export_completed_spy.at(0)
            assert len(signal_data) > 0
            assert signal_data[0] == temp_file

    def test_export_csv_user_cancelled(self, results_controller, mock_qfiledialog, mock_qapplication):
        """Test CSV export when user cancels file dialog."""
        # User cancels dialog
        mock_qfiledialog.getSaveFileName.return_value = ("", "")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportCsv()
            
            # No signals should be emitted
            assert export_completed_spy.count() == 0
            assert export_failed_spy.count() == 0

    def test_export_csv_invalid_path(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test CSV export with invalid path."""
        # Setup mocks
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = False
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportCsv()
            
            # Should emit export failed
            assert export_completed_spy.count() == 0
            assert export_failed_spy.count() == 1
            signal_data = export_failed_spy.at(0)
            assert "Cannot write to selected location" in signal_data[0]

    def test_export_csv_no_data(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test CSV export with no data available."""
        # Clear data
        results_controller._party_totals = []
        results_controller._candidate_totals = []
        
        # Setup mocks
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportCsv()
            
            # Should emit export failed
            assert export_completed_spy.count() == 0
            assert export_failed_spy.count() == 1
            # Use QSignalSpy methods to access signal arguments
            signal_data = export_failed_spy.at(0)
            assert "No data available for export" in signal_data[0]

    def test_export_csv_candidate_fallback(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test CSV export falls back to candidate data when no party data."""
        # Clear party data but keep candidate data
        results_controller._party_totals = []
        
        # Setup mocks
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_candidate_results_csv.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            
            # Call export
            results_controller.exportCsv()
            
            # Should use candidate export
            mock_export_module.export_candidate_results_csv.assert_called_once_with(
                results_controller._candidate_totals, temp_file
            )
            assert export_completed_spy.count() == 1

    def test_export_csv_exception_handling(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test CSV export exception handling."""
        # Setup mocks
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_party_totals_csv.side_effect = Exception("Export error")
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportCsv()
            
            # Should emit export failed with error message
            assert export_failed_spy.count() == 1
            # Use QSignalSpy methods to access signal arguments
            signal_data = export_failed_spy.at(0)
            assert "CSV export failed: Export error" in signal_data[0]

    def test_export_pdf_success(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test successful PDF export."""
        pdf_file = temp_file.replace('.csv', '.pdf')
        
        # Setup mocks
        mock_qfiledialog.getSaveFileName.return_value = (pdf_file, "PDF Files (*.pdf)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_results_pdf.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.pdf"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportPdf()
            
            # Verify export function was called with correct data
            mock_export_module.export_results_pdf.assert_called_once()
            call_args = mock_export_module.export_results_pdf.call_args[0]
            export_data = call_args[0]
            
            assert export_data["party_totals"] == results_controller._party_totals
            assert export_data["candidate_totals"] == results_controller._candidate_totals
            assert export_data["winners"] == results_controller._winners
            assert "metadata" in export_data
            
            # Verify signals
            assert export_completed_spy.count() == 1
            assert export_failed_spy.count() == 0
            # Use QSignalSpy methods to access signal arguments
            signal_data = export_completed_spy.at(0)
            assert signal_data[0] == pdf_file

    def test_export_pdf_no_data(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test PDF export with no data available."""
        # Clear all data
        results_controller._party_totals = []
        results_controller._candidate_totals = []
        results_controller._winners = []
        
        pdf_file = temp_file.replace('.csv', '.pdf')
        mock_qfiledialog.getSaveFileName.return_value = (pdf_file, "PDF Files (*.pdf)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.pdf"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_failed_spy = QSignalSpy(results_controller.exportFailed)
            
            # Call export
            results_controller.exportPdf()
            
            # Should emit export failed
            assert export_failed_spy.count() == 1
            # Use QSignalSpy methods to access signal arguments
            signal_data = export_failed_spy.at(0)
            assert "No data available for export" in signal_data[0]

    def test_export_pdf_metadata_content(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test that PDF export includes correct metadata."""
        # Set controller state
        results_controller._selected_pen_id = "pen_123"
        results_controller._show_all_pens = False
        results_controller._total_ballots = 1500
        results_controller._completion_percent = 75.5
        
        pdf_file = temp_file.replace('.csv', '.pdf')
        mock_qfiledialog.getSaveFileName.return_value = (pdf_file, "PDF Files (*.pdf)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_results_pdf.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.pdf"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Call export
            results_controller.exportPdf()
            
            # Verify metadata content
            call_args = mock_export_module.export_results_pdf.call_args[0]
            export_data = call_args[0]
            metadata = export_data["metadata"]
            
            assert metadata["pen_filter"] == "pen_123"
            assert metadata["total_ballots"] == 1500
            assert metadata["completion_percent"] == 75.5
            assert "exported_at" in metadata

    def test_export_pdf_all_pens_filter(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test PDF export with all pens filter."""
        # Set to show all pens
        results_controller._show_all_pens = True
        
        pdf_file = temp_file.replace('.csv', '.pdf')
        mock_qfiledialog.getSaveFileName.return_value = (pdf_file, "PDF Files (*.pdf)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_results_pdf.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.pdf"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Call export
            results_controller.exportPdf()
            
            # Verify metadata shows "all"
            call_args = mock_export_module.export_results_pdf.call_args[0]
            export_data = call_args[0]
            metadata = export_data["metadata"]
            
            assert metadata["pen_filter"] == "all"

    def test_export_signal_timing(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test that export signals are emitted within reasonable time."""
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_party_totals_csv.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            
            import time
            start_time = time.time()
            
            # Call export
            results_controller.exportCsv()
            
            end_time = time.time()
            
            # Should complete quickly (under 2 seconds as per acceptance criteria)
            assert (end_time - start_time) < 2.0
            assert export_completed_spy.count() == 1

    def test_export_filename_generation(self, results_controller, mock_qfiledialog, mock_qapplication):
        """Test that export generates appropriate default filenames."""
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.get_export_filename.return_value = "results_party_totals_test.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Test CSV filename generation
            results_controller.exportCsv()
            
            csv_call = mock_qfiledialog.getSaveFileName.call_args
            assert "results_party_totals_test.csv" in csv_call[0][2]  # Default filename
            assert "CSV Files (*.csv)" in csv_call[0][3]  # File filter
            
            # Reset mock
            mock_qfiledialog.reset_mock()
            mock_export_module.get_export_filename.return_value = "results_report_test.pdf"
            
            # Test PDF filename generation  
            results_controller.exportPdf()
            
            pdf_call = mock_qfiledialog.getSaveFileName.call_args
            assert "results_report_test.pdf" in pdf_call[0][2]  # Default filename
            assert "PDF Files (*.pdf)" in pdf_call[0][3]  # File filter

    def test_export_concurrent_calls(self, results_controller, temp_file, mock_qfiledialog, mock_qapplication):
        """Test that concurrent export calls are handled properly."""
        mock_qfiledialog.getSaveFileName.return_value = (temp_file, "CSV Files (*.csv)")
        
        # Create a mock module
        mock_export_module = MagicMock()
        mock_export_module.validate_export_path.return_value = True
        mock_export_module.export_party_totals_csv.return_value = True
        mock_export_module.get_export_filename.return_value = "test_filename.csv"
        
        with patch.dict('sys.modules', {'jcselect.utils.export': mock_export_module}):
            # Set up signal spy
            export_completed_spy = QSignalSpy(results_controller.exportCompleted)
            
            # Call export multiple times quickly
            results_controller.exportCsv()
            results_controller.exportCsv()
            results_controller.exportCsv()
            
            # Should handle all calls without issues
            assert export_completed_spy.count() == 3
            assert mock_export_module.export_party_totals_csv.call_count == 3

    def test_export_method_signatures(self, results_controller):
        """Test that export methods have correct signatures and are callable."""
        # Test that methods exist and are callable
        assert hasattr(results_controller, 'exportCsv')
        assert hasattr(results_controller, 'exportPdf')
        assert callable(results_controller.exportCsv)
        assert callable(results_controller.exportPdf)
        
        # Test that they are Qt slots
        assert hasattr(results_controller.exportCsv, '__func__')
        assert hasattr(results_controller.exportPdf, '__func__')

    def test_export_signals_exist(self, results_controller):
        """Test that required export signals exist."""
        # Test that signals exist
        assert hasattr(results_controller, 'exportCompleted')
        assert hasattr(results_controller, 'exportFailed')
        
        # Test that they are Qt signals (instances when attached to object)
        assert "Signal" in str(type(results_controller.exportCompleted))
        assert "Signal" in str(type(results_controller.exportFailed)) 