import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect 1.0
import "components"

Rectangle {
    id: root
    color: "#f5f5f5"
    
    property alias tallyController: tallyController
    
    TallyController {
        id: tallyController
        
        onBallotConfirmed: function(ballotNumber) {
            console.log("Ballot confirmed:", ballotNumber)
            statusText.text = "Ballot #" + ballotNumber + " confirmed successfully"
        }
        
        onRecountCompleted: {
            console.log("Recount completed")
            statusText.text = "Recount completed successfully"
        }
        
        onErrorOccurred: function(errorMessage) {
            console.error("Tally error:", errorMessage)
            statusText.text = "Error: " + errorMessage
            statusText.color = "#d32f2f"
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16
        
        // Header with pen info, ballot number, and recount button
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: "#1976d2"
            radius: 8
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                
                Text {
                    text: "فرز الأصوات - " + (tallyController.currentPenLabel || "لم يتم اختيار قلم")
                    // "Ballot Counting - " + pen label in Arabic
                    font.pixelSize: 24
                    font.bold: true
                    color: "white"
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight // RTL alignment
                }
                
                Text {
                    text: "ورقة رقم " + (tallyController.currentBallotNumber + 1)
                    // "Ballot #" in Arabic
                    font.pixelSize: 18
                    color: "white"
                    horizontalAlignment: Text.AlignRight
                }
                
                Button {
                    text: "إعادة العد" // "Start Recount" in Arabic
                    enabled: tallyController.totalVotes > 0
                    onClicked: tallyController.startRecount()
                    
                    background: Rectangle {
                        color: parent.enabled ? (parent.hovered ? "#e3f2fd" : "#ffffff") : "#757575"
                        radius: 6
                        border.color: parent.enabled ? "#1976d2" : "#bdbdbd"
                        border.width: 1
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 14
                        font.weight: Font.Medium
                        color: parent.enabled ? "#1976d2" : "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        
        // Main content area with three party columns + ballot type panel
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "white"
            radius: 8
            border.color: "#e0e0e0"
            border.width: 1
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16
                
                // Three party columns
                Repeater {
                    model: tallyController.partyColumns
                    
                    PartyColumn {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.maximumWidth: (parent.width - 220 - 48) / 3 // Reserve space for ballot panel + spacing
                        
                        partyData: modelData
                        selectedCandidate: tallyController.selectedCandidates[modelData.id] || ""
                        
                        onCandidateSelected: function(candidateId) {
                            tallyController.selectCandidate(modelData.id, candidateId)
                        }
                    }
                }
                
                // Ballot type panel
                BallotTypePanel {
                    Layout.preferredWidth: 220
                    Layout.fillHeight: true
                    
                    selectedType: tallyController.selectedBallotType
                    
                    onTypeSelected: function(ballotType) {
                        tallyController.selectBallotType(ballotType)
                    }
                }
            }
        }
        
        // Validation warnings (non-blocking)
        ValidationWarnings {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            warnings: tallyController.validationMessages
        }
        
        // Running totals
        TallyTotals {
            Layout.fillWidth: true
            Layout.preferredHeight: 160
            
            totalVotes: tallyController.totalVotes
            totalCounted: tallyController.totalCounted
            totalCandidates: tallyController.totalCandidates
            totalWhite: tallyController.totalWhite
            totalIllegal: tallyController.totalIllegal
            totalCancel: tallyController.totalCancel
            totalBlank: tallyController.totalBlank
        }
        
        // Action buttons (Cancel / Confirm Ballot)
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            
            Item { Layout.fillWidth: true } // Spacer to push buttons to the right
            
            Button {
                text: "إلغاء" // "Cancel" in Arabic
                Layout.preferredWidth: 120
                Layout.preferredHeight: 48
                
                onClicked: tallyController.clearCurrentBallot()
                
                background: Rectangle {
                    color: parent.hovered ? "#f5f5f5" : "white"
                    radius: 6
                    border.color: "#bdbdbd"
                    border.width: 1
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 16
                    font.weight: Font.Medium
                    color: "#424242"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
            
            Button {
                text: "تأكيد الورقة" // "Confirm Ballot" in Arabic
                enabled: tallyController.hasSelections
                highlighted: true
                Layout.preferredWidth: 160
                Layout.preferredHeight: 48
                
                onClicked: tallyController.confirmBallot()
                
                background: Rectangle {
                    color: parent.enabled ? 
                           (parent.hovered ? "#1565c0" : "#1976d2") : 
                           "#e0e0e0"
                    radius: 6
                    
                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 16
                    font.weight: Font.Bold
                    color: parent.enabled ? "white" : "#9e9e9e"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
        
        // Status bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: "#f0f0f0"
            radius: 4
            
            Text {
                id: statusText
                anchors.centerIn: parent
                text: "جاهز لفرز الأصوات" // "Ready for ballot counting" in Arabic
                color: "#333"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
    
    // Initialize session when component is loaded
    Component.onCompleted: {
        console.log("TallyCountingWindow loaded")
        statusText.text = "TallyController ready - initialize session to begin"
    }
} 