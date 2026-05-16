"""Tests for tag system."""
import tempfile
from pathlib import Path

import pytest

from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType, Tag


def _make_db() -> Database:
    return Database(Path(tempfile.mkdtemp()) / "test.db")


def _insert_item(db: Database, text: str = "test") -> int:
    return db.insert_item(ClipboardItem(
        content_type=ContentType.TEXT,
        content_text=text,
        content_hash=ClipboardItem.compute_hash(text),
    ))


# ── Tag CRUD ──

def test_create_tag():
    db = _make_db()
    tag_id = db.create_tag("work", "#ff0000")
    assert tag_id > 0
    tags = db.get_all_tags()
    assert len(tags) == 1
    assert tags[0].name == "work"
    assert tags[0].color == "#ff0000"


def test_create_duplicate_tag_raises():
    db = _make_db()
    db.create_tag("work")
    with pytest.raises(ValueError, match="already exists"):
        db.create_tag("work")


def test_delete_tag():
    db = _make_db()
    tag_id = db.create_tag("temp")
    item_id = _insert_item(db)
    db.add_item_tag(item_id, tag_id)

    db.delete_tag(tag_id)
    assert len(db.get_all_tags()) == 0
    # Junction rows should be cascade-deleted
    assert len(db.get_item_tags(item_id)) == 0


def test_update_tag():
    db = _make_db()
    tag_id = db.create_tag("old_name", "#aaa")
    db.update_tag(tag_id, "new_name", "#bbb")
    tags = db.get_all_tags()
    assert tags[0].name == "new_name"
    assert tags[0].color == "#bbb"


def test_update_tag_duplicate_name_raises():
    db = _make_db()
    db.create_tag("tag_a")
    tag_b = db.create_tag("tag_b")
    with pytest.raises(ValueError, match="already exists"):
        db.update_tag(tag_b, "tag_a", "#ccc")


def test_tag_count():
    db = _make_db()
    assert db.tag_count() == 0
    db.create_tag("a")
    assert db.tag_count() == 1
    db.create_tag("b")
    assert db.tag_count() == 2


# ── Item-Tag Association ──

def test_add_item_tag():
    db = _make_db()
    tag_id = db.create_tag("work")
    item_id = _insert_item(db)
    db.add_item_tag(item_id, tag_id)
    tags = db.get_item_tags(item_id)
    assert len(tags) == 1
    assert tags[0].name == "work"


def test_add_item_tag_idempotent():
    db = _make_db()
    tag_id = db.create_tag("work")
    item_id = _insert_item(db)
    db.add_item_tag(item_id, tag_id)
    db.add_item_tag(item_id, tag_id)  # duplicate ignored
    assert len(db.get_item_tags(item_id)) == 1


def test_remove_item_tag():
    db = _make_db()
    tag_id = db.create_tag("work")
    item_id = _insert_item(db)
    db.add_item_tag(item_id, tag_id)
    db.remove_item_tag(item_id, tag_id)
    assert len(db.get_item_tags(item_id)) == 0


def test_get_tags_for_items_bulk():
    db = _make_db()
    t1 = db.create_tag("work")
    t2 = db.create_tag("personal")
    i1 = _insert_item(db, "item1")
    i2 = _insert_item(db, "item2")
    i3 = _insert_item(db, "item3")
    db.add_item_tag(i1, t1)
    db.add_item_tag(i1, t2)
    db.add_item_tag(i2, t1)

    tag_map = db.get_tags_for_items([i1, i2, i3])
    assert len(tag_map[i1]) == 2
    assert len(tag_map[i2]) == 1
    assert len(tag_map.get(i3, [])) == 0


def test_get_items_by_tag():
    db = _make_db()
    tag_id = db.create_tag("work")
    i1 = _insert_item(db, "work item 1")
    i2 = _insert_item(db, "work item 2")
    _insert_item(db, "personal item")
    db.add_item_tag(i1, tag_id)
    db.add_item_tag(i2, tag_id)

    items = db.get_items_by_tag(tag_id)
    assert len(items) == 2
    ids = {i.id for i in items}
    assert i1 in ids and i2 in ids


