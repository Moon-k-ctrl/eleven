"""HTTP/WebSocket server bridging Python backend to Electron UI."""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from typing import Optional

import re

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import uvicorn

from src.core.clipboard_listener import set_clipboard_text, set_clipboard_files
from src.core.clipboard_manager import ClipboardManager
from src.core.config import Config, StorageMode
from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType, Tag

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eleven")

# ── 全局状态 ──
config = Config()
db = Database(config=config)
manager = ClipboardManager(db=db, config=config)

# WebSocket 连接池
ws_clients: set[WebSocket] = set()


# ── Pydantic 模型 ──

class ConfigUpdate(BaseModel):
    storage_mode: Optional[str] = None
    max_items: Optional[int] = None


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class TagCreate(BaseModel):
    name: str
    color: str = "#4A90D9"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Tag name cannot be empty")
        if len(v) > 50:
            raise ValueError("Tag name must be 50 characters or fewer")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not _HEX_COLOR_RE.fullmatch(v):
            raise ValueError("Color must be a hex color like #4A90D9")
        return v


class FileImport(BaseModel):
    files: list[str]
    source: str = "context-menu"
    project: str = "default"
    metadata: Optional[dict] = None


class ProjectCreate(BaseModel):
    name: str
    icon: str = "📁"
    color: str = "#4A90D9"


class TextImport(BaseModel):
    content_text: str
    content_html: Optional[str] = None
    source: str = "hotkey"
    project: str = "default"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Tag name cannot be empty")
        if len(v) > 50:
            raise ValueError("Tag name must be 50 characters or fewer")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not _HEX_COLOR_RE.fullmatch(v):
            raise ValueError("Color must be a hex color like #4A90D9")
        return v


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: Optional[str] = None


class ItemTagAction(BaseModel):
    tag_id: int


class ItemResponse(BaseModel):
    id: int
    content_type: str
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    file_path: Optional[str] = None
    source_app: Optional[str] = None
    is_pinned: bool = False
    is_favorite: bool = False
    group_id: Optional[int] = None
    thumbnail_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def item_to_dict(item: "ClipboardItem") -> dict:
    """Convert ClipboardItem to dict for JSON serialization."""
    return {
        "id": item.id,
        "content_type": item.content_type.value if hasattr(item.content_type, 'value') else item.content_type,
        "content_text": item.content_text,
        "content_html": item.content_html,
        "file_path": item.file_path,
        "source_app": item.source_app,
        "is_pinned": item.is_pinned,
        "is_favorite": item.is_favorite,
        "group_id": item.group_id,
        "thumbnail_path": item.thumbnail_path,
        "category": item.category,
        "source": item.source,
        "project": item.project,
        "is_starred": item.is_starred,
        "metadata": item.metadata,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in (item.tags or [])],
        "created_at": item.created_at.isoformat() if hasattr(item.created_at, 'isoformat') else str(item.created_at) if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if hasattr(item.updated_at, 'isoformat') else str(item.updated_at) if item.updated_at else None,
    }


# ── 广播给所有 WebSocket 客户端 ──

async def broadcast(event: str, data: dict) -> None:
    """Send event to all connected WebSocket clients."""
    message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
    dead: list[WebSocket] = []
    for ws in ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.discard(ws)


# ── 剪贴板变化回调 ──

def on_items_changed() -> None:
    """Called by ClipboardManager when items change. Schedule async broadcast."""
    count = manager.get_count()
    loop = getattr(on_items_changed, '_loop', None)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast("items-changed", {"count": count}),
            loop,
        )


# ── FastAPI 应用 ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # 启动剪贴板监听
    on_items_changed._loop = asyncio.get_event_loop()
    manager.add_callback(on_items_changed)
    manager.start()
    logger.info("Clipboard monitoring started")

    # 发送初始状态
    await broadcast("items-changed", {"count": manager.get_count()})

    yield

    # 关闭
    manager.stop()
    logger.info("Clipboard monitoring stopped")


