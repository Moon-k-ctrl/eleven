import QtQuick 2.15

Rectangle {
    property string label: "T"
    property color baseColor: Theme.accentCyan

    width: 36
    height: 36
    radius: 9
    color: Qt.rgba(baseColor.r, baseColor.g, baseColor.b, 0.15)
    border.color: Qt.rgba(baseColor.r, baseColor.g, baseColor.b, 0.25)
    border.width: 1

    Text {
        anchors.centerIn: parent
        text: label
        color: Theme.textPrimary
        font.pixelSize: 15
        font.weight: Theme.fontBold
        font.family: Theme.fontFamilyPrimary
    }
}
