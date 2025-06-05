import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects
import jcselect.ui 1.0
import jcselect.ui.components 1.0

Rectangle {
    id: root

    // Properties
    property string title: ""
    property string subtitle: ""
    property string iconSource: ""
    property int badgeCount: 0
    property bool badgeVisible: false
    property color badgeColor: Theme.success
    property bool enabled: true
    property bool loading: false
    
    // Visual Properties
    property real elevation: 1
    property real cornerRadius: 12
    property color surfaceColor: Theme.surface
    
    // Animation Properties
    property bool hovered: false
    property bool pressed: false

    // Legacy Properties for compatibility
    property string badgeText: badgeCount > 0 ? badgeCount.toString() : ""

    // Signals
    signal clicked()
    signal rightClicked()

    width: 200
    height: 160

    color: root.hovered ? Theme.surfaceVariant : root.surfaceColor
    radius: root.cornerRadius
    
    // Smooth color transition for hover effect
    Behavior on color {
        ColorAnimation {
            duration: Theme.durationFast
            easing.type: Theme.easingStandard
        }
    }

    // Drop Shadow with elevation
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: "#1A000000"
        shadowBlur: root.elevation * 0.2
        shadowVerticalOffset: root.elevation
        shadowHorizontalOffset: 0
    }

    // Content Layout
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing * 1.5
        spacing: 8

        // Icon Container
        Item {
            Layout.preferredHeight: 48
            Layout.preferredWidth: 48
            Layout.alignment: Qt.AlignHCenter

            // Icon Image with standardized rendering
            SvgIcon {
                id: icon
                anchors.centerIn: parent
                iconSize: 40
                source: root.iconSource
                color: root.enabled ? Theme.onSurface : Theme.onSurfaceVariant
                visible: !root.loading
            }

            // Loading Spinner
            BusyIndicator {
                anchors.centerIn: parent
                visible: root.loading
                running: root.loading
                width: 40
                height: 40
            }
        }

        // Text Content
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            Text {
                id: titleText
                text: root.title
                font: Theme.titleMediumFont
                color: Theme.onSurface
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            Text {
                id: subtitleText
                text: root.subtitle
                font: Theme.bodyMediumFont
                color: Theme.onSurfaceVariant
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                visible: text.length > 0
            }
        }

        Item { Layout.fillHeight: true } // Spacer
    }

    // Badge
    Rectangle {
        id: badge
        visible: root.badgeVisible && root.badgeCount > 0
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 8
        width: Math.max(20, badgeLabel.width + 8)
        height: 20
        radius: 10
        color: root.badgeColor

        Text {
            id: badgeLabel
            anchors.centerIn: parent
            text: root.badgeCount > 99 ? "99+" : root.badgeCount.toString()
            font: Theme.labelLargeFont
            color: Theme.onSuccess
        }

        // Badge Pulse Animation
        SequentialAnimation {
            id: pulseAnimation
            running: root.badgeVisible && !root.loading
            loops: Animation.Infinite
            alwaysRunToEnd: true
            
            ScaleAnimator {
                target: badge
                from: 1.0
                to: 1.1
                duration: Theme.durationMedium
                easing.type: Theme.easingStandard
            }

            ScaleAnimator {
                target: badge
                from: 1.1
                to: 1.0
                duration: Theme.durationMedium
                easing.type: Theme.easingStandard
            }

            PauseAnimation { duration: 2000 }
        }
    }

    // Mouse Area
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onEntered: {
            root.hovered = true
            hoverAnimation.start()
        }

        onExited: {
            root.hovered = false
            unhoverAnimation.start()
        }

        onPressed: {
            root.pressed = true
            pressAnimation.start()
        }

        onReleased: {
            root.pressed = false
            releaseAnimation.start()
        }

        onClicked: function(mouse) {
            if (!root.enabled) return

            if (mouse.button === Qt.LeftButton) {
                rippleAnimation.start()
                root.clicked()
            } else if (mouse.button === Qt.RightButton) {
                root.rightClicked()
            }
        }

        // Ripple Effect
        Rectangle {
            id: ripple
            anchors.centerIn: parent
            width: 0
            height: 0
            radius: width / 2
            color: Theme.primary
            opacity: 0
            
            // Cache layer for better performance
            layer.enabled: true

            ParallelAnimation {
                id: rippleAnimation
                alwaysRunToEnd: true
                
                PropertyAnimation {
                    target: ripple
                    property: "width"
                    from: 0
                    to: root.width * 2
                    duration: Theme.durationMedium
                    easing.type: Theme.easingStandard
                }
                PropertyAnimation {
                    target: ripple
                    property: "height"
                    from: 0
                    to: root.height * 2
                    duration: Theme.durationMedium
                    easing.type: Theme.easingStandard
                }
                PropertyAnimation {
                    target: ripple
                    property: "opacity"
                    from: 0.3
                    to: 0
                    duration: Theme.durationMedium
                    easing.type: Theme.easingStandard
                }
                
                onFinished: {
                    ripple.width = 0
                    ripple.height = 0
                    ripple.opacity = 0
                }
            }
        }
    }

    // Hover Animation
    PropertyAnimation {
        id: hoverAnimation
        target: root
        property: "elevation"
        to: 3
        duration: Theme.durationFast
        easing.type: Theme.easingStandard
    }

    PropertyAnimation {
        id: unhoverAnimation
        target: root
        property: "elevation"
        to: 1
        duration: Theme.durationFast
        easing.type: Theme.easingStandard
    }

    // Press Animations
    PropertyAnimation {
        id: pressAnimation
        target: root
        property: "elevation"
        to: 6
        duration: Theme.durationFast
        easing.type: Theme.easingStandard
    }

    PropertyAnimation {
        id: releaseAnimation
        target: root
        property: "elevation"
        to: 3
        duration: Theme.durationFast
        easing.type: Theme.easingStandard
    }

    // Keyboard focus support
    focus: true
    activeFocusOnTab: true

    Keys.onSpacePressed: if (enabled) clicked()
    Keys.onReturnPressed: if (enabled) clicked()
    Keys.onEnterPressed: if (enabled) clicked()

    // Enhanced focus indicator
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Theme.primary
        border.width: root.activeFocus ? 3 : 0
        radius: root.cornerRadius
        z: 100
        
        Behavior on border.width {
            NumberAnimation {
                duration: Theme.durationFast
                easing.type: Theme.easingStandard
            }
        }
        
        // Accessibility outline for high contrast
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1
            color: "transparent"
            border.color: "white"
            border.width: root.activeFocus ? 1 : 0
            radius: root.cornerRadius + 1
            z: -1
        }
    }
    
    // Tooltip
    Rectangle {
        id: tooltipRect
        anchors.bottom: root.top
        anchors.horizontalCenter: root.horizontalCenter
        anchors.bottomMargin: 8
        width: tooltipText.width + 16
        height: tooltipText.height + 12
        radius: 6
        color: "#333333"
        visible: root.hovered && root.tooltip.length > 0 && !root.loading
        z: 1000
        
        Text {
            id: tooltipText
            anchors.centerIn: parent
            text: root.tooltip
            color: "white"
            font: Theme.bodySmallFont
            wrapMode: Text.WordWrap
            maximumLineCount: 2
        }
        
        // Tooltip arrow
        Rectangle {
            anchors.top: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: 8
            height: 8
            rotation: 45
            color: parent.color
        }
        
        // Fade in/out animation
        Behavior on visible {
            PropertyAnimation {
                duration: 200
                easing.type: Easing.OutCubic
            }
        }
    }

    // Accessibility Properties
    property string accessibleName: title
    property string accessibleDescription: subtitle
    property string tooltip: title + (subtitle ? " - " + subtitle : "")
    
    // Accessible role
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName
    Accessible.description: accessibleDescription
    Accessible.focusable: root.enabled
    Accessible.onPressAction: if (enabled) clicked()
} 