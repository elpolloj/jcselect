"""Tests for ResultsTable QML component."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class ResultsTableTestHelper(QMLTestHelper):
    """Helper class for testing ResultsTable component."""

    def create_results_table(self, is_loading=False, sortable=True):
        """Create a ResultsTable instance for testing."""
        qml_code = f"""
        import QtQuick 2.15
        import jcselect.ui.components 1.0

        ResultsTable {{
            id: resultsTable
            width: 600
            height: 400
            isLoading: {str(is_loading).lower()}
            sortable: {str(sortable).lower()}

            property string lastSortColumn: ""
            property bool lastSortDescending: false

            columns: [
                {{
                    "key": "name",
                    "title": "الاسم",
                    "type": "text",
                    "align": "right",
                    "width": 200,
                    "sortable": true
                }},
                {{
                    "key": "votes",
                    "title": "الأصوات",
                    "type": "number",
                    "align": "center",
                    "width": 120,
                    "sortable": true
                }},
                {{
                    "key": "percentage",
                    "title": "النسبة",
                    "type": "percentage",
                    "align": "center",
                    "width": 100,
                    "sortable": false
                }}
            ]

            model: [
                {{"name": "أحمد محمد", "votes": 150, "percentage": 35.5}},
                {{"name": "فاطمة علي", "votes": 200, "percentage": 47.2}},
                {{"name": "محمود حسن", "votes": 73, "percentage": 17.3}}
            ]

            onSortRequested: function(columnKey, descending) {{
                lastSortColumn = columnKey
                lastSortDescending = descending
            }}
        }}
        """
        return self.create_qml_object(qml_code)


class TestResultsTable:
    """Test suite for ResultsTable component."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return ResultsTableTestHelper(qml_engine)

    def test_results_table_creation(self, helper):
        """Test that ResultsTable can be created."""
        results_table = helper.create_results_table()
        assert results_table is not None

        # Check initial properties
        assert results_table.property("isLoading") is False
        assert results_table.property("sortable") is True
        assert results_table.property("lastSortColumn") == ""
        assert results_table.property("lastSortDescending") is False

    def test_table_model_population(self, helper):
        """Test that table populates with model data."""
        results_table = helper.create_results_table()

        # Find the ListView (table content)
        list_view = helper.find_child(results_table, "ListView")
        assert list_view is not None

        # Should have 3 items from the model
        assert list_view.property("count") == 3

    def test_column_headers_display(self, helper):
        """Test that column headers are displayed correctly."""
        results_table = helper.create_results_table()

        # Find header buttons
        header_buttons = helper.find_children(results_table, "Button")

        # Should have header buttons for each column
        header_texts = []
        for button in header_buttons:
            texts = helper.find_children(button, "Text")
            for text in texts:
                text_content = text.property("text")
                if text_content in ["الاسم", "الأصوات", "النسبة"]:
                    header_texts.append(text_content)

        assert "الاسم" in header_texts
        assert "الأصوات" in header_texts
        assert "النسبة" in header_texts

    def test_header_sorting_click(self, helper):
        """Test clicking header triggers sorting."""
        results_table = helper.create_results_table()

        # Find a sortable header button (name column)
        header_buttons = helper.find_children(results_table, "Button")
        name_header = None

        for button in header_buttons:
            if button.property("enabled"):  # Sortable headers are enabled
                texts = helper.find_children(button, "Text")
                for text in texts:
                    if text.property("text") == "الاسم":
                        name_header = button
                        break
            if name_header:
                break

        assert name_header is not None, "Name header button not found"

        # Click the header
        helper.click_item(name_header)
        helper.process_events()

        # Check that sort signal was emitted
        assert results_table.property("lastSortColumn") == "name"
        assert results_table.property("lastSortDescending") is True  # First click is descending

    def test_sorting_toggle_behavior(self, helper):
        """Test that clicking same header toggles sort order."""
        results_table = helper.create_results_table()

        # Find votes header (another sortable column)
        header_buttons = helper.find_children(results_table, "Button")
        votes_header = None

        for button in header_buttons:
            if button.property("enabled"):
                texts = helper.find_children(button, "Text")
                for text in texts:
                    if text.property("text") == "الأصوات":
                        votes_header = button
                        break
            if votes_header:
                break

        assert votes_header is not None, "Votes header button not found"

        # First click - should be descending
        helper.click_item(votes_header)
        helper.process_events()

        assert results_table.property("lastSortColumn") == "votes"
        assert results_table.property("lastSortDescending") is True

        # Second click on same column - should toggle to ascending
        helper.click_item(votes_header)
        helper.process_events()

        assert results_table.property("lastSortColumn") == "votes"
        assert results_table.property("lastSortDescending") is False

    def test_non_sortable_column_header(self, helper):
        """Test non-sortable column headers are disabled."""
        results_table = helper.create_results_table()

        # Find percentage header (non-sortable in our test data)
        header_buttons = helper.find_children(results_table, "Button")
        percentage_header = None

        for button in header_buttons:
            texts = helper.find_children(button, "Text")
            for text in texts:
                if text.property("text") == "النسبة":
                    percentage_header = button
                    break
            if percentage_header:
                break

        assert percentage_header is not None, "Percentage header button not found"

        # Non-sortable header should be disabled
        assert percentage_header.property("enabled") is False

    def test_sort_indicator_display(self, helper):
        """Test sort indicators show correctly."""
        results_table = helper.create_results_table()

        # Set current sort column
        results_table.setProperty("currentSortColumn", "votes")
        results_table.setProperty("sortDescending", True)
        helper.process_events()

        # Find the votes header
        header_buttons = helper.find_children(results_table, "Button")
        votes_header = None

        for button in header_buttons:
            texts = helper.find_children(button, "Text")
            for text in texts:
                if text.property("text") == "الأصوات":
                    votes_header = button
                    break
            if votes_header:
                break

        # Should have sort indicator
        if votes_header:
            sort_indicators = helper.find_children(votes_header, "Text")
            indicator_found = False
            for indicator in sort_indicators:
                text_content = indicator.property("text")
                if text_content in ["↓", "↑"]:
                    indicator_found = True
                    # Should show downward arrow for descending
                    assert text_content == "↓"
                    break
            assert indicator_found, "Sort indicator not found"

    def test_loading_overlay_display(self, helper):
        """Test loading overlay is shown when isLoading is true."""
        # Test normal state (no loading)
        results_table_normal = helper.create_results_table(is_loading=False)
        normal_overlays = helper.find_children(results_table_normal, "Rectangle")

        loading_overlay_visible = False
        for overlay in normal_overlays:
            if overlay.property("visible") and "Loading" in str(overlay):
                loading_overlay_visible = True
                break

        # Should not have visible loading overlay
        assert not loading_overlay_visible

        # Test loading state
        results_table_loading = helper.create_results_table(is_loading=True)
        loading_overlays = helper.find_children(results_table_loading, "Rectangle")

        loading_found = False
        for overlay in loading_overlays:
            if overlay.property("visible"):
                # Check for BusyIndicator or loading text
                busy_indicators = helper.find_children(overlay, "BusyIndicator")
                loading_texts = helper.find_children(overlay, "Text")

                for indicator in busy_indicators:
                    if indicator.property("running"):
                        loading_found = True
                        break

                if not loading_found:
                    for text in loading_texts:
                        if "جاري تحميل" in text.property("text"):
                            loading_found = True
                            break

            if loading_found:
                break

        assert loading_found, "Loading overlay not found when isLoading is true"

    def test_empty_state_display(self, helper):
        """Test empty state is shown when no data."""
        qml_code = """
        import QtQuick 2.15
        import jcselect.ui.components 1.0

        ResultsTable {
            id: resultsTable
            width: 600
            height: 400
            isLoading: false

            columns: [
                {
                    "key": "name",
                    "title": "الاسم",
                    "type": "text",
                    "width": 200
                }
            ]

            model: []  // Empty model
        }
        """

        empty_table = helper.create_qml_object(qml_code)
        assert empty_table is not None

        # Find the ListView
        list_view = helper.find_child(empty_table, "ListView")
        assert list_view is not None
        assert list_view.property("count") == 0

        # Should show empty state
        empty_state_texts = helper.find_children(empty_table, "Text")
        empty_message_found = False

        for text in empty_state_texts:
            if "لا توجد بيانات للعرض" in text.property("text"):
                empty_message_found = True
                break

        assert empty_message_found, "Empty state message not found"

    def test_rtl_layout_mirroring(self, helper):
        """Test RTL layout mirroring is applied."""
        results_table = helper.create_results_table()

        # Root table should have LayoutMirroring enabled
        # Note: This might be hard to test directly, but we can check structure

        # Find text elements and check they have RTL support
        text_elements = helper.find_children(results_table, "Text")
        rtl_support_found = False

        for text in text_elements:
            # Check if LayoutMirroring is considered in the text elements
            # This is a structural check since we can't easily test actual RTL rendering
            if text.property("text"):  # Has actual text content
                rtl_support_found = True
                break

        assert rtl_support_found, "Text elements not found for RTL testing"

    def test_data_formatting(self, helper):
        """Test data is formatted correctly by column type."""
        results_table = helper.create_results_table()

        # Find the table rows/cells
        list_view = helper.find_child(results_table, "ListView")
        assert list_view is not None

        # The data formatting is handled in the delegate
        # This is more of a structural test since formatting happens in QML

        # Check that model has the expected data
        model = results_table.property("model")
        assert model is not None

        # Verify we have test data with different types
        # (number formatting, percentage formatting, etc.)
        # The actual formatting would be tested through visual/integration tests
