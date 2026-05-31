import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: delegate
    width: ListView.view ? ListView.view.width : 430
    height: Theme.itemHeight

    // Convert hex string to color object safely
    property color accentMintColor: Theme.accentMint

    color: (mouseArea.containsMouse || isSelected) ? Qt.rgba(accentMintColor.r, accentMintColor.g, accentMintColor.b, 0.075) : "transparent"
    border.color: (mouseArea.containsMouse || isSelected) ? Qt.rgba(accentMintColor.r, accentMintColor.g, accentMintColor.b, 0.18) : "transparent"
    border.width: 1

    // Model roles
    property int itemId: model.id || 0
    property string contentText: model.contentText || ""
    property string contentType: model.contentType || "TEXT"
    property string filePath: model.filePath || ""
    property string thumbnailPath: model.thumbnailPath || ""
    property bool isPinned: model.isPinned || false
    property bool isFavorite: model.isFavorite || false
    property bool isStarred: model.isStarred || false
    property string previewText: model.previewText || ""
    property string timeText: model.timeText || ""
    property string sourceIcon: model.sourceIcon || "📋"
    property var tags: model.tags || []
    property string displayType: model.displayType || "text"
    property string fileName: model.fileName || ""
    property string filePathDisplay: model.filePathDisplay || ""
    property string smartType: model.smartType || ""
    property string smartPreview: model.smartPreview || ""

    // Selection state — uses selectedItemIds property (updates via _selectedItemIdsChanged signal)
    property bool isSelected: bridge.multiSelectMode && bridge.selectedItemIds.indexOf(itemId) >= 0

    // Type icon color — based on displayType for precise file-type coloring
    function typeColor() {
        switch (displayType) {
            case "word": return Theme.typeWord
            case "excel": return Theme.typeExcel
            case "pdf": return Theme.typePdf
            case "ppt": return Theme.typePpt
            case "archive": return Theme.typeArchive
            case "image": return Theme.typeImage
            case "html": return Theme.accentCyan
            default: return Theme.typeText
        }
    }

    // Type icon letter — single character for the icon square
    function typeIcon() {
        switch (displayType) {
            case "word": return "W"
            case "excel": return "E"
            case "pdf": return "P"
            case "ppt": return "T"
            case "archive": return "A"
            case "image": return "🖼"
            case "html": return "🌐"
            case "text_file": return "📄"
            case "markdown": return "M"
            default: return "T"
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingSM
        anchors.rightMargin: Theme.spacingSM
        spacing: Theme.spacingSM

        // Multi-select checkbox
        Rectangle {
            visible: bridge.multiSelectMode
            width: 16
            height: 16
            radius: 3
            color: isSelected ? Theme.accentMint : "transparent"
            border.color: isSelected ? Theme.accentMint : Theme.border
            border.width: 1
            Layout.alignment: Qt.AlignVCenter

            Text {
                visible: isSelected
                anchors.centerIn: parent
                text: "✓"
                font.pixelSize: 10
                color: Theme.textInverse
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: bridge.toggleItemSelection(itemId)
            }
        }

        // Type icon / Thumbnail
        Item {
            width: Theme.thumbnailSize
            height: Theme.thumbnailSize
            Layout.alignment: Qt.AlignVCenter

            // Sibling background with opacity to safely render dynamic typeColor
            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusSM
                color: typeColor()
                opacity: 0.14
            }

            // Show thumbnail for images
            Image {
                visible: thumbnailPath !== "" && contentType === "IMAGE"
                anchors.fill: parent
                anchors.margins: 1
                source: thumbnailPath ? "file:///" + thumbnailPath : ""
                fillMode: Image.PreserveAspectCrop
                clip: true
            }

            // Colored type icon letter for non-images
            Text {
                visible: thumbnailPath === "" || contentType !== "IMAGE"
                anchors.centerIn: parent
                text: typeIcon()
                font.pixelSize: 20
                font.weight: Font.Bold
                color: typeColor()
            }
        }

        // Content column
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 2

            // Main title: fileName (bold) + smart badge
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingXS
                Layout.alignment: Qt.AlignBottom

                Text {
                    Layout.fillWidth: true
                    text: fileName
                    font.pixelSize: Theme.fontSizeLG
                    font.weight: Theme.fontBold
                    font.family: Theme.fontFamilyPrimary
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                // Smart content type badge
                Rectangle {
                    visible: smartType !== ""
                    width: smartBadgeText.implicitWidth + Theme.spacingXS * 2
                    height: 16
                    radius: 8
                    color: {
                        switch (smartType) {
                            case "url": return Qt.rgba(0.4, 0.72, 0.78, 0.15)
                            case "email": return Qt.rgba(0.62, 0.87, 1.0, 0.15)
                            case "phone": return Qt.rgba(0.95, 0.72, 0.29, 0.15)
                            case "color": return Qt.rgba(0.49, 0.88, 0.76, 0.15)
                            case "json": return Qt.rgba(0.95, 0.72, 0.29, 0.15)
                            case "code": return Qt.rgba(0.49, 0.88, 0.76, 0.15)
                            default: return Qt.rgba(1, 1, 1, 0.05)
                        }
                    }

                    Text {
                        id: smartBadgeText
                        anchors.centerIn: parent
                        text: {
                            switch (smartType) {
                                case "url": return "🔗 URL"
                                case "email": return "✉ Email"
                                case "phone": return "📱 Phone"
                                case "color": return "🎨 Color"
                                case "json": return "{ } JSON"
                                case "code": return "⌨ Code"
                                default: return smartType
                            }
                        }
                        font.pixelSize: 8
                        font.family: Theme.fontFamilySecondary
                        font.weight: Theme.fontBold
                        color: {
                            switch (smartType) {
                                case "url": return Theme.accentCyan
                                case "email": return "#9FCBFF"
                                case "phone": return Theme.accentGold
                                case "color": return Theme.accentMint
                                case "json": return Theme.accentGold
                                case "code": return Theme.accentMint
                                default: return Theme.textTertiary
                            }
                        }
                    }
                }
            }

            // Bottom row: filePathDisplay + time + source + tags
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingXS
                Layout.alignment: Qt.AlignTop

                // Path/folder info (only for FILES)
                Text {
                    visible: filePathDisplay !== ""
                    text: filePathDisplay
                    font.pixelSize: Theme.fontSizeXS
                    font.family: Theme.fontFamilySecondary
                    color: Theme.textTertiary
                }

                // Separator between path and time
                Rectangle {
                    visible: filePathDisplay !== ""
                    width: 1
                    height: 10
                    color: Theme.border
                }

                Text {
                    text: timeText
                    font.pixelSize: Theme.fontSizeXS
                    font.family: Theme.fontFamilySecondary
                    color: Theme.textTertiary
                }

                Text {
                    text: sourceIcon
                    font.pixelSize: Theme.fontSizeXS
                }

                // Tag chips (max 3)
                Repeater {
                    model: delegate.tags.length > 3 ? 3 : delegate.tags.length

                    Rectangle {
                        property var tagData: delegate.tags[index]
                        width: tagLabel.implicitWidth + Theme.spacingXS * 2
                        height: 14
                        radius: Theme.radiusFull
                        color: Qt.rgba(1, 1, 1, 0.045)

                        Text {
                            id: tagLabel
                            anchors.centerIn: parent
                            text: tagData.name || ""
                            font.pixelSize: 8
                            font.family: Theme.fontFamilyPrimary
                            color: Theme.textSecondary
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }
        }

        // Action indicators column
        ColumnLayout {
            spacing: 2
            Layout.alignment: Qt.AlignVCenter

            // Pin indicator
            Text {
                visible: isPinned
                text: Theme.iconPin
                font.pixelSize: Theme.fontSizeSM
                Layout.alignment: Qt.AlignRight
            }

            // Favorite indicator
            Text {
                visible: isFavorite
                text: Theme.iconFavorite
                font.pixelSize: Theme.fontSizeSM
                color: Theme.accentGold
                Layout.alignment: Qt.AlignRight
            }

            // Star indicator
            Text {
                visible: isStarred
                text: Theme.iconStar
                font.pixelSize: Theme.fontSizeXS
                Layout.alignment: Qt.AlignRight
            }
        }
    }

    // Mouse interaction
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                contextMenu.popup()
                return
            }
            if (bridge.multiSelectMode) {
                bridge.toggleItemSelection(itemId)
            } else {
                bridge.copyItem(itemId)
            }
        }

        onDoubleClicked: {
            bridge.requestPreview(itemId)
        }
    }

    // Context menu — enhanced with logical groups
    Menu {
        id: contextMenu

        // ── 快捷操作 ──
        MenuItem {
            text: "📋  复制"
            onTriggered: bridge.copyItem(itemId)
        }
        MenuItem {
            text: "📝  复制为纯文本"
            visible: contentType === "HTML"
            onTriggered: bridge.copyAsPlainText(itemId)
        }
        MenuItem {
            text: "✏️  编辑"
            onTriggered: bridge.editItem(itemId)
        }

        MenuSeparator {}

        // ── 整理 ──
        MenuItem {
            text: "🏷  添加标签"
            onTriggered: bridge.showTagDialog(itemId)
        }
        MenuItem {
            text: "📤  导出此条"
            onTriggered: bridge.exportSingleItem(itemId)
        }

        MenuSeparator {}

        // ── 发送 ──
        MenuItem {
            text: "◨  发送到预览栏"
            onTriggered: bridge.sendToPreviewBar(itemId)
        }
        MenuItem {
            text: "📥  发送到暂存架"
            onTriggered: bridge.addToStaging(itemId)
        }

        MenuSeparator {}

        // ── 标记 ──
        MenuItem {
            text: isFavorite ? "★  取消收藏" : "☆  收藏"
            onTriggered: bridge.toggleFavorite(itemId)
        }
        MenuItem {
            text: isStarred ? "⭐  取消星标" : "☆  星标"
            onTriggered: bridge.toggleStar(itemId)
        }
        MenuItem {
            text: isPinned ? "📌  取消置顶" : "📌  置顶"
            onTriggered: bridge.togglePin(itemId)
        }

        MenuSeparator {}

        // ── 危险操作 ──
        MenuItem {
            text: "🗑  删除"
            onTriggered: bridge.deleteItem(itemId)
        }
        MenuItem {
            text: "☑  多选模式"
            onTriggered: {
                if (!bridge.multiSelectMode) bridge.toggleMultiSelect()
                bridge.toggleItemSelection(itemId)
            }
        }
    }

    // Bottom border
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.lineSoft
    }
}