app = FastAPI(title="eleven", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST API ──

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "count": manager.get_count(),
        "max_items": manager.get_max_items(),
        "storage_mode": config.storage_mode.value,
    }


@app.get("/api/items")
def get_items(limit: int = 50, cursor: Optional[int] = None,
              tag_id: Optional[int] = None, q: Optional[str] = None,
              category: Optional[str] = None, group_id: Optional[int] = None,
              project: Optional[str] = None):
    if tag_id is not None or q is not None or category is not None or group_id is not None or project is not None:
        tag_ids = [tag_id] if tag_id is not None else None
        items = manager.search_with_filters(
            query=q, tag_ids=tag_ids, group_id=group_id,
            category=category, project=project, limit=limit,
        )
        return {"items": [item_to_dict(i) for i in items]}
    items = db.get_items_cursor(last_id=cursor, limit=limit)
    return {
        "items": [item_to_dict(i) for i in items],
        "has_more": len(items) == limit,
    }


@app.get("/api/items/search")
def search_items(q: str, limit: int = 50):
    items = manager.search(q)
    return {
        "items": [item_to_dict(i) for i in items[:limit]],
    }


@app.post("/api/items/{item_id}/copy")
def copy_item(item_id: int):
    # 找到指定 ID 的项目
    all_items = db.get_items(limit=200, offset=0)
    target = None
    for item in all_items:
        if item.id == item_id:
            target = item
            break
    if not target:
        raise HTTPException(status_code=404, detail="Item not found")
    manager.copy_to_clipboard(target)
    return {"ok": True}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    manager.delete_item(item_id)
    return {"ok": True}


@app.post("/api/items/{item_id}/pin")
def pin_item(item_id: int):
    manager.toggle_pin(item_id)
    return {"ok": True}


@app.post("/api/items/{item_id}/favorite")
def favorite_item(item_id: int):
    manager.toggle_favorite(item_id)
    return {"ok": True}


@app.post("/api/items/{item_id}/star")
def star_item(item_id: int):
    manager.toggle_star(item_id)
    return {"ok": True}


@app.post("/api/items/batch-delete")
def batch_delete(body: dict):
    item_ids = body.get("item_ids", [])
    for item_id in item_ids:
        manager.delete_item(item_id)
    return {"ok": True, "deleted": len(item_ids)}


@app.post("/api/items/paste")
def paste_from_clipboard():
    """Read system clipboard and add as new item."""
    added = manager.paste_from_clipboard()
    return {"ok": added}


