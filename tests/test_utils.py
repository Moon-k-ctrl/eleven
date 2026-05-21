"""Tests for utility functions and import/export."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType
from src.utils.helpers import format_timestamp, truncate_text
from src.utils.import_export import (
    export_to_csv,
    export_to_json,
    export_selected_items,
    import_from_csv,
    import_from_json,
)


# ── helpers.py ──

class TestTruncateText:
    """Tests for truncate_text()."""

    def test_short_text_unchanged(self):
        assert truncate_text("hello", max_len=10) == "hello"

    def test_exact_length_unchanged(self):
        assert truncate_text("12345", max_len=5) == "12345"

    def test_long_text_truncated(self):
        result = truncate_text("1234567890", max_len=5)
        assert len(result) == 5
        assert result.endswith("…")

    def test_empty_string(self):
        assert truncate_text("", max_len=10) == ""

    def test_default_max_len(self):
        text = "a" * 200
        result = truncate_text(text)
        assert len(result) == 100


class TestFormatTimestamp:
    """Tests for format_timestamp()."""

    def test_none_returns_empty(self):
        assert format_timestamp(None) == ""

    def test_very_recent_returns_just_now(self):
        from datetime import datetime
        now = datetime.utcnow()
        result = format_timestamp(now)
        assert result == "刚刚"  # "刚刚"

    def test_minutes_ago(self):
        from datetime import datetime, timedelta
        ts = datetime.utcnow() - timedelta(minutes=5)
        result = format_timestamp(ts)
        assert "分钟前" in result  # "分钟前"

    def test_today_shows_time(self):
        from datetime import datetime, timedelta
        ts = datetime.utcnow() - timedelta(hours=3)
        result = format_timestamp(ts)
        # Should show HH:MM
        assert ":" in result

    def test_string_input(self):
        from datetime import datetime
        ts_str = datetime.utcnow().isoformat()
        result = format_timestamp(ts_str)
        # Should not crash
        assert isinstance(result, str)

    def test_invalid_string_passthrough(self):
        result = format_timestamp("not-a-date")
        assert result == "not-a-date"


# ── import_export.py ──

class TestExportJson:
    """Tests for export_to_json()."""

    def test_export_creates_valid_json(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT,
            content_text="hello",
            content_hash=ClipboardItem.compute_hash("hello"),
        ))
        out = tmp_path / "export.json"
        count = export_to_json(db, out)
        assert count == 1

        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["content_text"] == "hello"

    def test_export_empty_db(self, tmp_db_file: Database, tmp_path: Path):
        out = tmp_path / "empty.json"
        count = export_to_json(tmp_db_file, out)
        assert count == 0

        data = json.loads(out.read_text(encoding="utf-8"))
        assert data == []

    def test_export_preserves_tags(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        tag_id = db.create_tag("work", "#ff0000")
        item_id = db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT,
            content_text="tagged",
            content_hash=ClipboardItem.compute_hash("tagged"),
        ))
        db.add_item_tag(item_id, tag_id)

        out = tmp_path / "tagged.json"
        export_to_json(db, out)

        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data[0]["tags"]) == 1
        assert data[0]["tags"][0]["name"] == "work"


class TestImportJson:
    """Tests for import_from_json()."""

    def test_import_from_json(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        json_data = [
            {
                "content_type": "TEXT",
                "content_text": "imported text",
                "content_html": None,
                "is_pinned": False,
                "is_favorite": False,
                "created_at": None,
                "tags": [],
            }
        ]
        f = tmp_path / "import.json"
        f.write_text(json.dumps(json_data), encoding="utf-8")

        count = import_from_json(db, f)
        assert count == 1
        assert db.count() == 1

    def test_import_skip_duplicates(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        json_data = [
            {
                "content_type": "TEXT",
                "content_text": "dup",
                "content_html": None,
                "is_pinned": False,
                "is_favorite": False,
                "created_at": None,
                "tags": [],
            }
        ]
        f = tmp_path / "dup.json"
        f.write_text(json.dumps(json_data), encoding="utf-8")

        assert import_from_json(db, f) == 1
        assert import_from_json(db, f) == 0  # skipped as duplicate

    def test_import_with_tags(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        json_data = [
            {
                "content_type": "TEXT",
                "content_text": "tagged import",
                "content_html": None,
                "is_pinned": False,
                "is_favorite": False,
                "created_at": None,
                "tags": [{"name": "imported", "color": "#00ff00"}],
            }
        ]
        f = tmp_path / "tagged.json"
        f.write_text(json.dumps(json_data), encoding="utf-8")

        count = import_from_json(db, f)
        assert count == 1
        tags = db.get_all_tags()
        assert len(tags) == 1
        assert tags[0].name == "imported"


class TestExportCsv:
    """Tests for export_to_csv()."""

    def test_export_csv(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        db.insert_item(ClipboardItem(
            content_type=ContentType.TEXT,
            content_text="csv test",
            content_hash=ClipboardItem.compute_hash("csv test"),
        ))
        out = tmp_path / "export.csv"
        count = export_to_csv(db, out)
        assert count == 1

        with open(out, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 2  # header + 1 row
        assert "csv test" in rows[1][2]

    def test_export_csv_empty(self, tmp_db_file: Database, tmp_path: Path):
        out = tmp_path / "empty.csv"
        count = export_to_csv(tmp_db_file, out)
        assert count == 0


class TestImportCsv:
    """Tests for import_from_csv()."""

    def test_import_csv(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        f = tmp_path / "import.csv"
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["ID", "类型", "内容", "HTML",
                             "置顶", "收藏", "创建时间", "标签"])
            writer.writerow(["1", "TEXT", "csv imported", "", "否", "否", "", ""])

        count = import_from_csv(db, f)
        assert count == 1

    def test_import_csv_skip_duplicates(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        f = tmp_path / "dup.csv"
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["ID", "类型", "内容", "HTML",
                             "置顶", "收藏", "创建时间", "标签"])
            writer.writerow(["1", "TEXT", "dup csv", "", "否", "否", "", ""])

        assert import_from_csv(db, f) == 1
        assert import_from_csv(db, f) == 0


class TestExportSelectedItems:
    """Tests for export_selected_items()."""

    def test_export_text_item(self, tmp_path: Path):
        item = ClipboardItem(
            id=1,
            content_type=ContentType.TEXT,
            content_text="plain text export",
        )
        success, errors = export_selected_items([item], tmp_path)
        assert success == 1
        assert len(errors) == 0

    def test_export_html_item(self, tmp_path: Path):
        item = ClipboardItem(
            id=2,
            content_type=ContentType.HTML,
            content_html="<b>bold</b>",
        )
        success, errors = export_selected_items([item], tmp_path)
        assert success == 1

    def test_export_markdown_detection(self, tmp_path: Path):
        item = ClipboardItem(
            id=3,
            content_type=ContentType.TEXT,
            content_text="# Heading\n\nSome **bold** text and [link](http://example.com)\n\n```code```",
        )
        success, errors = export_selected_items([item], tmp_path)
        assert success == 1
        # Find the exported file and check it's .md
        export_dirs = list(tmp_path.glob("*"))
        assert len(export_dirs) == 1
        md_files = list(export_dirs[0].glob("*.md"))
        assert len(md_files) == 1

    def test_export_unsupported_type(self, tmp_path: Path):
        # IMAGE without file_path is unsupported
        item = ClipboardItem(
            id=4,
            content_type=ContentType.IMAGE,
            file_path=None,
        )
        success, errors = export_selected_items([item], tmp_path)
        assert success == 0
        assert len(errors) == 1

    def test_export_empty_list(self, tmp_path: Path):
        success, errors = export_selected_items([], tmp_path)
        assert success == 0
        assert len(errors) == 0

    def test_progress_callback_called(self, tmp_path: Path):
        calls: list[int] = []
        item = ClipboardItem(
            id=5,
            content_type=ContentType.TEXT,
            content_text="callback test",
        )
        export_selected_items([item], tmp_path, progress_callback=lambda n: calls.append(n))
        assert calls == [1]


# ── ClipboardItem.display_type ──

class TestDisplayType:
    """Tests for ClipboardItem.display_type property."""

    def test_text_type(self):
        item = ClipboardItem(content_type=ContentType.TEXT)
        assert item.display_type == "text"

    def test_image_type(self):
        item = ClipboardItem(content_type=ContentType.IMAGE)
        assert item.display_type == "image"

    def test_html_type(self):
        item = ClipboardItem(content_type=ContentType.HTML)
        assert item.display_type == "html"

    def test_files_word(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/docs/report.docx")
        assert item.display_type == "word"

    def test_files_excel(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/data/sheet.xlsx")
        assert item.display_type == "excel"

    def test_files_pdf(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/docs/file.pdf")
        assert item.display_type == "pdf"

    def test_files_ppt(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/slides/deck.pptx")
        assert item.display_type == "ppt"

    def test_files_archive(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/archive.zip")
        assert item.display_type == "archive"

    def test_files_markdown(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/docs/readme.md")
        assert item.display_type == "markdown"

    def test_files_image_ext(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/img/photo.png")
        assert item.display_type == "image"

    def test_files_text_ext(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/code/main.py")
        assert item.display_type == "text_file"

    def test_files_unknown_ext(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/data/file.xyz")
        assert item.display_type == "files"

    def test_files_empty_content(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="")
        assert item.display_type == "unknown"


# ── ClipboardItem.preview_text ──

class TestPreviewText:
    """Tests for ClipboardItem.short_preview() method."""

    def test_text_preview(self):
        item = ClipboardItem(content_type=ContentType.TEXT, content_text="hello world")
        assert "hello" in item.short_preview()

    def test_image_preview_with_path(self):
        item = ClipboardItem(content_type=ContentType.IMAGE, file_path="/img/test.png")
        assert "Image" in item.short_preview()

    def test_files_preview(self):
        item = ClipboardItem(content_type=ContentType.FILES, content_text="/a.txt\n/b.txt")
        assert "Files" in item.short_preview()

    def test_html_preview(self):
        item = ClipboardItem(content_type=ContentType.HTML, content_html="<b>bold</b>")
        assert "bold" in item.short_preview()


# ── CSV Import with tags ──

class TestImportCsvWithTags:
    """Tests for import_from_csv() with tag handling."""

    def test_import_csv_with_tags(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        f = tmp_path / "tagged.csv"
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["ID", "类型", "内容", "HTML",
                             "置顶", "收藏", "创建时间", "标签"])
            writer.writerow(["1", "TEXT", "tagged csv", "", "否", "否", "", "work;urgent"])

        count = import_from_csv(db, f)
        assert count == 1
        tags = db.get_all_tags()
        assert len(tags) == 2

    def test_import_csv_with_existing_tag(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        db.create_tag("existing", "#ff0000")

        f = tmp_path / "reuse.csv"
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["ID", "类型", "内容", "HTML",
                             "置顶", "收藏", "创建时间", "标签"])
            writer.writerow(["1", "TEXT", "reuse tag", "", "否", "否", "", "existing"])

        count = import_from_csv(db, f)
        assert count == 1
        tags = db.get_all_tags()
        assert len(tags) == 1

    def test_import_csv_invalid_type_skipped(self, tmp_db_file: Database, tmp_path: Path):
        db = tmp_db_file
        f = tmp_path / "bad.csv"
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["ID", "类型", "内容", "HTML",
                             "置顶", "收藏", "创建时间", "标签"])
            writer.writerow(["1", "INVALID", "skipped", "", "否", "否", "", ""])

        count = import_from_csv(db, f)
        assert count == 0
