import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: card
    
    property string candidateName: ""
    property string partyName: ""
    property int totalVotes: 0
    property int rank: 0
    property bool isElected: false
    
    color: Theme.backgroundColor
    radius: Theme.radius
    border.color: isElected ? Theme.primaryColor : Theme.elevation2
    border.width: isElected ? 2 : 1
    
    // Winner badge
    Rectangle {
        id: badge
        anchors.top: parent.top
        anchors.right: Qt.application.layoutDirection === Qt.RightToLeft ? undefined : parent.right
        anchors.left: Qt.application.layoutDirection === Qt.RightToLeft ? parent.left : undefined
        anchors.margins: -8
        width: 32
        height: 32
        radius: 16
        color: {
            if (rank === 1) return "#FFD700" // Gold
            if (rank === 2) return "#C0C0C0" // Silver
            if (rank === 3) return "#CD7F32" // Bronze
            return Theme.primaryColor
        }
        visible: isElected
        
        Text {
            anchors.centerIn: parent
            text: rank.toString()
            font.pixelSize: Theme.bodySize
            font.weight: Font.Bold
            color: "white"
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacingSmall
        
        // Candidate photo placeholder
        Rectangle {
            Layout.preferredWidth: 60
            Layout.preferredHeight: 60
            Layout.alignment: Qt.AlignHCenter
            radius: 30
            color: Theme.elevation1
            border.color: Theme.elevation2
            border.width: 1
            
            Text {
                anchors.centerIn: parent
                text: candidateName.length > 0 ? candidateName.charAt(0) : "?"
                font.pixelSize: Theme.headlineMedium
                font.weight: Font.Bold
                color: Theme.textColor
            }
        }
        
        // Candidate name
        Text {
            text: candidateName
            font.pixelSize: Theme.titleSize
            font.weight: Font.Bold
            color: Theme.textColor
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        // Party name
        Text {
            text: partyName
            font.pixelSize: Theme.bodySize
            color: Theme.textColor
            opacity: 0.7
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        // Vote count
        Text {
            text: qsTr("الأصوات: ") + totalVotes.toLocaleString()
            font.pixelSize: Theme.bodySize
            font.weight: Font.Medium
            color: Theme.primaryColor
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
    }
    
    // Hover effect
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        
        onEntered: card.color = Theme.elevation1
        onExited: card.color = Theme.backgroundColor
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 