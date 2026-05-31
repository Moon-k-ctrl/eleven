"""HTTP/WebSocket client bridging PyQt6 UI to FastAPI server."""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from src.models.clipboard_item import ClipboardItem, ContentType, Tag

logger = logging.getLogger("eleven.client")


def _parse_item(data: dict) -> ClipboardItem:
    """Convert JSON dict from API to ClipboardItem."""
    tags = [
        Tag(id=t["id"], name=t["name"], color=t.get("color", "#4A90D9"))
        for t in data.get("tags", [])
    ]
    content_type_str = data.get("content_type", "TEXT")
    try:
        content_type = ContentType(content_type_str)
    except ValueError:
        content_type = ContentType.TEXT

    created_at = data.get("created_at")
    updated_at = data.get("updated_at")

    return ClipboardItem(
        id=data.get("id"),
        content_type=content_type,
        content_text=data.get("content_text"),
        content_html=data.get("content_html"),
        file_path=data.get("file_path"),
        source_app=data.get("source_app"),
        is_pinned=data.get("is_pinned", False),
        is_favorite=data.get("is_favorite", False),
        group_id=data.get("group_id"),
        thumbnail_path=data.get("thumbnail_path"),
        category=data.get("category"),
        source=data.get("source", "clipboard"),
        project=data.get("project", "default"),
        is_starred=data.get("is_starred", False),
        metadata=data.get("metadata"),
        tags=tags,
        created_at=created_at,
        updated_at=updated_at,
    )


def _parse_tag(data: dict) -> Tag:
    """Convert JSON dict from API to Tag."""
    return Tag(
        id=data.get("id"),
        name=data.get("name", ""),
        color=data.get("color", "#4A90D9"),
        created_at=data.get("created_at"),
    )


