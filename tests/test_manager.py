"""Tests for ClipboardManager."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.clipboard_manager import ClipboardManager
from src.core.config import Config
from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType


# ── Helpers ──

def _make_manager(tmp_path: Path, monkeypatch) -> ClipboardManager:
    """Create a ClipboardManager with a mocked listener."""
    config = Config(config_path=tmp_path / "config.json")
    db = Database(config=config)
    monkeypatch.setattr(
        "src.core.clipboard_manager.ClipboardListener",
        lambda cb: MagicMock(start=MagicMock(), stop=MagicMock()),
    )
    return ClipboardManager(db=db, config=config)


def _insert_text(manager: ClipboardManager, text: str = "test") -> int:
    """Insert a text item directly into the DB and return its id."""
    item = ClipboardItem(
        content_type=ContentType.TEXT,
        content_text=text,
        content_hash=ClipboardItem.compute_hash(text),
    )
    return manager.db.insert_item(item)


# ── Import Files ──

class TestImportFiles:
    """Tests for import_files()."""

    def test_import_text_file(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        txt = tmp_path / "hello.txt"
        txt.write_text("hello world", encoding="utf-8")

        imported, skipped = manager.import_files([str(txt)])
        assert imported == 1
        assert skipped == 0
        assert manager.get_count() == 1

    def test_import_multiple_files(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        for i in range(3):
            (tmp_path / f"f{i}.txt").write_text(f"content {i}", encoding="utf-8")

        paths = [str(tmp_path / f"f{i}.txt") for i in range(3)]
        imported, skipped = manager.import_files(paths)
        assert imported == 3
        assert skipped == 0

    def test_import_nonexistent_file_skipped(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        imported, skipped = manager.import_files([str(tmp_path / "nope.txt")])
        assert imported == 0
        assert skipped == 1

    def test_import_empty_list(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        imported, skipped = manager.import_files([])
        assert imported == 0
        assert skipped == 0

    def test_import_duplicate_text_skipped(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        txt = tmp_path / "dup.txt"
        txt.write_text("duplicate content", encoding="utf-8")

        imported1, _ = manager.import_files([str(txt)])
        imported2, skipped2 = manager.import_files([str(txt)])
        assert imported1 == 1
        assert imported2 == 0
        assert skipped2 == 1

    @patch("src.core.clipboard_manager.Image")
    def test_import_image_file(self, mock_image_cls, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)

        # Mock PIL Image.open
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 100
        mock_img.copy.return_value = mock_img
        mock_img.save = MagicMock()
        mock_image_cls.open.return_value = mock_img
        mock_image_cls.Resampling.LANCZOS = 1

        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        imported, skipped = manager.import_files([str(img_path)])
        assert imported == 1
        assert skipped == 0

    def test_import_generic_file(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        bin_file = tmp_path / "data.bin"
        bin_file.write_bytes(b"\x00\x01\x02\x03")

        imported, skipped = manager.import_files([str(bin_file)])
        assert imported == 1
        assert skipped == 0


# ── Copy to Clipboard ──

class TestCopyToClipboard:
    """Tests for copy_to_clipboard()."""

    @patch("src.core.clipboard_manager.set_clipboard_text")
    def test_copy_text_item(self, mock_set_text, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item = ClipboardItem(content_type=ContentType.TEXT, content_text="copy me")
        manager.copy_to_clipboard(item)
        mock_set_text.assert_called_once_with("copy me")

    @patch("src.core.clipboard_manager.set_clipboard_files")
    def test_copy_file_item(self, mock_set_files, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item = ClipboardItem(
            content_type=ContentType.FILES,
            content_text="/path/a.txt\n/path/b.txt",
        )
        manager.copy_to_clipboard(item)
        mock_set_files.assert_called_once_with(["/path/a.txt", "/path/b.txt"])

    @patch("src.core.clipboard_manager.set_clipboard_files")
    def test_copy_image_item(self, mock_set_files, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item = ClipboardItem(
            content_type=ContentType.IMAGE,
            file_path="/images/photo.jpg",
        )
        manager.copy_to_clipboard(item)
        mock_set_files.assert_called_once_with(["/images/photo.jpg"])


# ── Toggle Operations ──

class TestToggleOperations:
    """Tests for toggle_pin, toggle_favorite, toggle_star."""

    def test_toggle_pin(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item_id = _insert_text(manager)

        manager.toggle_pin(item_id)
        items = manager.get_items()
        assert items[0].is_pinned is True

        manager.toggle_pin(item_id)
        items = manager.get_items()
        assert items[0].is_pinned is False

    def test_toggle_favorite(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item_id = _insert_text(manager)

        manager.toggle_favorite(item_id)
        items = manager.get_items()
        assert items[0].is_favorite is True

        manager.toggle_favorite(item_id)
        items = manager.get_items()
        assert items[0].is_favorite is False

    def test_toggle_star(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item_id = _insert_text(manager)

        manager.toggle_star(item_id)
        items = manager.get_items()
        assert items[0].is_starred is True

        manager.toggle_star(item_id)
        items = manager.get_items()
        assert items[0].is_starred is False


# ── Clear All ──

class TestClearAll:
    """Tests for clear_all()."""

    def test_clear_all_removes_items(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        _insert_text(manager, "a")
        _insert_text(manager, "b")
        assert manager.get_count() == 2

        manager.clear_all()
        assert manager.get_count() == 0

    def test_clear_all_on_empty_db(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        manager.clear_all()  # should not raise
        assert manager.get_count() == 0


# ── Merge Items ──

class TestMergeItems:
    """Tests for merge_items()."""

    def test_merge_two_text_items(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        id1 = _insert_text(manager, "first")
        id2 = _insert_text(manager, "second")

        result = manager.merge_items([id1, id2])
        assert result is True
        # Original items still exist, plus merged
        assert manager.get_count() == 3

    def test_merge_less_than_two_returns_false(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        id1 = _insert_text(manager, "only one")
        assert manager.merge_items([id1]) is False

    def test_merge_preserves_tags(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        id1 = _insert_text(manager, "tagged1")
        id2 = _insert_text(manager, "tagged2")
        tag_id = manager.create_tag("merged-tag")
        manager.db.add_item_tag(id1, tag_id)

        result = manager.merge_items([id1, id2])
        assert result is True


# ── Paste from Clipboard ──

class TestPasteFromClipboard:
    """Tests for paste_from_clipboard()."""

    @patch("src.core.clipboard_manager.get_clipboard_image", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_files", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_html", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_text", return_value="pasted text")
    def test_paste_text(self, mock_text, mock_html, mock_files, mock_image, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        result = manager.paste_from_clipboard()
        assert result is True
        assert manager.get_count() == 1

    @patch("src.core.clipboard_manager.get_clipboard_image", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_files", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_html", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_text", return_value=None)
    def test_paste_empty_clipboard(self, mock_text, mock_html, mock_files, mock_image, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        result = manager.paste_from_clipboard()
        assert result is False
        assert manager.get_count() == 0

    @patch("src.core.clipboard_manager.get_clipboard_image", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_files", return_value=["/a.txt", "/b.txt"])
    @patch("src.core.clipboard_manager.get_clipboard_html", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_text", return_value=None)
    def test_paste_files(self, mock_text, mock_html, mock_files, mock_image, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        result = manager.paste_from_clipboard()
        assert result is True
        items = manager.get_items()
        assert items[0].content_type == ContentType.FILES


# ── Search with Filters ──

class TestSearchWithFilters:
    """Tests for search_with_filters()."""

    def test_search_text_only(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        _insert_text(manager, "Python rocks")
        _insert_text(manager, "Java is ok")

        results = manager.search_with_filters(query="Python")
        assert len(results) >= 1
        assert any("Python" in (r.content_text or "") for r in results)

    def test_search_tag_filter(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("work")
        item_id = _insert_text(manager, "work task")
        _insert_text(manager, "personal task")
        manager.db.add_item_tag(item_id, tag_id)

        results = manager.search_with_filters(tag_ids=[tag_id])
        assert len(results) == 1
        assert results[0].content_text == "work task"

    def test_search_category_filter(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        _insert_text(manager, "text item")

        results = manager.search_with_filters(category="DEFAULT")
        assert len(results) == 1

    def test_search_project_filter(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        _insert_text(manager, "default project item")

        results = manager.search_with_filters(project="default")
        assert len(results) == 1

    def test_search_combined(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("dev")
        item_id = _insert_text(manager, "Python dev task")
        _insert_text(manager, "Python other")
        manager.db.add_item_tag(item_id, tag_id)

        results = manager.search_with_filters(query="Python", tag_ids=[tag_id])
        assert len(results) == 1
        assert results[0].content_text == "Python dev task"


# ── Tag Management ──

class TestTagManagement:
    """Tests for tag CRUD via manager."""

    def test_create_tag(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("my-tag", "#ff0000")
        assert tag_id > 0
        tags = manager.get_all_tags()
        assert len(tags) == 1
        assert tags[0].name == "my-tag"

    def test_create_tag_limit_100(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        for i in range(100):
            manager.create_tag(f"tag_{i}")
        with pytest.raises(ValueError, match="Maximum 100"):
            manager.create_tag("tag_100")

    def test_delete_tag(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("temp")
        manager.delete_tag(tag_id)
        assert len(manager.get_all_tags()) == 0

    def test_update_tag(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("old")
        manager.update_tag(tag_id, "new", "#00ff00")
        tags = manager.get_all_tags()
        assert tags[0].name == "new"
        assert tags[0].color == "#00ff00"

    def test_add_tag_to_item(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("work")
        item_id = _insert_text(manager)

        manager.add_tag_to_item(item_id, tag_id)
        tags = manager.db.get_item_tags(item_id)
        assert len(tags) == 1

    def test_add_tag_to_item_limit_10(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item_id = _insert_text(manager)
        for i in range(10):
            tag_id = manager.create_tag(f"t{i}")
            manager.add_tag_to_item(item_id, tag_id)

        extra_tag = manager.create_tag("extra")
        with pytest.raises(ValueError, match="Maximum 10"):
            manager.add_tag_to_item(item_id, extra_tag)

    def test_remove_tag_from_item(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        tag_id = manager.create_tag("work")
        item_id = _insert_text(manager)
        manager.add_tag_to_item(item_id, tag_id)

        manager.remove_tag_from_item(item_id, tag_id)
        tags = manager.db.get_item_tags(item_id)
        assert len(tags) == 0


# ── Delete Item ──

class TestDeleteItem:
    """Tests for delete_item()."""

    def test_delete_item(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        item_id = _insert_text(manager, "delete me")
        assert manager.get_count() == 1

        manager.delete_item(item_id)
        assert manager.get_count() == 0


# ── Get Items ──

class TestGetItems:
    """Tests for get_items() and related methods."""

    def test_get_items_returns_list(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        _insert_text(manager, "a")
        _insert_text(manager, "b")

        items = manager.get_items(limit=10)
        assert len(items) == 2

    def test_get_count(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        assert manager.get_count() == 0
        _insert_text(manager)
        assert manager.get_count() == 1

    def test_get_max_items(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        assert manager.get_max_items() == 200  # default

    def test_search(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        _insert_text(manager, "findable content")
        _insert_text(manager, "other stuff")

        results = manager.search("findable")
        assert len(results) >= 1


# ── Callbacks ──

class TestCallbacks:
    """Tests for add_callback / remove_callback."""

    def test_callback_called_on_notify(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        calls: list[int] = []
        manager.add_callback(lambda: calls.append(1))

        _insert_text(manager, "trigger")
        manager.toggle_pin(1)  # triggers _notify
        assert len(calls) >= 1

    def test_remove_callback(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        calls: list[int] = []
        cb = lambda: calls.append(1)
        manager.add_callback(cb)
        manager.remove_callback(cb)

        _insert_text(manager, "trigger")
        manager.toggle_pin(1)
        assert len(calls) == 0

    def test_remove_nonexistent_callback(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        # Should not raise
        manager.remove_callback(lambda: None)


# ── Projects ──

class TestProjects:
    """Tests for project management via manager."""

    def test_get_projects(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        projects = manager.get_projects()
        # At least the default project
        assert len(projects) >= 1

    def test_create_project(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        pid = manager.create_project("my-project", "🎯", "#ff0000")
        assert pid > 0
        projects = manager.get_projects()
        names = [p["name"] for p in projects]
        assert "my-project" in names

    def test_delete_project(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        pid = manager.create_project("to-delete")
        manager.delete_project(pid)
        projects = manager.get_projects()
        names = [p["name"] for p in projects]
        assert "to-delete" not in names


# ── Groups ──

class TestGroups:
    """Tests for group management via manager."""

    def test_get_groups(self, tmp_path: Path, monkeypatch):
        manager = _make_manager(tmp_path, monkeypatch)
        groups = manager.get_groups()
        assert len(groups) >= 1  # default group
