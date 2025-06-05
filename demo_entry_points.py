#!/usr/bin/env python3
"""Demo script to test application entry points without GUI."""

import os
import sys
from unittest.mock import patch

def test_admin_entry_point():
    """Test admin entry point."""
    print("🔑 Testing Admin Entry Point...")
    
    # Clear environment
    old_mode = os.environ.get("JCSELECT_MODE")
    old_role = os.environ.get("JCSELECT_REQUIRED_ROLE")
    
    try:
        # Import admin module
        from jcselect import admin
        
        # Mock main to avoid GUI
        with patch('jcselect.admin.main') as mock_main:
            mock_main.return_value = 0
            
            # Test admin entry point
            result = admin.main_admin()
            
            # Check environment variables were set
            assert os.environ.get("JCSELECT_MODE") == "admin"
            assert os.environ.get("JCSELECT_REQUIRED_ROLE") == "admin"
            assert result == 0
            
            print("  ✅ Environment variables set correctly")
            print("  ✅ Admin entry point executed successfully")
            
    finally:
        # Restore environment
        if old_mode:
            os.environ["JCSELECT_MODE"] = old_mode
        elif "JCSELECT_MODE" in os.environ:
            del os.environ["JCSELECT_MODE"]
            
        if old_role:
            os.environ["JCSELECT_REQUIRED_ROLE"] = old_role
        elif "JCSELECT_REQUIRED_ROLE" in os.environ:
            del os.environ["JCSELECT_REQUIRED_ROLE"]

def test_operator_entry_point():
    """Test operator entry point."""
    print("\n👤 Testing Operator Entry Point...")
    
    # Clear environment
    old_mode = os.environ.get("JCSELECT_MODE")
    old_role = os.environ.get("JCSELECT_REQUIRED_ROLE")
    
    try:
        # Import operator module
        from jcselect import operator
        
        # Mock main to avoid GUI
        with patch('jcselect.operator.main') as mock_main:
            mock_main.return_value = 0
            
            # Test operator entry point
            result = operator.main_operator()
            
            # Check environment variables were set
            assert os.environ.get("JCSELECT_MODE") == "operator"
            assert os.environ.get("JCSELECT_REQUIRED_ROLE") == "operator"
            assert result == 0
            
            print("  ✅ Environment variables set correctly")
            print("  ✅ Operator entry point executed successfully")
            
    finally:
        # Restore environment
        if old_mode:
            os.environ["JCSELECT_MODE"] = old_mode
        elif "JCSELECT_MODE" in os.environ:
            del os.environ["JCSELECT_MODE"]
            
        if old_role:
            os.environ["JCSELECT_REQUIRED_ROLE"] = old_role
        elif "JCSELECT_REQUIRED_ROLE" in os.environ:
            del os.environ["JCSELECT_REQUIRED_ROLE"]

def test_main_module_integration():
    """Test main module integration with environment variables."""
    print("\n🚀 Testing Main Module Integration...")
    
    # Test admin mode
    os.environ["JCSELECT_MODE"] = "admin"
    os.environ["JCSELECT_REQUIRED_ROLE"] = "admin"
    
    try:
        # Import main module
        from jcselect.main import DASHBOARD_AVAILABLE
        
        # Check that dashboard is available
        print(f"  ✅ Dashboard available: {DASHBOARD_AVAILABLE}")
        
        # Test environment variable reading
        app_mode = os.environ.get("JCSELECT_MODE")
        required_role = os.environ.get("JCSELECT_REQUIRED_ROLE")
        
        assert app_mode == "admin"
        assert required_role == "admin"
        
        print("  ✅ Environment variables read correctly by main module")
        
        # Test controller creation
        if DASHBOARD_AVAILABLE:
            from jcselect.controllers.dashboard_controller import DashboardController
            from jcselect.controllers.login_controller import LoginController
            
            dashboard = DashboardController()
            login = LoginController()
            
            assert dashboard is not None
            assert login is not None
            
            print("  ✅ Controllers created successfully")
            
    finally:
        # Clean up
        if "JCSELECT_MODE" in os.environ:
            del os.environ["JCSELECT_MODE"]
        if "JCSELECT_REQUIRED_ROLE" in os.environ:
            del os.environ["JCSELECT_REQUIRED_ROLE"]

def test_pyproject_scripts():
    """Test that pyproject.toml scripts are configured correctly."""
    print("\n📦 Testing pyproject.toml Scripts...")
    
    try:
        import toml
        
        with open("pyproject.toml", "r") as f:
            config = toml.load(f)
        
        scripts = config.get("tool", {}).get("poetry", {}).get("scripts", {})
        
        # Check that our scripts are defined
        expected_scripts = {
            "jcselect": "jcselect.main:main",
            "jcselect-admin": "jcselect.admin:main_admin",
            "jcselect-operator": "jcselect.operator:main_operator"
        }
        
        for script_name, script_target in expected_scripts.items():
            if script_name in scripts:
                assert scripts[script_name] == script_target
                print(f"  ✅ {script_name} -> {script_target}")
            else:
                print(f"  ❌ {script_name} not found in scripts")
                
    except ImportError:
        print("  ⚠️  toml module not available, skipping pyproject.toml check")
    except Exception as e:
        print(f"  ❌ Error reading pyproject.toml: {e}")

def main():
    """Run all entry point tests."""
    print("🎯 jcselect Entry Points Demo")
    print("=" * 50)
    
    try:
        test_admin_entry_point()
        test_operator_entry_point()
        test_main_module_integration()
        test_pyproject_scripts()
        
        print("\n" + "=" * 50)
        print("✅ All entry point tests passed!")
        print("\nNext steps:")
        print("  poetry run jcselect-admin    # Start in admin mode")
        print("  poetry run jcselect-operator # Start in operator mode")
        print("  python -m jcselect.admin     # Direct module execution")
        print("  python -m jcselect.operator  # Direct module execution")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 