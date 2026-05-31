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
    stagingChanged = pyqtSignal()
    toastRequested = pyqtSignal(str, str, bool)  # message, type, showUndo

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
    _stagingCountChanged = pyqtSignal()
    _clipboardEnabledChanged = pyqtSignal()

    def __init__(self, api_client: ApiClient, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._api = api_client
        self._model = None  # set later via set_model()
        self._staging_model = None  # set later via set_staging_model()
        self._root = None   # QML root object, set later via set_root()

        # Filter state
        self._current_category: Optional[str] = None
        self._current_project: Optional[str] = "all"
        self._active_tag_ids: list[int] = []
        self._search_query: str = ""
        self._current_sort: str = "newest"

        # Multi-select state
        self._multi_select_mode = False
        self._selected_item_ids: set[int] = set()

        # Undo delete buffer
        self._last_deleted_id: int | None = None

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

    def set_staging_model(self, model) -> None:
        """Set the QStagingListModel instance."""
        self._staging_model = model

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

    @pyqtProperty(int, notify=_stagingCountChanged)
    def stagingCount(self) -> int:
        if self._staging_model:
            return self._staging_model.count_property()
        return 0

    @pyqtProperty(bool, notify=_clipboardEnabledChanged)
    def clipboardEnabled(self) -> bool:
        try:
            data = self._api._get("/api/config")
            return data.get("clipboard_enabled", True)
        except Exception:
            return True

    @pyqtProperty(str, notify=_currentCategoryChanged)
    def currentCategory(self) -> str:
        return self._current_category or "ALL"

    @pyqtProperty(str, notify=_currentProjectChanged)
    def currentProject(self) -> str:
        return self._current_project or "all"

    @pyqtProperty(str)
    def currentSort(self) -> str:
        return self._current_sort or "newest"

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
                sort=self._current_sort,
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
            self.toastRequested.emit("已复制到剪贴板", "success", False)
        except Exception as e:
            logger.error(f"copyItem({item_id}) failed: {e}")

    @pyqtSlot(int)
    def deleteItem(self, item_id: int) -> None:
        try:
            self._api.delete_item(item_id)
            self._last_deleted_id = item_id
            self.toastRequested.emit("已移到回收站", "info", True)
        except Exception as e:
            logger.error(f"deleteItem({item_id}) failed: {e}")

    @pyqtSlot(int)
    def copyAsPlainText(self, item_id: int) -> None:
        """Copy item content as plain text (strip HTML)."""
        try:
            if self._model:
                item = self._model.get_item_by_id(item_id)
                if item:
                    import re
                    text = item.content_text or ""
                    if item.content_html and not text:
                        text = re.sub(r"<[^>]+>", " ", item.content_html)
                        text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        from src.core.clipboard_listener import set_clipboard_text
                        set_clipboard_text(text)
        except Exception as e:
            logger.error(f"copyAsPlainText({item_id}) failed: {e}")

    @pyqtSlot(int)
    def editItem(self, item_id: int) -> None:
        """Open item for editing (emit signal for UI to handle)."""
        # For now, just copy to clipboard for editing in external editor
        self.copyItem(item_id)

    @pyqtSlot(int)
    def showTagDialog(self, item_id: int) -> None:
        """Show tag assignment dialog for an item."""
        # Emit signal that the QML tag dialog can listen to
        self.errorOccurred.emit(f"tag-dialog:{item_id}")

    @pyqtSlot(int)
    def exportSingleItem(self, item_id: int) -> None:
        """Export a single item."""
        try:
            if self._model:
                item = self._model.get_item_by_id(item_id)
                if item:
                    from src.utils.import_export import export_items_json
                    import tempfile, os
                    path = os.path.join(tempfile.gettempdir(), f"item_{item_id}.json")
                    export_items_json([item], path)
                    os.startfile(path)
        except Exception as e:
            logger.error(f"exportSingleItem({item_id}) failed: {e}")

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

    @pyqtSlot(str)
    def setSort(self, sort: str) -> None:
        """Set sort order and refresh list."""
        self._current_sort = sort
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
            self.toastRequested.emit(f"已删除 {len(item_ids)} 条记录", "info", False)
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

    # ── Staging Shelf (暂存架) ──

    @pyqtSlot()
    def refreshStaging(self) -> None:
        """Fetch staging items and update the staging model."""
        try:
            items = self._api.get_staging_items()
            if self._staging_model:
                self._staging_model.setItems(items)
            self._stagingCountChanged.emit()
            self.stagingChanged.emit()
        except Exception as e:
            logger.error(f"refreshStaging failed: {e}")

    @pyqtSlot(int)
    def addToStaging(self, item_id: int) -> None:
        """Add a clipboard history item to the staging shelf."""
        try:
            self._api.add_to_staging(item_id)
            self.refreshStaging()
            self.toastRequested.emit("已发送到暂存架", "success", False)
        except Exception as e:
            logger.error(f"addToStaging({item_id}) failed: {e}")
            self.errorOccurred.emit(str(e))

    @pyqtSlot(int)
    def removeFromStaging(self, staging_id: int) -> None:
        """Remove an item from the staging shelf."""
        try:
            self._api.remove_from_staging(staging_id)
            self.refreshStaging()
        except Exception as e:
            logger.error(f"removeFromStaging({staging_id}) failed: {e}")

    @pyqtSlot()
    def clearStaging(self) -> None:
        """Clear all items from the staging shelf."""
        try:
            self._api.clear_staging()
            self.refreshStaging()
        except Exception as e:
            logger.error(f"clearStaging failed: {e}")

    @pyqtSlot(int)
    def stagingToHistory(self, staging_id: int) -> None:
        """Move a staging item back to clipboard history."""
        try:
            self._api.staging_to_history(staging_id)
            self.refreshStaging()
            self.refreshList()
        except Exception as e:
            logger.error(f"stagingToHistory({staging_id}) failed: {e}")

    @pyqtSlot(int)
    def copyStagingItem(self, staging_id: int) -> None:
        """Copy a staging item to clipboard."""
        try:
            # Get staging item, then set clipboard directly
            items = self._api.get_staging_items()
            target = None
            for item in items:
                if item.get("id") == staging_id:
                    target = item
                    break
            if target:
                from src.core.clipboard_listener import set_clipboard_text, set_clipboard_files
                ct = target.get("content_type", "TEXT")
                if ct == "TEXT" and target.get("content_text"):
                    set_clipboard_text(target["content_text"])
                elif ct == "FILES" and target.get("content_text"):
                    set_clipboard_files(target["content_text"].split("\n"))
                elif ct == "HTML" and target.get("content_text"):
                    set_clipboard_text(target["content_text"])
        except Exception as e:
            logger.error(f"copyStagingItem({staging_id}) failed: {e}")

    # ── Monitoring toggle ──

    @pyqtSlot()
    def toggleMonitoring(self) -> None:
        """Toggle clipboard monitoring on/off."""
        try:
            current = self.clipboardEnabled
            self._api._post("/api/config", {"clipboard_enabled": not current})
            self._clipboardEnabledChanged.emit()
        except Exception as e:
            logger.error(f"toggleMonitoring failed: {e}")

    @pyqtSlot()
    def togglePhrasesPanel(self) -> None:
        """Toggle the quick phrases panel visibility."""
        if self._root:
            current = self._root.property("showPhrases")
            self._root.setProperty("showPhrases", not current)

    # ── Undo delete ──

    @pyqtSlot()
    def undoDelete(self) -> None:
        """Restore the last soft-deleted item."""
        if self._last_deleted_id:
            try:
                self._api.restore_from_trash(self._last_deleted_id)
                self.toastRequested.emit("已恢复", "success", False)
                self._last_deleted_id = None
                self.refreshList()
            except Exception as e:
                logger.error(f"undoDelete failed: {e}")

    # ── Trash (回收站) ──

    @pyqtSlot()
    def showTrash(self) -> None:
        """Load trash items into the main list model."""
        try:
            items = self._api.get_trash()
            if self._model:
                self._model.setItems(items)
            self._count = len(items)
            self._countChanged.emit()
        except Exception as e:
            logger.error(f"showTrash failed: {e}")

    @pyqtSlot(int)
    def restoreFromTrash(self, item_id: int) -> None:
        try:
            self._api.restore_from_trash(item_id)
            self.refreshList()
        except Exception as e:
            logger.error(f"restoreFromTrash({item_id}) failed: {e}")

    @pyqtSlot(int)
    def permanentDelete(self, item_id: int) -> None:
        try:
            self._api.permanent_delete(item_id)
            self.showTrash()  # refresh trash view
        except Exception as e:
            logger.error(f"permanentDelete({item_id}) failed: {e}")

    @pyqtSlot()
    def emptyTrash(self) -> None:
        try:
            self._api.empty_trash()
            self.showTrash()
        except Exception as e:
            logger.error(f"emptyTrash failed: {e}")

    # ── Quick Phrases (常用短语) ──

    @pyqtSlot(result=list)
    def getPhrases(self) -> list:
        try:
            phrases = self._api.get_phrases()
            return phrases
        except Exception:
            return []

    @pyqtSlot(str, str, str, result=int)
    def createPhrase(self, name: str, content: str, color: str) -> int:
        try:
            return self._api.create_phrase(name, content, color)
        except Exception as e:
            logger.error(f"createPhrase failed: {e}")
            return 0

    @pyqtSlot(int, str, str, str, result=bool)
    def updatePhrase(self, phrase_id: int, name: str, content: str, color: str) -> bool:
        try:
            return self._api.update_phrase(phrase_id, name, content, color)
        except Exception as e:
            logger.error(f"updatePhrase failed: {e}")
            return False

    @pyqtSlot(int)
    def deletePhrase(self, phrase_id: int) -> None:
        try:
            self._api.delete_phrase(phrase_id)
        except Exception as e:
            logger.error(f"deletePhrase failed: {e}")

    @pyqtSlot(int)
    def usePhrase(self, phrase_id: int) -> None:
        """Copy phrase content to clipboard and record usage."""
        try:
            content = self._api.use_phrase(phrase_id)
            if content:
                from src.core.clipboard_listener import set_clipboard_text
                set_clipboard_text(content)
        except Exception as e:
            logger.error(f"usePhrase({phrase_id}) failed: {e}")

    # ── Internal signal handlers ──

    def _on_items_changed(self) -> None:
        self.refreshList()
        self.refreshStaging()

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
