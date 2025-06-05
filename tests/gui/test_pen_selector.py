"""Tests for PenSelector QML component."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class PenSelectorTestHelper(QMLTestHelper):
    """Helper class for testing PenSelector component."""

    def create_pen_selector(self, show_all_option=True):
        """Create a PenSelector instance for testing."""
        qml_code = f"""
        import QtQuick 2.15
        import jcselect.ui.components 1.0

        PenSelector {{
            id: penSelector
            width: 300
            height: 40
            showAllPensOption: {str(show_all_option).lower()}

            property var receivedPenId: ""

            onPenSelected: {{
                receivedPenId = penId
            }}
        }}
        """
        return self.create_qml_object(qml_code)


class TestPenSelector:
    """Test suite for PenSelector component."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return PenSelectorTestHelper(qml_engine)

    def test_pen_selector_creation(self, helper):
        """Test that PenSelector can be created."""
        pen_selector = helper.create_pen_selector()
        assert pen_selector is not None

        # Check initial properties
        assert pen_selector.property("showAllPensOption") is True
        assert pen_selector.property("selectedPenId") == ""

    def test_pen_selector_without_all_option(self, helper):
        """Test PenSelector without 'All Pens' option."""
        pen_selector = helper.create_pen_selector(show_all_option=False)
        assert pen_selector is not None
        assert pen_selector.property("showAllPensOption") is False

    def test_pen_list_population(self, helper):
        """Test that pen list populates correctly."""
        pen_selector = helper.create_pen_selector()

        # Mock pen data
        pen_data = [
            {
                "id": "pen_1",
                "display_name": "قلم رقم 1 - الحي الأول",
                "label": "قلم 1",
                "town_name": "الحي الأول"
            },
            {
                "id": "pen_2",
                "display_name": "قلم رقم 2 - الحي الثاني",
                "label": "قلم 2",
                "town_name": "الحي الثاني"
            }
        ]

        # Set model
        pen_selector.setProperty("model", pen_data)

        # ComboBox should now have items (including "All Pens" if enabled)
        combo_box = helper.find_child(pen_selector, "ComboBox")
        assert combo_box is not None

        # Should have 3 items: "All Pens" + 2 pen items
        assert combo_box.property("count") == 3

    def test_all_pens_option_visibility(self, helper):
        """Test 'All Pens' option visibility based on showAllPensOption."""
        # Test with All Pens option enabled
        pen_selector_with_all = helper.create_pen_selector(show_all_option=True)
        combo_box_with_all = helper.find_child(pen_selector_with_all, "ComboBox")

        # Set some pen data
        pen_data = [{"id": "pen_1", "display_name": "قلم 1", "label": "قلم 1", "town_name": "حي"}]
        pen_selector_with_all.setProperty("model", pen_data)

        # Should have 2 items: "All Pens" + 1 pen
        assert combo_box_with_all.property("count") == 2

        # Test without All Pens option
        pen_selector_without_all = helper.create_pen_selector(show_all_option=False)
        combo_box_without_all = helper.find_child(pen_selector_without_all, "ComboBox")
        pen_selector_without_all.setProperty("model", pen_data)

        # Should have 1 item: just the pen
        assert combo_box_without_all.property("count") == 1

    def test_pen_selection_signal(self, helper):
        """Test that penSelected signal is emitted correctly."""
        pen_selector = helper.create_pen_selector()

        # Set pen data
        pen_data = [
            {
                "id": "pen_1",
                "display_name": "قلم رقم 1",
                "label": "قلم 1",
                "town_name": "حي"
            }
        ]
        pen_selector.setProperty("model", pen_data)

        # Find the ComboBox
        combo_box = helper.find_child(pen_selector, "ComboBox")
        assert combo_box is not None

        # Simulate selecting a pen (index 1 = first pen, 0 = "All Pens")
        combo_box.setProperty("currentIndex", 1)
        helper.process_events()

        # Check that the signal was handled
        received_pen_id = pen_selector.property("receivedPenId")
        assert received_pen_id == "pen_1"

        # Check selectedPenId property was updated
        assert pen_selector.property("selectedPenId") == "pen_1"

    def test_all_pens_selection(self, helper):
        """Test selecting 'All Pens' option."""
        pen_selector = helper.create_pen_selector()

        # Set pen data
        pen_data = [{"id": "pen_1", "display_name": "قلم 1", "label": "قلم 1", "town_name": "حي"}]
        pen_selector.setProperty("model", pen_data)

        combo_box = helper.find_child(pen_selector, "ComboBox")

        # Select "All Pens" (index 0)
        combo_box.setProperty("currentIndex", 0)
        helper.process_events()

        # Should emit "all" as pen ID
        received_pen_id = pen_selector.property("receivedPenId")
        assert received_pen_id == "all"
        assert pen_selector.property("selectedPenId") == "all"

    def test_search_functionality(self, helper):
        """Test search/filter functionality in ComboBox."""
        pen_selector = helper.create_pen_selector()

        # Set diverse pen data for searching
        pen_data = [
            {"id": "pen_1", "display_name": "قلم رقم 1 - الحي الأول", "label": "قلم 1", "town_name": "الحي الأول"},
            {"id": "pen_2", "display_name": "قلم رقم 2 - الحي الثاني", "label": "قلم 2", "town_name": "الحي الثاني"},
            {"id": "pen_3", "display_name": "قلم رقم 3 - الحي الثالث", "label": "قلم 3", "town_name": "الحي الثالث"}
        ]
        pen_selector.setProperty("model", pen_data)

        combo_box = helper.find_child(pen_selector, "ComboBox")

        # Verify the ComboBox is editable for search
        assert combo_box.property("editable") is True
        assert combo_box.property("selectTextByMouse") is True

        # Should have all items initially (3 pens + "All Pens")
        assert combo_box.property("count") == 4

    def test_default_selection(self, helper):
        """Test that 'All Pens' is selected by default when available."""
        pen_selector = helper.create_pen_selector()

        # Set pen data
        pen_data = [{"id": "pen_1", "display_name": "قلم 1", "label": "قلم 1", "town_name": "حي"}]
        pen_selector.setProperty("model", pen_data)

        combo_box = helper.find_child(pen_selector, "ComboBox")
        helper.process_events()

        # Should default to "All Pens" (index 0)
        assert combo_box.property("currentIndex") == 0
        assert pen_selector.property("selectedPenId") == "all"
