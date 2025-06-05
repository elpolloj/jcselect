import QtQuick 2.15
import QtQuick.Effects
import jcselect.ui 1.0

Item {
    id: root
    
    // Public properties
    property string source: ""
    property color color: Theme.onSurface
    property real iconSize: 24
    
    width: iconSize
    height: iconSize
    
    // High-quality SVG rendering with proper antialiasing
    Image {
        id: svgImage
        anchors.fill: parent
        source: root.source
        
        // Critical rendering properties for crisp SVG display
        fillMode: Image.PreserveAspectFit
        smooth: true
        antialiasing: true
        
        // 2x resolution for high DPI displays
        sourceSize: Qt.size(root.iconSize * 2, root.iconSize * 2)
        
        // Enable layer for colorization
        layer.enabled: true
        layer.effect: MultiEffect {
            colorization: 1.0
            colorizationColor: root.color
        }
        
        // Error handling for missing icons
        onStatusChanged: {
            if (status === Image.Error) {
                console.warn("Failed to load SVG icon:", root.source)
            }
        }
    }
} 