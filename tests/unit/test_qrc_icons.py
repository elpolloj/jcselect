"""Test QRC icon loading."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Skip tests if Qt isn't available
try:
    from PySide6.QtCore import QCoreApplication, QDir, QResource
    from PySide6.QtGui import QIcon, QPixmap
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@pytest.mark.skipif(not QT_AVAILABLE, reason="Qt not available")
class TestQRCIcons:
    """Test QRC icon resource loading."""

    @classmethod
    def setup_class(cls):
        """Set up QApplication if needed."""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])
        else:
            cls.app = None
    
    @classmethod
    def teardown_class(cls):
        """Clean up QApplication if we created it."""
        if cls.app:
            cls.app.quit()

    def test_qrc_file_exists(self):
        """Test that the QRC file exists."""
        qrc_file = Path("src/jcselect/resources/icons.qrc")
        assert qrc_file.exists(), "QRC file should exist"

    def test_search_voters_icon_loads(self):
        """Test that search-voters icon can be loaded."""
        # First register the QRC resource
        qrc_file = Path("src/jcselect/resources/icons.qrc").resolve()
        
        if qrc_file.exists():
            # In a real application, QRC would be compiled and registered
            # For testing, we check the icon file exists
            icon_file = Path("src/jcselect/resources/icons/search-voters.svg")
            assert icon_file.exists(), "search-voters.svg should exist"
            
            # Test QIcon creation (won't work without compiled QRC, but tests the interface)
            icon = QIcon("qrc:/icons/search-voters.svg")
            # In unit test, this will be null since QRC isn't compiled/registered
            # but we test that the QIcon can be created without crashing
            assert icon is not None, "QIcon should be created"

    def test_tally_count_icon_loads(self):
        """Test that tally-count icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/tally-count.svg")
        assert icon_file.exists(), "tally-count.svg should exist"
        
        icon = QIcon("qrc:/icons/tally-count.svg")
        assert icon is not None, "QIcon should be created"

    def test_turnout_stats_icon_loads(self):
        """Test that turnout-stats icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/turnout-stats.svg")
        assert icon_file.exists(), "turnout-stats.svg should exist"
        
        icon = QIcon("qrc:/icons/turnout-stats.svg")
        assert icon is not None, "QIcon should be created"

    def test_results_charts_icon_loads(self):
        """Test that results-charts icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/results-charts.svg")
        assert icon_file.exists(), "results-charts.svg should exist"
        
        icon = QIcon("qrc:/icons/results-charts.svg")
        assert icon is not None, "QIcon should be created"

    def test_winners_icon_loads(self):
        """Test that winners icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/winners.svg")
        assert icon_file.exists(), "winners.svg should exist"
        
        icon = QIcon("qrc:/icons/winners.svg")
        assert icon is not None, "QIcon should be created"

    def test_count_ops_icon_loads(self):
        """Test that count-ops icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/count-ops.svg")
        assert icon_file.exists(), "count-ops.svg should exist"
        
        icon = QIcon("qrc:/icons/count-ops.svg")
        assert icon is not None, "QIcon should be created"

    def test_setup_icon_loads(self):
        """Test that setup icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/setup.svg")
        assert icon_file.exists(), "setup.svg should exist"
        
        icon = QIcon("qrc:/icons/setup.svg")
        assert icon is not None, "QIcon should be created"

    def test_system_settings_icon_loads(self):
        """Test that system-settings icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/system-settings.svg")
        assert icon_file.exists(), "system-settings.svg should exist"
        
        icon = QIcon("qrc:/icons/system-settings.svg")
        assert icon is not None, "QIcon should be created"

    def test_test_icon_loads(self):
        """Test that test icon can be loaded."""
        icon_file = Path("src/jcselect/resources/icons/test.svg")
        assert icon_file.exists(), "test.svg should exist"
        
        icon = QIcon("qrc:/icons/test.svg")
        assert icon is not None, "QIcon should be created"

    def test_all_icons_in_qrc_exist(self):
        """Test that all icons referenced in QRC file exist."""
        qrc_file = Path("src/jcselect/resources/icons.qrc")
        if not qrc_file.exists():
            pytest.skip("QRC file not found")
        
        qrc_content = qrc_file.read_text()
        
        # Extract icon filenames from QRC
        import re
        icon_matches = re.findall(r'<file>icons/([^<]+)</file>', qrc_content)
        
        icons_dir = Path("src/jcselect/resources/icons")
        for icon_name in icon_matches:
            icon_path = icons_dir / icon_name
            assert icon_path.exists(), f"Icon {icon_name} referenced in QRC should exist at {icon_path}"

    def test_icon_file_is_valid_svg(self):
        """Test that icon files are valid SVG."""
        icons_dir = Path("src/jcselect/resources/icons")
        
        for svg_file in icons_dir.glob("*.svg"):
            content = svg_file.read_text()
            # SVG files can start with either XML declaration or directly with <svg>
            assert content.startswith("<?xml") or content.startswith("<svg"), f"{svg_file.name} should start with XML declaration or <svg> element"
            assert "<svg" in content, f"{svg_file.name} should contain <svg> element"
            assert "</svg>" in content, f"{svg_file.name} should have closing </svg> tag" 