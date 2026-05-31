import QtQuick 2.15
import QtQuick.Controls 2.15

ListView {
    id: listView
    clip: true
    spacing: 0
    model: clipboardModel

    delegate: ClipboardItemDelegate {}

    // Time group section headers
    section.property: "timeGroup"
    section.delegate: Rectangle {
        width: listView.width
        height: 28
        color: "transparent"

        Row {
            anchors.left: parent.left
            anchors.leftMargin: Theme.spacingSM
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.spacingXS

            Text {
                text: section === "今天" ? "📅" :
                      section === "昨天" ? "🕐" :
                      section === "本周" ? "📆" :
                      section === "本月" ? "📋" : "📦"
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: section
                font.pixelSize: Theme.fontSizeXS
                font.weight: Theme.fontBold
                font.family: Theme.fontFamilyPrimary
                color: Theme.textTertiary
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Subtle separator line
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: Theme.spacingSM
            anchors.rightMargin: Theme.spacingSM
            height: 1
            color: Theme.lineSoft
        }
    }

    // Empty state
    EmptyState {
        anchors.centerIn: parent
        hasSearch: bridge.searchQuery !== ""
        visible: clipboardModel.count === 0
    }

    // Scrollbar
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: 6

        contentItem: Rectangle {
            implicitWidth: 6
            radius: 3
            color: parent.pressed ? Theme.accentMint : Qt.rgba(0.49, 0.88, 0.76, 0.20)
        }
    }

    // Keyboard navigation
    Keys.onUpPressed: decrementCurrentIndex()
    Keys.onDownPressed: incrementCurrentIndex()
    Keys.onReturnPressed: {
        var item = clipboardModel.get_item(currentIndex)
        if (item) bridge.copyItem(item.id)
    }

    // Highlight on focus
    highlightFollowsCurrentItem: true
    highlight: Rectangle {
        color: Qt.rgba(0.49, 0.88, 0.76, 0.1)
        radius: Theme.radiusSM
    }
}
