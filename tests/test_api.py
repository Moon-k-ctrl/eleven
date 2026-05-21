"""Tests for FastAPI REST endpoints."""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ── Status ──

class TestStatusEndpoint:
    """GET /api/status"""

    def test_status_returns_200(self, api_client):
        resp = api_client.get("/api/status")
        assert resp.status_code == 200

    def test_status_has_required_fields(self, api_client):
        resp = api_client.get("/api/status")
        data = resp.json()
        assert "status" in data
        assert "count" in data
        assert "max_items" in data
        assert "storage_mode" in data

    def test_status_online(self, api_client):
        resp = api_client.get("/api/status")
        assert resp.json()["status"] == "online"


# ── Items CRUD ──

class TestItemsCRUD:
    """GET /api/items, POST /api/items/import-text, DELETE /api/items/{id}"""

    def test_get_items_empty(self, api_client):
        resp = api_client.get("/api/items")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["items"] == []

    def test_import_text(self, api_client):
        resp = api_client.post("/api/items/import-text", json={
            "content_text": "hello from api",
            "source": "test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["imported"] == 1

    def test_import_text_duplicate_skipped(self, api_client):
        api_client.post("/api/items/import-text", json={
            "content_text": "duplicate",
        })
        resp = api_client.post("/api/items/import-text", json={
            "content_text": "duplicate",
        })
        assert resp.json()["skipped"] == 1

    def test_get_items_after_import(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "item1"})
        api_client.post("/api/items/import-text", json={"content_text": "item2"})

        resp = api_client.get("/api/items")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is False

    def test_get_items_with_limit(self, api_client):
        for i in range(5):
            api_client.post("/api/items/import-text", json={"content_text": f"item{i}"})

        resp = api_client.get("/api/items?limit=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True

    def test_delete_item(self, api_client):
        resp = api_client.post("/api/items/import-text", json={"content_text": "delete me"})
        # Get the item id
        items = api_client.get("/api/items").json()["items"]
        item_id = items[0]["id"]

        resp = api_client.delete(f"/api/items/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify deleted
        items = api_client.get("/api/items").json()["items"]
        assert len(items) == 0

    def test_delete_nonexistent_item(self, api_client):
        resp = api_client.delete("/api/items/99999")
        assert resp.status_code == 200  # delete is idempotent


# ── Item Operations ──

class TestItemOperations:
    """Pin, favorite, star, batch-delete, merge, clear, paste."""

    def _create_item(self, api_client, text="test") -> int:
        api_client.post("/api/items/import-text", json={"content_text": text})
        items = api_client.get("/api/items").json()["items"]
        return items[0]["id"]

    def test_pin_item(self, api_client):
        item_id = self._create_item(api_client)
        resp = api_client.post(f"/api/items/{item_id}/pin")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify pinned
        items = api_client.get("/api/items").json()["items"]
        assert items[0]["is_pinned"] is True

    def test_favorite_item(self, api_client):
        item_id = self._create_item(api_client)
        resp = api_client.post(f"/api/items/{item_id}/favorite")
        assert resp.status_code == 200

        items = api_client.get("/api/items").json()["items"]
        assert items[0]["is_favorite"] is True

    def test_star_item(self, api_client):
        item_id = self._create_item(api_client)
        resp = api_client.post(f"/api/items/{item_id}/star")
        assert resp.status_code == 200

        items = api_client.get("/api/items").json()["items"]
        assert items[0]["is_starred"] is True

    def test_batch_delete(self, api_client):
        id1 = self._create_item(api_client, "a")
        id2 = self._create_item(api_client, "b")
        id3 = self._create_item(api_client, "c")

        resp = api_client.post("/api/items/batch-delete", json={
            "item_ids": [id1, id3],
        })
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2

        items = api_client.get("/api/items").json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == id2

    def test_merge_items(self, api_client):
        id1 = self._create_item(api_client, "first")
        id2 = self._create_item(api_client, "second")

        resp = api_client.post("/api/items/merge", json={
            "item_ids": [id1, id2],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_merge_single_item_returns_400(self, api_client):
        item_id = self._create_item(api_client)
        resp = api_client.post("/api/items/merge", json={
            "item_ids": [item_id],
        })
        assert resp.status_code == 400

    def test_clear_items(self, api_client):
        self._create_item(api_client, "a")
        self._create_item(api_client, "b")

        resp = api_client.post("/api/items/clear")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        items = api_client.get("/api/items").json()["items"]
        assert len(items) == 0

    @patch("src.core.clipboard_manager.get_clipboard_image", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_files", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_html", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_text", return_value="pasted")
    def test_paste_from_clipboard(self, mock_text, mock_html, mock_files, mock_image, api_client):
        resp = api_client.post("/api/items/paste")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @patch("src.core.clipboard_manager.get_clipboard_image", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_files", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_html", return_value=None)
    @patch("src.core.clipboard_manager.get_clipboard_text", return_value=None)
    def test_paste_empty_clipboard(self, mock_text, mock_html, mock_files, mock_image, api_client):
        resp = api_client.post("/api/items/paste")
        assert resp.json()["ok"] is False


# ── Copy Item ──

class TestCopyItem:
    """POST /api/items/{id}/copy"""

    @patch("src.core.clipboard_manager.set_clipboard_text")
    def test_copy_existing_item(self, mock_set, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "copy me"})
        items = api_client.get("/api/items").json()["items"]
        item_id = items[0]["id"]

        resp = api_client.post(f"/api/items/{item_id}/copy")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_copy_nonexistent_item_returns_404(self, api_client):
        resp = api_client.post("/api/items/99999/copy")
        assert resp.status_code == 404


# ── Search ──

class TestSearchEndpoint:
    """GET /api/items/search"""

    def test_search_returns_results(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "Python rocks"})
        api_client.post("/api/items/import-text", json={"content_text": "Java is ok"})

        resp = api_client.get("/api/items/search?q=Python")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        assert any("Python" in i["content_text"] for i in data["items"])

    def test_search_no_results(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "hello"})

        resp = api_client.get("/api/items/search?q=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# ── Items with Filters ──

class TestItemsWithFilters:
    """GET /api/items with query params."""

    def test_filter_by_category(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "text item"})

        resp = api_client.get("/api/items?category=DEFAULT")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_by_project(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "proj item"})

        resp = api_client.get("/api/items?project=default")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filter_by_query(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "searchable"})
        api_client.post("/api/items/import-text", json={"content_text": "other"})

        resp = api_client.get("/api/items?q=searchable")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1


# ── Tags CRUD ──

class TestTagsCRUD:
    """GET /api/tags, POST /api/tags, PUT /api/tags/{id}, DELETE /api/tags/{id}"""

    def test_get_tags_empty(self, api_client):
        resp = api_client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json()["tags"] == []

    def test_create_tag(self, api_client):
        resp = api_client.post("/api/tags", json={
            "name": "work",
            "color": "#ff0000",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["id"] > 0

    def test_create_tag_invalid_color(self, api_client):
        resp = api_client.post("/api/tags", json={
            "name": "bad",
            "color": "not-hex",
        })
        assert resp.status_code == 422  # validation error

    def test_create_tag_empty_name(self, api_client):
        resp = api_client.post("/api/tags", json={
            "name": "   ",
            "color": "#4A90D9",
        })
        assert resp.status_code == 422

    def test_create_duplicate_tag(self, api_client):
        api_client.post("/api/tags", json={"name": "dup"})
        resp = api_client.post("/api/tags", json={"name": "dup"})
        assert resp.status_code == 400

    def test_get_tags_after_create(self, api_client):
        api_client.post("/api/tags", json={"name": "t1"})
        api_client.post("/api/tags", json={"name": "t2"})

        resp = api_client.get("/api/tags")
        tags = resp.json()["tags"]
        assert len(tags) == 2

    def test_update_tag(self, api_client):
        resp = api_client.post("/api/tags", json={"name": "old", "color": "#aaaaaa"})
        tag_id = resp.json()["id"]

        resp = api_client.put(f"/api/tags/{tag_id}", json={
            "name": "new",
            "color": "#bbbbbb",
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_tag_partial(self, api_client):
        resp = api_client.post("/api/tags", json={"name": "partial", "color": "#aaaaaa"})
        tag_id = resp.json()["id"]

        resp = api_client.put(f"/api/tags/{tag_id}", json={"color": "#cccccc"})
        assert resp.status_code == 200

    def test_update_nonexistent_tag(self, api_client):
        resp = api_client.put("/api/tags/99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_delete_tag(self, api_client):
        resp = api_client.post("/api/tags", json={"name": "to-delete"})
        tag_id = resp.json()["id"]

        resp = api_client.delete(f"/api/tags/{tag_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify deleted
        tags = api_client.get("/api/tags").json()["tags"]
        assert len(tags) == 0


# ── Item-Tag Association ──

class TestItemTagAssociation:
    """POST /api/items/{id}/tags, DELETE /api/items/{id}/tags/{tag_id}, GET /api/items/{id}/tags"""

    def _create_item_and_tag(self, api_client) -> tuple[int, int]:
        api_client.post("/api/items/import-text", json={"content_text": "tagged item"})
        items = api_client.get("/api/items").json()["items"]
        item_id = items[0]["id"]

        resp = api_client.post("/api/tags", json={"name": "my-tag"})
        tag_id = resp.json()["id"]
        return item_id, tag_id

    def test_add_tag_to_item(self, api_client):
        item_id, tag_id = self._create_item_and_tag(api_client)

        resp = api_client.post(f"/api/items/{item_id}/tags", json={"tag_id": tag_id})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_get_item_tags(self, api_client):
        item_id, tag_id = self._create_item_and_tag(api_client)
        api_client.post(f"/api/items/{item_id}/tags", json={"tag_id": tag_id})

        resp = api_client.get(f"/api/items/{item_id}/tags")
        assert resp.status_code == 200
        tags = resp.json()["tags"]
        assert len(tags) == 1
        assert tags[0]["name"] == "my-tag"

    def test_remove_tag_from_item(self, api_client):
        item_id, tag_id = self._create_item_and_tag(api_client)
        api_client.post(f"/api/items/{item_id}/tags", json={"tag_id": tag_id})

        resp = api_client.delete(f"/api/items/{item_id}/tags/{tag_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify removed
        tags = api_client.get(f"/api/items/{item_id}/tags").json()["tags"]
        assert len(tags) == 0

    def test_add_tag_limit_10(self, api_client):
        api_client.post("/api/items/import-text", json={"content_text": "many tags"})
        items = api_client.get("/api/items").json()["items"]
        item_id = items[0]["id"]

        for i in range(10):
            resp = api_client.post("/api/tags", json={"name": f"t{i}"})
            tag_id = resp.json()["id"]
            api_client.post(f"/api/items/{item_id}/tags", json={"tag_id": tag_id})

        # 11th should fail
        resp = api_client.post("/api/tags", json={"name": "extra"})
        extra_id = resp.json()["id"]
        resp = api_client.post(f"/api/items/{item_id}/tags", json={"tag_id": extra_id})
        assert resp.status_code == 400


# ── Projects ──

class TestProjectsEndpoint:
    """GET /api/projects, POST /api/projects, DELETE /api/projects/{id}"""

    def test_get_projects(self, api_client):
        resp = api_client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        # At least default project
        assert len(data["projects"]) >= 1

    def test_create_project(self, api_client):
        resp = api_client.post("/api/projects", json={
            "name": "my-project",
            "icon": "🎯",
            "color": "#ff0000",
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["id"] > 0

    def test_create_duplicate_project(self, api_client):
        api_client.post("/api/projects", json={"name": "dup-project"})
        resp = api_client.post("/api/projects", json={"name": "dup-project"})
        assert resp.status_code == 400

    def test_delete_project(self, api_client):
        resp = api_client.post("/api/projects", json={"name": "to-delete"})
        pid = resp.json()["id"]

        resp = api_client.delete(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ── Config ──

class TestConfigEndpoint:
    """GET /api/config, POST /api/config"""

    def test_get_config(self, api_client):
        resp = api_client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "storage_mode" in data
        assert "max_items" in data
        assert "max_image_size" in data
        assert "jpeg_quality" in data

    def test_update_storage_mode(self, api_client):
        resp = api_client.post("/api/config", json={
            "storage_mode": "persistent",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["storage_mode"] == "persistent"

    def test_update_max_items(self, api_client):
        resp = api_client.post("/api/config", json={
            "max_items": 500,
        })
        assert resp.status_code == 200
        assert resp.json()["max_items"] == 500


# ── Groups ──

class TestGroupsEndpoint:
    """GET /api/groups"""

    def test_get_groups(self, api_client):
        resp = api_client.get("/api/groups")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data
        assert len(data["groups"]) >= 1  # default group


# ── Import Files ──

class TestImportFilesEndpoint:
    """POST /api/items/import"""

    def test_import_files_endpoint(self, api_client, tmp_path):
        txt = tmp_path / "api_import.txt"
        txt.write_text("imported via api", encoding="utf-8")

        resp = api_client.post("/api/items/import", json={
            "files": [str(txt)],
            "source": "test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["imported"] == 1

    def test_import_nonexistent_files(self, api_client):
        resp = api_client.post("/api/items/import", json={
            "files": ["/nonexistent/file.txt"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 0
        assert data["skipped"] == 1
