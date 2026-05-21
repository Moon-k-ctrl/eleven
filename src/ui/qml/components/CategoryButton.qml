import QtQuick 2.15

Rectangle {
    id: root
    property string category: ""
    property string label: ""
    property bool isActive: false
    signal clicked()

    width: labelItem.implicitWidth + Theme.spacingMD * 2
    height: 24
    radius: Theme.radiusSM
    color: isActive
        ? Qt.rgba(0.49, 0.88, 0.76, 0.10)
        : (mouseArea.containsMouse ? Qt.rgba(0.49, 0.88, 0.76, 0.08) : Qt.rgba(1,1,1,0.045))
    border.color: isActive
        ? Qt.rgba(0.49, 0.88, 0.76, 0.34)
        : (mouseArea.containsMouse ? Qt.rgba(0.49, 0.88, 0.76, 0.22) : Theme.lineSoft)
    border.width: 1

    Text {
        id: labelItem
        anchors.centerIn: parent
        text: root.label
        font.pixelSize: Theme.fontSizeXS
        font.family: Theme.fontFamilyPrimary
        font.weight: isActive ? Theme.fontMedium : Theme.fontNormal
        color: isActive ? Theme.accentMint : Theme.textSecondary
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
