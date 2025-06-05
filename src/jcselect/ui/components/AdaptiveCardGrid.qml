import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0

Flickable {
    id: root
    
    // Properties for the grid
    property int cardWidth: 280
    property int cardHeight: 160
    property alias spacing: flow.spacing
    property alias contentItem: flow
    default property alias children: flow.children  // Properly handle children
    
    // Calculated properties
    property int maxColumns: Math.max(1, Math.floor(width / (cardWidth + spacing)))
    property int actualColumns: Math.min(maxColumns, flow.children.length)
    
    // Flickable properties
    boundsBehavior: Flickable.StopAtBounds
    contentHeight: flow.childrenRect.height + spacing * 2
    contentWidth: width
    clip: true
    
    // Remove scrollbars by making them transparent
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        opacity: 0
    }
    
    ScrollBar.horizontal: ScrollBar {
        policy: ScrollBar.AlwaysOff
    }
    
    // Main layout container
    Flow {
        id: flow
        width: parent.width
        spacing: Theme.spacing * 2
        
        // RTL support as specified
        flow: Qt.RightToLeft
        layoutDirection: Qt.RightToLeft
        
        // Enable RTL mirroring for Arabic interface
        LayoutMirroring.enabled: true
        LayoutMirroring.childrenInherit: true
        
        // Automatic column calculation based on window width
        onWidthChanged: {
            root.updateLayout()
        }
        
        Component.onCompleted: {
            root.updateLayout()
        }
    }
    
    // Function to update layout calculations
    function updateLayout() {
        // Recalculate columns based on available width
        var availableWidth = width - (spacing * 2)  // Account for margins
        var columns = Math.floor(availableWidth / (cardWidth + spacing))
        maxColumns = Math.max(1, columns)
    }
    
    // Smooth scrolling with mouse wheel
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton
        propagateComposedEvents: true  // Let child mouse events work
        
        onWheel: function(wheel) {
            var delta = wheel.angleDelta.y / 120
            var scrollAmount = 60  // pixels per wheel step
            
            if (delta > 0) {
                // Scroll up
                root.contentY = Math.max(0, root.contentY - scrollAmount)
            } else {
                // Scroll down
                var maxY = Math.max(0, root.contentHeight - root.height)
                root.contentY = Math.min(maxY, root.contentY + scrollAmount)
            }
        }
    }
    
    // Keyboard navigation support
    focus: true
    
    Keys.onPressed: function(event) {
        switch (event.key) {
            case Qt.Key_Up:
                if (root.contentY > 0) {
                    root.contentY = Math.max(0, root.contentY - 60)
                }
                event.accepted = true
                break
            case Qt.Key_Down:
                var maxY = Math.max(0, root.contentHeight - root.height)
                if (root.contentY < maxY) {
                    root.contentY = Math.min(maxY, root.contentY + 60)
                }
                event.accepted = true
                break
            case Qt.Key_PageUp:
                root.contentY = Math.max(0, root.contentY - root.height * 0.9)
                event.accepted = true
                break
            case Qt.Key_PageDown:
                var maxYPageDown = Math.max(0, root.contentHeight - root.height)
                root.contentY = Math.min(maxYPageDown, root.contentY + root.height * 0.9)
                event.accepted = true
                break
            case Qt.Key_Home:
                root.contentY = 0
                event.accepted = true
                break
            case Qt.Key_End:
                var maxYEnd = Math.max(0, root.contentHeight - root.height)
                root.contentY = maxYEnd
                event.accepted = true
                break
        }
    }
    
    // Smooth scroll animations
    Behavior on contentY {
        NumberAnimation {
            duration: Theme.durationFast
            easing.type: Theme.easingStandard
        }
    }
    
    // Accessibility properties
    Accessible.role: Accessible.Grouping
    Accessible.name: qsTr("Dashboard cards grid")
    Accessible.description: qsTr("Grid layout containing dashboard navigation cards")
} 