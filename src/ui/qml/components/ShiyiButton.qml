import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: control
    property bool primary: false
    property bool danger: false
    property string iconText: ""

    property real hoverYOffset: (control.hovered && !control.pressed) ? -1.5 : 0
    Behavior on hoverYOffset { NumberAnimation { duration: Theme.animFast } }
    transform: Translate { y: control.hoverYOffset }

    implicitHeight: 32
    leftPadding: 12
    rightPadding: 12
    spacing: 6

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight

        Row {
            id: contentRow
            spacing: 6
            anchors.centerIn: parent
            Text {
                text: control.iconText
                color: label.color
                font.pixelSize: 13
                font.family: Theme.fontFamilyEmoji
                visible: control.iconText !== ""
            }
            Text {
                id: label
                text: control.text
                color: control.primary
                    ? Theme.textInverse
                    : control.danger
                        ? (control.hovered ? Theme.error : Theme.textSecondary)
                        : (control.hovered ? Theme.textPrimary : Theme.textSecondary)
                font.pixelSize: Theme.fontSizeSM
                font.weight: control.primary ? Theme.fontBold : Theme.fontMedium
                font.family: Theme.fontFamilyPrimary
                wrapMode: Text.NoWrap
            }
        }
    }

    background: Rectangle {
        radius: Theme.radiusSM
        gradient: control.primary
            ? Gradient {
                GradientStop { position: 0.0; color: Theme.accentMint }
                GradientStop { position: 1.0; color: "#69C9DC" }
              }
            : null
        color: control.primary
            ? "transparent"
            : control.hovered
                ? (control.danger ? Qt.rgba(0.94, 0.39, 0.39, 0.10) : Qt.rgba(0.49, 0.88, 0.76, 0.10))
                : Qt.rgba(1, 1, 1, 0.045)
        border.color: control.primary
            ? Qt.rgba(0.49, 0.88, 0.76, 0.72)
            : control.hovered
                ? (control.danger ? Qt.rgba(0.94, 0.39, 0.39, 0.32) : Qt.rgba(0.49, 0.88, 0.76, 0.32))
                : Theme.lineSoft
        border.width: 1

        Behavior on color { ColorAnimation { duration: Theme.animFast } }
        Behavior on border.color { ColorAnimation { duration: Theme.animFast } }
    }
}
