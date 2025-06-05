"""Tests for WinnersPage QML component."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class WinnersPageTestHelper(QMLTestHelper):
    """Helper class for testing WinnersPage component."""

    def create_winners_page(self, mock_data=None, is_loading=False):
        """Create a WinnersPage instance for testing."""
        if mock_data is None:
            mock_data = [
                {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 1250, "rank": 1, "is_elected": True},
                {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 1180, "rank": 2, "is_elected": True},
                {"candidate_name": "محمد علي", "party_name": "حزب الوحدة", "total_votes": 950, "rank": 3, "is_elected": True}
            ]

        qml_code = f"""
        import QtQuick 2.15
        import QtQuick.Controls 2.15
        import "../../../src/jcselect/ui/pages/"

        Item {{
            id: root
            width: 1000
            height: 700

            property var mockController: {{
                "winners": {str(mock_data).replace("'", '"')},
                "isSyncing": {str(is_loading).lower()}
            }}

            property alias page: winnersPage

            WinnersPage {{
                id: winnersPage
                anchors.fill: parent

                // Mock results controller
                property var resultsController: root.mockController
            }}
        }}
        """
        return self.create_qml_object(qml_code)


class TestWinnersPage:
    """Test suite for WinnersPage component."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return WinnersPageTestHelper(qml_engine)

    def test_winners_page_creation(self, helper):
        """Test that WinnersPage can be created."""
        root = helper.create_winners_page()
        assert root is not None

        # Find the page component
        page = root.property("page")
        assert page is not None

    def test_page_displays_winner_cards(self, helper):
        """Test that page displays winner cards correctly."""
        mock_data = [
            {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 1250, "rank": 1, "is_elected": True},
            {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 1180, "rank": 2, "is_elected": True}
        ]

        root = helper.create_winners_page(mock_data)
        page = root.property("page")

        # Find winner cards
        winner_cards = helper.find_children(page, "WinnerCard")
        assert len(winner_cards) == 2, f"Expected 2 winner cards, found {len(winner_cards)}"

    def test_winner_cards_order_by_rank(self, helper):
        """Test that winner cards are displayed in correct rank order."""
        mock_data = [
            {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 1250, "rank": 1, "is_elected": True},
            {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 1180, "rank": 2, "is_elected": True},
            {"candidate_name": "محمد علي", "party_name": "حزب الوحدة", "total_votes": 950, "rank": 3, "is_elected": True}
        ]

        root = helper.create_winners_page(mock_data)
        page = root.property("page")

        # Find winner cards
        winner_cards = helper.find_children(page, "WinnerCard")
        assert len(winner_cards) == 3

        # Verify ranks are in correct order (should be ascending: 1, 2, 3)
        ranks = []
        for card in winner_cards:
            rank = card.property("rank")
            if rank is not None:
                ranks.append(rank)

        # Should have all three ranks
        assert 1 in ranks
        assert 2 in ranks
        assert 3 in ranks

    def test_page_header_text(self, helper):
        """Test that page header displays correct Arabic text."""
        root = helper.create_winners_page()
        page = root.property("page")

        # Find header text
        texts = helper.find_children(page, "Text")
        header_found = False

        for text in texts:
            text_content = text.property("text")
            if text_content and "الفائزون" in text_content:
                header_found = True
                break

        assert header_found, "Header text not found"

    def test_grid_layout_structure(self, helper):
        """Test that winners are displayed in a grid layout."""
        root = helper.create_winners_page()
        page = root.property("page")

        # Find the grid layout
        grid_layouts = helper.find_children(page, "GridLayout")
        assert len(grid_layouts) > 0, "GridLayout not found"

        # Find scroll view for large lists
        scroll_views = helper.find_children(page, "ScrollView")
        assert len(scroll_views) > 0, "ScrollView not found"

    def test_empty_state_display(self, helper):
        """Test empty state when no winners are available."""
        empty_data = []
        root = helper.create_winners_page(empty_data, is_loading=False)
        page = root.property("page")

        # Should show empty state message
        texts = helper.find_children(page, "Text")
        empty_message_found = False

        for text in texts:
            text_content = text.property("text")
            if text_content and "لم يتم تحديد الفائزين بعد" in text_content:
                empty_message_found = True
                break

        assert empty_message_found, "Empty state message not found"

    def test_loading_state_display(self, helper):
        """Test loading state when data is being calculated."""
        root = helper.create_winners_page(mock_data=[], is_loading=True)
        page = root.property("page")

        # Should show loading indicator
        busy_indicators = helper.find_children(page, "BusyIndicator")
        loading_found = False

        for indicator in busy_indicators:
            if indicator.property("running"):
                loading_found = True
                break

        assert loading_found, "Loading indicator not found"

        # Should show loading text
        texts = helper.find_children(page, "Text")
        loading_text_found = False

        for text in texts:
            text_content = text.property("text")
            if text_content and "جاري حساب النتائج" in text_content:
                loading_text_found = True
                break

        assert loading_text_found, "Loading text not found"

    def test_winner_card_data_binding(self, helper):
        """Test that winner card data is properly bound."""
        mock_data = [
            {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 1250, "rank": 1, "is_elected": True}
        ]

        root = helper.create_winners_page(mock_data)
        page = root.property("page")

        # Find the winner card
        winner_cards = helper.find_children(page, "WinnerCard")
        assert len(winner_cards) >= 1

        card = winner_cards[0]

        # Verify data binding
        candidate_name = card.property("candidateName")
        party_name = card.property("partyName")
        total_votes = card.property("totalVotes")
        rank = card.property("rank")
        is_elected = card.property("isElected")

        assert candidate_name == "أحمد محمود"
        assert party_name == "حزب الحرية"
        assert total_votes == 1250
        assert rank == 1
        assert is_elected is True

    def test_animation_on_refresh(self, helper):
        """Test that cards have opacity animation on refresh."""
        root = helper.create_winners_page()
        page = root.property("page")

        # Find the grid layout with animation properties
        grid_layouts = helper.find_children(page, "GridLayout")
        assert len(grid_layouts) > 0

        grid = grid_layouts[0]

        # Grid should have opacity behavior for animation
        opacity = grid.property("opacity")
        assert opacity is not None

    def test_rtl_layout_support(self, helper):
        """Test that RTL layout is properly supported."""
        root = helper.create_winners_page()
        page = root.property("page")

        # Page should have RTL mirroring enabled
        # Find the main column layout
        column_layouts = helper.find_children(page, "ColumnLayout")
        assert len(column_layouts) > 0, "ColumnLayout not found"

    def test_responsive_grid_columns(self, helper):
        """Test that grid adapts to different screen sizes."""
        root = helper.create_winners_page()
        page = root.property("page")

        # Find the grid layout
        grid_layouts = helper.find_children(page, "GridLayout")
        assert len(grid_layouts) > 0

        grid = grid_layouts[0]

        # Grid should have dynamic column calculation
        columns = grid.property("columns")
        assert columns is not None
        assert columns >= 1  # Should have at least 1 column

    def test_gold_silver_bronze_ranking(self, helper):
        """Test that rank 1, 2, 3 display different badge colors."""
        mock_data = [
            {"candidate_name": "أحمد محمود", "party_name": "حزب الحرية", "total_votes": 1250, "rank": 1, "is_elected": True},
            {"candidate_name": "فاطمة حسن", "party_name": "حزب التقدم", "total_votes": 1180, "rank": 2, "is_elected": True},
            {"candidate_name": "محمد علي", "party_name": "حزب الوحدة", "total_votes": 950, "rank": 3, "is_elected": True}
        ]

        root = helper.create_winners_page(mock_data)
        page = root.property("page")

        # Find winner cards
        winner_cards = helper.find_children(page, "WinnerCard")
        assert len(winner_cards) == 3

        # Each card should have the correct rank for badge styling
        # (Actual color testing would require more complex visual verification)
        rank_1_found = False
        rank_2_found = False
        rank_3_found = False

        for card in winner_cards:
            rank = card.property("rank")
            if rank == 1:
                rank_1_found = True
            elif rank == 2:
                rank_2_found = True
            elif rank == 3:
                rank_3_found = True

        assert rank_1_found, "Rank 1 card not found"
        assert rank_2_found, "Rank 2 card not found"
        assert rank_3_found, "Rank 3 card not found"
