import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0

Rectangle {
    id: searchBar
    
    property alias text: textInput.text
    property string placeholderText: qsTr("Search voters...")
    property bool isLoading: false
    property bool hasError: false
    property string errorText: ""
    
    signal searchTextChanged(string text)
    signal focusRequested()
    signal validationError(string message)
    
    width: parent.width
    height: Theme.searchBarHeight + (errorLabel.visible ? errorLabel.height + Theme.spacingTiny : 0)
    color: "transparent"

    Column {
        anchors.fill: parent
        spacing: Theme.spacingTiny
        
        // Main search input rectangle
        Rectangle {
            id: inputContainer
            width: parent.width
            height: Theme.searchBarHeight
            radius: Theme.radius
            color: Theme.surfaceColor
            border.color: {
                if (hasError) return Theme.errorColor
                if (textInput.activeFocus) return Theme.primaryColor
                return "transparent"
            }
            border.width: {
                if (hasError) return 2
                if (textInput.activeFocus) return 2
                return 0
            }
            
            // Elevation shadow
            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 1
                radius: parent.radius
                color: Theme.elevation1
                z: -1
                opacity: 0.5
            }
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingMedium
                layoutDirection: Qt.RightToLeft // RTL layout
                spacing: Theme.spacingSmall
                
                // Search icon
                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    color: "transparent"
                    
                    Text {
                        anchors.centerIn: parent
                        text: "🔍"
                        font.pixelSize: 16
                        color: Theme.textColor
                    }
                }
                
                // Text input field
                TextInput {
                    id: textInput
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    selectByMouse: true
                    horizontalAlignment: TextInput.AlignRight // RTL alignment
                    
                    // Placeholder text handling
                    Text {
                        anchors.fill: parent
                        text: searchBar.placeholderText
                        font: textInput.font
                        color: Qt.darker(Theme.textColor, 1.5)
                        visible: textInput.text.length === 0 && !textInput.activeFocus
                        horizontalAlignment: TextInput.AlignRight
                        verticalAlignment: TextInput.AlignVCenter
                    }
                    
                    onTextChanged: {
                        searchBar.searchTextChanged(text)
                        
                        // Clear error when user types
                        if (hasError) {
                            hasError = false
                            errorText = ""
                        }
                        
                        // Validate empty search (but allow user to clear intentionally)
                        if (text.length === 0 && searchBar.text.length > 0) {
                            // User cleared the search, don't show error
                            return
                        }
                    }
                    
                    Keys.onPressed: (event) => {
                        if (event.key === Qt.Key_Escape) {
                            text = ""
                            focus = false
                            hasError = false
                            errorText = ""
                        }
                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                            // Validate on enter
                            if (text.trim().length === 0) {
                                hasError = true
                                errorText = qsTr("Enter a search term")
                                validationError(errorText)
                            }
                        }
                    }
                }
                
                // Clear button
                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 12
                    color: clearMouseArea.containsMouse ? Theme.elevation2 : "transparent"
                    visible: textInput.text.length > 0
                    
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 12
                        color: Theme.textColor
                    }
                    
                    MouseArea {
                        id: clearMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            textInput.text = ""
                            textInput.forceActiveFocus()
                        }
                    }
                }
                
                // Loading indicator
                Rectangle {
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    radius: 10
                    color: "transparent"
                    visible: searchBar.isLoading
                    
                    Rectangle {
                        id: loadingDot
                        width: 4
                        height: 4
                        radius: 2
                        color: Theme.primaryColor
                        anchors.centerIn: parent
                        
                        SequentialAnimation on opacity {
                            running: searchBar.isLoading
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.3; duration: Theme.animationDurationShort }
                            NumberAnimation { to: 1.0; duration: Theme.animationDurationShort }
                        }
                    }
                }
            }
        }
        
        // Error label
        Rectangle {
            width: parent.width
            height: errorLabel.visible ? errorLabel.height + Theme.spacingTiny : 0
            color: "transparent"
            
            Text {
                id: errorLabel
                text: errorText
                color: Theme.errorColor
                font.pixelSize: Theme.bodySize
                visible: errorText.length > 0
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.spacingTiny
            }
        }
    }
    
    // Focus handling
    function requestFocus() {
        textInput.forceActiveFocus()
        focusRequested()
    }
    
    // Error handling
    function showError(message) {
        hasError = true
        errorText = message
    }
    
    function clearError() {
        hasError = false
        errorText = ""
    }
    
    // Global shortcut handling (Ctrl+F)
    Shortcut {
        sequence: "Ctrl+F"
        onActivated: requestFocus()
    }
    
    // Mouse click to focus
    MouseArea {
        anchors.fill: inputContainer
        onClicked: textInput.forceActiveFocus()
    }
} 