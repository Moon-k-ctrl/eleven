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
        db.close()


def test_dedup():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        h = ClipboardItem.compute_hash("dup test")
        assert not db.exists_hash(h)
        db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT, content_text="dup test", content_hash=h,
        ))
        assert db.exists_hash(h)
        db.close()


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
        db.close()


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
        db.close()


def test_delete_items_batch():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        ids = []
        for i in range(5):
            item = ClipboardItem(
                content_type=ContentType.TEXT,
                content_text=f"batch item {i}",
                content_hash=ClipboardItem.compute_hash(f"batch item {i}"),
            )
            ids.append(db.insert_item(item))
        assert db.count() == 5
        deleted = db.delete_items_batch(ids[:3])
        assert deleted == 3
        assert db.count() == 2
        db.close()


def test_staging_crud():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        assert db.staging_count() == 0

        # Add staging item
        sid = db.add_staging_item(
            content_type="TEXT",
            content_text="staging test",
        )
        assert sid > 0
        assert db.staging_count() == 1

        # Get staging items
        items = db.get_staging_items()
        assert len(items) == 1
        assert items[0]["content_text"] == "staging test"

        # Get by id
        item = db.get_staging_item_by_id(sid)
        assert item is not None
        assert item["content_text"] == "staging test"

        # Remove
        db.remove_staging_item(sid)
        assert db.staging_count() == 0

        # Add multiple then clear
        for i in range(3):
            db.add_staging_item(content_type="TEXT", content_text=f"item {i}")
        assert db.staging_count() == 3
        db.clear_staging_items()
        assert db.staging_count() == 0
        db.close()
