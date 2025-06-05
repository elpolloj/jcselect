"""
Tests for Enhanced Dashboard Features (Steps 1-10 of Dashboard Polish Specification)

This test module verifies the implementation of:
- Resource loading system with icons
- Enhanced theme system and Material 3 design
- CardTile component with animations and interactions
- Dashboard controller with live data and performance optimizations
- Status indicators and StatCard components
- Enhanced dashboard layout with real-time updates
- Navigation integration with keyboard shortcuts
- Performance optimizations including async loading and caching
- Accessibility features and keyboard navigation
- Final polish and comprehensive functionality

Test Categories:
- Visual/Component Tests: UI rendering and interaction
- Data Integration Tests: Controller and database integration
- Performance Tests: Loading times and animation smoothness
- Accessibility Tests: Keyboard navigation and screen reader support
- Navigation Tests: Route handling and shortcuts
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtCore import Qt, QTimer, QDateTime, QObject, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.mark.gui
class TestDashboardEnhancements:
    """Test suite for enhanced dashboard features."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])

    def test_icon_loading_system(self):
        """Test that icon resources load correctly (Step 1)."""
        import os
        
        # Test that Theme.qml contains icon loading functionality
        theme_path = "src/jcselect/ui/Theme.qml"
        assert os.path.exists(theme_path)
        
        with open(theme_path, 'r') as f:
            content = f.read()
            
        # Test icon path functions exist
        assert 'function iconPath(' in content
        assert 'function legacyIconPath(' in content
        
        # Test that icon directory exists
        icon_dir = "resources/icons"
        assert os.path.exists(icon_dir)
        
        # Test that key icons exist
        key_icons = ['voter-search.svg', 'ballot-count.svg', 'live-results.svg']
        for icon in key_icons:
            icon_path = os.path.join(icon_dir, icon)
            assert os.path.exists(icon_path), f"Icon {icon} not found"

    def test_theme_system_material3(self):
        """Test Material 3 theme system implementation (Step 2)."""
        import os
        
        theme_path = "src/jcselect/ui/Theme.qml"
        assert os.path.exists(theme_path)
        
        with open(theme_path, 'r') as f:
            content = f.read()
        
        # Test color system properties
        color_properties = [
            'property color primary', 'property color primaryText',
            'property color surface', 'property color success',
            'property color warning', 'property color error'
        ]
        for prop in color_properties:
            assert prop in content, f"Color property {prop} missing"
            
        # Test typography system
        font_properties = [
            'property font headlineLargeFont', 'property font titleMediumFont',
            'property font bodyMediumFont'
        ]
        for prop in font_properties:
            assert prop in content, f"Font property {prop} missing"
        
        # Test legacy compatibility
        legacy_properties = [
            'property int headlineLarge', 'property int bodySize',
            'property color primaryColor'
        ]
        for prop in legacy_properties:
            assert prop in content, f"Legacy property {prop} missing"
        
        # Test animation properties
        animation_properties = [
            'property int durationFast', 'property int durationMedium'
        ]
        for prop in animation_properties:
            assert prop in content, f"Animation property {prop} missing"

    def test_cardtile_component_features(self):
        """Test enhanced CardTile component functionality (Step 3)."""
        import os
        
        # Test properties exist in QML file
        cardtile_path = "src/jcselect/components/CardTile.qml"
        assert os.path.exists(cardtile_path)
        
        with open(cardtile_path, 'r') as f:
            content = f.read()
            
        # Test properties exist
        properties = [
            'property string title', 'property string subtitle', 'property string iconSource',
            'property int badgeCount', 'property bool badgeVisible', 'property color badgeColor',
            'property bool enabled', 'property bool loading', 'property real elevation',
            'property real cornerRadius', 'property color surfaceColor', 'property bool hovered',
            'property bool pressed', 'property string accessibleName', 'property string accessibleDescription',
            'property string tooltip'
        ]
        
        for prop in properties:
            assert prop in content, f"Property {prop} missing in CardTile.qml"
            
        # Verify key features are implemented
        assert 'PropertyAnimation' in content  # Animations
        assert 'Accessible.role' in content    # Accessibility
        assert 'Keys.onSpacePressed' in content  # Keyboard support
        assert 'MultiEffect' in content  # Shadow effects
        assert 'BusyIndicator' in content  # Loading state

    @patch('jcselect.controllers.dashboard_controller.get_session')
    def test_dashboard_controller_data_refresh(self, mock_session):
        """Test dashboard controller data refresh functionality (Step 4)."""
        from jcselect.controllers.dashboard_controller import DashboardController
        
        # Mock database session
        mock_session_instance = Mock()
        mock_session.return_value.__enter__ = Mock(return_value=mock_session_instance)
        mock_session.return_value.__exit__ = Mock(return_value=None)
        
        # Mock query results
        mock_session_instance.exec.return_value.first.return_value = 100
        
        # Create controller
        controller = DashboardController()
        
        # Test initial state
        assert controller._is_refreshing == False
        assert controller._total_voters_registered == 0
        
        # Test refresh
        controller.refreshDashboardData()
        
        # Should set refreshing state
        assert controller._is_refreshing == True
        
        # Wait for async completion (using QTimer.singleShot)
        QTest.qWait(100)
        
        # Verify data was updated
        assert controller._total_voters_registered == 100

    def test_status_indicator_component(self):
        """Test StatusIndicator component functionality (Step 5)."""
        # Test component file exists
        import os
        status_path = "src/jcselect/ui/components/StatusIndicator.qml"
        assert os.path.exists(status_path)
        
        with open(status_path, 'r') as f:
            content = f.read()
            
        # Verify key features
        assert 'property bool online' in content
        assert 'property bool syncing' in content
        assert 'RotationAnimator' in content  # Syncing animation

    def test_stat_card_component(self):
        """Test StatCard component with loading states (Step 5)."""
        import os
        stat_card_path = "src/jcselect/ui/components/StatCard.qml"
        assert os.path.exists(stat_card_path)
        
        with open(stat_card_path, 'r') as f:
            content = f.read()
            
        # Verify loading skeleton features
        assert 'property bool loading' in content
        assert 'PropertyAnimation' in content  # Shimmer animation
        assert 'visible: !root.loading' in content  # Loading state handling

    def test_dashboard_layout_integration(self):
        """Test enhanced dashboard layout (Step 6)."""
        import os
        dashboard_path = "src/jcselect/ui/AdminDashboard.qml"
        assert os.path.exists(dashboard_path)
        
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verify layout enhancements
        assert 'StatusIndicator' in content
        assert 'StatCard' in content
        assert 'GridLayout' in content
        assert 'accessibleName' in content  # Accessibility
        assert 'tooltip' in content
        
        # Verify Arabic labels (wrapped in qsTr())
        assert 'qsTr("البحث في الناخبين")' in content
        assert 'qsTr("فرز الأصوات")' in content
        assert 'qsTr("النتائج المباشرة")' in content
        
        # Verify component integrations
        assert 'dashboardController' in content
        assert 'CardTile' in content

    def test_navigation_integration(self):
        """Test navigation system integration (Step 7)."""
        from jcselect.controllers.dashboard_controller import DashboardController
        
        controller = DashboardController()
        
        # Test navigation methods exist
        assert hasattr(controller, 'openVoterSearch')
        assert hasattr(controller, 'openTallyCounting')
        assert hasattr(controller, 'openLiveResults')
        assert hasattr(controller, 'openSyncStatus')
        assert hasattr(controller, 'openAuditLogs')
        
        # Test signal emission
        with patch.object(controller, 'navigationRequested') as mock_signal:
            controller.openVoterSearch()
            mock_signal.emit.assert_called_with("voter_search")

    def test_performance_optimizations(self):
        """Test performance improvements (Step 8)."""
        from jcselect.controllers.dashboard_controller import DashboardController
        
        controller = DashboardController()
        
        # Test concurrent refresh prevention
        controller._is_refreshing = True
        initial_time = time.time()
        
        controller.refreshDashboardData()  # Should return immediately
        
        elapsed = time.time() - initial_time
        assert elapsed < 0.01  # Should be nearly instantaneous
        
        # Test async execution (using QTimer.singleShot)
        controller._is_refreshing = False
        controller.refreshDashboardData()
        
        # Should complete without blocking
        QTest.qWait(50)

    def test_accessibility_features(self):
        """Test accessibility and keyboard navigation (Step 9)."""
        # Test keyboard shortcuts in App.qml
        import os
        app_path = "src/jcselect/ui/App.qml"
        assert os.path.exists(app_path)
        
        with open(app_path, 'r') as f:
            content = f.read()
            
        # Verify keyboard shortcuts
        assert 'Ctrl+F' in content  # Voter search
        assert 'Ctrl+T' in content  # Tally counting
        assert 'Ctrl+R' in content  # Live results
        assert 'Ctrl+D' in content  # Dashboard
        
        # Test CardTile accessibility
        cardtile_path = "src/jcselect/components/CardTile.qml"
        with open(cardtile_path, 'r') as f:
            cardtile_content = f.read()
            
        assert 'Accessible.role: Accessible.Button' in cardtile_content
        assert 'Accessible.name' in cardtile_content
        assert 'Accessible.description' in cardtile_content
        assert 'activeFocusOnTab: true' in cardtile_content

    def test_component_loading_performance(self):
        """Test component loading times and memory usage."""
        import os
        import sys
        
        # Test QML file sizes (should be reasonable)
        cardtile_size = os.path.getsize("src/jcselect/components/CardTile.qml")
        assert cardtile_size < 15000  # Should be under 15KB
        
        dashboard_size = os.path.getsize("src/jcselect/ui/AdminDashboard.qml")
        assert dashboard_size < 20000  # Should be under 20KB
        
        # Test memory usage of controller
        from jcselect.controllers.dashboard_controller import DashboardController
        
        initial_memory = sys.getsizeof(DashboardController)
        controller = DashboardController()
        controller_memory = sys.getsizeof(controller)
        
        # Controller should not use excessive memory
        assert controller_memory - initial_memory < 10000  # Under 10KB overhead

    def test_animation_performance(self):
        """Test animation performance and smoothness."""
        import os
        
        # Test that animation durations are reasonable by checking Theme.qml
        theme_path = "src/jcselect/ui/Theme.qml"
        assert os.path.exists(theme_path)
        
        with open(theme_path, 'r') as f:
            content = f.read()
        
        # Test animation duration properties exist
        assert 'durationFast' in content
        assert 'durationMedium' in content
        assert 'durationSlow' in content
        
        # Check that reasonable values are set (look for typical animation ranges)
        # Fast animations should be under 200ms, medium under 300ms, slow under 500ms
        import re
        
        # Extract duration values (simplified check)
        fast_match = re.search(r'durationFast:\s*(\d+)', content)
        if fast_match:
            fast_duration = int(fast_match.group(1))
            assert fast_duration <= 200, f"Fast duration {fast_duration}ms too long"
            
        medium_match = re.search(r'durationMedium:\s*(\d+)', content)
        if medium_match:
            medium_duration = int(medium_match.group(1))
            assert medium_duration <= 300, f"Medium duration {medium_duration}ms too long"

    @patch('jcselect.controllers.dashboard_controller.get_session')
    def test_error_handling(self, mock_session):
        """Test error handling in dashboard operations."""
        from jcselect.controllers.dashboard_controller import DashboardController
        
        # Mock database error
        mock_session.side_effect = Exception("Database connection failed")
        
        controller = DashboardController()
        
        # Test error handling in refresh
        controller.refreshDashboardData()
        QTest.qWait(100)
        
        # Should set error message
        assert len(controller._error_message) > 0
        assert "Failed to refresh data" in controller._error_message

    def test_rtl_layout_support(self):
        """Test right-to-left layout support for Arabic interface."""
        import os
        
        # Test AdminDashboard has Arabic content
        dashboard_path = "src/jcselect/ui/AdminDashboard.qml"
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Should contain Arabic text
        assert 'لوحة إدارة الانتخابات' in content
        assert 'البحث في الناخبين' in content
        assert 'فرز الأصوات' in content
        
        # Test theme has RTL helpers
        theme_path = "src/jcselect/ui/Theme.qml"
        with open(theme_path, 'r') as f:
            theme_content = f.read()
            
        assert 'leftMargin' in theme_content
        assert 'rightMargin' in theme_content

    def test_integration_with_existing_features(self):
        """Test integration with existing application features."""
        # Test that enhanced dashboard doesn't break existing functionality
        
        # Test voter search integration
        import os
        assert os.path.exists("src/jcselect/ui/VoterSearchWindow.qml")
        assert os.path.exists("src/jcselect/controllers/voter_search_controller.py")
        
        # Test tally counting integration  
        assert os.path.exists("src/jcselect/ui/TallyCountingWindow.qml")
        assert os.path.exists("src/jcselect/controllers/tally_controller.py")
        
        # Test results integration
        assert os.path.exists("src/jcselect/ui/ResultsWindow.qml")

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any created objects
        pass


@pytest.mark.performance
class TestDashboardPerformance:
    """Performance-specific tests for dashboard enhancements."""
    
    def test_dashboard_load_time(self):
        """Test that dashboard loads within acceptable time."""
        from jcselect.controllers.dashboard_controller import DashboardController
        
        start_time = time.time()
        controller = DashboardController()
        end_time = time.time()
        
        load_time = end_time - start_time
        assert load_time < 1.0  # Should load within 1 second
    
    @patch('jcselect.controllers.dashboard_controller.get_session')
    def test_data_refresh_time(self, mock_session):
        """Test that data refresh completes within acceptable time."""
        from jcselect.controllers.dashboard_controller import DashboardController
        
        # Mock fast database response
        mock_session_instance = Mock()
        mock_session.return_value.__enter__ = Mock(return_value=mock_session_instance)
        mock_session.return_value.__exit__ = Mock(return_value=None)
        mock_session_instance.exec.return_value.first.return_value = 100
        
        controller = DashboardController()
        
        start_time = time.time()
        controller.refreshDashboardData()
        QTest.qWait(200)  # Wait for async completion
        end_time = time.time()
        
        refresh_time = end_time - start_time
        assert refresh_time < 2.0  # Should refresh within 2 seconds


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 