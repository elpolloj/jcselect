import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0
import QtQuick.Layouts 1.15

Rectangle {
    id: voterCard
    
    property string voterId: ""
    property string voterNumber: ""
    property string fullName: ""
    property string fatherName: ""
    property string motherName: ""
    property bool hasVoted: false
    property bool isSelected: false
    
    signal selected(string voterId)
    
    width: parent.width
    height: Math.max(Theme.cardMinHeight, contentLayout.implicitHeight + Theme.spacingMedium * 2)
    radius: Theme.radius
    color: isSelected ? Theme.primaryContainer : Theme.surfaceColor
    border.color: isSelected ? Theme.primaryColor : "transparent"
    border.width: isSelected ? 2 : 0
    
    // Elevation shadow
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: mouseArea.containsMouse ? 3 : 1
        radius: parent.radius
        color: Theme.elevation2
        z: -1
        opacity: mouseArea.containsMouse ? 0.8 : 0.3
        
        Behavior on anchors.topMargin {
            NumberAnimation { duration: Theme.animationDurationShort; easing.type: Theme.animationEasingStandard }
        }
        Behavior on opacity {
            NumberAnimation { duration: Theme.animationDurationShort; easing.type: Theme.animationEasingStandard }
        }
    }
    
    RowLayout {
        id: contentLayout
        anchors.fill: parent
        anchors.margins: Theme.spacingMedium
        layoutDirection: Qt.RightToLeft // RTL layout
        spacing: Theme.spacingMedium
        
        // Voting status badge
        Rectangle {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            Layout.alignment: Qt.AlignTop
            radius: 16
            color: hasVoted ? Theme.successContainer : Theme.elevation2
            
            Text {
                anchors.centerIn: parent
                text: hasVoted ? "✓" : "○"
                font.pixelSize: 16
                font.bold: hasVoted
                color: hasVoted ? Theme.successColor : Theme.textColor
            }
        }
        
        // Voter information
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingTiny
            
            // Voter name and number
            RowLayout {
                Layout.fillWidth: true
                layoutDirection: Qt.RightToLeft
                spacing: Theme.spacingSmall
                
                Text {
                    Layout.fillWidth: true
                    text: fullName
                    font.pixelSize: Theme.titleSize
                    font.bold: true
                    color: isSelected ? Theme.primaryContainerOn : Theme.textColor
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideLeft
                    
                    Behavior on color {
                        ColorAnimation { duration: Theme.animationDurationShort }
                    }
                }
                
                Rectangle {
                    Layout.preferredWidth: numberText.implicitWidth + Theme.spacingSmall * 2
                    Layout.preferredHeight: numberText.implicitHeight + Theme.spacingTiny * 2
                    radius: Theme.spacingTiny
                    color: Theme.elevation1
                    
                    Text {
                        id: numberText
                        anchors.centerIn: parent
                        text: voterNumber
                        font.pixelSize: Theme.captionSize
                        font.bold: true
                        color: Theme.textColor
                    }
                }
            }
            
            // Father and mother names
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                
                Text {
                    Layout.fillWidth: true
                    text: fatherName ? qsTr("Father: %1").arg(fatherName) : ""
                    font.pixelSize: Theme.captionSize
                    color: Qt.darker(isSelected ? Theme.primaryContainerOn : Theme.textColor, 1.3)
                    horizontalAlignment: Text.AlignRight
                    visible: fatherName.length > 0
                    elide: Text.ElideLeft
                    
                    Behavior on color {
                        ColorAnimation { duration: Theme.animationDurationShort }
                    }
                }
                
                Text {
                    Layout.fillWidth: true
                    text: motherName ? qsTr("Mother: %1").arg(motherName) : ""
                    font.pixelSize: Theme.captionSize
                    color: Qt.darker(isSelected ? Theme.primaryContainerOn : Theme.textColor, 1.3)
                    horizontalAlignment: Text.AlignRight
                    visible: motherName.length > 0
                    elide: Text.ElideLeft
                    
                    Behavior on color {
                        ColorAnimation { duration: Theme.animationDurationShort }
                    }
                }
            }
        }
    }
    
    // Mouse interaction
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        
        onClicked: {
            voterCard.selected(voterId)
        }
    }
    
    // Selection animation
    Behavior on color {
        ColorAnimation { duration: Theme.animationDurationMedium; easing.type: Theme.animationEasingStandard }
    }
    
    Behavior on border.color {
        ColorAnimation { duration: Theme.animationDurationMedium; easing.type: Theme.animationEasingStandard }
    }
} 