import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

RowLayout {
    id: root
    
    property alias model: comboBox.model
    property string selectedPenId: ""
    property bool showAllPensOption: true
    
    signal penSelected(string penId)
    
    spacing: Theme.spacingSmall
    
    Text {
        text: qsTr("القلم:")
        font.pixelSize: Theme.bodySize
        color: Theme.textColor
        Layout.alignment: Qt.AlignVCenter
        
        LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    }
    
    ComboBox {
        id: comboBox
        Layout.fillWidth: true
        Layout.preferredWidth: 200
        Layout.preferredHeight: Theme.buttonHeight
        
        // Enable search functionality
        editable: true
        selectTextByMouse: true
        
        displayText: {
            if (currentIndex === 0 && showAllPensOption) {
                return qsTr("جميع الأقلام")
            }
            return currentText
        }
        
        model: {
            var items = []
            if (showAllPensOption) {
                items.push({
                    "id": "all",
                    "display_name": qsTr("جميع الأقلام"),
                    "label": qsTr("جميع الأقلام"),
                    "town_name": ""
                })
            }
            
            if (root.model && Array.isArray(root.model)) {
                items = items.concat(root.model)
            }
            
            return items
        }
        
        textRole: "display_name"
        valueRole: "id"
        
        delegate: ItemDelegate {
            width: comboBox.width
            height: 40
            
            contentItem: Text {
                text: modelData.display_name || ""
                font.pixelSize: Theme.bodySize
                color: Theme.textColor
                verticalAlignment: Text.AlignVCenter
                
                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            }
            
            background: Rectangle {
                color: parent.hovered ? Theme.elevation1 : "transparent"
                radius: Theme.radius
            }
        }
        
        background: Rectangle {
            color: Theme.backgroundColor
            border.color: comboBox.activeFocus ? Theme.primaryColor : "#e0e0e0"
            border.width: comboBox.activeFocus ? 2 : 1
            radius: Theme.radius
        }
        
        contentItem: Text {
            text: comboBox.displayText
            font.pixelSize: Theme.bodySize
            color: Theme.textColor
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Qt.application.layoutDirection === Qt.RightToLeft ? Text.AlignRight : Text.AlignLeft
            leftPadding: Theme.spacingSmall
            rightPadding: Theme.spacingSmall
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        onCurrentValueChanged: {
            if (currentValue) {
                selectedPenId = currentValue
                penSelected(currentValue)
            }
        }
        
        // Search functionality
        onEditTextChanged: {
            if (!popup.visible) return
            
            var searchText = editText.toLowerCase()
            var filteredModel = []
            
            // Always include "All Pens" option if enabled
            if (showAllPensOption) {
                filteredModel.push({
                    "id": "all",
                    "display_name": qsTr("جميع الأقلام"),
                    "label": qsTr("جميع الأقلام"),
                    "town_name": ""
                })
            }
            
            // Filter pens based on search text
            if (root.model && Array.isArray(root.model)) {
                for (var i = 0; i < root.model.length; i++) {
                    var pen = root.model[i]
                    if (pen.display_name.toLowerCase().includes(searchText) ||
                        pen.label.toLowerCase().includes(searchText) ||
                        pen.town_name.toLowerCase().includes(searchText)) {
                        filteredModel.push(pen)
                    }
                }
            }
            
            comboBox.model = filteredModel
        }
        
        Component.onCompleted: {
            // Set default selection to "All Pens" if available
            if (showAllPensOption && count > 0) {
                currentIndex = 0
                selectedPenId = "all"
            }
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 