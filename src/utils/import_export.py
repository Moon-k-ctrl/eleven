"""Data import/export utilities for eleven."""
from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from src.core.database import Database
from src.models.clipboard_item import ClipboardItem, ContentType, Tag


def export_to_json(db: Database, file_path: Path,
                   include_images: bool = False) -> int:
    """Export clipboard items to JSON file.

    Returns the number of items exported.
    """
    items = db.get_items(limit=10000)

    data = []
    for item in items:
        entry = {
            "id": item.id,
            "content_type": item.content_type.value,
            "content_text": item.content_text,
            "content_html": item.content_html,
            "is_pinned": item.is_pinned,
            "is_favorite": item.is_favorite,
            "created_at": (item.created_at.isoformat() if isinstance(item.created_at, datetime) else item.created_at) if item.created_at else None,
            "tags": [{"name": t.name, "color": t.color} for t in (item.tags or [])],
        }

        # 图片：导出路径或 base64
        if item.content_type == ContentType.IMAGE:
            if include_images and item.file_path:
                import base64
                try:
                    with open(item.file_path, "rb") as f:
                        entry["image_data"] = base64.b64encode(f.read()).decode("ascii")
                except OSError:
                    pass
            entry["file_path"] = item.file_path
            entry["thumbnail_path"] = item.thumbnail_path

        data.append(entry)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return len(data)


