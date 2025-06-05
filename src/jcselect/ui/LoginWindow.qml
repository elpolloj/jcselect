import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0

Rectangle {
    id: root
    
    property bool isLoading: false
    
    color: Theme.backgroundColor
    
    // Error message
    property string errorMessage: ""
    
    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(400, parent.width - Theme.margin * 4)
        spacing: Theme.spacing * 2
        
        // Logo/Title area
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spacing
            
            Text {
                text: "🗳️"
                font.pixelSize: 48
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: qsTr("jcselect")
                font.pixelSize: Theme.headlineLarge
                font.weight: Font.Bold
                color: Theme.primaryColor
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: qsTr("Lebanese Election System")
                font.pixelSize: Theme.bodySize
                color: Theme.textColor
                opacity: 0.7
                Layout.alignment: Qt.AlignHCenter
            }
        }
        
        // Login form
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing
            
            // Username field
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                
                Text {
                    text: qsTr("Username")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                }
                
                TextField {
                    id: usernameField
                    Layout.fillWidth: true
                    placeholderText: qsTr("Enter your username")
                    enabled: !root.isLoading
                    
                    background: Rectangle {
                        color: Theme.surfaceColor
                        border.color: parent.activeFocus ? Theme.primaryColor : Theme.outlineColor
                        border.width: parent.activeFocus ? 2 : 1
                        radius: Theme.radius
                    }
                    
                    Keys.onReturnPressed: {
                        if (passwordField.text !== "") {
                            loginButton.clicked()
                        } else {
                            passwordField.forceActiveFocus()
                        }
                    }
                }
            }
            
            // Password field
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                
                Text {
                    text: qsTr("Password")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                }
                
                TextField {
                    id: passwordField
                    Layout.fillWidth: true
                    placeholderText: qsTr("Enter your password")
                    echoMode: TextInput.Password
                    enabled: !root.isLoading
                    
                    background: Rectangle {
                        color: Theme.surfaceColor
                        border.color: parent.activeFocus ? Theme.primaryColor : Theme.outlineColor
                        border.width: parent.activeFocus ? 2 : 1
                        radius: Theme.radius
                    }
                    
                    Keys.onReturnPressed: loginButton.clicked()
                }
            }
            
            // Remember me checkbox
            CheckBox {
                id: rememberMeCheckBox
                text: qsTr("Remember me")
                checked: true
                enabled: !root.isLoading
                
                indicator: Rectangle {
                    implicitWidth: 20
                    implicitHeight: 20
                    x: parent.leftPadding
                    y: parent.topPadding + (parent.availableHeight - height) / 2
                    radius: 3
                    border.color: parent.checked ? Theme.primaryColor : Theme.outlineColor
                    border.width: parent.checked ? 2 : 1
                    color: parent.checked ? Theme.primaryColor : Theme.surfaceColor
                    
                    Text {
                        text: "✓"
                        color: "white"
                        anchors.centerIn: parent
                        font.pixelSize: 12
                        visible: parent.parent.checked
                    }
                }
            }
            
            // Login button
            Button {
                id: loginButton
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                text: root.isLoading ? qsTr("Logging in...") : qsTr("Login")
                enabled: !root.isLoading && usernameField.text !== "" && passwordField.text !== ""
                
                background: Rectangle {
                    color: parent.enabled ? Theme.primaryColor : Theme.surfaceColor
                    radius: Theme.radius
                    opacity: parent.pressed ? 0.8 : 1.0
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: Theme.bodySize
                    font.weight: Font.Medium
                    color: parent.enabled ? "white" : Theme.textColor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                
                onClicked: {
                    console.log("=== Login button clicked ===");
                    console.log("loginController exists:", !!loginController);
                    console.log("loginController type:", typeof loginController);
                    console.log("Username:", usernameField.text);
                    console.log("Password length:", passwordField.text.length);
                    
                    if (loginController) {
                        console.log("Calling loginController.authenticate...");
                        root.isLoading = true
                        root.errorMessage = ""
                        loginController.authenticate(
                            usernameField.text,
                            passwordField.text,
                            rememberMeCheckBox.checked
                        )
                        console.log("authenticate() called");
                    } else {
                        console.log("ERROR: loginController is null/undefined!");
                    }
                }
            }
            
            // Error message
            Text {
                Layout.fillWidth: true
                text: root.errorMessage
                color: Theme.errorColor
                font.pixelSize: Theme.bodySize
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                visible: root.errorMessage !== ""
                
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -Theme.spacing / 2
                    color: Theme.errorColor
                    opacity: 0.1
                    radius: Theme.radius
                    visible: parent.visible
                }
            }
        }
        
        // Status information
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 4
            
            Text {
                text: appMode === "admin" ? qsTr("Administrator Mode") : 
                      appMode === "operator" ? qsTr("Operator Mode") : 
                      qsTr("Auto Mode")
                font.pixelSize: Theme.captionSize
                color: Theme.primaryColor
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: qsTr("Version 0.1.0")
                font.pixelSize: Theme.captionSize
                color: Theme.textColor
                opacity: 0.5
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
    
    // Loading indicator
    Rectangle {
        anchors.fill: parent
        color: "#80000000"
        visible: root.isLoading
        
        BusyIndicator {
            anchors.centerIn: parent
            running: parent.visible
        }
    }
    
    // Connections to login controller
    Connections {
        target: loginController
        
        function onLoginSuccessful(userInfo) {
            root.isLoading = false
            // Success will be handled by App.qml
        }
        
        function onLoginFailed(errorMessage) {
            root.isLoading = false
            root.errorMessage = errorMessage
        }
        
        function onPenSelectionRequired() {
            root.isLoading = false
            // Pen selection will be handled by App.qml
        }
    }
    
    // Focus management
    Component.onCompleted: {
        usernameField.forceActiveFocus()
    }
} 