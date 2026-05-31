"""Staging shelf item data model."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.models.clipboard_item import ContentType


@dataclass
class StagingItem:
    """Represents an item on the staging shelf (暂存架)."""

    id: Optional[int] = None
    content_type: ContentType = ContentType.TEXT
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    source_item_id: Optional[int] = None
    sort_order: int = 0
    created_at: Optional[str] = None

    @property
    def display_type(self) -> str:
        """Determine the display type for UI rendering."""
        if self.content_type == ContentType.IMAGE:
            return "image"
        if self.content_type == ContentType.TEXT:
            return "text"
        if self.content_type == ContentType.HTML:
            return "html"
        if self.content_type == ContentType.FILES and self.content_text:
            first_file = self.content_text.split("\n")[0].strip()
            ext = Path(first_file).suffix.lower()
            ext_map = {
                ".pdf": "pdf", ".doc": "word", ".docx": "word",
                ".xls": "excel", ".xlsx": "excel",
                ".ppt": "ppt", ".pptx": "ppt",
                ".md": "markdown", ".markdown": "markdown",
            }
            if ext in ext_map:
                return ext_map[ext]
            image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
            if ext in image_exts:
                return "image"
            return "files"
        return "text"

    @property
    def preview_text(self) -> str:
        """Short preview text for card display."""
        if self.content_type == ContentType.TEXT:
            return (self.content_text or "")[:40].replace("\n", " ")
        if self.content_type == ContentType.IMAGE:
            return "图片"
        if self.content_type == ContentType.FILES:
            if self.content_text:
                names = [Path(p).name for p in self.content_text.split("\n") if p.strip()]
                return names[0] if names else "文件"
            return "文件"
        if self.content_type == ContentType.HTML:
            import re
            text = re.sub(r"<[^>]+>", "", self.content_html or "")
            return text[:40].replace("\n", " ")
        return ""

    @property
    def card_title(self) -> str:
        """Title text for the staging card."""
        if self.content_type == ContentType.TEXT:
            text = (self.content_text or "")[:30].replace("\n", " ")
            return text or "文本"
        if self.content_type == ContentType.IMAGE:
            return "图片"
        if self.content_type == ContentType.FILES:
            if self.content_text:
                first = self.content_text.split("\n")[0].strip()
                return Path(first).name if first else "文件"
            return "文件"
        if self.content_type == ContentType.HTML:
            import re
            text = re.sub(r"<[^>]+>", "", self.content_html or "")
            return text[:30].replace("\n", " ") or "HTML"
        return "内容"
