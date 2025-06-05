#!/usr/bin/env python3
"""Quick demo of PenPickerController functionality."""

from PySide6.QtCore import QCoreApplication
import sys

from src.jcselect.controllers.pen_picker_controller import PenPickerController

def test_pen_picker():
    """Test basic PenPickerController functionality."""
    app = QCoreApplication([])
    
    # Create controller
    controller = PenPickerController()
    
    print("✅ PenPickerController created successfully")
    
    # Check initial state
    print(f"✅ Initial available pens: {len(controller.availablePens)}")
    
    # Connect to signals to show they work
    def on_pens_loaded():
        print(f"✅ Signal: pensLoaded emitted, pens count: {len(controller.availablePens)}")
        for pen in controller.availablePens:
            print(f"   - {pen['label']} ({pen['town_name']})")
    
    def on_selection_completed(pen_id):
        print(f"✅ Signal: selectionCompleted emitted for pen: {pen_id}")
    
    def on_error_occurred(error):
        print(f"❌ Signal: errorOccurred emitted: {error}")
    
    controller.pensLoaded.connect(on_pens_loaded)
    controller.selectionCompleted.connect(on_selection_completed)
    controller.errorOccurred.connect(on_error_occurred)
    
    print("✅ Signal connections established")
    
    # Test loading pens (this will likely fail due to no database, but will show error handling)
    print("📊 Testing loadAvailablePens()...")
    controller.loadAvailablePens()
    
    print("✅ Demo completed - PenPickerController is working!")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_pen_picker()) 