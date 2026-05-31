"""Clipboard item data model."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ContentType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILES = "FILES"
    HTML = "HTML"


class Category(str, Enum):
    """Auto-classification category for clipboard items."""
    ALL = "ALL"
    DEFAULT = "DEFAULT"
    IMAGE = "IMAGE"
    WORD = "WORD"
    EXCEL = "EXCEL"
    PDF = "PDF"
    PPT = "PPT"
    ARCHIVE = "ARCHIVE"


class Source(str, Enum):
    """How the item was delivered to the system."""
    CLIPBOARD = "clipboard"
    CONTEXT_MENU = "context-menu"
    DRAG_DROP = "drag-drop"
    HOTKEY = "hotkey"
    BROWSER_PLUGIN = "browser-plugin"
    API = "api"


_FILE_CATEGORY_MAP: dict[str, Category] = {
    ".doc": Category.WORD,
    ".docx": Category.WORD,
    ".xls": Category.EXCEL,
    ".xlsx": Category.EXCEL,
    ".pdf": Category.PDF,
    ".ppt": Category.PPT,
    ".pptx": Category.PPT,
    ".zip": Category.ARCHIVE,
    ".rar": Category.ARCHIVE,
    ".7z": Category.ARCHIVE,
    ".tar": Category.ARCHIVE,
    ".gz": Category.ARCHIVE,
    ".bz2": Category.ARCHIVE,
    ".xz": Category.ARCHIVE,
    ".tgz": Category.ARCHIVE,
}


def classify_item(item: "ClipboardItem") -> str:
    """Derive category from content_type and file extension."""
    if item.content_type == ContentType.IMAGE:
        return Category.IMAGE.value
    if item.content_type in (ContentType.TEXT, ContentType.HTML):
        return Category.DEFAULT.value
    if item.content_type == ContentType.FILES and item.content_text:
        first_file = item.content_text.split("\n")[0].strip()
        ext = Path(first_file).suffix.lower()
        return _FILE_CATEGORY_MAP.get(ext, Category.DEFAULT).value
    return Category.DEFAULT.value


@dataclass
class Tag:
    """Represents a user-defined tag."""

    id: Optional[int] = None
    name: str = ""
    color: str = "#4A90D9"
    created_at: Optional[datetime] = None


@dataclass
class ClipboardItem:
    """Represents a single clipboard entry."""

    id: Optional[int] = None
    content_type: ContentType = ContentType.TEXT
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    file_path: Optional[str] = None        # 图片在磁盘上的存储路径
    source_app: Optional[str] = None       # 来源窗口标题
    is_pinned: bool = False
    is_favorite: bool = False
    group_id: Optional[int] = None
    thumbnail_path: Optional[str] = None
    content_hash: Optional[str] = None
    category: Optional[str] = None
    tags: list[Tag] = field(default_factory=list)
    source: str = Source.CLIPBOARD.value
    project: str = "default"
    is_starred: bool = False
    metadata: Optional[str] = None  # JSON string for extended metadata
    use_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @staticmethod
    def compute_hash(content: str | bytes) -> str:
        """SHA256 hash for deduplication."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def short_preview(self, max_len: int = 80) -> str:
        """Return a short text preview for UI display."""
        if self.content_type == ContentType.TEXT:
            text = (self.content_text or "")[:max_len]
            return text.replace("\n", " ")
        elif self.content_type == ContentType.IMAGE:
            return f"[Image] {self.file_path or ''}"
        elif self.content_type == ContentType.FILES:
            text = (self.content_text or "").replace("\n", " ")
            return f"[Files] {text}"
        elif self.content_type == ContentType.HTML:
            # 降级为纯文本预览
            import re
            text = re.sub(r"<[^>]+>", "", self.content_html or "")
            return text[:max_len].replace("\n", " ")
        return ""

    @property
    def display_type(self) -> str:
        """Determine the preview display type for the preview window."""
        if self.content_type == ContentType.IMAGE:
            return "image"
        if self.content_type == ContentType.TEXT:
            return "text"
        if self.content_type == ContentType.HTML:
            return "html"
        if self.content_type == ContentType.FILES and self.content_text:
            first_file = self.content_text.split("\n")[0].strip()
            ext = Path(first_file).suffix.lower()
            if ext == ".pdf":
                return "pdf"
            if ext in (".doc", ".docx"):
                return "word"
            if ext in (".xls", ".xlsx"):
                return "excel"
            if ext in (".ppt", ".pptx"):
                return "ppt"
            archive_exts = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"}
            if ext in archive_exts:
                return "archive"
            if ext in (".md", ".markdown"):
                return "markdown"
            image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
                          ".svg", ".ico", ".tiff", ".tif"}
            if ext in image_exts:
                return "image"
            text_exts = {".txt", ".log", ".py", ".js", ".json", ".xml", ".csv",
                         ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bat",
                         ".html", ".htm", ".css", ".rb", ".go", ".rs", ".java",
                         ".c", ".cpp", ".h", ".hpp", ".ts", ".tsx", ".jsx"}
            if ext in text_exts:
                return "text_file"
            return "files"
        return "unknown"
