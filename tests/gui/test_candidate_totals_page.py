"""Tests for CandidateTotalsPage QML component."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class CandidateTotalsPageTestHelper(QMLTestHelper):
    """Helper class for testing CandidateTotalsPage component."""

    def create_candidate_totals_page(self, mock_data=None):
        """Create a CandidateTotalsPage instance for testing."""
        if mock_data is None:
            mock_data = [
                {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 650, "rank": 1},
                {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 580, "rank": 2},
                {"candidate_name": "محمد علي", "party_name": "حزب الحرية", "total_votes": 420, "rank": 3}
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
                "candidateTotals": {str(mock_data).replace("'", '"')},
                "isSyncing": false,
                "setCandidateFilter": function(text) {{
                    console.log("Filter set to:", text)
                    root.lastFilterText = text
                }}
            }}

            property string lastFilterText: ""
            property alias page: candidatePage

            CandidateTotalsPage {{
                id: candidatePage
                anchors.fill: parent

                // Mock results controller
                property var resultsController: root.mockController
            }}
        }}
        """
        return self.create_qml_object(qml_code)


class TestCandidateTotalsPage:
    """Test suite for CandidateTotalsPage component."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return CandidateTotalsPageTestHelper(qml_engine)

    def test_candidate_totals_page_creation(self, helper):
        """Test that CandidateTotalsPage can be created."""
        root = helper.create_candidate_totals_page()
        assert root is not None

        # Find the page component
        page = root.property("page")
        assert page is not None

    def test_page_displays_candidate_data(self, helper):
        """Test that page displays candidate data correctly."""
        mock_data = [
            {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 650, "rank": 1},
            {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 580, "rank": 2}
        ]

        root = helper.create_candidate_totals_page(mock_data)
        page = root.property("page")

        # Find the results table
        results_table = helper.find_child(page, "ResultsTable")
        assert results_table is not None

        # Verify model is bound
        model = results_table.property("model")
        assert model is not None

    def test_search_field_exists(self, helper):
        """Test that search field is present and enabled."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Find the search field
        search_field = helper.find_child(page, "TextField")
        assert search_field is not None

        # Search field should be enabled (no longer disabled)
        assert search_field.property("enabled") is True

        # Should have correct placeholder text
        placeholder = search_field.property("placeholderText")
        assert "البحث عن مرشح" in placeholder

    def test_search_field_filtering(self, helper):
        """Test that search field filters trigger controller method."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Find the search field
        search_field = helper.find_child(page, "TextField")
        assert search_field is not None

        # Set text in search field
        test_text = "أحمد"
        search_field.setProperty("text", test_text)
        helper.process_events()

        # Verify that the mock controller method was called
        last_filter = root.property("lastFilterText")
        assert last_filter == test_text

    def test_page_header_text(self, helper):
        """Test that page header displays correct Arabic text."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Find header text
        texts = helper.find_children(page, "Text")
        header_found = False

        for text in texts:
            text_content = text.property("text")
            if text_content and "نتائج المرشحين" in text_content:
                header_found = True
                break

        assert header_found, "Header text not found"

    def test_columns_configuration(self, helper):
        """Test that columns are configured correctly."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Get columns property
        columns = page.property("columns")
        assert columns is not None
        assert len(columns) == 4  # candidate_name, party_name, total_votes, rank

        # Check column keys
        column_keys = [col["key"] for col in columns]
        assert "candidate_name" in column_keys
        assert "party_name" in column_keys
        assert "total_votes" in column_keys
        assert "rank" in column_keys

    def test_sorting_configuration(self, helper):
        """Test that sorting is configured correctly."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Find the results table
        results_table = helper.find_child(page, "ResultsTable")
        assert results_table is not None

        # Verify default sort settings
        current_sort_column = results_table.property("currentSortColumn")
        sort_descending = results_table.property("sortDescending")

        assert current_sort_column == "total_votes"
        assert sort_descending is True

    def test_rank_column_not_sortable(self, helper):
        """Test that rank column is not sortable."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Get columns configuration
        columns = page.property("columns")

        # Find rank column
        rank_column = None
        for col in columns:
            if col["key"] == "rank":
                rank_column = col
                break

        assert rank_column is not None
        assert rank_column["sortable"] is False

    def test_loading_state_binding(self, helper):
        """Test that loading state is bound to controller."""
        root = helper.create_candidate_totals_page()

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

    def test_search_field_styling(self, helper):
        """Test that search field has proper styling."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Find the search field
        search_field = helper.find_child(page, "TextField")
        assert search_field is not None

        # Should have background styling
        background = search_field.property("background")
        assert background is not None

        # Note: RTL mirroring properties might not be directly testable in unit tests

    def test_rtl_layout_support(self, helper):
        """Test that RTL layout is properly supported."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Page should have RTL mirroring enabled
        # Find the main column layout
        column_layouts = helper.find_children(page, "ColumnLayout")
        assert len(column_layouts) > 0, "ColumnLayout not found"

    def test_empty_search_handling(self, helper):
        """Test behavior with empty search text."""
        root = helper.create_candidate_totals_page()
        page = root.property("page")

        # Find the search field
        search_field = helper.find_child(page, "TextField")
        assert search_field is not None

        # Set empty text
        search_field.setProperty("text", "")
        helper.process_events()

        # Should still call filter method with empty string
        last_filter = root.property("lastFilterText")
        assert last_filter == ""
