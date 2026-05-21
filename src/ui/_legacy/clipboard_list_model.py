"""Virtual list model for clipboard items."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QMimeData, QModelIndex, Qt

from src.models.clipboard_item import ClipboardItem

MIME_TYPE = "application/x-clipboard-item"


class ClipboardListModel(QAbstractListModel):
    """Model for clipboard items with lazy loading and drag-and-drop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[ClipboardItem] = []
        self._page_size = 50
        self._has_more = True

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None

        item = self._items[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return item.short_preview()
        elif role == Qt.ItemDataRole.UserRole:
            return item
        elif role == Qt.ItemDataRole.ToolTipRole:
            text = item.short_preview(200)
            if item.tags:
                tag_names = ", ".join(t.name for t in item.tags)
                text = f"{text}\nTags: {tag_names}"
            return text

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return flags for drag-and-drop support."""
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled
        return default_flags | Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self) -> Qt.DropAction:
        """Support internal move only."""
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        """Return supported MIME types."""
        return [MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> Optional[QMimeData]:
        """Create MIME data for drag operation."""
        if not indexes:
            return None

        mime_data = QMimeData()
        # 存储源行号
        rows = [index.row() for index in indexes]
        mime_data.setData(MIME_TYPE, str(rows[0]).encode())
        return mime_data

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction,
                     row: int, column: int, parent: QModelIndex) -> bool:
        """Handle drop operation for reordering."""
        if action != Qt.DropAction.MoveAction:
            return False

        if not data.hasFormat(MIME_TYPE):
            return False

        # 获取源行号
        source_row = int(data.data(MIME_TYPE).data().decode())

        # 计算目标位置
        if row == -1:
            if parent.isValid():
                dest_row = parent.row()
            else:
                return False
        else:
            dest_row = row

        # 执行移动
        if source_row == dest_row:
            return True

        # 更新模型
        self.beginResetModel()
        item = self._items.pop(source_row)
        self._items.insert(dest_row, item)
        self.endResetModel()

        return True

    def set_items(self, items: list[ClipboardItem]) -> None:
        """Replace all items."""
        self.beginResetModel()
        self._items = items
        self._has_more = len(items) >= self._page_size
        self.endResetModel()

    def append_items(self, items: list[ClipboardItem]) -> None:
        """Append items for lazy loading."""
        if not items:
            return

        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(items) - 1)
        self._items.extend(items)
        self._has_more = len(items) >= self._page_size
        self.endInsertRows()

    def get_item(self, index: QModelIndex) -> Optional[ClipboardItem]:
        """Get the item at the given index."""
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()]
        return None

    def get_items(self) -> list[ClipboardItem]:
        """Get all items."""
        return self._items.copy()

    def has_more(self) -> bool:
        """Check if there are more items to load."""
        return self._has_more

    def clear(self) -> None:
        """Clear all items."""
        self.beginResetModel()
        self._items.clear()
        self._has_more = True
        self.endResetModel()
