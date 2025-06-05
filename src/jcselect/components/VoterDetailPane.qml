import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0
import QtQuick.Layouts 1.15

Rectangle {
    id: voterDetailPane
    
    // Voter object property for easier binding
    property var voter: null
    
    property string voterId: voter ? voter.id : ""
    property string voterNumber: voter ? voter.number : ""
    property string fullName: voter ? voter.fullName : ""
    property string fatherName: voter ? voter.fatherName : ""
    property string motherName: voter ? voter.motherName : ""
    property string penLabel: voter ? voter.penLabel : ""
    property bool hasVoted: voter ? voter.hasVoted : false
    property string votedAt: voter ? voter.votedAt : ""
    property string votedByOperator: voter ? voter.votedByOperator : ""
    property bool isLoading: false
    property bool hasError: false
    property string errorMessage: ""
    
    signal markVoted(string voterId)
    signal errorOccurred(string message)
    
    color: Theme.backgroundColor
    radius: Theme.radius
    
    // Elevation shadow
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 2
        radius: parent.radius
        color: Theme.elevation1
        z: -1
        opacity: 0.3
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLarge
        spacing: Theme.spacingMedium
        
        // Header with voter name and number
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: headerLayout.implicitHeight + Theme.spacingMedium * 2
            radius: Theme.radius
            color: hasVoted ? Theme.successContainer : Theme.primaryContainer
            
            RowLayout {
                id: headerLayout
                anchors.fill: parent
                anchors.margins: Theme.spacingMedium
                layoutDirection: Qt.RightToLeft
                spacing: Theme.spacingMedium
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingTiny
                    
                    Text {
                        Layout.fillWidth: true
                        text: fullName || qsTr("No voter selected")
                        font.pixelSize: Theme.headlineMedium
                        font.bold: true
                        color: hasVoted ? Theme.successColor : Theme.primaryContainerOn
                        horizontalAlignment: Text.AlignRight
                        elide: Text.ElideLeft
                    }
                    
                    Text {
                        Layout.fillWidth: true
                        text: voterNumber ? qsTr("Voter #%1").arg(voterNumber) : ""
                        font.pixelSize: Theme.labelLarge
                        color: Qt.darker(hasVoted ? Theme.successColor : Theme.primaryContainerOn, 1.2)
                        horizontalAlignment: Text.AlignRight
                        visible: voterNumber.length > 0
                    }
                }
                
                // Status indicator
                Rectangle {
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    radius: 24
                    color: hasVoted ? Theme.successColor : Theme.elevation2
                    
                    Text {
                        anchors.centerIn: parent
                        text: hasVoted ? "✓" : "○"
                        font.pixelSize: 24
                        font.bold: true
                        color: hasVoted ? "white" : Theme.textColor
                    }
                }
            }
        }
        
        // Voter details
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            
            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacingMedium
                
                // Family information
                GroupBox {
                    Layout.fillWidth: true
                    title: qsTr("Family Information")
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: Theme.spacingSmall
                        
                        DetailRow {
                            Layout.fillWidth: true
                            label: qsTr("Father's Name:")
                            value: fatherName
                            visible: fatherName.length > 0
                        }
                        
                        DetailRow {
                            Layout.fillWidth: true
                            label: qsTr("Mother's Name:")
                            value: motherName
                            visible: motherName.length > 0
                        }
                        
                        DetailRow {
                            Layout.fillWidth: true
                            label: qsTr("Polling Station:")
                            value: penLabel
                            visible: penLabel.length > 0
                        }
                    }
                }
                
                // Voting information
                GroupBox {
                    Layout.fillWidth: true
                    title: qsTr("Voting Status")
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: Theme.spacingSmall
                        
                        DetailRow {
                            Layout.fillWidth: true
                            label: qsTr("Status:")
                            value: hasVoted ? qsTr("Voted ✓") : qsTr("Not voted")
                            valueColor: hasVoted ? Theme.successColor : Theme.textColor
                        }
                        
                        DetailRow {
                            Layout.fillWidth: true
                            label: qsTr("Voted at:")
                            value: votedAt
                            visible: hasVoted && votedAt.length > 0
                        }
                        
                        DetailRow {
                            Layout.fillWidth: true
                            label: qsTr("Operator:")
                            value: votedByOperator
                            visible: hasVoted && votedByOperator.length > 0
                        }
                    }
                }
                
                // Action area
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMedium
                    
                    // Error display
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: errorLayout.visible ? errorLayout.implicitHeight + Theme.spacingSmall * 2 : 0
                        radius: Theme.radius
                        color: Theme.errorContainer
                        visible: hasError
                        
                        RowLayout {
                            id: errorLayout
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSmall
                            spacing: Theme.spacingSmall
                            layoutDirection: Qt.RightToLeft
                            visible: hasError
                            
                            Text {
                                Layout.fillWidth: true
                                text: errorMessage
                                font.pixelSize: Theme.bodySize
                                color: Theme.errorColor
                                horizontalAlignment: Text.AlignRight
                                wrapMode: Text.WordWrap
                            }
                            
                            Text {
                                text: "⚠️"
                                font.pixelSize: 20
                                color: Theme.errorColor
                            }
                        }
                    }
                    
                    VoteButton {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Theme.buttonHeight * 1.5
                        voterId: voterDetailPane.voterId
                        hasVoted: voterDetailPane.hasVoted
                        isLoading: voterDetailPane.isLoading
                        hasError: voterDetailPane.hasError
                        errorMessage: voterDetailPane.errorMessage
                        
                        onMarkVoted: (id) => {
                            voterDetailPane.markVoted(id)
                        }
                        
                        onVotingError: (message) => {
                            voterDetailPane.errorOccurred(message)
                        }
                    }
                    
                    Text {
                        Layout.fillWidth: true
                        text: hasVoted ? 
                            qsTr("This voter has already been marked as voted.") :
                            qsTr("Click the button above to mark this voter as voted.")
                        font.pixelSize: Theme.captionSize
                        color: Qt.darker(Theme.textColor, 1.5)
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
                
                // Spacer
                Item {
                    Layout.fillHeight: true
                }
            }
        }
    }
    
    // Detail row component
    component DetailRow: RowLayout {
        property string label: ""
        property string value: ""
        property color valueColor: Theme.textColor
        
        layoutDirection: Qt.RightToLeft
        spacing: Theme.spacingSmall
        
        Text {
            Layout.preferredWidth: 120
            text: label
            font.pixelSize: Theme.bodySize
            font.bold: true
            color: Theme.textColor
            horizontalAlignment: Text.AlignRight
        }
        
        Text {
            Layout.fillWidth: true
            text: value
            font.pixelSize: Theme.bodySize
            color: valueColor
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideLeft
            wrapMode: Text.WordWrap
        }
    }
    
    // Empty state
    Rectangle {
        anchors.centerIn: parent
        width: emptyLayout.implicitWidth + Theme.spacingLarge * 2
        height: emptyLayout.implicitHeight + Theme.spacingLarge * 2
        radius: Theme.radius
        color: Theme.elevation1
        visible: !voterId
        
        ColumnLayout {
            id: emptyLayout
            anchors.centerIn: parent
            spacing: Theme.spacingMedium
            
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "👤"
                font.pixelSize: 48
                color: Qt.darker(Theme.textColor, 1.5)
            }
            
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("Select a voter to view details")
                font.pixelSize: Theme.titleSize
                color: Qt.darker(Theme.textColor, 1.3)
                horizontalAlignment: Text.AlignHCenter
            }
            
            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: 200
                text: qsTr("Click on any voter card from the search results to display their information here.")
                font.pixelSize: Theme.captionSize
                color: Qt.darker(Theme.textColor, 1.5)
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }
    
    // Error management functions
    function showError(message) {
        hasError = true
        errorMessage = message
    }
    
    function clearError() {
        hasError = false
        errorMessage = ""
    }
    
    // Clear error when voter changes
    onVoterIdChanged: {
        clearError()
    }
} 