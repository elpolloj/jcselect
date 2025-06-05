#!/usr/bin/env python3
"""
Smoke test for Live Results navigation.

This script validates that the Live Results implementation is accessible
and that the navigation integration works at the import level.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def setup_test_environment():
    """Set up test environment variables."""
    os.environ["JCSELECT_ENV"] = "test"
    os.environ["JCSELECT_DB_URL"] = "sqlite:///:memory:"


def main():
    """Main entry point for smoke test."""
    print("🚀 Starting Live Results smoke test...")
    
    setup_test_environment()
    
    try:
        # Test 1: Import all required controllers
        print("📦 Testing imports...")
        from jcselect.controllers.dashboard_controller import DashboardController
        from jcselect.controllers.results_controller import ResultsController
        print("✅ Core controllers imported successfully")
        
        # Test 2: Create controller instances
        print("🔧 Testing controller instantiation...")
        dashboard_controller = DashboardController()
        results_controller = ResultsController()
        print("✅ Controllers instantiated successfully")
        
        # Test 3: Check required methods exist
        print("🔍 Testing required methods...")
        assert hasattr(dashboard_controller, 'openLiveResults'), "openLiveResults method missing"
        assert hasattr(dashboard_controller, 'hasNewResults'), "hasNewResults property missing"
        assert hasattr(results_controller, 'hasNewResults'), "hasNewResults property missing"
        assert hasattr(results_controller, 'autoRefreshEnabled'), "autoRefreshEnabled property missing"
        assert hasattr(results_controller, 'refreshNow'), "refreshNow method missing"
        print("✅ All required methods found")
        
        # Test 4: Test property values
        print("⚙️ Testing property defaults...")
        assert dashboard_controller.hasNewResults is False, "hasNewResults should start as False"
        assert results_controller.hasNewResults is False, "hasNewResults should start as False"
        assert results_controller.autoRefreshEnabled is True, "autoRefreshEnabled should start as True"
        print("✅ Property defaults correct")
        
        # Test 5: Test method invocation
        print("🎯 Testing method calls...")
        dashboard_controller.openLiveResults()  # Should emit signal
        results_controller.refreshNow()  # Should attempt refresh
        print("✅ Method calls successful")
        
        # Test 6: Test property setters
        print("🔄 Testing property modifications...")
        dashboard_controller._set_has_new_results(True)
        assert dashboard_controller.hasNewResults is True, "hasNewResults setter failed"
        
        results_controller._set_has_new_results(True)
        assert results_controller.hasNewResults is True, "hasNewResults setter failed"
        
        results_controller._set_auto_refresh_enabled(False)
        assert results_controller.autoRefreshEnabled is False, "autoRefreshEnabled setter failed"
        print("✅ Property modifications successful")
        
        # Test 7: Test flag clearing
        print("🧹 Testing flag clearing...")
        results_controller._clear_new_results_flag()
        assert results_controller.hasNewResults is False, "Flag clearing failed"
        print("✅ Flag clearing successful")
        
        print("🎉 LIVE RESULTS ROUTE OK")
        return 0
        
    except Exception as e:
        print(f"💥 SMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 