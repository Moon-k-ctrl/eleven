"""Central bridge layer: wraps ApiClient for QML consumption."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import (
    QObject, QTimer, pyqtSignal, pyqtSlot, pyqtProperty,
)

from src.api_client import ApiClient
from src.models.clipboard_item import ClipboardItem

logger = logging.getLogger("eleven.qml_bridge")


class QmlBridge(QObject):
    """Exposes ApiClient methods and state to QML via slots/properties."""

    # ── Signals forwarded to QML ──
    itemsChanged = pyqtSignal()
    statusChanged = pyqtSignal(str)
    previewRequested = pyqtSignal(object)  # ClipboardItem dict
    previewBarToggle = pyqtSignal()
    previewBarSendRequested = pyqtSignal(object)  # ClipboardItem for preview bar
    exportRequested = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    # ── Property change signals (required by pyqtProperty) ──
    _statusChanged = pyqtSignal()
    _countChanged = pyqtSignal()
    _maxItemsChanged = pyqtSignal()
    _currentCategoryChanged = pyqtSignal()
    _currentProjectChanged = pyqtSignal()
    _multiSelectModeChanged = pyqtSignal()
    _selectedCountChanged = pyqtSignal()
    _searchQueryChanged = pyqtSignal()
    _selectedItemIdsChanged = pyqtSignal()

    def __init__(self, api_client: ApiClient, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._api = api_client
        self._model = None  # set later via set_model()
        self._root = None   # QML root object, set later via set_root()

        # Filter state
        self._current_category: Optional[str] = None
        self._current_project: Optional[str] = "all"
        self._active_tag_ids: list[int] = []
        self._search_query: str = ""

        # Multi-select state
        self._multi_select_mode = False
        self._selected_item_ids: set[int] = set()

        # Cached counts
        self._count = 0
        self._max_items = 200

        # Search debounce
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        # Forward ApiClient signals
        self._api.items_changed.connect(self._on_items_changed)
        self._api.status_changed.connect(self._on_status_changed)

    # ── Initialization ──

    def set_model(self, model) -> None:
        """Set the QClipboardListModel instance."""
        self._model = model

    def set_root(self, root) -> None:
        """Set the QML root object for window manipulation."""
        self._root = root

    # ── Properties ──

    @pyqtProperty(str, notify=_statusChanged)
    def status(self) -> str:
        return self._api.status

    @pyqtProperty(int, notify=_countChanged)
    def count(self) -> int:
        return self._count

    @pyqtProperty(int, notify=_maxItemsChanged)
    def maxItems(self) -> int:
        return self._max_items

    @pyqtProperty(str, notify=_currentCategoryChanged)
    def currentCategory(self) -> str:
        return self._current_category or "ALL"

    @pyqtProperty(str, notify=_currentProjectChanged)
    def currentProject(self) -> str:
        return self._current_project or "all"

    @pyqtProperty(bool, notify=_multiSelectModeChanged)
    def multiSelectMode(self) -> bool:
        return self._multi_select_mode

    @pyqtProperty(int, notify=_selectedCountChanged)
    def selectedCount(self) -> int:
        return len(self._selected_item_ids)

    @pyqtProperty(str, notify=_searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @pyqtProperty(list, notify=_selectedItemIdsChanged)
    def selectedItemIds(self) -> list:
        return list(self._selected_item_ids)

    # ── Window management (called by TrayIcon / PreviewBar) ──

    def toggle(self) -> None:
        if self._root:
            if self._root.property("visible"):
                self._root.setProperty("visible", False)
            else:
                self._root.setProperty("visible", True)
                if hasattr(self._root, "requestActivate"):
                    self._root.requestActivate()
                self._center_on_screen()
                self.refreshList()

    def show(self) -> None:
        if self._root:
            self._root.setProperty("visible", True)
            if hasattr(self._root, "requestActivate"):
                self._root.requestActivate()

    def hide(self) -> None:
        if self._root:
            self._root.setProperty("visible", False)

    def raisePanel(self) -> None:
        if self._root:
            self._root.setProperty("visible", True)
            if hasattr(self._root, "raise_"):
                self._root.raise_()
            if hasattr(self._root, "requestActivate"):
                self._root.requestActivate()

    def isVisible(self) -> bool:
        if self._root:
            return self._root.property("visible")
        return False

    def focusSearch(self) -> None:
        if self._root:
            # Invoke QML method to focus search field
            from PyQt6.QtQml import QQmlExpression
            engine = self._root.engine() if hasattr(self._root, "engine") else None
            if engine:
                ctx = engine.rootContext()
                expr = QQmlExpression(ctx, self._root, "searchBar.forceActiveFocus()")
                expr.evaluate()

    def _center_on_screen(self) -> None:
        if not self._root:
            return
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = self._root.property("width") or 380
            h = self._root.property("height") or 520
            x = geo.right() - int(w) - 20
            y = geo.top() + (geo.height() - int(h)) // 2
            self._root.setPosition(x, y)

    # ── Data operations (slots callable from QML) ──

    @pyqtSlot()
    def refreshList(self) -> None:
        """Fetch items from server with current filters and update model."""
        try:
            items = self._api.search_with_filters(
                query=self._search_query or None,
                tag_ids=self._active_tag_ids or None,
                category=self._current_category,
                project=self._current_project,
                limit=200,
            )
            if self._model:
                self._model.setItems(items)
            self._count = len(items)
            self._countChanged.emit()
            self.itemsChanged.emit()
        except Exception as e:
            logger.error(f"refreshList failed: {e}")
            self.errorOccurred.emit(str(e))

    @pyqtSlot(int)
    def copyItem(self, item_id: int) -> None:
        try:
            self._api.copy_item(item_id)
        except Exception as e:
            logger.error(f"copyItem({item_id}) failed: {e}")

    @pyqtSlot(int)
    def deleteItem(self, item_id: int) -> None:
        try:
            self._api.delete_item(item_id)
        except Exception as e:
            logger.error(f"deleteItem({item_id}) failed: {e}")

    @pyqtSlot(int)
    def togglePin(self, item_id: int) -> None:
        try:
            self._api.toggle_pin(item_id)
        except Exception as e:
            logger.error(f"togglePin({item_id}) failed: {e}")

    @pyqtSlot(int)
    def toggleFavorite(self, item_id: int) -> None:
        try:
            self._api.toggle_favorite(item_id)
        except Exception as e:
            logger.error(f"toggleFavorite({item_id}) failed: {e}")

    @pyqtSlot(int)
    def toggleStar(self, item_id: int) -> None:
        try:
            self._api.toggle_star(item_id)
        except Exception as e:
            logger.error(f"toggleStar({item_id}) failed: {e}")

    @pyqtSlot(str)
    def setCategory(self, category: str) -> None:
        if self._current_category != category:
            self._current_category = category
            self._currentCategoryChanged.emit()
            self.refreshList()

    @pyqtSlot(str)
    def setProject(self, project: str) -> None:
        if self._current_project != project:
            self._current_project = project
            self._currentProjectChanged.emit()
            self.refreshList()

    @pyqtSlot(int)
    def toggleTag(self, tag_id: int) -> None:
        if tag_id in self._active_tag_ids:
            self._active_tag_ids.remove(tag_id)
        else:
            self._active_tag_ids.append(tag_id)
        self.refreshList()

    @pyqtSlot(str)
    def searchTextChanged(self, text: str) -> None:
        self._search_query = text
        self._searchQueryChanged.emit()
        self._search_timer.start()

    @pyqtSlot()
    def doSearch(self) -> None:
        self._search_timer.stop()
        self.refreshList()

    @pyqtSlot()
    def clearSearch(self) -> None:
        self._search_query = ""
        self._searchQueryChanged.emit()
        self._search_timer.stop()
        self.refreshList()

    @pyqtSlot()
    def clearAll(self) -> None:
        try:
            self._api.clear_all()
        except Exception as e:
            logger.error(f"clearAll failed: {e}")

    @pyqtSlot(list)
    def batchDelete(self, item_ids: list) -> None:
        try:
            self._api.batch_delete([int(i) for i in item_ids])
        except Exception as e:
            logger.error(f"batchDelete failed: {e}")

    @pyqtSlot(list)
    def mergeItems(self, item_ids: list) -> None:
        try:
            self._api.merge_items([int(i) for i in item_ids])
        except Exception as e:
            logger.error(f"mergeItems failed: {e}")

    @pyqtSlot(list)
    def importFiles(self, paths: list) -> None:
        try:
            self._api.import_files([str(p) for p in paths])
        except Exception as e:
            logger.error(f"importFiles failed: {e}")

    @pyqtSlot(int, int)
    def addTagToItem(self, item_id: int, tag_id: int) -> None:
        try:
            self._api.add_tag_to_item(item_id, tag_id)
        except Exception as e:
            logger.error(f"addTagToItem failed: {e}")

    @pyqtSlot(int, int)
    def removeTagFromItem(self, item_id: int, tag_id: int) -> None:
        try:
            self._api.remove_tag_from_item(item_id, tag_id)
        except Exception as e:
            logger.error(f"removeTagFromItem failed: {e}")

    # ── Data queries (callable from QML) ──

    @pyqtSlot(result=list)
    def getAllTags(self) -> list:
        try:
            tags = self._api.get_all_tags()
            return [{"id": t.id, "name": t.name, "color": t.color} for t in tags]
        except Exception:
            return []

    @pyqtSlot(result=list)
    def getProjects(self) -> list:
        try:
            return self._api.get_projects()
        except Exception:
            return []

    @pyqtSlot(str, result=int)
    def createProject(self, name: str) -> int:
        try:
            return self._api.create_project(name)
        except Exception:
            return 0

    @pyqtSlot(str, str, result=int)
    def createTag(self, name: str, color: str) -> int:
        try:
            return self._api.create_tag(name, color)
        except Exception:
            return 0

    # ── Multi-select ──

    @pyqtSlot()
    def toggleMultiSelect(self) -> None:
        self._multi_select_mode = not self._multi_select_mode
        if not self._multi_select_mode:
            self._selected_item_ids.clear()
        self._multiSelectModeChanged.emit()
        self._selectedCountChanged.emit()
        self._selectedItemIdsChanged.emit()

    @pyqtSlot(int)
    def toggleItemSelection(self, item_id: int) -> None:
        if item_id in self._selected_item_ids:
            self._selected_item_ids.discard(item_id)
        else:
            self._selected_item_ids.add(item_id)
        self._selectedCountChanged.emit()
        self._selectedItemIdsChanged.emit()

    @pyqtSlot()
    def selectAll(self) -> None:
        if self._model:
            for item in self._model.get_items():
                if item.id is not None:
                    self._selected_item_ids.add(item.id)
            self._selectedCountChanged.emit()
            self._selectedItemIdsChanged.emit()

    @pyqtSlot()
    def deselectAll(self) -> None:
        self._selected_item_ids.clear()
        self._selectedCountChanged.emit()
        self._selectedItemIdsChanged.emit()

    @pyqtSlot()
    def cancelMultiSelect(self) -> None:
        self._multi_select_mode = False
        self._selected_item_ids.clear()
        self._multiSelectModeChanged.emit()
        self._selectedCountChanged.emit()
        self._selectedItemIdsChanged.emit()

    @pyqtSlot(result=list)
    def getSelectedItemIds(self) -> list:
        return list(self._selected_item_ids)

    # ── Preview ──

    @pyqtSlot(int)
    def requestPreview(self, item_id: int) -> None:
        if self._model:
            item = self._model.get_item_by_id(item_id)
            if item:
                self.previewRequested.emit(item)

    @pyqtSlot(int)
    def sendToPreviewBar(self, item_id: int) -> None:
        if self._model:
            item = self._model.get_item_by_id(item_id)
            if item:
                self.previewBarSendRequested.emit(item)

    # ── Paste ──

    @pyqtSlot()
    def pasteFromClipboard(self) -> None:
        try:
            self._api.paste_from_clipboard()
        except Exception as e:
            logger.error(f"pasteFromClipboard failed: {e}")

    # ── Internal signal handlers ──

    def _on_items_changed(self) -> None:
        self.refreshList()

    def _on_status_changed(self, status: str) -> None:
        self._statusChanged.emit()
        self.statusChanged.emit(status)

    def _do_search(self) -> None:
        self.refreshList()

    def updateStatus(self, status: str) -> None:
        """Called externally to update status display."""
        self._statusChanged.emit()
        self.statusChanged.emit(status)

    def onPreviewRequested(self, item: ClipboardItem) -> None:
        """Called externally (e.g. PreviewBar) to open preview."""
        self.previewRequested.emit(item)
