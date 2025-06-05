"""Tests for export utilities."""

import csv
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any

import pytest
import pandas as pd

from src.jcselect.utils.export import (
    export_party_totals_csv,
    export_candidate_results_csv,
    export_results_pdf,
    get_export_filename,
    validate_export_path,
    format_arabic_text
)


class TestExportUtils:
    """Test suite for export utility functions."""

    @pytest.fixture
    def sample_party_totals(self) -> List[Dict[str, Any]]:
        """Sample party totals data for testing."""
        return [
            {
                "party_id": "party_1",
                "party_name": "حزب التقدم",
                "total_votes": 1250,
                "candidate_count": 5
            },
            {
                "party_id": "party_2", 
                "party_name": "حزب الوحدة الوطنية",
                "total_votes": 980,
                "candidate_count": 4
            },
            {
                "party_id": "party_3",
                "party_name": "التيار الديمقراطي",
                "total_votes": 750,
                "candidate_count": 3
            }
        ]

    @pytest.fixture
    def sample_candidate_totals(self) -> List[Dict[str, Any]]:
        """Sample candidate totals data for testing."""
        return [
            {
                "candidate_id": "cand_1",
                "candidate_name": "أحمد محمد علي",
                "party_id": "party_1",
                "party_name": "حزب التقدم",
                "total_votes": 450,
                "rank": 1
            },
            {
                "candidate_id": "cand_2",
                "candidate_name": "فاطمة حسن محمود",
                "party_id": "party_1", 
                "party_name": "حزب التقدم",
                "total_votes": 380,
                "rank": 2
            },
            {
                "candidate_id": "cand_3",
                "candidate_name": "خالد عبد الرحمن",
                "party_id": "party_2",
                "party_name": "حزب الوحدة الوطنية",
                "total_votes": 320,
                "rank": 3
            }
        ]

    @pytest.fixture
    def sample_results_data(self, sample_party_totals, sample_candidate_totals) -> Dict[str, Any]:
        """Complete results data for PDF testing."""
        return {
            "party_totals": sample_party_totals,
            "candidate_totals": sample_candidate_totals,
            "winners": [
                {
                    "candidate_id": "cand_1",
                    "candidate_name": "أحمد محمد علي",
                    "party_name": "حزب التقدم",
                    "total_votes": 450,
                    "rank": 1,
                    "is_elected": True
                },
                {
                    "candidate_id": "cand_2", 
                    "candidate_name": "فاطمة حسن محمود",
                    "party_name": "حزب التقدم",
                    "total_votes": 380,
                    "rank": 2,
                    "is_elected": True
                }
            ],
            "metadata": {
                "exported_at": "2024-01-15 14:30:00",
                "pen_filter": "all",
                "total_ballots": 2980,
                "completion_percent": 85.5
            }
        }

    @pytest.fixture
    def temp_file(self) -> str:
        """Create a temporary file path for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            yield tmp.name
        # Cleanup
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass

    def test_export_party_totals_csv_success(self, sample_party_totals, temp_file):
        """Test successful party totals CSV export."""
        # Export the data
        result = export_party_totals_csv(sample_party_totals, temp_file)
        
        assert result is True
        assert os.path.exists(temp_file)
        
        # Read back and verify content
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        
        # Check required columns exist
        assert 'party_name' in df.columns
        assert 'total_votes' in df.columns
        assert 'export_timestamp' in df.columns
        assert 'export_type' in df.columns
        
        # Check data integrity
        assert len(df) == len(sample_party_totals)
        assert df['export_type'].iloc[0] == 'party_totals'
        
        # Check specific values
        assert df['party_name'].iloc[0] == "حزب التقدم"
        assert df['total_votes'].iloc[0] == 1250

    def test_export_party_totals_csv_round_trip(self, sample_party_totals, temp_file):
        """Test CSV export and import round-trip preserves data."""
        # Export
        export_party_totals_csv(sample_party_totals, temp_file)
        
        # Import and verify
        with open(temp_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        # Check all original data is preserved
        assert len(rows) == len(sample_party_totals)
        
        for i, original in enumerate(sample_party_totals):
            row = rows[i]
            assert row['party_name'] == original['party_name']
            assert int(row['total_votes']) == original['total_votes']
            if 'candidate_count' in original:
                assert int(row['candidate_count']) == original['candidate_count']

    def test_export_candidate_results_csv_success(self, sample_candidate_totals, temp_file):
        """Test successful candidate results CSV export."""
        result = export_candidate_results_csv(sample_candidate_totals, temp_file)
        
        assert result is True
        assert os.path.exists(temp_file)
        
        # Read back and verify content
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        
        # Check required columns
        assert 'candidate_name' in df.columns
        assert 'total_votes' in df.columns
        assert 'export_timestamp' in df.columns
        assert 'export_type' in df.columns
        
        # Check data integrity
        assert len(df) == len(sample_candidate_totals)
        assert df['export_type'].iloc[0] == 'candidate_results'

    def test_export_candidate_results_csv_round_trip(self, sample_candidate_totals, temp_file):
        """Test candidate results CSV round-trip."""
        # Export
        export_candidate_results_csv(sample_candidate_totals, temp_file)
        
        # Import and verify
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        
        # Check all data preserved
        assert len(df) == len(sample_candidate_totals)
        
        for i, original in enumerate(sample_candidate_totals):
            assert df.iloc[i]['candidate_name'] == original['candidate_name']
            assert df.iloc[i]['total_votes'] == original['total_votes']
            assert df.iloc[i]['party_name'] == original['party_name']

    def test_export_csv_empty_data_raises_error(self, temp_file):
        """Test that empty data raises ValueError."""
        with pytest.raises(ValueError, match="No party totals data provided"):
            export_party_totals_csv([], temp_file)
            
        with pytest.raises(ValueError, match="No candidate totals data provided"):
            export_candidate_results_csv([], temp_file)

    def test_export_csv_missing_columns_raises_error(self, temp_file):
        """Test that missing required columns raises ValueError."""
        invalid_party_data = [{"party_id": "1", "votes": 100}]  # Missing party_name
        
        with pytest.raises(ValueError, match="Missing required columns"):
            export_party_totals_csv(invalid_party_data, temp_file)
            
        invalid_candidate_data = [{"candidate_id": "1", "votes": 100}]  # Missing candidate_name
        
        with pytest.raises(ValueError, match="Missing required columns"):
            export_candidate_results_csv(invalid_candidate_data, temp_file)

    def test_export_results_pdf_success(self, sample_results_data, temp_file):
        """Test successful PDF export."""
        pdf_file = temp_file + ".pdf"
        
        result = export_results_pdf(sample_results_data, pdf_file)
        
        assert result is True
        assert os.path.exists(pdf_file)
        
        # Check file size is reasonable (>0 bytes)
        file_size = os.path.getsize(pdf_file)
        assert file_size > 0
        
        # Basic PDF header check
        with open(pdf_file, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF'

    def test_export_results_pdf_empty_data_raises_error(self, temp_file):
        """Test that empty results data raises ValueError."""
        pdf_file = temp_file + ".pdf"
        
        with pytest.raises(ValueError, match="No results data provided"):
            export_results_pdf({}, pdf_file)
            
        with pytest.raises(ValueError, match="No results data provided"):
            export_results_pdf(None, pdf_file)

    def test_export_results_pdf_partial_data(self, sample_party_totals, temp_file):
        """Test PDF export with only partial data (party totals only)."""
        pdf_file = temp_file + ".pdf"
        
        partial_data = {
            "party_totals": sample_party_totals,
            "candidate_totals": [],
            "winners": []
        }
        
        result = export_results_pdf(partial_data, pdf_file)
        
        assert result is True
        assert os.path.exists(pdf_file)
        assert os.path.getsize(pdf_file) > 0

    def test_get_export_filename(self):
        """Test export filename generation."""
        filename = get_export_filename("party_totals", "csv", "results")
        
        assert filename.startswith("results_party_totals_")
        assert filename.endswith(".csv")
        assert len(filename.split("_")) >= 4  # results, party, totals, timestamp
        
        # Test with different parameters
        filename2 = get_export_filename("report", "pdf", "election")
        assert filename2.startswith("election_report_")
        assert filename2.endswith(".pdf")

    def test_validate_export_path_success(self, temp_file):
        """Test export path validation success."""
        # Test with existing directory
        result = validate_export_path(temp_file)
        assert result is True

    def test_validate_export_path_new_directory(self):
        """Test export path validation with new directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_subdir", "deeper")
            test_file = os.path.join(new_dir, "test.csv")
            
            result = validate_export_path(test_file)
            assert result is True
            assert os.path.exists(new_dir)

    def test_validate_export_path_invalid_path(self):
        """Test export path validation with invalid path."""
        # Try to write to a path that should fail (root directory on Unix-like systems)
        if os.name != 'nt':  # Not Windows
            invalid_path = "/root/protected/file.csv"
            result = validate_export_path(invalid_path)
            assert result is False

    def test_format_arabic_text_available(self):
        """Test Arabic text formatting when libraries are available."""
        arabic_text = "النتائج الانتخابية"
        result = format_arabic_text(arabic_text)
        
        # Should return some text (either formatted or original)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_arabic_text_empty_input(self):
        """Test Arabic text formatting with empty input."""
        assert format_arabic_text("") == ""
        assert format_arabic_text(None) == None

    def test_csv_encoding_preserves_arabic(self, temp_file):
        """Test that CSV export preserves Arabic text encoding."""
        arabic_data = [
            {
                "party_name": "حزب التقدم والعدالة",
                "total_votes": 1500,
                "candidate_count": 6
            }
        ]
        
        export_party_totals_csv(arabic_data, temp_file)
        
        # Read back with UTF-8 encoding
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        assert df.iloc[0]['party_name'] == "حزب التقدم والعدالة"

    def test_csv_column_ordering(self, sample_party_totals, temp_file):
        """Test that CSV columns are ordered logically."""
        export_party_totals_csv(sample_party_totals, temp_file)
        
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        columns = list(df.columns)
        
        # Check that primary columns come first
        assert columns[0] == 'party_name'
        assert columns[1] == 'total_votes'
        
        # Metadata columns should be present
        assert 'export_timestamp' in columns
        assert 'export_type' in columns
        
        # Check that metadata columns come after data columns
        export_timestamp_idx = columns.index('export_timestamp')
        export_type_idx = columns.index('export_type')
        assert export_timestamp_idx > 2  # After party_name and total_votes
        assert export_type_idx > 2       # After party_name and total_votes

    def test_pdf_file_size_reasonable(self, sample_results_data, temp_file):
        """Test that generated PDF has reasonable file size."""
        pdf_file = temp_file + ".pdf"
        
        export_results_pdf(sample_results_data, pdf_file)
        
        file_size = os.path.getsize(pdf_file)
        
        # Should be at least 1KB for a proper PDF with data
        assert file_size > 1024
        
        # Should not be excessively large (under 1MB for test data)
        assert file_size < 1024 * 1024

    def test_export_handles_unicode_filenames(self, sample_party_totals):
        """Test export with Unicode characters in filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use Arabic characters in filename
            unicode_filename = os.path.join(temp_dir, "نتائج_الانتخابات.csv")
            
            try:
                result = export_party_totals_csv(sample_party_totals, unicode_filename)
                assert result is True
                assert os.path.exists(unicode_filename)
            except (UnicodeError, OSError):
                # Some filesystems don't support Unicode filenames
                pytest.skip("Filesystem doesn't support Unicode filenames")

    def test_concurrent_export_safety(self, sample_party_totals):
        """Test that concurrent exports don't interfere with each other."""
        import threading
        import time
        
        results = []
        errors = []
        
        def export_worker(worker_id):
            try:
                with tempfile.NamedTemporaryFile(suffix=f"_{worker_id}.csv", delete=False) as tmp:
                    temp_path = tmp.name
                
                time.sleep(0.01)  # Small delay to encourage race conditions
                result = export_party_totals_csv(sample_party_totals, temp_path)
                results.append(result)
                
                # Verify file was created correctly
                assert os.path.exists(temp_path)
                df = pd.read_csv(temp_path, encoding='utf-8-sig')
                assert len(df) == len(sample_party_totals)
                
                os.unlink(temp_path)
                
            except Exception as e:
                errors.append(e)
        
        # Run multiple exports concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=export_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All exports should succeed
        assert len(errors) == 0
        assert len(results) == 5
        assert all(results) 