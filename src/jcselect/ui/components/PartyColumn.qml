import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    property var partyData: null
    property string selectedCandidate: ""
    
    signal candidateSelected(string candidateId)
    
    color: "white"
    radius: 8
    border.color: "#e0e0e0"
    border.width: 1
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8
        
        // Party header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: Theme.primaryColor
            radius: 6
            
            Text {
                anchors.centerIn: parent
                text: root.partyData ? root.partyData.name : "Loading..."
                font.pixelSize: 16
                font.weight: Font.Bold
                color: "white"
                horizontalAlignment: Text.AlignHCenter
            }
        }
        
        // Candidate list
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ListView {
                id: candidatesList
                anchors.fill: parent
                model: root.partyData ? root.partyData.candidates : []
                spacing: 4
                
                delegate: CandidateCheckbox {
                    width: candidatesList.width
                    
                    candidateData: modelData
                    checked: root.selectedCandidate === modelData.id
                    
                    onToggled: function(candidateId, isChecked) {
                        if (isChecked) {
                            root.candidateSelected(candidateId)
                        } else {
                            root.candidateSelected("")
                        }
                    }
                }
            }
        }
    }
} 