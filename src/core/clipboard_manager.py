"""Central clipboard manager coordinating listener, DB, and UI signals."""
from __future__ import annotations

import io
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal
import win32clipboard
import win32con

logger = logging.getLogger("eleven.clipboard")

from src.core.clipboard_listener import (
    ClipboardListener,
    get_clipboard_text,
    get_clipboard_files,
    get_clipboard_image,
    get_clipboard_html,
    set_clipboard_text,
    set_clipboard_files,
)
from src.core.config import Config
from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType, Source, Tag, classify_item

# 图片存储目录
IMAGES_DIR = Path.home() / ".eleven" / "images"


class ClipboardManager(QObject):
    """Manages clipboard monitoring, storage, and retrieval."""

    items_changed = pyqtSignal()  # UI 用这个信号刷新列表

    def __init__(self, db: Optional[Database] = None, config: Optional[Config] = None):
        super().__init__()
        self.config = config or Config()
        self.db = db or Database(config=self.config)
        self._listener = ClipboardListener(self._on_clipboard_change)
        self._listener_thread: Optional[threading.Thread] = None
        self._ignore_next = False  # 防止自己写入触发监听
        self._callbacks: list[Callable[[], None]] = []  # 服务端模式回调

    def start(self) -> None:
        """Start clipboard monitoring in a background thread (if enabled)."""
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        if self.config.clipboard_enabled:
            self._listener_thread = threading.Thread(
                target=self._listener.start, daemon=True, name="clipboard-listener"
            )
            self._listener_thread.start()
            logger.info("Clipboard monitoring enabled")
        else:
            logger.info("Clipboard monitoring disabled (active delivery mode)")

    def stop(self) -> None:
        self._listener.stop()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2)

    def add_callback(self, callback: Callable[[], None]) -> None:
        """Register a non-Qt callback for item changes (server mode)."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove a previously registered callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    def get_items(self, limit: int = 50, offset: int = 0) -> list[ClipboardItem]:
        return self.db.get_items(limit, offset)

    def search(self, query: str) -> list[ClipboardItem]:
        return self.db.search(query)

    def copy_to_clipboard(self, item: ClipboardItem) -> None:
        """Write an item back to system clipboard."""
        self._ignore_next = True
        if item.content_type == ContentType.TEXT and item.content_text:
            set_clipboard_text(item.content_text)
        elif item.content_type == ContentType.FILES and item.content_text:
            files = item.content_text.split("\n")
            set_clipboard_files(files)
        elif item.content_type == ContentType.HTML and item.content_html:
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                if item.content_text:
                    win32clipboard.SetClipboardData(
                        win32con.CF_UNICODETEXT, item.content_text
                    )
            finally:
                win32clipboard.CloseClipboard()
        elif item.content_type == ContentType.IMAGE and item.file_path:
            set_clipboard_files([item.file_path])

    def delete_item(self, item_id: int) -> None:
        self.db.delete_item(item_id)
        self._notify()

    def toggle_pin(self, item_id: int) -> None:
        self.db.toggle_pin(item_id)
        self._notify()

    def toggle_favorite(self, item_id: int) -> None:
        self.db.toggle_favorite(item_id)
        self._notify()

    def toggle_star(self, item_id: int) -> None:
        self.db.toggle_star(item_id)
        self._notify()

    def import_files(self, file_paths: list[str], source: str = "context-menu",
                     project: str = "default", metadata: Optional[dict] = None) -> tuple[int, int]:
        """Import files into the system. Returns (imported_count, skipped_count)."""
        imported = 0
        skipped = 0
        meta_str = None
        if metadata:
            import json
            meta_str = json.dumps(metadata, ensure_ascii=False)

        for fp in file_paths:
            try:
                p = Path(fp)
                if not p.exists():
                    skipped += 1
                    continue

                # Determine content type from extension
                ext = p.suffix.lower()
                image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff", ".tif"}

                if ext in image_exts:
                    item = self._import_image(p, source, project, meta_str)
                else:
                    # Read text content for text-like files
                    text_exts = {".txt", ".log", ".py", ".js", ".json", ".xml", ".csv",
                                 ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bat",
                                 ".html", ".htm", ".css", ".rb", ".go", ".rs", ".java",
                                 ".c", ".cpp", ".h", ".hpp", ".ts", ".tsx", ".jsx", ".md"}
                    if ext in text_exts:
                        try:
                            content = p.read_text(encoding="utf-8", errors="replace")
                            content_hash = ClipboardItem.compute_hash(content)
                            if self.db.exists_hash(content_hash):
                                skipped += 1
                                continue
                            item = ClipboardItem(
                                content_type=ContentType.TEXT,
                                content_text=content,
                                file_path=str(p),
                                source_app=p.name,
                                content_hash=content_hash,
                                source=source,
                                project=project,
                                metadata=meta_str,
                            )
                        except Exception:
                            # Fall through to FILES type
                            item = None
                    else:
                        item = None

                    if item is None:
                        # Generic file
                        text = str(p)
                        content_hash = ClipboardItem.compute_hash(text)
                        if self.db.exists_hash(content_hash):
                            skipped += 1
                            continue
                        item = ClipboardItem(
                            content_type=ContentType.FILES,
                            content_text=text,
                            file_path=str(p),
                            source_app=p.name,
                            content_hash=content_hash,
                            source=source,
                            project=project,
                            metadata=meta_str,
                        )

                item.category = classify_item(item)
                self.db.insert_item(item)
                imported += 1
            except Exception:
                logger.error(f"Failed to import file: {fp}", exc_info=True)
                skipped += 1

        if imported > 0:
            excess = self.db.count() - self.config.max_items
            if excess > 0:
                self.db.delete_oldest_non_pinned(excess)
            self._notify()

        return imported, skipped

    def _import_image(self, path: Path, source: str, project: str,
                      meta_str: Optional[str]) -> Optional[ClipboardItem]:
        """Import an image file: copy to IMAGES_DIR, generate thumbnail."""
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        image = Image.open(str(path))

        max_size = self.config.max_image_size
        if image.width > max_size[0] or image.height > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        file_name = f"{uuid.uuid4().hex}.jpg"
        file_path = IMAGES_DIR / file_name
        image.save(str(file_path), "JPEG", quality=self.config.jpeg_quality)

        # Thumbnail
        thumb = image.copy()
        thumb.thumbnail((80, 80), Image.Resampling.LANCZOS)
        thumb_name = f"thumb_{file_name}"
        thumb_path = IMAGES_DIR / thumb_name
        thumb.save(str(thumb_path), "JPEG", quality=70)

        content_hash = ClipboardItem.compute_hash(path.read_bytes())
        if self.db.exists_hash(content_hash):
            return None

        return ClipboardItem(
            content_type=ContentType.IMAGE,
            file_path=str(file_path),
            thumbnail_path=str(thumb_path),
            source_app=path.name,
            content_hash=content_hash,
            source=source,
            project=project,
            metadata=meta_str,
        )

    def clear_all(self) -> None:
        self.db.clear_all()
        self._notify()

    def get_count(self) -> int:
        """Get current item count."""
        return self.db.count()

    def get_max_items(self) -> int:
        """Get max items limit."""
        return self.config.max_items

    def merge_items(self, item_ids: list[int]) -> bool:
        """Merge multiple items into one. Returns True if successful."""
        if len(item_ids) < 2:
            return False

        # Collect tags from source items before merge
        tag_map = self.db.get_tags_for_items(item_ids)
        all_tags: list[Tag] = []
        seen_ids: set[int] = set()
        for tags in tag_map.values():
            for tag in tags:
                if tag.id and tag.id not in seen_ids:
                    all_tags.append(tag)
                    seen_ids.add(tag.id)

        new_id = self.db.merge_items(item_ids)
        if new_id:
            # Apply inherited tags (up to 10)
            for tag in all_tags[:10]:
                if tag.id:
                    self.db.add_item_tag(new_id, tag.id)
            self._notify()
            return True
        return False

    # ── 标签管理 ──

    def create_tag(self, name: str, color: str = "#4A90D9") -> int:
        """Create a new tag. Raises ValueError if limit reached or name taken."""
        if self.db.tag_count() >= 100:
            raise ValueError("Maximum 100 tags reached")
        return self.db.create_tag(name, color)

    def delete_tag(self, tag_id: int) -> None:
        self.db.delete_tag(tag_id)
        self._notify()

    def update_tag(self, tag_id: int, name: str, color: str) -> None:
        self.db.update_tag(tag_id, name, color)
        self._notify()

    def get_all_tags(self) -> list[Tag]:
        return self.db.get_all_tags()

    def add_tag_to_item(self, item_id: int, tag_id: int) -> None:
        """Add a tag to an item. Raises ValueError if limit reached."""
        if len(self.db.get_item_tags(item_id)) >= 10:
            raise ValueError("Maximum 10 tags per item reached")
        self.db.add_item_tag(item_id, tag_id)
        self._notify()

    def remove_tag_from_item(self, item_id: int, tag_id: int) -> None:
        self.db.remove_item_tag(item_id, tag_id)
        self._notify()

    def get_items_by_tag(self, tag_id: int, limit: int = 50) -> list[ClipboardItem]:
        return self.db.get_items_by_tag(tag_id, limit)

    def get_groups(self) -> list[dict]:
        """Get all groups."""
        return self.db.get_groups()

    # ── 项目空间 ──

    def get_projects(self) -> list[dict]:
        return self.db.get_projects()

    def create_project(self, name: str, icon: str = "📁", color: str = "#4A90D9") -> int:
        return self.db.create_project(name, icon, color)

    def delete_project(self, project_id: int) -> None:
        self.db.delete_project(project_id)

    def copy_item(self, item_id: int) -> None:
        """Copy item to clipboard by id (compat with ApiClient interface)."""
        items = self.db.get_items(limit=200, offset=0)
        for item in items:
            if item.id == item_id:
                self.copy_to_clipboard(item)
                return

    def paste_from_clipboard(self) -> bool:
        """Read current clipboard and add as new item. Returns True if added."""
        item = self._read_clipboard()
        if item is None:
            return False
        # 跳过去重，强制添加
        item.category = classify_item(item)
        self.db.insert_item(item)
        excess = self.db.count() - self.config.max_items
        if excess > 0:
            self.db.delete_oldest_non_pinned(excess)
        self._notify()
        return True

    def search_with_filters(self, query: Optional[str] = None,
                            tag_ids: Optional[list[int]] = None,
                            group_id: Optional[int] = None,
                            category: Optional[str] = None,
                            project: Optional[str] = None,
                            limit: int = 50) -> list[ClipboardItem]:
        return self.db.search_with_filters(query, tag_ids, group_id, category, project, limit)

    # ── 内部方法 ──

    def _on_clipboard_change(self) -> None:
        """Called by listener on each clipboard change."""
        if self._ignore_next:
            self._ignore_next = False
            return

        try:
            item = self._read_clipboard()
            if item is None:
                return

            # 去重
            if item.content_hash and self.db.exists_hash(item.content_hash):
                return

            # 自动分类 + 标记来源
            item.category = classify_item(item)
            item.source = Source.CLIPBOARD.value

            self.db.insert_item(item)

            # 容量限制：FIFO 淘汰
            excess = self.db.count() - self.config.max_items
            if excess > 0:
                self.db.delete_oldest_non_pinned(excess)

            self._notify()
        except Exception:
            logger.error("Clipboard change handler failed", exc_info=True)

    def _notify(self) -> None:
        """Notify all listeners (Qt signal + plain callbacks)."""
        self.items_changed.emit()
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

    def _read_clipboard(self) -> Optional[ClipboardItem]:
        """Read current clipboard content into a ClipboardItem."""
        # IMAGE 优先（截图、复制图片等场景最常见）
        dib_data = get_clipboard_image()
        if dib_data:
            return self._process_image(dib_data)

        files = get_clipboard_files()
        if files:
            text = "\n".join(files)
            return ClipboardItem(
                content_type=ContentType.FILES,
                content_text=text,
                content_hash=ClipboardItem.compute_hash(text),
            )

        html = get_clipboard_html()
        if html:
            text = get_clipboard_text() or ""
            return ClipboardItem(
                content_type=ContentType.HTML,
                content_text=text,
                content_html=html,
                content_hash=ClipboardItem.compute_hash(html),
            )

        text = get_clipboard_text()
        if text:
            return ClipboardItem(
                content_type=ContentType.TEXT,
                content_text=text,
                content_hash=ClipboardItem.compute_hash(text),
            )

        return None

    def _process_image(self, dib_data: bytes) -> Optional[ClipboardItem]:
        """Convert DIB bytes to compressed image and create ClipboardItem."""
        try:
            import struct

            width = struct.unpack_from("<i", dib_data, 4)[0]
            height = struct.unpack_from("<i", dib_data, 8)[0]

            bmp_header = struct.pack("<2sIHHI", b"BM", 14 + len(dib_data), 0, 0, 14 + 40)
            bmp_data = bmp_header + dib_data

            image = Image.open(io.BytesIO(bmp_data))
            image = image.transpose(Image.FLIP_TOP_BOTTOM)

            max_size = self.config.max_image_size
            if image.width > max_size[0] or image.height > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            file_name = f"{uuid.uuid4().hex}.jpg"
            file_path = IMAGES_DIR / file_name

            image.save(str(file_path), "JPEG", quality=self.config.jpeg_quality)

            thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
            thumb_path = IMAGES_DIR / thumb_name
            thumb = image.copy()
            thumb.thumbnail((80, 80))
            thumb.save(str(thumb_path), "JPEG", quality=70)

            content_hash = ClipboardItem.compute_hash(dib_data)

            return ClipboardItem(
                content_type=ContentType.IMAGE,
                file_path=str(file_path),
                thumbnail_path=str(thumb_path),
                content_hash=content_hash,
            )
        except Exception as e:
            logger.error(f"Failed to process image: {e}", exc_info=True)
            return None
