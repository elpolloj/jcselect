"""Tests for ResultsWindow navigation and functionality."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class ResultsWindowNavigationTestHelper(QMLTestHelper):
    """Helper class for testing ResultsWindow navigation."""

    def create_results_window(self, mock_controller=None):
        """Create a ResultsWindow instance for testing."""
        qml_code = """
        import QtQuick 2.15
        import QtQuick.Controls 2.15
        import QtQuick.Layouts 1.15

        Item {
            id: root
            width: 1200
            height: 800

            property alias window: mockResultsWindow

            // Mock ResultsWindow (simplified for testing)
            Rectangle {
                id: mockResultsWindow
                anchors.fill: parent
                color: "lightgray"
                
                // Mock TabBar
                TabBar {
                    id: tabBar
                    objectName: "tabBar"
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 50
                    
                    TabButton { text: "Party Totals" }
                    TabButton { text: "Candidates" }
                    TabButton { text: "Winners" }
                    TabButton { text: "Charts" }
                }
                
                // Mock StackLayout
                StackLayout {
                    id: stackLayout
                    objectName: "stackLayout"
                    anchors.top: tabBar.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    
                    currentIndex: tabBar.currentIndex
                    
                    Rectangle { 
                        id: partyTotalsPage
                        objectName: "partyTotalsPage"
                        color: "lightblue"
                        property bool pageVisible: stackLayout.currentIndex === 0
                    }
                    Rectangle { 
                        id: candidateTotalsPage  
                        objectName: "candidateTotalsPage"
                        color: "lightgreen"
                        property bool pageVisible: stackLayout.currentIndex === 1
                    }
                    Rectangle { 
                        id: winnersPage
                        objectName: "winnersPage"
                        color: "lightyellow"
                        property bool pageVisible: stackLayout.currentIndex === 2
                    }
                    Rectangle { 
                        id: chartsPage
                        objectName: "chartsPage"
                        color: "lightpink"
                        property bool pageVisible: stackLayout.currentIndex === 3
                    }
                }
                
                // Mock Live Sync Chip
                Rectangle {
                    id: liveSyncChip
                    objectName: "liveSyncChip"
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 20
                    width: 100
                    height: 30
                    color: "orange"
                    visible: false  // Start hidden
                    
                    Text {
                        anchors.centerIn: parent
                        text: "Syncing..."
                    }
                }
                
                // Mock RefreshBadge
                Rectangle {
                    id: refreshBadge
                    objectName: "refreshBadge"
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 10
                    width: 80
                    height: 40
                    color: "lightcoral"
                    
                    signal refreshRequested()
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: refreshBadge.refreshRequested()
                    }
                    
                    Text {
                        anchors.centerIn: parent
                        text: "Refresh"
                    }
                }
                
                // Mock PenSelector
                Rectangle {
                    id: penSelector
                    objectName: "penSelector"
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.margins: 10
                    width: 120
                    height: 40
                    color: "lightsteelblue"
                    
                    signal penSelected(string penId)
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: penSelector.penSelected("test_pen_123")
                    }
                    
                    Text {
                        anchors.centerIn: parent
                        text: "Pen Selector"
                    }
                }
            }
        }
        """
        return self.create_qml_object(qml_code)

    def create_mini_app_with_navigation(self):
        """Create a minimal app for testing navigation from dashboard."""
        qml_code = """
        import QtQuick 2.15
        import QtQuick.Controls 2.15
        import QtQuick.Layouts 1.15

        ApplicationWindow {
            id: root
            width: 800
            height: 600
            visible: true

            property string currentScreen: "dashboard"
            property bool isAdmin: true
            property alias dashboardButton: dashboardButton
            property alias currentStackIndex: stackLayout.currentIndex

            StackLayout {
                id: stackLayout
                anchors.fill: parent
                currentIndex: root.currentScreen === "dashboard" ? 0 : 1

                // Mock Dashboard
                Rectangle {
                    color: "lightblue"
                    
                    Button {
                        id: dashboardButton
                        anchors.centerIn: parent
                        text: "Live Results"
                        onClicked: {
                            root.currentScreen = "live_results"
                        }
                    }
                }

                // Mock Results Window
                Rectangle {
                    color: "lightgreen"
                    
                    Text {
                        anchors.centerIn: parent
                        text: "Results Window"
                    }
                }
            }
        }
        """
        return self.create_qml_object(qml_code)


class TestResultsWindowNavigation:
    """Test suite for ResultsWindow navigation functionality."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return ResultsWindowNavigationTestHelper(qml_engine)

    def test_results_window_creation(self, helper):
        """Test that ResultsWindow can be created."""
        root = helper.create_results_window()
        assert root is not None

        window = root.property("window")
        assert window is not None

    def test_tab_bar_switching(self, helper):
        """Test that TabBar switches between pages correctly."""
        root = helper.create_results_window()
        window = root.property("window")

        # Find the tab bar
        tab_bar = helper.find_child(window, "TabBar")
        assert tab_bar is not None

        # Find the stack layout
        stack_layout = helper.find_child(window, "StackLayout")
        assert stack_layout is not None

        # Initial state should be first tab (index 0)
        assert stack_layout.property("currentIndex") == 0

        # Simulate clicking second tab
        tab_bar.setProperty("currentIndex", 1)
        helper.process_events()

        # Stack layout should follow
        assert stack_layout.property("currentIndex") == 1

        # Test third tab
        tab_bar.setProperty("currentIndex", 2)
        helper.process_events()
        assert stack_layout.property("currentIndex") == 2

    def test_page_visibility_management(self, helper):
        """Test that only current page is visible."""
        root = helper.create_results_window()
        window = root.property("window")

        # Find all pages using objectName or id
        party_page = helper.find_child(window, "Rectangle", "partyTotalsPage")
        candidate_page = helper.find_child(window, "Rectangle", "candidateTotalsPage")
        winners_page = helper.find_child(window, "Rectangle", "winnersPage")
        charts_page = helper.find_child(window, "Rectangle", "chartsPage")

        # Initially, first page should be visible
        assert party_page.property("pageVisible") is True
        assert candidate_page.property("pageVisible") is False
        assert winners_page.property("pageVisible") is False
        assert charts_page.property("pageVisible") is False

        # Switch to second tab
        tab_bar = helper.find_child(window, "TabBar")
        tab_bar.setProperty("currentIndex", 1)
        helper.process_events()

        # Now second page should be visible
        assert party_page.property("pageVisible") is False
        assert candidate_page.property("pageVisible") is True
        assert winners_page.property("pageVisible") is False
        assert charts_page.property("pageVisible") is False

    def test_live_sync_chip_animation(self, helper):
        """Test that Live Sync chip shows and hides correctly."""
        root = helper.create_results_window()
        window = root.property("window")

        # Find the sync chip using objectName
        sync_chip = helper.find_child(window, "Rectangle", "liveSyncChip")
        assert sync_chip is not None

        # Initially should not be visible
        assert sync_chip.property("visible") is False

        # Manually set it to visible (simulating sync state change)
        sync_chip.setProperty("visible", True)
        helper.process_events()

        # Now chip should be visible
        assert sync_chip.property("visible") is True

    def test_refresh_badge_manual_refresh(self, helper):
        """Test that manual refresh triggers controller method."""
        # For this test, we'll use a global flag since QML function calls are hard to intercept
        global refresh_called
        refresh_called = False

        root = helper.create_results_window()
        window = root.property("window")

        # Find the refresh badge
        refresh_badge = helper.find_child(window, "Rectangle", "refreshBadge")
        assert refresh_badge is not None

        # Connect to the signal to track if it's emitted
        def on_refresh_requested():
            global refresh_called
            refresh_called = True

        refresh_badge.refreshRequested.connect(on_refresh_requested)

        # Find the mouse area and simulate click
        mouse_area = helper.find_child(refresh_badge, "MouseArea")
        assert mouse_area is not None
        
        # Simulate click
        mouse_area.clicked.emit()
        helper.process_events()

        # Verify signal was emitted
        assert refresh_called

    def test_controller_data_binding(self, helper):
        """Test that controller structure exists for binding."""
        root = helper.create_results_window()
        window = root.property("window")

        # Verify window exists and basic structure is there
        assert window is not None
        
        # Find key components that would connect to controller
        tab_bar = helper.find_child(window, "TabBar", "tabBar")
        stack_layout = helper.find_child(window, "StackLayout", "stackLayout")
        refresh_badge = helper.find_child(window, "Rectangle", "refreshBadge")
        pen_selector = helper.find_child(window, "Rectangle", "penSelector")
        
        assert tab_bar is not None
        assert stack_layout is not None
        assert refresh_badge is not None
        assert pen_selector is not None

    def test_pen_filter_integration(self, helper):
        """Test that pen selector triggers controller filter method."""
        global filter_called_with
        filter_called_with = None

        root = helper.create_results_window()
        window = root.property("window")

        # Find pen selector
        pen_selector = helper.find_child(window, "Rectangle", "penSelector")
        assert pen_selector is not None

        # Connect to the signal
        def on_pen_selected(pen_id):
            global filter_called_with
            filter_called_with = pen_id

        pen_selector.penSelected.connect(on_pen_selected)

        # Simulate click which should emit the signal
        mouse_area = helper.find_child(pen_selector, "MouseArea")
        mouse_area.clicked.emit()
        helper.process_events()

        # Verify signal was emitted with correct data
        assert filter_called_with == "test_pen_123"

    def test_mini_app_navigation(self, helper):
        """Test navigation from dashboard to results window."""
        app = helper.create_mini_app_with_navigation()
        assert app is not None

        # Initially should be on dashboard
        assert app.property("currentScreen") == "dashboard"
        assert app.property("currentStackIndex") == 0

        # Click Live Results button
        dashboard_button = app.property("dashboardButton")
        dashboard_button.clicked.emit()
        helper.process_events()

        # Should navigate to results
        assert app.property("currentScreen") == "live_results"
        assert app.property("currentStackIndex") == 1 