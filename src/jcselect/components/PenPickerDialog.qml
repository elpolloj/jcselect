import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0
import jcselect 1.0

Dialog {
    id: root

    property var controller: penController

    title: qsTr("Select Polling Station")
    modal: true
    closePolicy: Dialog.NoAutoClose

    width: 400
    height: 300

    anchors.centerIn: parent

    // Ensure RTL support
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    // Pen picker controller (will be registered as QML type)
    property var penController: null

    Component.onCompleted: {
        if (penController) {
            penController.loadAvailablePens()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.margin
        spacing: Theme.spacing

        Text {
            text: qsTr("Please select your assigned polling station:")
            font.pixelSize: Theme.bodySize
            color: Theme.textColor
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        ComboBox {
            id: penComboBox
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.searchBarHeight

            textRole: "label"
            valueRole: "id"

            displayText: currentIndex >= 0 ? 
                qsTr("%1 - %2").arg(model[currentIndex]?.label || "").arg(model[currentIndex]?.town_name || "") : 
                qsTr("Select a polling station...")

            delegate: ItemDelegate {
                width: penComboBox.width
                contentItem: ColumnLayout {
                    spacing: 2
                    Text {
                        text: model.label
                        font.pixelSize: Theme.bodySize
                        font.weight: Font.Medium
                        color: Theme.textColor
                        Layout.fillWidth: true
                    }
                    Text {
                        text: model.town_name
                        font.pixelSize: Theme.captionSize
                        color: Theme.textColor
                        opacity: 0.7
                        Layout.fillWidth: true
                    }
                }

                background: Rectangle {
                    color: parent.hovered ? Theme.surfaceColor : "transparent"
                    radius: Theme.radius
                }
            }

            background: Rectangle {
                color: Theme.surfaceColor
                border.color: penComboBox.activeFocus ? Theme.primaryColor : Theme.textColor
                border.width: penComboBox.activeFocus ? 2 : 1
                radius: Theme.radius
            }

            popup: Popup {
                y: penComboBox.height + 4
                width: penComboBox.width
                implicitHeight: contentItem.implicitHeight
                padding: 1

                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: penComboBox.popup.visible ? penComboBox.delegateModel : null
                    currentIndex: penComboBox.highlightedIndex

                    ScrollIndicator.vertical: ScrollIndicator { }
                }

                background: Rectangle {
                    color: Theme.backgroundColor
                    border.color: Theme.primaryColor
                    border.width: 1
                    radius: Theme.radius
                }
            }
        }

        // Error text
        Text {
            id: errorText
            visible: false
            color: Theme.errorColor
            font.pixelSize: Theme.captionSize
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            Button {
                id: confirmButton
                text: qsTr("Confirm Selection")
                enabled: penComboBox.currentIndex >= 0

                background: Rectangle {
                    color: parent.enabled ? Theme.primaryColor : Theme.surfaceColor
                    radius: Theme.radius
                    opacity: parent.enabled ? 1.0 : 0.6
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
                    if (penComboBox.currentIndex >= 0 && penController) {
                        const selectedPen = penComboBox.model[penComboBox.currentIndex]
                        penController.selectPen(selectedPen.id)
                    }
                }
            }
        }
    }

    // Connection to controller signals
    Connections {
        target: penController
        function onPensLoaded() {
            if (penController) {
                penComboBox.model = penController.availablePens
            }
        }
        function onSelectionCompleted(penId) {
            root.accept()
        }
        function onErrorOccurred(error) {
            errorText.text = error
            errorText.visible = true
        }
    }
} 