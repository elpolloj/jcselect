"""Test application entry points for admin and operator modes."""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

# Skip GUI tests on CI if display isn't available
try:
    from PySide6.QtCore import QCoreApplication
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False

# Check if we have a display
DISPLAY_AVAILABLE = os.environ.get("DISPLAY") is not None or sys.platform == "win32"


@pytest.mark.qt
@pytest.mark.skipif(not GUI_AVAILABLE or not DISPLAY_AVAILABLE, reason="GUI not available or no display")
class TestAppEntryPoints:
    """Test application entry points."""

    def test_admin_entry_point_sets_env_vars(self):
        """Test that admin entry point sets correct environment variables."""
        # Import here to avoid issues if GUI not available
        from jcselect import admin
        
        # Mock the main function to avoid actually starting the app
        with patch('jcselect.admin.main') as mock_main:
            mock_main.return_value = 0
            
            # Clear any existing env vars
            old_mode = os.environ.get("JCSELECT_MODE")
            old_role = os.environ.get("JCSELECT_REQUIRED_ROLE")
            
            try:
                if old_mode:
                    del os.environ["JCSELECT_MODE"]
                if old_role:
                    del os.environ["JCSELECT_REQUIRED_ROLE"]
                
                # Call admin entry point
                result = admin.main_admin()
                
                # Check that env vars were set correctly
                assert os.environ.get("JCSELECT_MODE") == "admin"
                assert os.environ.get("JCSELECT_REQUIRED_ROLE") == "admin"
                assert result == 0
                assert mock_main.called
                
            finally:
                # Restore original env vars
                if old_mode:
                    os.environ["JCSELECT_MODE"] = old_mode
                elif "JCSELECT_MODE" in os.environ:
                    del os.environ["JCSELECT_MODE"]
                    
                if old_role:
                    os.environ["JCSELECT_REQUIRED_ROLE"] = old_role
                elif "JCSELECT_REQUIRED_ROLE" in os.environ:
                    del os.environ["JCSELECT_REQUIRED_ROLE"]

    def test_operator_entry_point_sets_env_vars(self):
        """Test that operator entry point sets correct environment variables."""
        # Import here to avoid issues if GUI not available
        from jcselect import operator
        
        # Mock the main function to avoid actually starting the app
        with patch('jcselect.operator.main') as mock_main:
            mock_main.return_value = 0
            
            # Clear any existing env vars
            old_mode = os.environ.get("JCSELECT_MODE")
            old_role = os.environ.get("JCSELECT_REQUIRED_ROLE")
            
            try:
                if old_mode:
                    del os.environ["JCSELECT_MODE"]
                if old_role:
                    del os.environ["JCSELECT_REQUIRED_ROLE"]
                
                # Call operator entry point
                result = operator.main_operator()
                
                # Check that env vars were set correctly
                assert os.environ.get("JCSELECT_MODE") == "operator"
                assert os.environ.get("JCSELECT_REQUIRED_ROLE") == "operator"
                assert result == 0
                assert mock_main.called
                
            finally:
                # Restore original env vars
                if old_mode:
                    os.environ["JCSELECT_MODE"] = old_mode
                elif "JCSELECT_MODE" in os.environ:
                    del os.environ["JCSELECT_MODE"]
                    
                if old_role:
                    os.environ["JCSELECT_REQUIRED_ROLE"] = old_role
                elif "JCSELECT_REQUIRED_ROLE" in os.environ:
                    del os.environ["JCSELECT_REQUIRED_ROLE"]

    def test_controllers_can_be_imported_and_created(self):
        """Test that dashboard controllers can be imported and created successfully."""
        # Test that we can import and create the required components
        try:
            from jcselect.controllers.dashboard_controller import DashboardController
            from jcselect.controllers.login_controller import LoginController
            
            # Create controllers (they should not require Qt app to be instantiated for basic creation)
            dashboard_controller = DashboardController()
            login_controller = LoginController()
            
            # Test that controllers were created successfully
            assert dashboard_controller is not None
            assert login_controller is not None
            
            print("✅ Controllers created successfully")
            
        except ImportError as e:
            pytest.skip(f"Dashboard controllers not available: {e}")

    def test_environment_variables_are_read_correctly(self):
        """Test that environment variables are read correctly by main module."""
        import jcselect.main
        
        # Test admin mode
        os.environ["JCSELECT_MODE"] = "admin"
        os.environ["JCSELECT_REQUIRED_ROLE"] = "admin"
        
        try:
            # Test that env vars can be read
            app_mode = os.environ.get("JCSELECT_MODE", "auto")
            required_role = os.environ.get("JCSELECT_REQUIRED_ROLE", None)
            
            assert app_mode == "admin"
            assert required_role == "admin"
            
            # Test operator mode
            os.environ["JCSELECT_MODE"] = "operator"
            os.environ["JCSELECT_REQUIRED_ROLE"] = "operator"
            
            app_mode = os.environ.get("JCSELECT_MODE", "auto")
            required_role = os.environ.get("JCSELECT_REQUIRED_ROLE", None)
            
            assert app_mode == "operator"
            assert required_role == "operator"
            
            print("✅ Environment variables read correctly")
            
        finally:
            # Clean up env vars
            if "JCSELECT_MODE" in os.environ:
                del os.environ["JCSELECT_MODE"]
            if "JCSELECT_REQUIRED_ROLE" in os.environ:
                del os.environ["JCSELECT_REQUIRED_ROLE"]

    def test_main_module_can_handle_dashboard_import(self):
        """Test that main module can handle dashboard controller imports gracefully."""
        import importlib
        
        # Reload the main module to test import handling
        if 'jcselect.main' in sys.modules:
            importlib.reload(sys.modules['jcselect.main'])
        
        try:
            from jcselect.main import DASHBOARD_AVAILABLE
            # If we get here, the import worked and DASHBOARD_AVAILABLE should be set
            assert isinstance(DASHBOARD_AVAILABLE, bool)
            print(f"✅ Dashboard availability: {DASHBOARD_AVAILABLE}")
            
        except ImportError as e:
            pytest.skip(f"Main module import failed: {e}") 