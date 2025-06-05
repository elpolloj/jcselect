import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui.components 1.0
import "../"

Rectangle {
    id: root
    
    property bool isLoading: resultsController.isSyncing
    
    color: Theme.backgroundColor
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacingMedium
        
        // Page header
        Text {
            text: qsTr("الفائزون")
            font.pixelSize: Theme.titleLarge
            font.weight: Font.Bold
            color: Theme.textColor
            Layout.fillWidth: true
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        // Winners grid
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            GridLayout {
                id: winnersGrid
                width: parent.width
                columns: Math.max(1, Math.floor(width / 300))
                columnSpacing: Theme.spacing
                rowSpacing: Theme.spacing
                
                // Animate opacity on refresh
                opacity: root.isLoading ? 0.5 : 1.0
                
                Behavior on opacity {
                    NumberAnimation {
                        duration: Theme.animationDurationMedium
                        easing.type: Theme.animationEasingStandard
                    }
                }
                
                Repeater {
                    model: resultsController.winners
                    
                    delegate: WinnerCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        Layout.minimumWidth: 280
                        
                        candidateName: modelData.candidate_name || ""
                        partyName: modelData.party_name || ""
                        totalVotes: modelData.total_votes || 0
                        rank: modelData.rank || 0
                        isElected: modelData.is_elected || false
                        
                        // Animate card appearance on data refresh
                        opacity: 0
                        
                        PropertyAnimation on opacity {
                            to: 1
                            duration: Theme.animationDurationMedium
                            easing.type: Theme.animationEasingEmphasized
                        }
                    }
                }
            }
        }
        
        // Empty state
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            visible: (!resultsController.winners || resultsController.winners.length === 0) && !root.isLoading
            
            Column {
                anchors.centerIn: parent
                spacing: Theme.spacingLarge
                
                Text {
                    text: "🏆"
                    font.pixelSize: 64
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    opacity: 0.5
                }
                
                Text {
                    text: qsTr("لم يتم تحديد الفائزين بعد")
                    font.pixelSize: Theme.headlineMedium
                    color: Theme.textColor
                    opacity: 0.7
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
                
                Text {
                    text: qsTr("سيتم عرض النتائج عند اكتمال العد")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.5
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
            }
        }
        
        // Loading state
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            visible: root.isLoading
            
            Column {
                anchors.centerIn: parent
                spacing: Theme.spacingLarge
                
                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 48
                    height: 48
                    running: root.isLoading
                }
                
                Text {
                    text: qsTr("جاري حساب النتائج...")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
            }
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 