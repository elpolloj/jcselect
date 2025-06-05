import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    property alias model: tableView.model
    property var columns: []
    property bool isLoading: false
    property bool sortable: true
    property string currentSortColumn: ""
    property bool sortDescending: true
    
    signal sortRequested(string columnKey, bool descending)
    
    color: Theme.backgroundColor
    radius: Theme.radius
    border.color: Theme.elevation2
    border.width: 1
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 0
        
        // Header row
        Rectangle {
            id: headerRect
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: Theme.elevation1
            radius: Theme.radius
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingSmall
                anchors.rightMargin: Theme.spacingSmall
                spacing: 0
                
                Repeater {
                    model: root.columns
                    
                    delegate: Button {
                        id: headerButton
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: modelData.width || 100
                        
                        enabled: root.sortable && modelData.sortable !== false
                        
                        contentItem: RowLayout {
                            spacing: Theme.spacingTiny
                            
                            Text {
                                text: modelData.title || modelData.key
                                font.pixelSize: Theme.bodySize
                                font.weight: Font.Medium
                                color: Theme.textColor
                                Layout.fillWidth: true
                                horizontalAlignment: Qt.application.layoutDirection === Qt.RightToLeft ? 
                                                   Text.AlignRight : Text.AlignLeft
                                
                                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                            }
                            
                            // Sort indicator
                            Text {
                                text: {
                                    if (root.currentSortColumn === modelData.key) {
                                        return root.sortDescending ? "↓" : "↑"
                                    }
                                    return ""
                                }
                                font.pixelSize: 12
                                color: Theme.primaryColor
                                visible: headerButton.enabled && root.currentSortColumn === modelData.key
                            }
                        }
                        
                        background: Rectangle {
                            color: headerButton.pressed ? Theme.elevation2 : 
                                   headerButton.hovered ? Theme.elevation1 : "transparent"
                            radius: Theme.radius
                        }
                        
                        onClicked: {
                            if (root.currentSortColumn === modelData.key) {
                                root.sortDescending = !root.sortDescending
                            } else {
                                root.currentSortColumn = modelData.key
                                root.sortDescending = true
                            }
                            root.sortRequested(modelData.key, root.sortDescending)
                        }
                    }
                }
            }
        }
        
        // Table content
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ListView {
                id: tableView
                anchors.fill: parent
                
                // RTL support
                layoutDirection: Qt.application.layoutDirection
                
                delegate: Rectangle {
                    id: rowDelegate
                    width: tableView.width
                    height: 40
                    color: index % 2 === 0 ? "transparent" : Theme.elevation1
                    
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        
                        onEntered: parent.color = Theme.elevation2
                        onExited: parent.color = index % 2 === 0 ? "transparent" : Theme.elevation1
                    }
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spacingSmall
                        anchors.rightMargin: Theme.spacingSmall
                        spacing: 0
                        
                        Repeater {
                            model: root.columns
                            
                            delegate: Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredWidth: modelData.width || 100
                                
                                Text {
                                    anchors.fill: parent
                                    text: {
                                        var value = rowDelegate.ListView.view.model[index] ? 
                                                   rowDelegate.ListView.view.model[index][modelData.key] : ""
                                        
                                        // Format value based on column type
                                        if (modelData.type === "number") {
                                            return Number(value).toLocaleString()
                                        } else if (modelData.type === "percentage") {
                                            return Number(value).toFixed(1) + "%"
                                        }
                                        return value || ""
                                    }
                                    font.pixelSize: Theme.bodySize
                                    color: Theme.textColor
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: {
                                        if (modelData.align === "center") return Text.AlignHCenter
                                        if (modelData.align === "right") return Text.AlignRight
                                        if (Qt.application.layoutDirection === Qt.RightToLeft) {
                                            return modelData.type === "number" ? Text.AlignLeft : Text.AlignRight
                                        } else {
                                            return modelData.type === "number" ? Text.AlignRight : Text.AlignLeft
                                        }
                                    }
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                    
                                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                                }
                            }
                        }
                    }
                }
                
                // Empty state
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.6
                    height: 100
                    color: "transparent"
                    visible: tableView.count === 0 && !root.isLoading
                    
                    Column {
                        anchors.centerIn: parent
                        spacing: Theme.spacingSmall
                        
                        Text {
                            text: "📊"
                            font.pixelSize: 48
                            horizontalAlignment: Text.AlignHCenter
                            anchors.horizontalCenter: parent.horizontalCenter
                            opacity: 0.5
                        }
                        
                        Text {
                            text: qsTr("لا توجد بيانات للعرض")
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
        }
    }
    
    // Loading overlay
    Rectangle {
        anchors.fill: parent
        color: "white"
        opacity: 0.8
        radius: Theme.radius
        visible: root.isLoading
        
        BusyIndicator {
            anchors.centerIn: parent
            width: 48
            height: 48
            running: root.isLoading
            
            contentItem: Item {
                implicitWidth: 48
                implicitHeight: 48
                
                Rectangle {
                    id: spinner
                    width: 32
                    height: 32
                    radius: 16
                    anchors.centerIn: parent
                    color: "transparent"
                    border.color: Theme.primaryColor
                    border.width: 3
                    
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: Theme.primaryColor
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.topMargin: 2
                    }
                    
                    RotationAnimation on rotation {
                        running: root.isLoading
                        loops: Animation.Infinite
                        duration: 1000
                        from: 0
                        to: 360
                    }
                }
            }
        }
        
        Text {
            anchors.top: parent.verticalCenter
            anchors.topMargin: 30
            anchors.horizontalCenter: parent.horizontalCenter
            text: qsTr("جاري تحميل البيانات...")
            font.pixelSize: Theme.bodySize
            color: Theme.textColor
            opacity: 0.8
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 