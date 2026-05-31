import QtQuick 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    spacing: Theme.spacingSM

    property bool hasSearch: false
    property bool monitoringEnabled: bridge.clipboardEnabled

    visible: clipboardModel.count === 0

    // Icon area with radial gradient
    Item {
        Layout.fillWidth: true
        Layout.preferredHeight: 80
        Layout.topMargin: Theme.spacingMD

        Rectangle {
            anchors.centerIn: parent
            width: 72
            height: 72
            radius: 36
            color: "transparent"
            border.color: Qt.rgba(0.49, 0.88, 0.76, 0.15)
            border.width: 1

            Rectangle {
                anchors.fill: parent
                radius: 36
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Qt.rgba(0.49, 0.88, 0.76, 0.08) }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Text {
                anchors.centerIn: parent
                text: hasSearch ? Theme.iconSearch : (monitoringEnabled ? Theme.iconClipboard : "⏸")
                font.pixelSize: 32
            }
        }
    }

    // Title
    Text {
        text: hasSearch ? "未找到匹配内容" :
              monitoringEnabled ? "暂无剪贴内容" : "剪贴板监听已关闭"
        font.pixelSize: Theme.fontSizeLG
        font.weight: Theme.fontBold
        font.family: Theme.fontFamilyPrimary
        color: Theme.textSecondary
        Layout.alignment: Qt.AlignHCenter
    }

    // Subtitle
    Text {
        text: hasSearch ? "尝试其他关键词" :
              monitoringEnabled ? "复制内容后将自动出现在这里" : "开启后将自动记录复制内容"
        font.pixelSize: Theme.fontSizeXS
        font.family: Theme.fontFamilyPrimary
        color: Theme.textPlaceholder
        Layout.alignment: Qt.AlignHCenter
    }

    // Toggle monitoring button
    Rectangle {
        visible: !hasSearch
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: Theme.spacingSM
        width: monitorBtnText.implicitWidth + Theme.spacingMD * 2
        height: 32
        radius: 16
        color: {
            if (monitoringEnabled) return Qt.rgba(0.49, 0.88, 0.76, 0.08)
            if (monitorBtnMouse.containsMouse) return Qt.rgba(0.49, 0.88, 0.76, 0.25)
            return Qt.rgba(0.49, 0.88, 0.76, 0.15)
        }
        border.color: monitoringEnabled ? Qt.rgba(0.49, 0.88, 0.76, 0.3) : Qt.rgba(0.49, 0.88, 0.76, 0.5)
        border.width: 1

        // Breathing glow (only when monitoring is off)
        Rectangle {
            visible: !monitoringEnabled
            anchors.fill: parent
            radius: 16
            color: "transparent"
            border.color: Qt.rgba(0.49, 0.88, 0.76, 0.15)
            border.width: 2
            opacity: glowAnim.value

            NumberAnimation {
                id: glowAnim
                target: parent
                property: "opacity"
                from: 0.2; to: 0.6
                duration: 3000
                easing.type: Easing.InOutSine
                loops: Animation.Infinite
                running: !monitoringEnabled
            }
        }

        Text {
            id: monitorBtnText
            anchors.centerIn: parent
            text: monitoringEnabled ? "✓ 剪贴板监听已开启" : "▶  开启监听"
            font.pixelSize: Theme.fontSizeSM
            font.weight: Theme.fontBold
            font.family: Theme.fontFamilyPrimary
            color: monitoringEnabled ? Theme.accentMint : Theme.textPrimary
        }

        MouseArea {
            id: monitorBtnMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: bridge.toggleMonitoring()
        }
    }

    // Shortcut hints
    Column {
        visible: !hasSearch
        spacing: 4
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: Theme.spacingSM

        Repeater {
            model: [
                { key: "Win+Shift+V", desc: "打开/隐藏面板" },
                { key: "Ctrl+F", desc: "搜索内容" },
                { key: "Ctrl+V", desc: "从剪贴板粘贴到此处" },
            ]

            Row {
                spacing: Theme.spacingXS
                anchors.horizontalCenter: parent.horizontalCenter

                Rectangle {
                    width: keyLabel.implicitWidth + 8
                    height: 18
                    radius: 4
                    color: "#1AFFFFFF"
                    border.color: Theme.border
                    border.width: 1

                    Text {
                        id: keyLabel
                        anchors.centerIn: parent
                        text: modelData.key
                        font.pixelSize: 9
                        font.family: Theme.fontFamilySecondary
                        color: Theme.textSecondary
                    }
                }

                Text {
                    text: modelData.desc
                    font.pixelSize: Theme.fontSizeXS
                    font.family: Theme.fontFamilyPrimary
                    color: Theme.textPlaceholder
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
