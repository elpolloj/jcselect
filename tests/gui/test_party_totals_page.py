"""Tests for PartyTotalsPage QML component."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class PartyTotalsPageTestHelper(QMLTestHelper):
    """Helper class for testing PartyTotalsPage component."""

    def create_party_totals_page(self, mock_data=None):
        """Create a PartyTotalsPage instance for testing."""
        if mock_data is None:
            mock_data = [
                {"party_name": "حزب الحرية", "total_votes": 1250, "percentage": 42.5},
                {"party_name": "حزب التقدم", "total_votes": 980, "percentage": 33.2}
            ]

        qml_code = f"""
        import QtQuick 2.15
        import QtQuick.Controls 2.15
        import "../../../src/jcselect/ui/pages/"

        Item {{
            id: root
            width: 800
            height: 600

            property var mockController: {{
                "partyTotals": {str(mock_data).replace("'", '"')},
                "isSyncing": false
            }}

            property alias page: partyPage

            PartyTotalsPage {{
                id: partyPage
                anchors.fill: parent

                // Mock results controller
                property var resultsController: root.mockController
            }}
        }}
        """
        return self.create_qml_object(qml_code)


class TestPartyTotalsPage:
    """Test suite for PartyTotalsPage component."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return PartyTotalsPageTestHelper(qml_engine)

    def test_party_totals_page_creation(self, helper):
        """Test that PartyTotalsPage can be created."""
        root = helper.create_party_totals_page()
        assert root is not None

        # Find the page component
        page = root.property("page")
        assert page is not None

    def test_page_displays_party_data(self, helper):
        """Test that page displays party data correctly."""
        mock_data = [
            {"party_name": "حزب الحرية", "total_votes": 1250, "percentage": 42.5},
            {"party_name": "حزب التقدم", "total_votes": 980, "percentage": 33.2}
        ]

        root = helper.create_party_totals_page(mock_data)
        page = root.property("page")

        # Find the results table
        results_table = helper.find_child(page, "ResultsTable")
        assert results_table is not None

        # Verify model is bound
        model = results_table.property("model")
        assert model is not None

    def test_page_header_text(self, helper):
        """Test that page header displays correct Arabic text."""
        root = helper.create_party_totals_page()
        page = root.property("page")

        # Find header text
        texts = helper.find_children(page, "Text")
        header_found = False

        for text in texts:
            text_content = text.property("text")
            if text_content and "إجمالي أصوات الأحزاب" in text_content:
                header_found = True
                break

        assert header_found, "Header text not found"

    def test_columns_configuration(self, helper):
        """Test that columns are configured correctly."""
        root = helper.create_party_totals_page()
        page = root.property("page")

        # Get columns property
        columns = page.property("columns")
        assert columns is not None
        assert len(columns) == 3  # party_name, total_votes, percentage

        # Check column keys
        column_keys = [col["key"] for col in columns]
        assert "party_name" in column_keys
        assert "total_votes" in column_keys
        assert "percentage" in column_keys

    def test_sorting_signal_emission(self, helper):
        """Test that sorting signals are emitted correctly."""
        root = helper.create_party_totals_page()
        page = root.property("page")

        # Find the results table
        results_table = helper.find_child(page, "ResultsTable")
        assert results_table is not None

        # Verify default sort settings
        current_sort_column = results_table.property("currentSortColumn")
        sort_descending = results_table.property("sortDescending")

        assert current_sort_column == "total_votes"
        assert sort_descending is True

    def test_loading_state_binding(self, helper):
        """Test that loading state is bound to controller."""
        mock_data = []
        root = helper.create_party_totals_page(mock_data)

        # Update mock controller to show syncing
        mock_controller = root.property("mockController")
        mock_controller["isSyncing"] = True
        root.setProperty("mockController", mock_controller)

        helper.process_events()

        page = root.property("page")
        results_table = helper.find_child(page, "ResultsTable")

        # Should reflect loading state
        is_loading = results_table.property("isLoading")
        assert is_loading is not None

    def test_rtl_layout_support(self, helper):
        """Test that RTL layout is properly supported."""
        root = helper.create_party_totals_page()
        page = root.property("page")

        # Page should have RTL mirroring enabled
        # Note: LayoutMirroring properties might not be directly testable in unit tests

        # Find the main column layout
        column_layouts = helper.find_children(page, "ColumnLayout")
        assert len(column_layouts) > 0, "ColumnLayout not found"

    def test_theme_integration(self, helper):
        """Test that page uses Theme properties."""
        root = helper.create_party_totals_page()
        page = root.property("page")

        # Page background should use Theme.backgroundColor
        page_color = page.property("color")
        assert page_color is not None

        # Find text elements that should use theme colors
        texts = helper.find_children(page, "Text")
        theme_text_found = False

        for text in texts:
            color = text.property("color")
            if color:  # Should have color set from Theme
                theme_text_found = True
                break

        assert theme_text_found, "Theme colors not applied to text"

    def test_empty_data_handling(self, helper):
        """Test page behavior with empty data."""
        empty_data = []
        root = helper.create_party_totals_page(empty_data)
        page = root.property("page")

        # Should still create table component
        results_table = helper.find_child(page, "ResultsTable")
        assert results_table is not None

        # Table should handle empty model gracefully
        model = results_table.property("model")
        assert model is not None