class _WebSocketThread(QThread):
    """Background thread that listens for WebSocket events."""

    items_changed = pyqtSignal(int)
    disconnected = pyqtSignal()

    def __init__(self, url: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._url = url
        self._running = True

    def run(self) -> None:
        import websocket  # websocket-client

        while self._running:
            try:
                ws = websocket.create_connection(
                    self._url, timeout=30, ping_interval=20
                )
                logger.info("WebSocket connected")
                while self._running:
                    try:
                        raw = ws.recv()
                        if not raw:
                            break
                        msg = json.loads(raw)
                        event = msg.get("event")
                        data = msg.get("data", {})
                        if event == "items-changed":
                            count = data.get("count", 0)
                            self.items_changed.emit(count)
                        elif event == "pong":
                            pass
                    except websocket.WebSocketTimeoutException:
                        continue
                    except websocket.WebSocketConnectionClosedException:
                        break
                    except Exception as e:
                        logger.warning(f"WebSocket recv error: {e}")
                        break
            except Exception as e:
                logger.warning(f"WebSocket connection failed: {e}")
            finally:
                try:
                    ws.close()
                except Exception:
                    pass

            if self._running:
                self.disconnected.emit()
                self.msleep(3000)

    def stop(self) -> None:
        self._running = False
        self.wait(5000)


class ApiClient(QObject):
    """Client that talks to the eleven FastAPI server via HTTP/WebSocket."""

    items_changed = pyqtSignal()
    status_changed = pyqtSignal(str)  # "online" | "warning" | "error" | "offline"

    def __init__(self, base_url: str = "http://127.0.0.1:8199",
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._base = base_url.rstrip("/")
        self._ws_thread: Optional[_WebSocketThread] = None
        self._timeout = 10
        self._status = "offline"

    def start(self) -> None:
        """Connect WebSocket for real-time updates + HTTP polling fallback."""
        ws_url = self._base.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"
        self._ws_thread = _WebSocketThread(ws_url, self)
        self._ws_thread.items_changed.connect(self._on_items_changed)
        self._ws_thread.disconnected.connect(self._on_disconnected)
        self._ws_thread.start()

        # HTTP polling fallback (every 10s) for offline detection
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(10000)

        logger.info(f"ApiClient started, base={self._base}")

    def stop(self) -> None:
        """Disconnect WebSocket and stop polling."""
        if hasattr(self, '_poll_timer'):
            self._poll_timer.stop()
        if self._ws_thread:
            self._ws_thread.stop()
            self._ws_thread = None

    def _poll_status(self) -> None:
        """Periodic HTTP poll to detect server status changes."""
        try:
            data = self._get("/api/status")
            count = data.get("count", 0)
            prev = self._status
            self._set_status("online")
            # If we just reconnected, emit items_changed to refresh UI
            if prev != "online":
                self.items_changed.emit()
        except Exception:
            if self._status == "online":
                self._set_status("warning")
            elif self._status == "warning":
                self._set_status("offline")

    @pyqtSlot(int)
    def _on_items_changed(self, count: int = 0) -> None:
        self._set_status("online")
        self.items_changed.emit()

    @pyqtSlot()
    def _on_disconnected(self) -> None:
        logger.warning("WebSocket disconnected, will retry...")
        self._set_status("offline")

    def _set_status(self, status: str) -> None:
        if self._status != status:
            self._status = status
            self.status_changed.emit(status)

    @property
    def status(self) -> str:
        return self._status

    # ── HTTP helpers ──

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self._base}{path}"
        if params:
            query = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url = f"{url}?{query}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, body: Optional[dict] = None) -> dict:
        url = f"{self._base}{path}"
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _put(self, path: str, body: Optional[dict] = None) -> dict:
        url = f"{self._base}{path}"
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _delete(self, path: str) -> dict:
        url = f"{self._base}{path}"
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ── Items ──

    def get_items(self, limit: int = 50, offset: int = 0) -> list[ClipboardItem]:
        cursor = offset if offset > 0 else None
        data = self._get("/api/items", {"limit": limit, "cursor": cursor})
        return [_parse_item(d) for d in data.get("items", [])]

    def search(self, query: str, limit: int = 50) -> list[ClipboardItem]:
        data = self._get("/api/items/search", {"q": query, "limit": limit})
        return [_parse_item(d) for d in data.get("items", [])]

    def search_with_filters(self, query: Optional[str] = None,
                            tag_ids: Optional[list[int]] = None,
                            group_id: Optional[int] = None,
                            category: Optional[str] = None,
                            project: Optional[str] = None,
                            sort: str = "newest",
                            limit: int = 50) -> list[ClipboardItem]:
        params: dict = {"limit": limit, "sort": sort}
        if query:
            params["q"] = query
        if tag_ids and len(tag_ids) == 1:
            params["tag_id"] = tag_ids[0]
        if group_id is not None:
            params["group_id"] = group_id
        if category is not None and category != "ALL":
            params["category"] = category
        if project is not None and project != "all":
            params["project"] = project
        data = self._get("/api/items", params)
        items = [_parse_item(d) for d in data.get("items", [])]
        # Client-side filter for multiple tags (server only supports single tag_id)
        if tag_ids and len(tag_ids) > 1:
            tag_id_set = set(tag_ids)
            items = [
                i for i in items
                if tag_id_set.issubset({t.id for t in i.tags if t.id is not None})
            ]
        return items

    def copy_item(self, item_id: int) -> None:
        self._post(f"/api/items/{item_id}/copy")

    def delete_item(self, item_id: int) -> None:
        self._delete(f"/api/items/{item_id}")

    def toggle_pin(self, item_id: int) -> None:
        self._post(f"/api/items/{item_id}/pin")

    def toggle_favorite(self, item_id: int) -> None:
        self._post(f"/api/items/{item_id}/favorite")

    def toggle_star(self, item_id: int) -> None:
        self._post(f"/api/items/{item_id}/star")

    def get_most_used(self, limit: int = 20) -> list[ClipboardItem]:
        """Get most frequently used items."""
        data = self._get("/api/items/most-used", {"limit": limit})
        return [_parse_item(d) for d in data.get("items", [])]

    def import_files(self, file_paths: list[str], source: str = "context-menu",
                     project: str = "default") -> dict:
        return self._post("/api/items/import", {
            "files": file_paths, "source": source, "project": project,
        })

    def import_text(self, content_text: str, content_html: str = "",
                    source: str = "hotkey", project: str = "default") -> dict:
        body: dict = {"content_text": content_text, "source": source, "project": project}
        if content_html:
            body["content_html"] = content_html
        return self._post("/api/items/import-text", body)

    def batch_delete(self, item_ids: list[int]) -> int:
        result = self._post("/api/items/batch-delete", {"item_ids": item_ids})
        return result.get("deleted", 0)

    def get_item_by_id(self, item_id: int) -> Optional[ClipboardItem]:
        """Get a single item by ID."""
        try:
            data = self._get(f"/api/items/{item_id}")
            return _parse_item(data)
        except Exception:
            return None

    def paste_from_clipboard(self) -> bool:
        """Read system clipboard and add as new item via API."""
        result = self._post("/api/items/paste")
        return result.get("ok", False)

    def clear_all(self) -> None:
        self._post("/api/items/clear")

    def merge_items(self, item_ids: list[int]) -> bool:
        result = self._post("/api/items/merge", {"item_ids": item_ids})
        return result.get("ok", False)

    # ── Status ──

    def get_count(self) -> int:
        try:
            data = self._get("/api/status")
            self._set_status("online")
            return data.get("count", 0)
        except Exception:
            self._set_status("error")
            return 0

    def get_max_items(self) -> int:
        try:
            data = self._get("/api/status")
            return data.get("max_items", 200)
        except Exception:
            return 200

    def get_status(self) -> str:
        try:
            data = self._get("/api/status")
            self._set_status("online")
            return data.get("status", "online")
        except Exception:
            self._set_status("error")
            return "error"

    # ── Tags ──

    def get_all_tags(self) -> list[Tag]:
        data = self._get("/api/tags")
        return [_parse_tag(d) for d in data.get("tags", [])]

    def create_tag(self, name: str, color: str = "#4A90D9") -> int:
        result = self._post("/api/tags", {"name": name, "color": color})
        return result.get("id", 0)

    def delete_tag(self, tag_id: int) -> None:
        self._delete(f"/api/tags/{tag_id}")

    def update_tag(self, tag_id: int, name: str, color: str) -> None:
        self._put(f"/api/tags/{tag_id}", {"name": name, "color": color})

    def add_tag_to_item(self, item_id: int, tag_id: int) -> None:
        self._post(f"/api/items/{item_id}/tags", {"tag_id": tag_id})

    def remove_tag_from_item(self, item_id: int, tag_id: int) -> None:
        self._delete(f"/api/items/{item_id}/tags/{tag_id}")

    def get_item_tags(self, item_id: int) -> list[Tag]:
        data = self._get(f"/api/items/{item_id}/tags")
        return [_parse_tag(d) for d in data.get("tags", [])]

    # ── Groups ──

    def get_groups(self) -> list[dict]:
        data = self._get("/api/groups")
        return data.get("groups", [])

    # ── Projects (v3.0) ──

    def get_projects(self) -> list[dict]:
        data = self._get("/api/projects")
        return data.get("projects", [])

    def create_project(self, name: str, icon: str = "📁", color: str = "#4A90D9") -> int:
        result = self._post("/api/projects", {"name": name, "icon": icon, "color": color})
        return result.get("id", 0)

    def delete_project(self, project_id: int) -> None:
        self._delete(f"/api/projects/{project_id}")

    # ── Staging Shelf (暂存架) ──

    def get_staging_items(self) -> list[dict]:
        data = self._get("/api/staging")
        return data.get("items", [])

    def add_to_staging(self, item_id: int) -> bool:
        result = self._post("/api/staging", {"item_id": item_id})
        return result.get("ok", False)

    def remove_from_staging(self, staging_id: int) -> bool:
        result = self._delete(f"/api/staging/{staging_id}")
        return result.get("ok", False)

    def clear_staging(self) -> None:
        self._post("/api/staging/clear")

    def staging_to_history(self, staging_id: int) -> bool:
        result = self._post(f"/api/staging/{staging_id}/to-history")
        return result.get("ok", False)

    # ── Trash (回收站) ──

    def get_trash(self, limit: int = 100) -> list[ClipboardItem]:
        data = self._get("/api/trash", {"limit": limit})
        return [_parse_item(d) for d in data.get("items", [])]

    def restore_from_trash(self, item_id: int) -> bool:
        result = self._post(f"/api/trash/{item_id}/restore")
        return result.get("ok", False)

    def permanent_delete(self, item_id: int) -> bool:
        result = self._delete(f"/api/trash/{item_id}")
        return result.get("ok", False)

    def empty_trash(self) -> int:
        result = self._post("/api/trash/empty")
        return result.get("deleted", 0)

    def trash_count(self) -> int:
        try:
            data = self._get("/api/trash/count")
            return data.get("count", 0)
        except Exception:
            return 0

    # ── Quick Phrases (常用短语) ──

    def get_phrases(self) -> list[dict]:
        data = self._get("/api/phrases")
        return data.get("phrases", [])

    def create_phrase(self, name: str, content: str, color: str = "#7CE0C3") -> int:
        result = self._post("/api/phrases", {"name": name, "content": content, "color": color})
        return result.get("id", 0)

    def update_phrase(self, phrase_id: int, name: str, content: str, color: str = "#7CE0C3") -> bool:
        result = self._put(f"/api/phrases/{phrase_id}", {"name": name, "content": content, "color": color})
        return result.get("ok", False)

    def delete_phrase(self, phrase_id: int) -> bool:
        result = self._delete(f"/api/phrases/{phrase_id}")
        return result.get("ok", False)

    def use_phrase(self, phrase_id: int) -> str:
        """Use a phrase (increment count) and return its content."""
        result = self._post(f"/api/phrases/{phrase_id}/use")
        return result.get("content", "")

    # ── Backup / Restore ──

    def export_backup(self) -> dict:
        """Export all data as a backup dict."""
        return self._get("/api/backup")

    def import_restore(self, data: dict) -> dict:
        """Import data from a backup dict."""
        return self._post("/api/restore", data)

    def get_stats(self) -> dict:
        """Get database statistics."""
        return self._get("/api/stats")
