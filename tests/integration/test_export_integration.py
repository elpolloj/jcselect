"""Integration tests for export functionality with sample data."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
import pandas as pd

from src.jcselect.utils.export import (
    export_results_csv,
    export_results_pdf,
    generate_summary_report_pdf
)
from src.jcselect.controllers.results_controller import ResultsController


class TestExportIntegration:
    """Integration tests for export functionality."""

    @pytest.fixture
    def sample_results_data(self):
        """Sample results data similar to real election results."""
        return {
            "party_totals": [
                {
                    "party_id": "party_001",
                    "party_name": "حزب التقدم والعدالة الاجتماعية",
                    "total_votes": 12500,
                    "candidate_count": 8,
                    "pen_breakdown": {
                        "pen_001": 4500,
                        "pen_002": 3200,
                        "pen_003": 4800
                    }
                },
                {
                    "party_id": "party_002", 
                    "party_name": "الحزب الوطني الديمقراطي",
                    "total_votes": 9800,
                    "candidate_count": 6,
                    "pen_breakdown": {
                        "pen_001": 3100,
                        "pen_002": 3300,
                        "pen_003": 3400
                    }
                },
                {
                    "party_id": "party_003",
                    "party_name": "تيار المستقبل اللبناني",
                    "total_votes": 7200,
                    "candidate_count": 5,
                    "pen_breakdown": {
                        "pen_001": 2400,
                        "pen_002": 2200,
                        "pen_003": 2600
                    }
                }
            ],
            "candidate_totals": [
                {
                    "candidate_id": "cand_001",
                    "candidate_name": "أحمد محمد علي الخوري",
                    "party_id": "party_001",
                    "party_name": "حزب التقدم والعدالة الاجتماعية",
                    "total_votes": 4200,
                    "rank": 1,
                    "pen_breakdown": {
                        "pen_001": 1500,
                        "pen_002": 1200,
                        "pen_003": 1500
                    }
                },
                {
                    "candidate_id": "cand_002",
                    "candidate_name": "فاطمة حسن محمود السيد",
                    "party_id": "party_001",
                    "party_name": "حزب التقدم والعدالة الاجتماعية",
                    "total_votes": 3800,
                    "rank": 2,
                    "pen_breakdown": {
                        "pen_001": 1400,
                        "pen_002": 1100,
                        "pen_003": 1300
                    }
                },
                {
                    "candidate_id": "cand_003",
                    "candidate_name": "خالد عبد الرحمن زكريا",
                    "party_id": "party_002",
                    "party_name": "الحزب الوطني الديمقراطي",
                    "total_votes": 3500,
                    "rank": 3,
                    "pen_breakdown": {
                        "pen_001": 1200,
                        "pen_002": 1150,
                        "pen_003": 1150
                    }
                },
                {
                    "candidate_id": "cand_004",
                    "candidate_name": "مريم يوسف أنطون البدوي",
                    "party_id": "party_002",
                    "party_name": "الحزب الوطني الديمقراطي", 
                    "total_votes": 3200,
                    "rank": 4,
                    "pen_breakdown": {
                        "pen_001": 1000,
                        "pen_002": 1100,
                        "pen_003": 1100
                    }
                },
                {
                    "candidate_id": "cand_005",
                    "candidate_name": "سمير جورج فرنسيس حداد",
                    "party_id": "party_003",
                    "party_name": "تيار المستقبل اللبناني",
                    "total_votes": 2900,
                    "rank": 5,
                    "pen_breakdown": {
                        "pen_001": 980,
                        "pen_002": 960,
                        "pen_003": 960
                    }
                }
            ],
            "winners": [
                {
                    "candidate_id": "cand_001",
                    "candidate_name": "أحمد محمد علي الخوري",
                    "party_name": "حزب التقدم والعدالة الاجتماعية",
                    "total_votes": 4200,
                    "rank": 1,
                    "is_elected": True
                },
                {
                    "candidate_id": "cand_002",
                    "candidate_name": "فاطمة حسن محمود السيد",
                    "party_name": "حزب التقدم والعدالة الاجتماعية",
                    "total_votes": 3800,
                    "rank": 2,
                    "is_elected": True
                },
                {
                    "candidate_id": "cand_003",
                    "candidate_name": "خالد عبد الرحمن زكريا",
                    "party_name": "الحزب الوطني الديمقراطي",
                    "total_votes": 3500,
                    "rank": 3,
                    "is_elected": True
                }
            ],
            "metadata": {
                "exported_at": "2024-01-15 14:30:00",
                "pen_filter": "all",
                "municipality": "بيروت - الأشرفية",
                "total_ballots": 29500,
                "completion_percent": 92.5,
                "voter_turnout": {
                    "registered_voters": 31000,
                    "ballots_cast": 29500,
                    "turnout_percentage": 95.2
                }
            }
        }

    @pytest.fixture
    def temp_export_dir(self):
        """Create temporary directory for export tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_complete_csv_export_workflow(self, sample_results_data, temp_export_dir):
        """Test complete CSV export workflow with realistic data."""
        csv_file = os.path.join(temp_export_dir, "complete_results.csv")
        
        # Export data
        result = export_results_csv(sample_results_data, csv_file)
        assert result is True
        assert os.path.exists(csv_file)
        
        # Verify file content
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check metadata section (only fields that are actually exported)
        assert "JCSELECT Results Export" in content
        assert "29500" in content  # total_ballots
        assert "92.5%" in content  # completion_percent
        
        # Check party totals section
        assert "PARTY TOTALS" in content
        assert "حزب التقدم والعدالة الاجتماعية" in content
        assert "12500" in content  # party votes
        
        # Check candidate totals section
        assert "CANDIDATE TOTALS" in content
        assert "أحمد محمد علي الخوري" in content
        assert "4200" in content  # candidate votes
        
        # Check winners section
        assert "WINNERS" in content
        assert "فاطمة حسن محمود السيد" in content
        
        # Verify UTF-8 encoding preserved Arabic text
        lines = content.split('\n')
        arabic_found = any('حزب' in line for line in lines)
        assert arabic_found, "Arabic text not preserved in CSV export"

    def test_complete_pdf_export_workflow(self, sample_results_data, temp_export_dir):
        """Test complete PDF export workflow with realistic data."""
        pdf_file = os.path.join(temp_export_dir, "complete_results.pdf")
        
        # Export data
        result = export_results_pdf(sample_results_data, pdf_file)
        assert result is True
        assert os.path.exists(pdf_file)
        
        # Verify file is valid PDF
        with open(pdf_file, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF', "Invalid PDF header"
            
        # Check file size is reasonable (should contain substantial content)
        file_size = os.path.getsize(pdf_file)
        assert file_size > 1000, f"PDF file too small: {file_size} bytes"
        assert file_size < 500000, f"PDF file too large: {file_size} bytes"

    def test_large_dataset_export_performance(self, temp_export_dir):
        """Test export performance with large dataset."""
        import time
        
        # Generate large dataset (simulating 500 candidates across 50 parties)
        large_dataset = {
            "party_totals": [],
            "candidate_totals": [],
            "winners": [],
            "metadata": {
                "exported_at": "2024-01-15 14:30:00",
                "pen_filter": "all",
                "total_ballots": 150000,
                "completion_percent": 95.0
            }
        }
        
        # Generate parties
        for i in range(50):
            party = {
                "party_id": f"party_{i:03d}",
                "party_name": f"الحزب رقم {i+1}",
                "total_votes": 3000 + (i * 10),
                "candidate_count": 10
            }
            large_dataset["party_totals"].append(party)
            
        # Generate candidates
        for i in range(500):
            candidate = {
                "candidate_id": f"cand_{i:03d}",
                "candidate_name": f"المرشح الكريم {i+1}",
                "party_id": f"party_{i//10:03d}",
                "party_name": f"الحزب رقم {(i//10)+1}",
                "total_votes": 300 + (i * 2),
                "rank": i + 1
            }
            large_dataset["candidate_totals"].append(candidate)
            
        # Generate top 50 winners
        for i in range(50):
            winner = {
                "candidate_id": f"cand_{i:03d}",
                "candidate_name": f"المرشح الكريم {i+1}",
                "party_name": f"الحزب رقم {(i//10)+1}",
                "total_votes": 1000 - (i * 5),
                "rank": i + 1,
                "is_elected": i < 25  # Top 25 are elected
            }
            large_dataset["winners"].append(winner)
        
        # Test CSV export performance
        csv_file = os.path.join(temp_export_dir, "large_dataset.csv")
        csv_start = time.time()
        csv_result = export_results_csv(large_dataset, csv_file)
        csv_duration = time.time() - csv_start
        
        assert csv_result is True
        assert csv_duration < 5.0, f"CSV export too slow: {csv_duration:.2f}s"
        
        # Test PDF export performance
        pdf_file = os.path.join(temp_export_dir, "large_dataset.pdf")
        pdf_start = time.time()
        pdf_result = export_results_pdf(large_dataset, pdf_file)
        pdf_duration = time.time() - pdf_start
        
        assert pdf_result is True
        assert pdf_duration < 10.0, f"PDF export too slow: {pdf_duration:.2f}s"
        
        # Verify large files are reasonable size (adjusted thresholds)
        csv_size = os.path.getsize(csv_file)
        pdf_size = os.path.getsize(pdf_file)
        
        assert csv_size > 30000, f"Large CSV file unexpectedly small: {csv_size} bytes"
        assert pdf_size > 10000, f"Large PDF file unexpectedly small: {pdf_size} bytes"

    def test_results_controller_export_integration(self, sample_results_data, temp_export_dir):
        """Test results controller export functionality with real data flow."""
        # Mock the file dialog to return our test path
        csv_file = os.path.join(temp_export_dir, "controller_export.csv")
        pdf_file = os.path.join(temp_export_dir, "controller_export.pdf")
        
        with patch.object(ResultsController, '_connect_sync_signals'), \
             patch.object(ResultsController, 'loadAvailablePens'), \
             patch.object(ResultsController, 'refreshData'):
            
            controller = ResultsController()
            
            # Stop timers
            if hasattr(controller, '_new_results_timer') and controller._new_results_timer:
                controller._new_results_timer.stop()
            if hasattr(controller, '_refresh_timer') and controller._refresh_timer:
                controller._refresh_timer.stop()
                
            # Set up realistic data
            controller._party_totals = sample_results_data["party_totals"]
            controller._candidate_totals = sample_results_data["candidate_totals"]
            controller._winners = sample_results_data["winners"]
            controller._total_ballots = sample_results_data["metadata"]["total_ballots"]
            controller._completion_percent = sample_results_data["metadata"]["completion_percent"]
            
            # Mock file dialogs and QApplication
            mock_qapplication = Mock()
            mock_qapplication.instance.return_value.activeWindow.return_value = None
            
            # Test CSV export
            with patch('PySide6.QtWidgets.QFileDialog') as mock_dialog, \
                 patch('PySide6.QtWidgets.QApplication', mock_qapplication), \
                 patch.dict('sys.modules', {'jcselect.utils.export': Mock(
                     export_party_totals_csv=Mock(return_value=True),
                     validate_export_path=Mock(return_value=True),
                     get_export_filename=Mock(return_value="test.csv")
                 )}):
                
                mock_dialog.getSaveFileName.return_value = (csv_file, "CSV Files (*.csv)")
                
                # Track signals
                export_completed_calls = []
                export_failed_calls = []
                
                controller.exportCompleted.connect(lambda path: export_completed_calls.append(path))
                controller.exportFailed.connect(lambda error: export_failed_calls.append(error))
                
                # Trigger export
                controller.exportCsv()
                
                # Should complete successfully
                assert len(export_completed_calls) == 1
                assert len(export_failed_calls) == 0
                assert export_completed_calls[0] == csv_file

    def test_export_file_naming_convention(self, sample_results_data, temp_export_dir):
        """Test that exported files follow proper naming conventions."""
        from src.jcselect.utils.export import get_export_filename
        
        # Test various export types
        csv_filename = get_export_filename("party_totals", "csv", "results")
        pdf_filename = get_export_filename("report", "pdf", "election")
        
        # Verify format: base_type_timestamp.extension
        assert csv_filename.startswith("results_party_totals_")
        assert csv_filename.endswith(".csv")
        assert len(csv_filename.split("_")) >= 4
        
        assert pdf_filename.startswith("election_report_")
        assert pdf_filename.endswith(".pdf")
        
        # Test actual file creation with proper names
        csv_path = os.path.join(temp_export_dir, csv_filename)
        export_results_csv(sample_results_data, csv_path)
        assert os.path.exists(csv_path)
        
        pdf_path = os.path.join(temp_export_dir, pdf_filename)
        export_results_pdf(sample_results_data, pdf_path)
        assert os.path.exists(pdf_path)

    def test_export_error_recovery(self, sample_results_data, temp_export_dir):
        """Test export error handling and recovery."""
        # Test with malformed data that should cause an actual error
        malformed_data = {
            "party_totals": "not a list",  # Invalid type
            "candidate_totals": [],
            "winners": []
        }
        
        valid_file = os.path.join(temp_export_dir, "error_test.pdf")
        with pytest.raises(Exception):
            export_results_pdf(malformed_data, valid_file)

    def test_unicode_filename_handling(self, sample_results_data, temp_export_dir):
        """Test export with Unicode filenames (Arabic characters)."""
        # Use Arabic characters in filename
        arabic_filename = "نتائج_الانتخابات_2024.csv"
        unicode_path = os.path.join(temp_export_dir, arabic_filename)
        
        try:
            result = export_results_csv(sample_results_data, unicode_path)
            assert result is True
            assert os.path.exists(unicode_path)
            
            # Verify content is readable
            with open(unicode_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "حزب التقدم" in content
                
        except (UnicodeError, OSError):
            # Some Windows systems don't support Unicode filenames
            pytest.skip("Filesystem doesn't support Unicode filenames")

    def test_concurrent_export_operations(self, sample_results_data, temp_export_dir):
        """Test that concurrent export operations don't interfere."""
        import threading
        import time
        
        results = []
        errors = []
        
        def export_worker(worker_id):
            try:
                csv_file = os.path.join(temp_export_dir, f"concurrent_{worker_id}.csv")
                pdf_file = os.path.join(temp_export_dir, f"concurrent_{worker_id}.pdf")
                
                # Small random delay to encourage race conditions
                time.sleep(0.01 * worker_id)
                
                csv_result = export_results_csv(sample_results_data, csv_file)
                pdf_result = export_results_pdf(sample_results_data, pdf_file)
                
                results.append((worker_id, csv_result, pdf_result))
                
                # Verify files exist and have content
                assert os.path.exists(csv_file)
                assert os.path.exists(pdf_file)
                assert os.path.getsize(csv_file) > 0
                assert os.path.getsize(pdf_file) > 0
                
            except Exception as e:
                errors.append((worker_id, e))
        
        # Run 5 concurrent export operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=export_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        assert all(csv_result and pdf_result for _, csv_result, pdf_result in results)

    def test_export_data_integrity(self, sample_results_data, temp_export_dir):
        """Test that exported data maintains integrity and accuracy."""
        csv_file = os.path.join(temp_export_dir, "integrity_test.csv")
        
        # Export data
        export_results_csv(sample_results_data, csv_file)
        
        # Read back and verify critical data points
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Find and verify specific data points
        party_lines = [line for line in lines if "حزب التقدم والعدالة الاجتماعية" in line]
        assert len(party_lines) > 0, "Main party not found in export"
        
        candidate_lines = [line for line in lines if "أحمد محمد علي الخوري" in line]
        assert len(candidate_lines) > 0, "Main candidate not found in export"
        
        # Verify vote counts are preserved
        total_votes_line = [line for line in lines if "29500" in line]  # total_ballots
        assert len(total_votes_line) > 0, "Total votes not found in export"
        
        # Verify completion percentage is preserved
        completion_line = [line for line in lines if "92.5%" in line]
        assert len(completion_line) > 0, "Completion percentage not found in export"

    @pytest.mark.skipif(not hasattr(__builtins__, '__import__'), reason="psutil not available")
    def test_export_memory_efficiency(self, temp_export_dir):
        """Test that export functions handle large datasets without excessive memory usage."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")
            
        import gc
        
        # Get baseline memory usage
        process = psutil.Process()
        baseline_memory = process.memory_info().rss
        
        # Create large dataset (smaller for CI environments)
        large_dataset = {
            "party_totals": [
                {
                    "party_id": f"party_{i}",
                    "party_name": f"الحزب الكبير رقم {i}",
                    "total_votes": 5000 + i,
                    "candidate_count": 20
                } for i in range(100)  # Reduced from 1000
            ],
            "candidate_totals": [
                {
                    "candidate_id": f"cand_{i}",
                    "candidate_name": f"المرشح المحترم جداً {i}",
                    "party_id": f"party_{i//20}",
                    "party_name": f"الحزب الكبير رقم {i//20}",
                    "total_votes": 1000 + i,
                    "rank": i + 1
                } for i in range(2000)  # Reduced from 20000
            ],
            "winners": [],
            "metadata": {
                "exported_at": "2024-01-15 14:30:00",
                "pen_filter": "all",
                "total_ballots": 500000,
                "completion_percent": 98.0
            }
        }
        
        # Export using CSV (more memory efficient)
        csv_file = os.path.join(temp_export_dir, "memory_test.csv")
        export_results_csv(large_dataset, csv_file)
        
        # Check memory usage didn't spike excessively
        current_memory = process.memory_info().rss
        memory_increase = current_memory - baseline_memory
        
        # Memory increase should be reasonable (less than 50MB for this smaller dataset)
        assert memory_increase < 50 * 1024 * 1024, f"Memory usage increased by {memory_increase / 1024 / 1024:.1f}MB"
        
        # Cleanup
        del large_dataset
        gc.collect()
        
        # Verify file was created and has reasonable size
        assert os.path.exists(csv_file)
        file_size = os.path.getsize(csv_file)
        assert file_size > 100000, "Large dataset file unexpectedly small"  # Should be > 100KB 