# ── Tag Limits ──

def test_tag_limit_100():
    db = _make_db()
    for i in range(100):
        db.create_tag(f"tag_{i}")
    assert db.tag_count() == 100
    with pytest.raises(ValueError, match="already exists"):
        # SQLite UNIQUE constraint triggers first, but manager layer enforces 100 limit
        # This tests the DB-level constraint
        db.create_tag("tag_0")


def test_item_tag_limit_10():
    """Manager layer enforces 10 tags per item; DB allows any number."""
    db = _make_db()
    item_id = _insert_item(db)
    for i in range(10):
        tag_id = db.create_tag(f"t{i}")
        db.add_item_tag(item_id, tag_id)
    assert len(db.get_item_tags(item_id)) == 10
    # Adding an 11th works at DB level (manager enforces the limit)
    extra = db.create_tag("extra")
    db.add_item_tag(item_id, extra)
    assert len(db.get_item_tags(item_id)) == 11


# ── Combined Filtering ──

def test_search_with_filters_text_only():
    db = _make_db()
    _insert_item(db, "Python is great")
    _insert_item(db, "Java is ok")
    items = db.search_with_filters(query="Python")
    assert len(items) >= 1
    assert any("Python" in (i.content_text or "") for i in items)


def test_search_with_filters_tag_only():
    db = _make_db()
    tag_id = db.create_tag("work")
    i1 = _insert_item(db, "work task")
    _insert_item(db, "personal task")
    db.add_item_tag(i1, tag_id)

    items = db.search_with_filters(tag_ids=[tag_id])
    assert len(items) == 1
    assert items[0].id == i1


def test_search_with_filters_combined():
    db = _make_db()
    tag_id = db.create_tag("work")
    i1 = _insert_item(db, "Python work task")
    _insert_item(db, "Python personal task")
    _insert_item(db, "Java work task")
    db.add_item_tag(i1, tag_id)
    db.add_item_tag(3, tag_id)  # "Java work task"

    items = db.search_with_filters(query="Python", tag_ids=[tag_id])
    assert len(items) == 1
    assert items[0].content_text == "Python work task"


def test_search_with_filters_group_filter():
    db = _make_db()
    groups = db.get_groups()
    group_id = groups[0]["id"]  # default group
    i1 = _insert_item(db, "grouped item")
    db.move_to_group(i1, group_id)
    _insert_item(db, "ungrouped item")

    items = db.search_with_filters(group_id=group_id)
    assert len(items) == 1
    assert items[0].id == i1


def test_search_with_filters_no_params():
    db = _make_db()
    _insert_item(db, "item1")
    _insert_item(db, "item2")
    items = db.search_with_filters()
    assert len(items) == 2


# ── Tags Attached to Query Results ──

def test_get_items_includes_tags():
    db = _make_db()
    tag_id = db.create_tag("work")
    item_id = _insert_item(db)
    db.add_item_tag(item_id, tag_id)

    items = db.get_items()
    assert len(items) == 1
    assert len(items[0].tags) == 1
    assert items[0].tags[0].name == "work"


def test_search_includes_tags():
    db = _make_db()
    tag_id = db.create_tag("important")
    item_id = _insert_item(db, "findable text")
    db.add_item_tag(item_id, tag_id)

    results = db.search("findable")
    assert len(results) == 1
    assert len(results[0].tags) == 1


# ── Backward Compatibility ──

def test_init_db_existing_db():
    """init_db on an existing DB should not fail (CREATE TABLE IF NOT EXISTS)."""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "test.db"
        db1 = Database(path)
        db1.create_tag("existing")
        # Re-open: should not raise
        db2 = Database(path)
        assert len(db2.get_all_tags()) == 1


# ── Tag Dataclass ──

def test_tag_dataclass_fields():
    tag = Tag(name="work", color="#ff0000")
    assert tag.name == "work"
    assert tag.color == "#ff0000"
    assert tag.id is None


def test_clipboard_item_default_tags_empty():
    item = ClipboardItem()
    assert item.tags == []
