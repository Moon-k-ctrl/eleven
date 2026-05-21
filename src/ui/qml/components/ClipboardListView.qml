import QtQuick 2.15
import QtQuick.Controls 2.15

ListView {
    id: listView
    clip: true
    spacing: 0
    model: clipboardModel

    delegate: ClipboardItemDelegate {}

    // Empty state
    EmptyState {
        anchors.centerIn: parent
        hasSearch: bridge.searchQuery !== "" // TODO: expose searchQuery property
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
