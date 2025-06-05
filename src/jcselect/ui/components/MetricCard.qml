import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects
import jcselect.ui 1.0
import jcselect.ui.components 1.0

Rectangle {
    id: root
    
    // Properties as specified in the dashboard polish spec
    property color accentColor: Theme.primary
    property int value: 0
    property string title: ""
    property string subtitle: ""
    property string iconSource: ""
    property bool isStable: false  // Shows ✓ when value unchanged for 60s
    property bool isAnimating: false
    property int previousValue: 0
    
    // Internal properties for animation
    property bool hovered: false
    property real animationScale: 1.0
    property real shadowRadius: 4
    
    // Stability timer
    Timer {
        id: stabilityTimer
        interval: 60000  // 60 seconds
        running: false
        onTriggered: {
            if (root.value === root.previousValue) {
                root.isStable = true
            }
        }
    }
    
    // Watch for value changes
    onValueChanged: {
        if (value !== previousValue) {
            isStable = false
            isAnimating = true
            valueChangeAnimation.start()
            stabilityTimer.restart()
            previousValue = value
        }
    }
    
    width: 280
    height: 120
    radius: Theme.cornerRadius
    color: Theme.surface
    
    // Scale transformation for hover effect
    transform: Scale {
        origin.x: root.width / 2
        origin.y: root.height / 2
        xScale: animationScale
        yScale: animationScale
    }
    
    // Drop shadow system with radius 4px, color #00000015
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Theme.shadowLight
        shadowBlur: shadowRadius * 0.25
        shadowVerticalOffset: shadowRadius
        shadowHorizontalOffset: 0
    }
    
    // Content layout with RTL support
    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingMedium
        spacing: Theme.spacingMedium
        layoutDirection: Qt.RightToLeft  // RTL for Arabic
        
        // Icon circle (right-aligned for RTL)
        Rectangle {
            Layout.preferredWidth: 48
            Layout.preferredHeight: 48
            radius: 24
            color: root.accentColor
            Layout.alignment: Qt.AlignTop
            
            SvgIcon {
                anchors.centerIn: parent
                source: root.iconSource
                iconSize: 24
                color: Theme.primaryText
            }
        }
        
        // Text content area
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 4
            
            // Value display with animation
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                
                Text {
                    id: valueText
                    anchors.centerIn: parent
                    text: root.value.toLocaleString()
                    font: Theme.displayLarge
                    color: Theme.onSurface
                    horizontalAlignment: Text.AlignHCenter
                }
                
                // Animated value text for transitions
                Text {
                    id: animatedValueText
                    anchors.centerIn: parent
                    text: root.previousValue.toLocaleString()
                    font: Theme.displayLarge
                    color: Theme.onSurface
                    horizontalAlignment: Text.AlignHCenter
                    opacity: 0
                    visible: false
                }
            }
            
            // Title text
            Text {
                text: root.title
                font: Theme.titleMedium
                color: Theme.onSurface
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            
            // Subtitle with stability indicator
            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                
                Text {
                    text: root.subtitle
                    font: Theme.bodyMediumFont
                    color: Theme.onSurfaceVariant
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }
                
                // Stability indicator (green checkmark)
                Text {
                    text: "✓"
                    font: Theme.labelLargeFont
                    color: Theme.stableIndicator
                    visible: root.isStable
                    Layout.alignment: Qt.AlignCenter
                }
            }
        }
    }
    
    // Mouse area for hover effects
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        
        onEntered: {
            root.hovered = true
            hoverInAnimation.start()
        }
        
        onExited: {
            root.hovered = false
            hoverOutAnimation.start()
        }
    }
    
    // Hover animations
    ParallelAnimation {
        id: hoverInAnimation
        
        NumberAnimation {
            target: root
            property: "animationScale"
            to: 1.02
            duration: Theme.hoverDuration
            easing.type: Easing.OutQuart
        }
        
        NumberAnimation {
            target: root
            property: "shadowRadius"
            to: 8
            duration: Theme.hoverDuration
            easing.type: Easing.OutQuart
        }
    }
    
    ParallelAnimation {
        id: hoverOutAnimation
        
        NumberAnimation {
            target: root
            property: "animationScale"
            to: 1.0
            duration: Theme.hoverDuration
            easing.type: Easing.OutQuart
        }
        
        NumberAnimation {
            target: root
            property: "shadowRadius"
            to: 4
            duration: Theme.hoverDuration
            easing.type: Easing.OutQuart
        }
    }
    
    // Value change animation sequence
    SequentialAnimation {
        id: valueChangeAnimation
        
        ParallelAnimation {
            // Fade out current value while translating up
            NumberAnimation {
                target: valueText
                property: "opacity"
                to: 0
                duration: Theme.valueChangeDuration / 2
                easing.type: Easing.OutCubic
            }
            
            NumberAnimation {
                target: valueText
                property: "y"
                to: valueText.y - 4
                duration: Theme.valueChangeDuration / 2
                easing.type: Easing.OutCubic
            }
        }
        
        ScriptAction {
            script: {
                // Update the text during the middle of animation
                valueText.y = valueText.y + 8  // Reset position below
            }
        }
        
        ParallelAnimation {
            // Fade in new value while translating to position
            NumberAnimation {
                target: valueText
                property: "opacity"
                to: 1
                duration: Theme.valueChangeDuration / 2
                easing.type: Easing.OutCubic
            }
            
            NumberAnimation {
                target: valueText
                property: "y"
                to: valueText.y - 4  // Back to center
                duration: Theme.valueChangeDuration / 2
                easing.type: Easing.OutCubic
            }
        }
        
        onFinished: {
            root.isAnimating = false
        }
    }
    
    // Accessibility properties
    Accessible.role: Accessible.StaticText
    Accessible.name: title + " " + value + " " + subtitle
    Accessible.description: qsTr("Dashboard metric card")
    
    // Keyboard focus support
    focus: true
    activeFocusOnTab: true
    
    // Focus indicator
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Theme.primary
        border.width: root.activeFocus ? 2 : 0
        radius: root.radius
        
        Behavior on border.width {
            NumberAnimation {
                duration: Theme.durationFast
                easing.type: Theme.easingStandard
            }
        }
    }
} 