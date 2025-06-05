import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0

Rectangle {
    id: root
    
    // Properties
    property var resultsController: null
    property bool isExporting: false
    
    // Signals
    signal exportStarted()
    signal exportCompleted(string filePath)
    signal exportFailed(string errorMessage)
    
    width: exportButton.width
    height: exportButton.height
    color: "transparent"
    
    // Main export button
    Button {
        id: exportButton
        text: qsTr("تصدير")
        icon.name: "document-export"
        
        background: Rectangle {
            color: parent.pressed ? Theme.primaryColorDark 
                 : parent.hovered ? Theme.primaryColorLight 
                 : Theme.primaryColor
            radius: Theme.radius
            border.width: 1
            border.color: Theme.outlineColor
        }
        
        contentItem: RowLayout {
            spacing: Theme.spacing / 2
            
            Text {
                text: parent.parent.text
                font: parent.parent.font
                color: Theme.onPrimaryColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
            }
            
            // Busy indicator when exporting
            BusyIndicator {
                id: busyIndicator
                visible: root.isExporting
                running: visible
                
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                
                contentItem: Rectangle {
                    color: "transparent"
                    
                    Rectangle {
                        width: parent.width * 0.6
                        height: width
                        radius: width / 2
                        color: Theme.primaryColor
                        anchors.centerIn: parent
                        
                        RotationAnimation on rotation {
                            running: busyIndicator.running
                            duration: 1000
                            loops: Animation.Infinite
                            from: 0
                            to: 360
                        }
                    }
                }
            }
        }
        
        onClicked: {
            if (!root.isExporting) {
                exportMenu.open()
            }
        }
    }
    
    // Export options menu
    Menu {
        id: exportMenu
        y: exportButton.height + Theme.spacing / 2
        
        MenuItem {
            text: qsTr("تصدير CSV")
            icon.name: "text-csv"
            enabled: !root.isExporting
            
            onTriggered: {
                if (resultsController) {
                    root._startExport()
                    resultsController.exportCsv()
                }
            }
        }
        
        MenuItem {
            text: qsTr("تصدير PDF")
            icon.name: "application-pdf"
            enabled: !root.isExporting
            
            onTriggered: {
                if (resultsController) {
                    root._startExport()
                    resultsController.exportPdf()
                }
            }
        }
        
        MenuSeparator {}
        
        MenuItem {
            text: qsTr("إلغاء")
            icon.name: "dialog-cancel"
            onTriggered: exportMenu.close()
        }
    }
    
    // Snackbar for success/error messages
    Rectangle {
        id: snackbar
        anchors.bottom: parent.bottom
        anchors.bottomMargin: -height - 20
        anchors.horizontalCenter: parent.horizontalCenter
        
        width: Math.max(snackbarText.implicitWidth + 32, 200)
        height: 48
        radius: Theme.radius
        color: snackbarSuccess ? Theme.successColor : Theme.errorColor
        opacity: 0
        
        property bool snackbarSuccess: true
        property string snackbarMessage: ""
        
        Text {
            id: snackbarText
            anchors.centerIn: parent
            text: parent.snackbarMessage
            color: Theme.onSuccessColor
            font.pixelSize: Theme.bodyMedium
            horizontalAlignment: Text.AlignHCenter
        }
        
        // Auto-hide animation
        NumberAnimation {
            id: snackbarAnimation
            target: snackbar
            property: "opacity"
            duration: 250
            easing.type: Easing.InOutQuad
        }
        
        Timer {
            id: snackbarTimer
            interval: 3000
            onTriggered: root._hideSnackbar()
        }
        
        function show(message, success) {
            snackbarMessage = message
            snackbarSuccess = success
            snackbarAnimation.to = 1
            snackbarAnimation.start()
            snackbarTimer.start()
        }
        
        function hide() {
            snackbarAnimation.to = 0
            snackbarAnimation.start()
            snackbarTimer.stop()
        }
    }
    
    // Connection to results controller
    Connections {
        target: resultsController
        
        function onExportCompleted(filePath) {
            root._endExport()
            snackbar.show(qsTr("تم التصدير بنجاح"), true)
            root.exportCompleted(filePath)
        }
        
        function onExportFailed(errorMessage) {
            root._endExport()
            snackbar.show(qsTr("فشل التصدير: ") + errorMessage, false)
            root.exportFailed(errorMessage)
        }
    }
    
    // Internal functions
    function _startExport() {
        isExporting = true
        exportStarted()
    }
    
    function _endExport() {
        isExporting = false
    }
    
    function _hideSnackbar() {
        snackbar.hide()
    }
    
    // Tooltip
    ToolTip {
        text: root.isExporting ? qsTr("جاري التصدير...") : qsTr("تصدير النتائج")
        visible: exportButton.hovered
        delay: 500
    }
} 