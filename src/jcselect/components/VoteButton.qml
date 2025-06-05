import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0
import QtQuick.Layouts 1.15

Rectangle {
    id: voteButton
    
    property string voterId: ""
    property bool hasVoted: false
    property bool isLoading: false
    property bool hasError: false
    property string errorMessage: ""
    property bool enabled: !hasVoted && !isLoading && !hasError
    
    signal markVoted(string voterId)
    signal votingError(string message)
    
    width: parent.width
    height: Theme.buttonHeight * 1.5 // Larger button for prominence
    radius: Theme.radius
    color: {
        if (!enabled) return Theme.elevation2
        if (hasError) return Theme.errorContainer
        if (mouseArea.pressed) return Qt.darker(Theme.primaryColor, 1.2)
        if (mouseArea.containsMouse) return Qt.lighter(Theme.primaryColor, 1.1)
        return Theme.primaryColor
    }
    
    border.color: enabled ? "transparent" : Theme.elevation3
    border.width: enabled ? 0 : 1
    
    // Elevation shadow
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: enabled && mouseArea.containsMouse ? 4 : 2
        radius: parent.radius
        color: Theme.elevation3
        z: -1
        opacity: enabled ? 0.6 : 0.2
        
        Behavior on anchors.topMargin {
            NumberAnimation { duration: Theme.animationDurationShort; easing.type: Theme.animationEasingStandard }
        }
    }
    
    RowLayout {
        anchors.centerIn: parent
        spacing: Theme.spacingSmall
        layoutDirection: Qt.RightToLeft // RTL layout
        
        // Button text
        Text {
            Layout.alignment: Qt.AlignCenter
            text: {
                if (hasError) return qsTr("Error occurred") + " ⚠️"
                if (hasVoted) return qsTr("تم التصويت ✓")
                if (isLoading) return qsTr("جاري التسجيل...")
                return qsTr("تم ✅")
            }
            font.pixelSize: Theme.titleLarge
            font.bold: true
            color: {
                if (!enabled) return Qt.darker(Theme.textColor, 1.5)
                if (hasError) return Theme.errorColor
                return "white"
            }
            horizontalAlignment: Text.AlignHCenter
        }
        
        // Loading indicator
        Rectangle {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            radius: 10
            color: "transparent"
            visible: isLoading
            
            Rectangle {
                id: loadingSpinner
                width: 16
                height: 16
                radius: 8
                anchors.centerIn: parent
                color: "transparent"
                border.color: "white"
                border.width: 2
                
                Rectangle {
                    width: 4
                    height: 4
                    radius: 2
                    color: "white"
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 2
                }
                
                RotationAnimation on rotation {
                    running: isLoading
                    loops: Animation.Infinite
                    duration: 1000
                    from: 0
                    to: 360
                }
            }
        }
    }
    
    // Mouse interaction
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ForbiddenCursor
        
        onClicked: {
            if (enabled && !hasVoted && !hasError) {
                // Clear any previous errors
                hasError = false
                errorMessage = ""
                
                // Success animation
                successAnimation.start()
                voteButton.markVoted(voterId)
            } else if (hasError) {
                // If there's an error, emit signal to retry or show details
                voteButton.votingError(errorMessage)
            }
        }
    }
    
    // Success animation
    SequentialAnimation {
        id: successAnimation
        
        ParallelAnimation {
            ScaleAnimator {
                target: voteButton
                from: 1.0
                to: 1.05
                duration: Theme.animationDurationShort
                easing.type: Theme.animationEasingEmphasized
            }
            ColorAnimation {
                target: voteButton
                property: "color"
                to: Theme.successColor
                duration: Theme.animationDurationShort
            }
        }
        
        ParallelAnimation {
            ScaleAnimator {
                target: voteButton
                from: 1.05
                to: 1.0
                duration: Theme.animationDurationMedium
                easing.type: Theme.animationEasingStandard
            }
            ColorAnimation {
                target: voteButton
                property: "color"
                to: voteButton.enabled ? Theme.primaryColor : Theme.elevation2
                duration: Theme.animationDurationMedium
            }
        }
    }
    
    // Color transitions
    Behavior on color {
        ColorAnimation { 
            duration: Theme.animationDurationShort
            easing.type: Theme.animationEasingStandard 
        }
    }
    
    // Error state management
    function showError(message) {
        hasError = true
        errorMessage = message
        // Flash error color
        errorFlashAnimation.start()
    }
    
    function clearError() {
        hasError = false
        errorMessage = ""
    }
    
    // Error flash animation
    SequentialAnimation {
        id: errorFlashAnimation
        
        ColorAnimation {
            target: voteButton
            property: "color"
            to: Theme.errorColor
            duration: Theme.animationDurationShort
        }
        
        ColorAnimation {
            target: voteButton
            property: "color"
            to: Theme.errorContainer
            duration: Theme.animationDurationShort
        }
    }
    
    // Accessibility
    Accessible.role: Accessible.Button
    Accessible.name: {
        if (hasError) return qsTr("Vote button - Error: %1").arg(errorMessage)
        if (hasVoted) return qsTr("Voter already marked")
        return qsTr("Mark voter as voted")
    }
    Accessible.description: {
        if (hasError) return qsTr("Click to retry or view error details")
        if (hasVoted) return qsTr("This voter has already been marked as voted")
        return qsTr("Click to mark this voter as having voted")
    }
} 