@app.post("/api/items/merge")
def merge_items(body: dict):
    item_ids = body.get("item_ids", [])
    if len(item_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 items to merge")
    ok = manager.merge_items(item_ids)
    return {"ok": ok}


@app.post("/api/items/clear")
def clear_items():
    manager.clear_all()
    return {"ok": True}


@app.post("/api/items/import")
def import_files(body: FileImport):
    """Import files via active delivery channel (context-menu, drag-drop, hotkey, etc.)."""
    imported, skipped = manager.import_files(
        body.files, source=body.source, project=body.project, metadata=body.metadata,
    )
    return {"ok": True, "imported": imported, "skipped": skipped}


@app.post("/api/items/import-text")
def import_text(body: TextImport):
    """Import text content directly (e.g., from hotkey capture)."""
    content_hash = ClipboardItem.compute_hash(body.content_text)
    if db.exists_hash(content_hash):
        return {"ok": True, "imported": 0, "skipped": 1}
    item = ClipboardItem(
        content_type=ContentType.HTML if body.content_html else ContentType.TEXT,
        content_text=body.content_text,
        content_html=body.content_html,
        content_hash=content_hash,
        source=body.source,
        project=body.project,
    )
    from src.models.clipboard_item import classify_item
    item.category = classify_item(item)
    db.insert_item(item)
    return {"ok": True, "imported": 1, "skipped": 0}


@app.get("/api/config")
def get_config():
    return {
        "storage_mode": config.storage_mode.value,
        "max_items": config.max_items,
        "max_image_size": list(config.max_image_size),
        "jpeg_quality": config.jpeg_quality,
    }


@app.post("/api/config")
def update_config(body: ConfigUpdate):
    if body.storage_mode is not None:
        config.storage_mode = StorageMode(body.storage_mode)
    return get_config()


@app.post("/api/config/clipboard-enabled")
def toggle_clipboard_monitoring(body: dict):
    """Toggle clipboard monitoring on/off at runtime."""
    enabled = body.get("enabled", not config.clipboard_enabled)
    config.clipboard_enabled = enabled
    if enabled:
        manager.start()
    else:
        manager.stop()
    return {"ok": True, "clipboard_enabled": config.clipboard_enabled}


# ── Groups ──

@app.get("/api/groups")
def get_groups():
    groups = db.get_groups()
    return {"groups": groups}


# ── Projects (v3.0) ──

@app.get("/api/projects")
def get_projects():
    return {"projects": db.get_projects()}


@app.post("/api/projects")
def create_project(body: ProjectCreate):
    try:
        pid = db.create_project(body.name, body.icon, body.color)
        return {"ok": True, "id": pid}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/projects/{project_id}")
def delete_project_endpoint(project_id: int):
    db.delete_project(project_id)
    return {"ok": True}


# ── Tags ──

def _tag_to_dict(tag: "Tag") -> dict:
    return {
        "id": tag.id,
        "name": tag.name,
        "color": tag.color,
        "created_at": tag.created_at.isoformat() if hasattr(tag.created_at, 'isoformat') else str(tag.created_at) if tag.created_at else None,
    }


@app.get("/api/tags")
def get_tags():
    tags = manager.get_all_tags()
    return {"tags": [_tag_to_dict(t) for t in tags]}


@app.post("/api/tags")
def create_tag(body: TagCreate):
    try:
        tag_id = manager.create_tag(body.name, body.color)
        return {"ok": True, "id": tag_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/tags/{tag_id}")
def update_tag(tag_id: int, body: TagUpdate):
    # Merge partial update with existing tag
    existing = None
    for t in manager.get_all_tags():
        if t.id == tag_id:
            existing = t
            break
    if not existing:
        raise HTTPException(status_code=404, detail="Tag not found")
    try:
        manager.update_tag(
            tag_id,
            body.name if body.name is not None else existing.name,
            body.color if body.color is not None else existing.color,
        )
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: int):
    manager.delete_tag(tag_id)
    return {"ok": True}


@app.get("/api/items/{item_id}/tags")
def get_item_tags(item_id: int):
    tags = db.get_item_tags(item_id)
    return {"tags": [_tag_to_dict(t) for t in tags]}


@app.post("/api/items/{item_id}/tags")
def add_item_tag(item_id: int, body: ItemTagAction):
    try:
        manager.add_tag_to_item(item_id, body.tag_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/items/{item_id}/tags/{tag_id}")
def remove_item_tag(item_id: int, tag_id: int):
    manager.remove_tag_from_item(item_id, tag_id)
    return {"ok": True}


# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    logger.info(f"WebSocket client connected ({len(ws_clients)} total)")
    try:
        # 发送当前状态
        await ws.send_text(json.dumps({
            "event": "items-changed",
            "data": {"count": manager.get_count()},
        }, ensure_ascii=False))

        # 保持连接，等待客户端消息或断开
        while True:
            data = await ws.receive_text()
            # 处理客户端命令
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "ping":
                    await ws.send_text(json.dumps({"event": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(ws)
        logger.info(f"WebSocket client disconnected ({len(ws_clients)} total)")


# ── 入口 ──

def run_server(host: str = "127.0.0.1", port: int = 8199):
    """Run the server (blocking)."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
