"""Helper classes for QML component testing."""
from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, qmlRegisterType
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


class QMLTestHelper:
    """Base helper class for testing QML components."""
    
    def __init__(self, qml_engine: QQmlApplicationEngine):
        """Initialize with QML engine."""
        self.engine = qml_engine
        
    def create_qml_object(self, qml_code: str) -> QQuickItem:
        """Create a QML object from QML code."""
        # Register the components module
        self.engine.addImportPath("src/jcselect/ui")
        
        # Create component from string using QQmlComponent
        component = QQmlComponent(self.engine)
        component.setData(qml_code.encode('utf-8'), QUrl())
        
        if component.isError():
            errors = component.errors()
            error_msgs = [f"Line {err.line()}: {err.description()}" for err in errors]
            raise RuntimeError(f"QML errors: {'; '.join(error_msgs)}")
        
        # Create object
        obj = component.create()
        if obj is None:
            raise RuntimeError("Failed to create QML object")
            
        return obj
    
    def find_child(self, parent: QQuickItem, class_name: str, name_hint: str = None) -> QQuickItem:
        """Find a child item by class name."""
        if parent is None:
            return None
            
        # Check if parent matches
        if parent.metaObject().className() == class_name:
            return parent
            
        # Search children recursively
        for child in parent.childItems():
            result = self.find_child(child, class_name, name_hint)
            if result:
                return result
                
        return None
    
    def find_children(self, parent: QQuickItem, class_name: str) -> list[QQuickItem]:
        """Find all child items by class name."""
        if parent is None:
            return []
            
        results = []
        
        # Check if parent matches
        if parent.metaObject().className() == class_name:
            results.append(parent)
            
        # Search children recursively
        for child in parent.childItems():
            results.extend(self.find_children(child, class_name))
                
        return results
    
    def find_child_by_property(self, parent: QQuickItem, prop_name: str, prop_value: Any) -> QQuickItem:
        """Find child by property value."""
        if parent is None:
            return None
            
        # Check if parent matches
        if parent.property(prop_name) == prop_value:
            return parent
            
        # Search children recursively
        for child in parent.childItems():
            result = self.find_child_by_property(child, prop_name, prop_value)
            if result:
                return result
                
        return None
    
    def click_item(self, item: QQuickItem) -> None:
        """Simulate clicking on an item."""
        if item is None:
            return
            
        # Get the center point of the item
        center_x = item.width() / 2
        center_y = item.height() / 2
        
        # Convert to global coordinates if possible
        try:
            pos = item.mapToGlobal(center_x, center_y)
            QTest.mouseClick(item.window(), 1, 0, pos.toPoint())  # Qt.LeftButton = 1
        except:
            # Fallback to simple click without position
            QTest.mouseClick(item.window(), 1)
    
    def process_events(self) -> None:
        """Process pending events."""
        QApplication.processEvents()


@pytest.fixture(scope="function")
def qml_engine():
    """Create QML engine for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    engine = QQmlApplicationEngine()
    
    # Add import paths
    engine.addImportPath("src/jcselect/ui")
    
    yield engine
    
    # Cleanup
    engine.clearComponentCache() 