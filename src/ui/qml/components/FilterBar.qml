import QtQuick 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root
    spacing: Theme.spacingSM

    property string currentCategory: "ALL"
    signal categorySelected(string category)

    // Category definitions
    ListModel {
        id: categoryModel
        ListElement { key: "ALL"; label: "全部" }
        ListElement { key: "DEFAULT"; label: "文本" }
        ListElement { key: "IMAGE"; label: "图片" }
        ListElement { key: "WORD"; label: "Word" }
        ListElement { key: "EXCEL"; label: "Excel" }
        ListElement { key: "PDF"; label: "PDF" }
        ListElement { key: "PPT"; label: "PPT" }
        ListElement { key: "ARCHIVE"; label: "压缩" }
    }

    Repeater {
        model: categoryModel

        CategoryButton {
            category: model.key
            label: model.label
            isActive: root.currentCategory === model.key
            onClicked: {
                root.currentCategory = model.key
                root.categorySelected(model.key)
            }
        }
    }

    Item { Layout.fillWidth: true }
}
