import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0
import QtQuick.Layouts 1.15

Rectangle {
    id: snackbar
    
    property string message: ""
    property string actionText: ""
    property int duration: 2000 // Auto-dismiss after 2 seconds
    property int variant: Snackbar.Success // Success, Error, Info
    
    signal actionClicked()
    signal dismissed()
    
    enum Variant {
        Success,
        Error,
        Info
    }
    
    width: parent.width - Theme.spacingLarge * 2
    height: Theme.snackbarHeight
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: Theme.spacingLarge
    radius: Theme.radius
    
    // Color based on variant
    color: {
        switch (variant) {
            case Snackbar.Success: return Theme.successContainer
            case Snackbar.Error: return Theme.errorContainer
            default: return Theme.elevation2
        }
    }
    
    // Initial state - hidden
    visible: false
    opacity: 0
    scale: 0.8
    
    // Elevation shadow
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 3
        radius: parent.radius
        color: Theme.elevation3
        z: -1
        opacity: 0.6
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingMedium
        layoutDirection: Qt.RightToLeft // RTL layout
        spacing: Theme.spacingMedium
        
        // Message text
        Text {
            Layout.fillWidth: true
            text: message
            font.pixelSize: Theme.bodySize
            color: {
                switch (variant) {
                    case Snackbar.Success: return Theme.successColor
                    case Snackbar.Error: return Theme.errorColor
                    default: return Theme.textColor
                }
            }
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideLeft
            wrapMode: Text.WordWrap
        }
        
        // Action button (optional)
        Rectangle {
            Layout.preferredWidth: actionButton.implicitWidth + Theme.spacingSmall * 2
            Layout.preferredHeight: Theme.buttonHeight * 0.8
            radius: Theme.spacingTiny
            color: actionMouseArea.containsMouse ? Theme.elevation1 : "transparent"
            visible: actionText.length > 0
            
            Text {
                id: actionButton
                anchors.centerIn: parent
                text: actionText
                font.pixelSize: Theme.labelLarge
                font.bold: true
                color: Theme.primaryColor
            }
            
            MouseArea {
                id: actionMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                
                onClicked: {
                    snackbar.actionClicked()
                    hide()
                }
            }
        }
        
        // Status icon
        Rectangle {
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24
            radius: 12
            color: "transparent"
            
            Text {
                anchors.centerIn: parent
                text: {
                    switch (variant) {
                        case Snackbar.Success: return "✓"
                        case Snackbar.Error: return "✕"
                        default: return "ℹ"
                    }
                }
                font.pixelSize: 14
                font.bold: true
                color: {
                    switch (variant) {
                        case Snackbar.Success: return Theme.successColor
                        case Snackbar.Error: return Theme.errorColor
                        default: return Theme.primaryColor
                    }
                }
            }
        }
        
        // Close button
        Rectangle {
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24
            radius: 12
            color: closeMouseArea.containsMouse ? Theme.elevation1 : "transparent"
            
            Text {
                anchors.centerIn: parent
                text: "✕"
                font.pixelSize: 12
                color: Qt.darker(Theme.textColor, 1.3)
            }
            
            MouseArea {
                id: closeMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                
                onClicked: hide()
            }
        }
    }
    
    // Show animation
    function show(msg, type = Snackbar.Success, autoHide = true) {
        message = msg
        variant = type
        
        // Start show animation
        showAnimation.start()
        
        // Auto-hide after duration
        if (autoHide && duration > 0) {
            autoHideTimer.start()
        }
    }
    
    // Hide animation
    function hide() {
        autoHideTimer.stop()
        hideAnimation.start()
    }
    
    // Show animation sequence
    SequentialAnimation {
        id: showAnimation
        
        PropertyAction {
            target: snackbar
            property: "visible"
            value: true
        }
        
        ParallelAnimation {
            NumberAnimation {
                target: snackbar
                property: "opacity"
                from: 0
                to: 1
                duration: Theme.animationDurationMedium
                easing.type: Theme.animationEasingStandard
            }
            
            NumberAnimation {
                target: snackbar
                property: "scale"
                from: 0.8
                to: 1.0
                duration: Theme.animationDurationMedium
                easing.type: Theme.animationEasingEmphasized
            }
            
            NumberAnimation {
                target: snackbar
                property: "anchors.bottomMargin"
                from: -snackbar.height
                to: Theme.spacingLarge
                duration: Theme.animationDurationMedium
                easing.type: Theme.animationEasingEmphasized
            }
        }
    }
    
    // Hide animation sequence
    SequentialAnimation {
        id: hideAnimation
        
        ParallelAnimation {
            NumberAnimation {
                target: snackbar
                property: "opacity"
                from: 1
                to: 0
                duration: Theme.animationDurationShort
                easing.type: Theme.animationEasingStandard
            }
            
            NumberAnimation {
                target: snackbar
                property: "scale"
                from: 1.0
                to: 0.8
                duration: Theme.animationDurationShort
                easing.type: Theme.animationEasingStandard
            }
            
            NumberAnimation {
                target: snackbar
                property: "anchors.bottomMargin"
                from: Theme.spacingLarge
                to: -snackbar.height
                duration: Theme.animationDurationShort
                easing.type: Theme.animationEasingStandard
            }
        }
        
        PropertyAction {
            target: snackbar
            property: "visible"
            value: false
        }
        
        ScriptAction {
            script: snackbar.dismissed()
        }
    }
    
    // Auto-hide timer
    Timer {
        id: autoHideTimer
        interval: duration
        repeat: false
        onTriggered: hide()
    }
    
    // Convenience functions for different variants
    function showSuccess(msg, autoHide = true) {
        show(msg, Snackbar.Success, autoHide)
    }
    
    function showError(msg, autoHide = true, withRetry = false) {
        show(msg, Snackbar.Error, autoHide)
        if (withRetry) {
            actionText = qsTr("Retry")
        }
    }
    
    function showInfo(msg, autoHide = true) {
        show(msg, Snackbar.Info, autoHide)
    }

    // Error-specific convenience function with standard styling
    function showErrorWithAction(msg, action, autoHide = true) {
        message = msg
        actionText = action
        variant = Snackbar.Error
        
        // Start show animation
        showAnimation.start()
        
        // Auto-hide after duration
        if (autoHide && duration > 0) {
            autoHideTimer.start()
        }
    }
} 