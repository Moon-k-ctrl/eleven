"""Tests for ClipboardItem model."""
from src.models.clipboard_item import ClipboardItem, ContentType


def test_short_preview_text():
    item = ClipboardItem(
        content_type=ContentType.TEXT,
        content_text="Hello\nWorld",
    )
    assert "Hello" in item.short_preview()


def test_short_preview_image():
    item = ClipboardItem(
        content_type=ContentType.IMAGE,
        file_path="/tmp/img.png",
    )
    assert "[Image]" in item.short_preview()


def test_compute_hash_deterministic():
    h1 = ClipboardItem.compute_hash("test")
    h2 = ClipboardItem.compute_hash("test")
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


def test_compute_hash_different():
    h1 = ClipboardItem.compute_hash("foo")
    h2 = ClipboardItem.compute_hash("bar")
    assert h1 != h2
