"""QAbstractListModel for the staging shelf, optimized for QML GridView binding."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, pyqtSlot

from src.models.clipboard_item import ContentType


class QStagingListModel(QAbstractListModel):
    """List model exposing staging shelf items for QML."""

    IdRole = Qt.ItemDataRole.UserRole + 1
    ContentTypeRole = Qt.ItemDataRole.UserRole + 2
    ContentTextRole = Qt.ItemDataRole.UserRole + 3
    FilePathRole = Qt.ItemDataRole.UserRole + 4
    ThumbnailPathRole = Qt.ItemDataRole.UserRole + 5
    DisplayTypeRole = Qt.ItemDataRole.UserRole + 6
    PreviewTextRole = Qt.ItemDataRole.UserRole + 7
    CardTitleRole = Qt.ItemDataRole.UserRole + 8
    SourceItemIdRole = Qt.ItemDataRole.UserRole + 9

    _ROLE_NAMES: dict[int, bytes] = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []

    def roleNames(self) -> dict[int, QByteArray]:
        if not self._ROLE_NAMES:
            names = {
                self.IdRole: b"id",
                self.ContentTypeRole: b"contentType",
                self.ContentTextRole: b"contentText",
                self.FilePathRole: b"filePath",
                self.ThumbnailPathRole: b"thumbnailPath",
                self.DisplayTypeRole: b"displayType",
                self.PreviewTextRole: b"previewText",
                self.CardTitleRole: b"cardTitle",
                self.SourceItemIdRole: b"sourceItemId",
            }
            QStagingListModel._ROLE_NAMES = {
                k: QByteArray(v) for k, v in names.items()
            }
        return self._ROLE_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        match role:
            case self.IdRole:
                return item.get("id")
            case self.ContentTypeRole:
                return item.get("content_type", "TEXT")
            case self.ContentTextRole:
                return item.get("content_text", "")
            case self.FilePathRole:
                return item.get("file_path", "")
            case self.ThumbnailPathRole:
                return item.get("thumbnail_path", "")
            case self.DisplayTypeRole:
                return self._display_type(item)
            case self.PreviewTextRole:
                return self._preview_text(item)
            case self.CardTitleRole:
                return self._card_title(item)
            case self.SourceItemIdRole:
                return item.get("source_item_id")
        return None

    @pyqtSlot(list)
    def setItems(self, items: list) -> None:
        """Replace all staging items."""
        self.beginResetModel()
        self._items = items if isinstance(items, list) else list(items)
        self.endResetModel()

    def get_item(self, row: int) -> Optional[dict]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def count_property(self) -> int:
        return len(self._items)

    # ── Helper methods ──

    @staticmethod
    def _display_type(item: dict) -> str:
        ct = item.get("content_type", "TEXT")
        if ct == "IMAGE":
            return "image"
        if ct == "HTML":
            return "html"
        if ct == "FILES":
            fp = (item.get("content_text") or "").split("\n")[0].strip()
            ext = Path(fp).suffix.lower() if fp else ""
            ext_map = {
                ".pdf": "pdf", ".doc": "word", ".docx": "word",
                ".xls": "excel", ".xlsx": "excel",
                ".ppt": "ppt", ".pptx": "ppt",
            }
            return ext_map.get(ext, "files")
        return "text"

    @staticmethod
    def _preview_text(item: dict) -> str:
        ct = item.get("content_type", "TEXT")
        if ct == "TEXT":
            return (item.get("content_text") or "")[:40].replace("\n", " ")
        if ct == "IMAGE":
            return "图片"
        if ct == "FILES":
            paths = (item.get("content_text") or "").split("\n")
            names = [Path(p).name for p in paths if p.strip()]
            return names[0] if names else "文件"
        if ct == "HTML":
            text = re.sub(r"<[^>]+>", "", item.get("content_html") or "")
            return text[:40].replace("\n", " ")
        return ""

    @staticmethod
    def _card_title(item: dict) -> str:
        ct = item.get("content_type", "TEXT")
        if ct == "TEXT":
            text = (item.get("content_text") or "")[:30].replace("\n", " ")
            return text or "文本"
        if ct == "IMAGE":
            return "图片"
        if ct == "FILES":
            fp = (item.get("content_text") or "").split("\n")[0].strip()
            return Path(fp).name if fp else "文件"
        if ct == "HTML":
            text = re.sub(r"<[^>]+>", "", item.get("content_html") or "")
            return text[:30].replace("\n", " ") or "HTML"
        return "内容"