def import_from_json(db: Database, file_path: Path,
                     skip_duplicates: bool = True) -> int:
    """Import clipboard items from JSON file.

    Returns the number of items imported.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    imported = 0
    existing_tags: dict[str, int] = {t.name: t.id for t in db.get_all_tags()}  # type: ignore[misc]
    for entry in data:
        try:
            content_type = ContentType(entry.get("content_type", "TEXT"))
        except ValueError:
            continue  # skip entries with invalid content type
        content_text = entry.get("content_text")
        content_html = entry.get("content_html")

        # 计算哈希用于去重
        hash_content = (content_text or "") + (content_html or "")
        content_hash = ClipboardItem.compute_hash(hash_content) if hash_content else None

        # 跳过重复
        if skip_duplicates and content_hash and db.exists_hash(content_hash):
            continue

        # 处理图片数据
        file_path_img = entry.get("file_path")
        thumbnail_path = entry.get("thumbnail_path")

        if content_type == ContentType.IMAGE and entry.get("image_data"):
            import base64
            image_data = base64.b64decode(entry["image_data"])
            # 保存到图片目录
            from src.core.clipboard_manager import IMAGES_DIR
            IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            import uuid
            file_name = f"{uuid.uuid4().hex}.png"
            file_path_img = str(IMAGES_DIR / file_name)
            with open(file_path_img, "wb") as f:
                f.write(image_data)

        item = ClipboardItem(
            content_type=content_type,
            content_text=content_text,
            content_html=content_html,
            file_path=file_path_img,
            thumbnail_path=thumbnail_path,
            content_hash=content_hash,
        )

        item_id = db.insert_item(item)
        imported += 1

        # 处理标签
        tags_data = entry.get("tags")
        if tags_data:
            for tag_dict in tags_data:
                tag_name = tag_dict.get("name")
                tag_color = tag_dict.get("color", "#4A90D9")
                if not tag_name:
                    continue
                tag_id = existing_tags.get(tag_name)
                if tag_id is None:
                    try:
                        tag_id = db.create_tag(tag_name, tag_color)
                        existing_tags[tag_name] = tag_id
                    except ValueError:
                        continue
                db.add_item_tag(item_id, tag_id)

    return imported


def export_to_csv(db: Database, file_path: Path) -> int:
    """Export clipboard items to CSV file.

    Returns the number of items exported.
    """
    items = db.get_items(limit=10000)

    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "类型", "内容", "HTML", "置顶", "收藏", "创建时间", "标签"
        ])

        for item in items:
            tag_names = ";".join(t.name for t in (item.tags or []))
            writer.writerow([
                item.id,
                item.content_type.value,
                (item.content_text or "")[:500],  # 截断过长内容
                (item.content_html or "")[:500],
                "是" if item.is_pinned else "否",
                "是" if item.is_favorite else "否",
                (item.created_at.isoformat() if isinstance(item.created_at, datetime) else str(item.created_at)) if item.created_at else "",
                tag_names,
            ])

    return len(items)


def import_from_csv(db: Database, file_path: Path,
                    skip_duplicates: bool = True) -> int:
    """Import clipboard items from CSV file.

    Returns the number of items imported.
    """
    imported = 0
    existing_tags: dict[str, int] = {t.name: t.id for t in db.get_all_tags()}  # type: ignore[misc]

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                content_type = ContentType(row.get("类型", "TEXT"))
            except ValueError:
                continue  # skip entries with invalid content type
            content_text = row.get("内容")
            content_html = row.get("HTML")

            # 计算哈希
            hash_content = (content_text or "") + (content_html or "")
            content_hash = ClipboardItem.compute_hash(hash_content) if hash_content else None

            if skip_duplicates and content_hash and db.exists_hash(content_hash):
                continue

            item = ClipboardItem(
                content_type=content_type,
                content_text=content_text,
                content_html=content_html,
                content_hash=content_hash,
            )

            item_id = db.insert_item(item)
            imported += 1

            # 处理标签
            tags_str = row.get("标签", "")
            if tags_str:
                for tag_name in tags_str.split(";"):
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue
                    tag_id = existing_tags.get(tag_name)
                    if tag_id is None:
                        try:
                            tag_id = db.create_tag(tag_name)
                            existing_tags[tag_name] = tag_id
                        except ValueError:
                            continue
                    db.add_item_tag(item_id, tag_id)

    return imported


def _unique_path(target: Path) -> Path:
    """Return a unique file path by appending (1), (2), etc. if needed."""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _is_markdown(text: str) -> bool:
    """Heuristic: detect if text looks like Markdown."""
    patterns = [
        r"^#{1,6}\s",
        r"\*\*.*\*\*",
        r"\[.*\]\(.*\)",
        r"```[\s\S]*```",
        r"^\|.*\|.*\|",
        r"^\s*[-*+]\s",
        r"^>\s",
    ]
    match_count = sum(1 for p in patterns if re.search(p, text, re.MULTILINE))
    return match_count >= 2


def export_selected_items(items: list[ClipboardItem], target_dir: Path,
                          progress_callback: Optional[Callable[[int], None]] = None
                          ) -> tuple[int, list[str]]:
    """Export selected items to target_dir.

    Returns (success_count, error_messages).
    """
    export_dir = target_dir / f"拾遗导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    export_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    errors: list[str] = []

    for idx, item in enumerate(items):
        try:
            if item.content_type == ContentType.TEXT and item.content_text:
                ext = ".md" if _is_markdown(item.content_text) else ".txt"
                file_path = _unique_path(export_dir / f"{item.id}{ext}")
                file_path.write_text(item.content_text, encoding="utf-8")

            elif item.content_type == ContentType.HTML and item.content_html:
                file_path = _unique_path(export_dir / f"{item.id}.html")
                file_path.write_text(item.content_html, encoding="utf-8")

            elif item.content_type == ContentType.IMAGE and item.file_path:
                src = Path(item.file_path)
                if src.exists():
                    file_path = _unique_path(export_dir / src.name)
                    shutil.copy2(str(src), str(file_path))
                else:
                    errors.append(f"图片文件不存在: {item.file_path}")
                    continue

            elif item.content_type == ContentType.FILES and item.content_text:
                files = item.content_text.split("\n")
                for f in files:
                    f = f.strip()
                    if not f:
                        continue
                    src = Path(f)
                    if src.exists():
                        file_path = _unique_path(export_dir / src.name)
                        shutil.copy2(str(src), str(file_path))
                    else:
                        errors.append(f"文件不存在: {f}")
                        continue

            else:
                errors.append(f"不支持的内容类型: {item.content_type}")
                continue

            success += 1
        except Exception as e:
            errors.append(f"导出失败 (item {item.id}): {e}")

        if progress_callback:
            progress_callback(idx + 1)

    return success, errors
