import QtQuick 2.15
import jcselect.ui 1.0

Rectangle {
    anchors.fill: parent
    color: "transparent"
    visible: !Theme.isDarkMode   // hide in dark mode
    z: -1                              // sits behind cards

    Image {
        anchors.fill: parent
        source: "qrc:/bg/pattern.svg"
        fillMode: Image.Tile
        opacity: 0.10                  // 10% opacity for subtle effect
        mirror: Qt.RightToLeft        // keep pattern direction consistent in RTL
    }
} 