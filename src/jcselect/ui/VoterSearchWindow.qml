import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0
import jcselect.components 1.0
import "."

Rectangle {
    id: root
    color: "transparent"

    // Controller property to be set from parent
    property var controller
    
    // Expose searchBar for keyboard shortcuts
    property alias searchBar: searchBar

    Component.onCompleted: {
        // Connect controller signals to UI feedback
        if (controller) {
            controller.voterMarkedSuccessfully.connect(function(msg) {
                feedbackBar.showSuccess(qsTr("Vote recorded successfully") + ": " + msg);
                voterDetailPane.clearError(); // Clear any previous errors
            });
            controller.operationFailed.connect(function(msg) {
                feedbackBar.showError(qsTr("Error") + ": " + msg, true, true); // Show with retry option
                voterDetailPane.showError(msg); // Show error in detail pane
            });
            controller.searchBarFocusRequested.connect(function() {
                searchBar.requestFocus();
            });
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacingMedium

        // Search bar at the top
        SearchBar {
            id: searchBar
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.searchBarHeight
            
            onSearchTextChanged: {
                if (controller) {
                    controller.setSearchQuery(text);
                }
            }
            
            onValidationError: {
                if (controller) {
                    controller.operationFailed(message);
                }
            }
            
            isLoading: controller ? controller.isLoading : false
        }

        // Main content area with results list and detail pane
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingMedium

            // Voter results list
            ListView {
                id: resultsList
                Layout.preferredWidth: parent.width * 0.6
                Layout.fillHeight: true
                
                model: controller ? controller.searchResults : []
                
                delegate: VoterCard {
                    required property var modelData
                    
                    width: resultsList.width
                    voterId: modelData.id || ""
                    voterNumber: modelData.number || ""
                    fullName: modelData.fullName || ""
                    fatherName: modelData.fatherName || ""
                    motherName: modelData.motherName || ""
                    hasVoted: modelData.hasVoted || false
                    
                    onSelected: function(voterId) {
                        if (controller) {
                            controller.selectVoter(voterId);
                        }
                    }
                }
                
                // Performance optimizations
                cacheBuffer: 200
                reuseItems: true
                
                // Empty state
                Label {
                    anchors.centerIn: parent
                    visible: resultsList.count === 0 && !controller.isLoading
                    text: controller && controller.searchQuery.length > 0 
                        ? qsTr("No search results found")
                        : qsTr("Start typing voter number or name to search")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    horizontalAlignment: Text.AlignHCenter
                }
                
                // Loading indicator
                BusyIndicator {
                    anchors.centerIn: parent
                    visible: controller ? controller.isLoading : false
                    running: visible
                }
            }

            // Voter detail pane
            VoterDetailPane {
                id: voterDetailPane
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                voter: controller ? controller.selectedVoter : null
                
                onMarkVoted: function(voterId, operatorId) {
                    if (controller) {
                        controller.markVoterAsVoted(voterId, operatorId);
                    }
                }
                
                onErrorOccurred: function(message) {
                    feedbackBar.showError(qsTr("Vote marking failed") + ": " + message, true, true);
                }
            }
        }

        // Feedback snackbar at the bottom
        Snackbar {
            id: feedbackBar
            Layout.fillWidth: true
            message: ""
            visible: false
            
            onActionClicked: {
                // Handle retry action
                if (controller && feedbackBar.actionText === qsTr("Retry")) {
                    controller.refreshSearch();
                }
            }
            
            onDismissed: {
                visible = false;
            }
        }
    }

    // Performance overlay
    PerformanceOverlay {
        controller: root.controller
        debugMode: Qt.application.arguments.indexOf("--debug") !== -1
    }
} 