import QtQuick 2.15

Rectangle {
    id: root
    property int tagId: 0
    property string tagName: ""
    property color tagColor: "#4A90D9"
    property bool isActive: false
    signal clicked()

    width: chipText.implicitWidth + Theme.spacingMD * 2
    height: 22
    radius: Theme.radiusFull
    color: isActive ? Qt.rgba(0.95, 0.72, 0.35, 0.12) : Qt.rgba(tagColor.r, tagColor.g, tagColor.b, 0.12)
    border.color: isActive ? Qt.rgba(0.95, 0.72, 0.35, 0.42) : (mouseArea.containsMouse ? Qt.rgba(0.49, 0.88, 0.76, 0.28) : Theme.lineSoft)
    border.width: 1

    Text {
        id: chipText
        anchors.centerIn: parent
        text: root.tagName
        font.pixelSize: Theme.fontSizeXS
        font.family: Theme.fontFamilyPrimary
        font.weight: isActive ? Theme.fontMedium : Theme.fontNormal
        color: isActive ? "#FFD98A" : Theme.textSecondary
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
