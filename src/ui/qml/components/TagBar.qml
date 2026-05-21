import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    height: Theme.tagBarHeight
    color: "transparent"

    property var tags: []
    property var activeTagIds: []
    signal tagToggled(int tagId)

    function refreshTags() {
        tags = bridge.getAllTags()
    }

    Component.onCompleted: refreshTags()

    ScrollView {
        anchors.fill: parent
        clip: true

        RowLayout {
            spacing: Theme.spacingXS

            Text {
                text: "标签"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.textTertiary
                Layout.alignment: Qt.AlignVCenter
            }

            Repeater {
                model: root.tags

                TagChip {
                    tagId: modelData.id || 0
                    tagName: modelData.name || ""
                    tagColor: modelData.color || "#4A90D9"
                    isActive: root.activeTagIds.indexOf(tagId) >= 0
                    onClicked: root.tagToggled(tagId)
                }
            }

            // Add tag button
            Rectangle {
                width: 22
                height: 22
                radius: Theme.radiusFull
                color: addTagMouse.containsMouse ? Qt.rgba(0.49, 0.88, 0.76, 0.08) : "transparent"
                border.color: addTagMouse.containsMouse ? Qt.rgba(0.49, 0.88, 0.76, 0.42) : Theme.lineSoft
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "+"
                    font.pixelSize: Theme.fontSizeMD
                    color: addTagMouse.containsMouse ? Theme.accentMint : Theme.textTertiary
                }

                MouseArea {
                    id: addTagMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    // TODO: open tag management dialog
                }
            }

            Item { Layout.fillWidth: true }
        }
    }
}
