"""Integration tests for QML components."""
import os
import pytest
from pathlib import Path


class TestQMLComponentFiles:
    """Test that QML component files exist and are valid."""
    
    def test_component_files_exist(self):
        """Test that all required component files exist."""
        components_dir = Path("src/jcselect/ui/components")
        
        required_components = [
            "PenSelector.qml",
            "RefreshBadge.qml", 
            "ExportMenu.qml",
            "ResultsTable.qml",
            "WinnerCard.qml"
        ]
        
        for component in required_components:
            component_path = components_dir / component
            assert component_path.exists(), f"Component {component} does not exist"
            assert component_path.is_file(), f"{component} is not a file"
    
    def test_qmldir_exists_and_valid(self):
        """Test that qmldir exists and contains our components."""
        qmldir_path = Path("src/jcselect/ui/components/qmldir")
        assert qmldir_path.exists(), "components/qmldir does not exist"
        
        qmldir_content = qmldir_path.read_text(encoding='utf-8')
        
        # Check that all our components are registered
        required_exports = [
            "PenSelector 1.0 PenSelector.qml",
            "RefreshBadge 1.0 RefreshBadge.qml",
            "ExportMenu 1.0 ExportMenu.qml", 
            "ResultsTable 1.0 ResultsTable.qml",
            "WinnerCard 1.0 WinnerCard.qml"
        ]
        
        for export in required_exports:
            assert export in qmldir_content, f"Missing export: {export}"
    
    def test_component_basic_syntax(self):
        """Test that component files have basic QML syntax."""
        components_dir = Path("src/jcselect/ui/components")
        
        component_files = [
            "PenSelector.qml",
            "RefreshBadge.qml", 
            "ExportMenu.qml",
            "ResultsTable.qml",
            "WinnerCard.qml"
        ]
        
        for component_file in component_files:
            component_path = components_dir / component_file
            content = component_path.read_text(encoding='utf-8')
            
            # Basic syntax checks
            assert "import QtQuick" in content, f"{component_file} missing QtQuick import"
            assert "{" in content and "}" in content, f"{component_file} missing braces"
    
    def test_page_files_use_components(self):
        """Test that page files import and use our components."""
        pages_dir = Path("src/jcselect/ui/pages")
        
        page_files = [
            "PartyTotalsPage.qml",
            "CandidateTotalsPage.qml",
            "WinnersPage.qml"
        ]
        
        for page_file in page_files:
            page_path = pages_dir / page_file
            assert page_path.exists(), f"Page {page_file} does not exist"
            
            content = page_path.read_text(encoding='utf-8')
            
            # Should import components
            assert "import jcselect.ui.components 1.0" in content, f"{page_file} missing components import"
            
            # Should use ResultsTable or WinnerCard
            if "Results" in page_file:
                assert "ResultsTable" in content, f"{page_file} should use ResultsTable component"
            elif "Winners" in page_file:
                assert "WinnerCard" in content, f"{page_file} should use WinnerCard component"
    
    def test_theme_file_exists(self):
        """Test that Theme.qml exists and has required properties."""
        theme_path = Path("src/jcselect/ui/Theme.qml")
        assert theme_path.exists(), "Theme.qml does not exist"
        
        content = theme_path.read_text(encoding='utf-8')
        
        # Check for key theme properties
        required_properties = [
            "primaryColor",
            "backgroundColor", 
            "textColor",
            "spacing",
            "buttonHeight",
            "radius"
        ]
        
        for prop in required_properties:
            assert prop in content, f"Theme missing property: {prop}"


if __name__ == "__main__":
    pytest.main([__file__]) 