import QtQuick 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    spacing: Theme.spacingSM

    property bool hasSearch: false

    visible: clipboardModel.count === 0

    Text {
        text: hasSearch ? Theme.iconSearch : Theme.iconClipboard
        font.pixelSize: 36
        Layout.alignment: Qt.AlignHCenter
    }

    Text {
        text: hasSearch ? "未找到匹配内容" : "暂无剪贴内容"
        font.pixelSize: Theme.fontSizeMD
        font.family: Theme.fontFamilyPrimary
        color: Theme.textTertiary
        Layout.alignment: Qt.AlignHCenter
    }

    Text {
        visible: !hasSearch
        text: "复制内容后将自动出现在这里"
        font.pixelSize: Theme.fontSizeXS
        font.family: Theme.fontFamilyPrimary
        color: Theme.textPlaceholder
        Layout.alignment: Qt.AlignHCenter
    }
}
