"""Tests for Database."""
import tempfile
from pathlib import Path

from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType


def test_insert_and_get():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        item = ClipboardItem(
            content_type=ContentType.TEXT,
            content_text="hello world",
            content_hash=ClipboardItem.compute_hash("hello world"),
        )
        item_id = db.insert_item(item)
        assert item_id > 0

        items = db.get_items(limit=10)
        assert len(items) == 1
        assert items[0].content_text == "hello world"
        assert items[0].id == item_id


def test_dedup():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        h = ClipboardItem.compute_hash("dup test")
        assert not db.exists_hash(h)
        db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT, content_text="dup test", content_hash=h,
        ))
        assert db.exists_hash(h)


def test_delete():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        item = ClipboardItem(
            content_type=ContentType.TEXT, content_text="delete me",
            content_hash=ClipboardItem.compute_hash("delete me"),
        )
        item_id = db.insert_item(item)
        db.delete_item(item_id)
        assert db.count() == 0


def test_search():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT, content_text="Python is great",
            content_hash=ClipboardItem.compute_hash("Python is great"),
        ))
        db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT, content_text="Java is ok",
            content_hash=ClipboardItem.compute_hash("Java is ok"),
        ))
        results = db.search("Python")
        assert len(results) >= 1
        assert any("Python" in (r.content_text or "") for r in results)
