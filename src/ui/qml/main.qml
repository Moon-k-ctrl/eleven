import QtQuick 2.15
import QtQuick.Layouts 1.15
import "components"

Window {
    id: root
    title: "拾遗"
    width: Theme.panelWidth
    height: Theme.panelHeight
    minimumWidth: Theme.panelWidth
    minimumHeight: Theme.panelHeight
    flags: Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
    visible: false
    color: "transparent"

    // Public API for Python bridge
    property alias searchBar: searchBar
    property bool showPhrases: false

    signal previewBarToggle()
    signal exportRequested()

    Rectangle {
        id: bgContainer
        anchors.fill: parent
        radius: Theme.radiusMD
        border.color: Theme.lineStrong
        border.width: 1
        clip: true

        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.bgPrimary }
            GradientStop { position: 1.0; color: Theme.bgSecondary }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacingMD
            anchors.rightMargin: Theme.spacingMD
            anchors.bottomMargin: Theme.spacingMD
            spacing: Theme.spacingSM

            TitleBar {
                Layout.fillWidth: true
            }

            FilterBar {
                id: filterBar
                Layout.fillWidth: true
                onCategorySelected: function(category) {
                    bridge.setCategory(category)
                }
                onSortSelected: function(sort) {
                    bridge.setSort(sort)
                }
            }

            TagBar {
                id: tagBar
                Layout.fillWidth: true
                onTagToggled: function(tagId) {
                    bridge.toggleTag(tagId)
                }
            }

            SearchBar {
                id: searchBar
                Layout.fillWidth: true
            }

            ActionBar {
                Layout.fillWidth: true
            }

            // ── Staging Shelf (暂存架) ──
            StagingShelf {
                id: stagingShelf
                Layout.fillWidth: true
                visible: stagingModel.count > 0 || stagingShelf.expanded
            }

            // Main list with drop overlay
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ClipboardListView {
                    id: listView
                    anchors.fill: parent
                    visible: !showPhrases
                }

                // Quick phrases panel
                QuickPhrasesPanel {
                    id: phrasesPanel
                    anchors.fill: parent
                    visible: showPhrases
                }

                // Empty state overlay
                EmptyState {
                    anchors.centerIn: parent
                    visible: clipboardModel.count === 0 && !showPhrases
                }

                // Drop overlay
                DropOverlay {
                    anchors.fill: parent
                }
            }
        }
    }

    // Connections
    Connections {
        target: bridge
        function onStatusChanged(status) {
            // titleBar auto-updates via property binding
        }
        function onItemsChanged() {
            // Refresh tag bar when items change
            tagBar.refreshTags()
        }
        function onStagingChanged() {
            // Staging shelf auto-updates via model
        }
    }

    // Keyboard shortcuts
    Keys.onEscapePressed: {
        if (searchBar.text) {
            searchBar.text = ""
            bridge.clearSearch()
        } else {
            root.visible = false
        }
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_V && (event.modifiers & Qt.ControlModifier)) {
            bridge.pasteFromClipboard()
            event.accepted = true
        } else if (event.key === Qt.Key_F && (event.modifiers & Qt.ControlModifier)) {
            searchBar.forceActiveFocus()
            event.accepted = true
        } else if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier) && bridge.multiSelectMode) {
            bridge.selectAll()
            event.accepted = true
        }
    }

    // Window close handler
    onVisibleChanged: {
        if (visible) {
            bridge.refreshList()
        }
    }
}

