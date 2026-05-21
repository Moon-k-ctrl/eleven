"""SQLite database wrapper for clipboard items."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from src.core.config import Config, StorageMode
from src.models.clipboard_item import ClipboardItem, ContentType, Source, Tag

# 默认数据库路径
DEFAULT_DB_PATH = Path.home() / ".eleven" / "data.db"


class Database:
    """SQLite storage backend with dual mode support."""

    def __init__(self, db_path: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()

        if db_path:
            self.db_path = db_path
        elif self.config.storage_mode == StorageMode.VOLATILE:
            self.db_path = ":memory:"
        else:
            self.db_path = DEFAULT_DB_PATH
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn_ref: Optional[sqlite3.Connection] = None
        self.init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        # 内存模式复用连接，持久模式每次新建
        if self.db_path == ":memory:":
            if self._conn_ref is None:
                self._conn_ref = sqlite3.connect(":memory:", check_same_thread=False)
                self._conn_ref.row_factory = sqlite3.Row
            conn = self._conn_ref
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS groups (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    color       TEXT DEFAULT '#4A90D9',
                    sort_order  INTEGER DEFAULT 0,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS clipboard_items (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_type   TEXT NOT NULL,
                    content_text   TEXT,
                    content_html   TEXT,
                    file_path      TEXT,
                    source_app     TEXT,
                    is_pinned      BOOLEAN DEFAULT 0,
                    is_favorite    BOOLEAN DEFAULT 0,
                    group_id       INTEGER,
                    thumbnail_path TEXT,
                    content_hash   TEXT,
                    sort_order     INTEGER DEFAULT 0,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_hash ON clipboard_items(content_hash);
                CREATE INDEX IF NOT EXISTS idx_created ON clipboard_items(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_group ON clipboard_items(group_id);
                CREATE INDEX IF NOT EXISTS idx_type_created ON clipboard_items(content_type, created_at DESC);

                CREATE TABLE IF NOT EXISTS tags (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,
                    color       TEXT DEFAULT '#4A90D9',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS item_tags (
                    item_id     INTEGER NOT NULL,
                    tag_id      INTEGER NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (item_id, tag_id),
                    FOREIGN KEY (item_id) REFERENCES clipboard_items(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id)  REFERENCES tags(id)            ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_item_tags_item ON item_tags(item_id);
                CREATE INDEX IF NOT EXISTS idx_item_tags_tag  ON item_tags(tag_id);
            """)
            # FTS5 全文搜索
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS clipboard_fts
                    USING fts5(content_text, content='clipboard_items', content_rowid='id')
                """)
            except sqlite3.OperationalError:
                pass  # FTS5 不可用时跳过

            # 插入默认分组
            conn.execute("""
                INSERT OR IGNORE INTO groups (id, name, color, sort_order)
                VALUES (1, '默认', '#4A90D9', 0)
            """)

            # 迁移：添加 category 列（兼容已有数据库）
            try:
                conn.execute("ALTER TABLE clipboard_items ADD COLUMN category TEXT DEFAULT 'DEFAULT'")
            except sqlite3.OperationalError:
                pass  # 列已存在
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_category ON clipboard_items(category, created_at DESC)"
            )

            # v3.0 迁移：添加 source, project, is_starred, metadata 列
            for col, default in [
                ("source", "clipboard"),
                ("project", "'default'"),
                ("is_starred", "0"),
                ("metadata", "NULL"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE clipboard_items ADD COLUMN {col} TEXT DEFAULT {default}")
                except sqlite3.OperationalError:
                    pass  # 列已存在

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_project ON clipboard_items(project, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_starred ON clipboard_items(is_starred, created_at DESC)"
            )

            # v3.0 项目空间表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,
                    icon        TEXT DEFAULT '📁',
                    color       TEXT DEFAULT '#4A90D9',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO projects (id, name) VALUES (1, 'default')
            """)

    def insert_item(self, item: ClipboardItem) -> int:
        """Insert a new clipboard item, return its id."""
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO clipboard_items
                   (content_type, content_text, content_html, file_path,
                    source_app, is_pinned, is_favorite, group_id,
                    thumbnail_path, content_hash, category,
                    source, project, is_starred, metadata,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.content_type.value, item.content_text, item.content_html,
                    item.file_path, item.source_app, item.is_pinned, item.is_favorite,
                    item.group_id, item.thumbnail_path, item.content_hash,
                    item.category or "DEFAULT",
                    item.source, item.project, item.is_starred, item.metadata,
                    now, now,
                ),
            )
            # 同步 FTS
            if item.content_text:
                try:
                    conn.execute(
                        "INSERT INTO clipboard_fts(rowid, content_text) VALUES (?, ?)",
                        (cur.lastrowid, item.content_text),
                    )
                except sqlite3.OperationalError:
                    pass
            return cur.lastrowid  # type: ignore

    def get_items(self, limit: int = 50, offset: int = 0,
                  pinned_first: bool = True) -> list[ClipboardItem]:
        """Fetch clipboard items, newest first (pinned on top)."""
        order = "is_pinned DESC, created_at DESC" if pinned_first else "created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM clipboard_items ORDER BY {order} LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        items = [self._row_to_item(r) for r in rows]
        self._attach_tags(items)
        return items

    def delete_item(self, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM clipboard_items WHERE id = ?", (item_id,))
            try:
                conn.execute("DELETE FROM clipboard_fts WHERE rowid = ?", (item_id,))
            except sqlite3.OperationalError:
                pass

    def toggle_pin(self, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE clipboard_items SET is_pinned = NOT is_pinned, updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), item_id),
            )

    def toggle_favorite(self, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE clipboard_items SET is_favorite = NOT is_favorite, updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), item_id),
            )

    def toggle_star(self, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE clipboard_items SET is_starred = NOT is_starred, updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), item_id),
            )

    def search(self, query: str, limit: int = 50) -> list[ClipboardItem]:
        """Full-text search."""
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    """SELECT c.* FROM clipboard_items c
                       JOIN clipboard_fts f ON c.id = f.rowid
                       WHERE clipboard_fts MATCH ?
                       ORDER BY rank LIMIT ?""",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                # FTS 不可用时 fallback 到 LIKE
                rows = conn.execute(
                    "SELECT * FROM clipboard_items WHERE content_text LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{query}%", limit),
                ).fetchall()
        items = [self._row_to_item(r) for r in rows]
        self._attach_tags(items)
        return items

    def exists_hash(self, content_hash: str) -> bool:
        """Check if a hash already exists (dedup)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM clipboard_items WHERE content_hash = ? LIMIT 1",
                (content_hash,),
            ).fetchone()
        return row is not None

    def count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM clipboard_items").fetchone()
        return row[0]  # type: ignore

    def delete_oldest_non_pinned(self, count: int) -> None:
        """Delete the oldest non-pinned items."""
        with self._conn() as conn:
            # 获取要删除的行 ID
            rows = conn.execute(
                """SELECT id FROM clipboard_items
                   WHERE is_pinned = 0
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (count,),
            ).fetchall()
            ids = [r["id"] for r in rows]
            if ids:
                placeholders = ",".join("?" * len(ids))
                conn.execute(
                    f"DELETE FROM clipboard_items WHERE id IN ({placeholders})", ids
                )
                try:
                    conn.execute(
                        f"DELETE FROM clipboard_fts WHERE rowid IN ({placeholders})", ids
                    )
                except sqlite3.OperationalError:
                    pass

    def clear_all(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM clipboard_items")
            try:
                conn.execute("DELETE FROM clipboard_fts")
            except sqlite3.OperationalError:
                pass

    # ── 分组操作 ──

    def get_groups(self) -> list[dict]:
        """Get all groups."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM groups ORDER BY sort_order, id"
            ).fetchall()
        return [dict(r) for r in rows]

    def create_group(self, name: str, color: str = "#4A90D9") -> int:
        """Create a new group, return its id."""
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO groups (name, color) VALUES (?, ?)",
                (name, color),
            )
            return cur.lastrowid  # type: ignore

    def delete_group(self, group_id: int) -> None:
        """Delete a group. Items in this group will have group_id set to NULL."""
        with self._conn() as conn:
            conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))

    def move_to_group(self, item_id: int, group_id: Optional[int]) -> None:
        """Move an item to a group (or None for ungrouped)."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE clipboard_items SET group_id = ?, updated_at = ? WHERE id = ?",
                (group_id, datetime.utcnow().isoformat(), item_id),
            )

    def get_items_by_group(self, group_id: Optional[int], limit: int = 50,
                           offset: int = 0) -> list[ClipboardItem]:
        """Get items filtered by group."""
        with self._conn() as conn:
            if group_id is None:
                rows = conn.execute(
                    """SELECT * FROM clipboard_items
                       WHERE group_id IS NULL
                       ORDER BY is_pinned DESC, created_at DESC
                       LIMIT ? OFFSET ?""",
                    (limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM clipboard_items
                       WHERE group_id = ?
                       ORDER BY is_pinned DESC, created_at DESC
                       LIMIT ? OFFSET ?""",
                    (group_id, limit, offset),
                ).fetchall()
        items = [self._row_to_item(r) for r in rows]
        self._attach_tags(items)
        return items

    def get_item_by_id(self, item_id: int) -> Optional[ClipboardItem]:
        """Get a single item by its id."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM clipboard_items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            return None
        item = self._row_to_item(row)
        self._attach_tags([item])
        return item

    def get_items_cursor(self, last_id: Optional[int] = None,
                         limit: int = 50) -> list[ClipboardItem]:
        """Get items using cursor-based pagination for better performance."""
        with self._conn() as conn:
            if last_id is None:
                rows = conn.execute(
                    """SELECT * FROM clipboard_items
                       ORDER BY is_pinned DESC, created_at DESC, id DESC
                       LIMIT ?""",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM clipboard_items
                       WHERE id < ?
                       ORDER BY is_pinned DESC, created_at DESC, id DESC
                       LIMIT ?""",
                    (last_id, limit),
                ).fetchall()
        items = [self._row_to_item(r) for r in rows]
        self._attach_tags(items)
        return items

    def cleanup_orphan_images(self, images_dir: Path) -> int:
        """Clean up image files that are no longer referenced in the database.

        Returns the number of files deleted.
        """
        if not images_dir.exists():
            return 0

        # 获取数据库中所有图片路径
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT file_path FROM clipboard_items WHERE file_path IS NOT NULL"
            ).fetchall()
            db_paths = {r["file_path"] for r in rows}

            # 获取缩略图路径
            rows = conn.execute(
                "SELECT DISTINCT thumbnail_path FROM clipboard_items WHERE thumbnail_path IS NOT NULL"
            ).fetchall()
            db_paths.update(r["thumbnail_path"] for r in rows)

        # 扫描目录中的文件
        deleted = 0
        for file_path in images_dir.glob("*.png"):
            if str(file_path) not in db_paths:
                try:
                    file_path.unlink()
                    deleted += 1
                except OSError:
                    pass

        return deleted

    def update_sort_order(self, item_id: int, sort_order: int) -> None:
        """Update the sort order of an item."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE clipboard_items SET sort_order = ?, updated_at = ? WHERE id = ?",
                (sort_order, datetime.utcnow().isoformat(), item_id),
            )

    def merge_items(self, item_ids: list[int], separator: str = "\n---\n") -> Optional[int]:
        """Merge multiple items into one. Returns the new item's id, or None on failure."""
        if len(item_ids) < 2:
            return None

        with self._conn() as conn:
            # 获取所有要合并的条目
            placeholders = ",".join("?" * len(item_ids))
            rows = conn.execute(
                f"SELECT * FROM clipboard_items WHERE id IN ({placeholders}) ORDER BY created_at",
                item_ids,
            ).fetchall()

            if len(rows) < 2:
                return None

            # 合并文本内容
            texts = []
            htmls = []
            for row in rows:
                if row["content_text"]:
                    texts.append(row["content_text"])
                if row["content_html"]:
                    htmls.append(row["content_html"])

            merged_text = separator.join(texts) if texts else None
            merged_html = separator.join(htmls) if htmls else None

            # 计算哈希
            import hashlib
            hash_content = (merged_text or "") + (merged_html or "")
            content_hash = hashlib.sha256(hash_content.encode("utf-8")).hexdigest()

            # 创建新条目
            now = datetime.utcnow().isoformat()
            cur = conn.execute(
                """INSERT INTO clipboard_items
                   (content_type, content_text, content_html, content_hash,
                    is_pinned, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("TEXT" if merged_text else "HTML",
                 merged_text, merged_html, content_hash,
                 0, now, now),
            )
            new_id = cur.lastrowid

            # 同步 FTS
            if merged_text:
                try:
                    conn.execute(
                        "INSERT INTO clipboard_fts(rowid, content_text) VALUES (?, ?)",
                        (new_id, merged_text),
                    )
                except sqlite3.OperationalError:
                    pass

            return new_id

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> ClipboardItem:
        keys = row.keys()
        return ClipboardItem(
            id=row["id"],
            content_type=ContentType(row["content_type"]),
            content_text=row["content_text"],
            content_html=row["content_html"],
            file_path=row["file_path"],
            source_app=row["source_app"],
            is_pinned=bool(row["is_pinned"]),
            is_favorite=bool(row["is_favorite"]),
            group_id=row["group_id"],
            thumbnail_path=row["thumbnail_path"],
            content_hash=row["content_hash"],
            category=row["category"] if "category" in keys else None,
            source=row["source"] if "source" in keys else Source.CLIPBOARD.value,
            project=row["project"] if "project" in keys else "default",
            is_starred=bool(int(row["is_starred"])) if "is_starred" in keys and row["is_starred"] is not None else False,
            metadata=row["metadata"] if "metadata" in keys else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _attach_tags(self, items: list[ClipboardItem]) -> None:
        """Bulk-load tags and attach to items (avoids N+1 queries)."""
        if not items:
            return
        tag_map = self.get_tags_for_items([i.id for i in items if i.id is not None])
        for item in items:
            item.tags = tag_map.get(item.id, [])

    # ── 标签操作 ──

    def get_all_tags(self) -> list[Tag]:
        """Get all tags ordered by name."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tags ORDER BY name"
            ).fetchall()
        return [Tag(id=r["id"], name=r["name"], color=r["color"],
                     created_at=r["created_at"]) for r in rows]

    def create_tag(self, name: str, color: str = "#4A90D9") -> int:
        """Create a new tag, return its id. Raises ValueError on duplicate name."""
        with self._conn() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO tags (name, color) VALUES (?, ?)",
                    (name, color),
                )
                return cur.lastrowid  # type: ignore
            except sqlite3.IntegrityError:
                raise ValueError(f"Tag '{name}' already exists")

    def delete_tag(self, tag_id: int) -> None:
        """Delete a tag (CASCADE removes junction rows)."""
        with self._conn() as conn:
            conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))

    def update_tag(self, tag_id: int, name: str, color: str) -> None:
        """Update tag name and color."""
        with self._conn() as conn:
            try:
                conn.execute(
                    "UPDATE tags SET name = ?, color = ? WHERE id = ?",
                    (name, color, tag_id),
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"Tag '{name}' already exists")

    def tag_count(self) -> int:
        """Count total tags."""
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM tags").fetchone()
        return row[0]  # type: ignore

    def add_item_tag(self, item_id: int, tag_id: int) -> None:
        """Add a tag to an item (ignore if already exists)."""
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
                (item_id, tag_id),
            )

    def remove_item_tag(self, item_id: int, tag_id: int) -> None:
        """Remove a tag from an item."""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM item_tags WHERE item_id = ? AND tag_id = ?",
                (item_id, tag_id),
            )

    def get_item_tags(self, item_id: int) -> list[Tag]:
        """Get all tags for one item."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT t.* FROM tags t
                   JOIN item_tags it ON t.id = it.tag_id
                   WHERE it.item_id = ?
                   ORDER BY t.name""",
                (item_id,),
            ).fetchall()
        return [Tag(id=r["id"], name=r["name"], color=r["color"],
                     created_at=r["created_at"]) for r in rows]

    def get_tags_for_items(self, item_ids: list[int]) -> dict[int, list[Tag]]:
        """Bulk fetch tags for multiple items. Returns {item_id: [Tag, ...]}."""
        if not item_ids:
            return {}
        placeholders = ",".join("?" * len(item_ids))
        with self._conn() as conn:
            rows = conn.execute(
                f"""SELECT it.item_id, t.id, t.name, t.color, t.created_at
                    FROM item_tags it
                    JOIN tags t ON t.id = it.tag_id
                    WHERE it.item_id IN ({placeholders})
                    ORDER BY t.name""",
                item_ids,
            ).fetchall()
        result: dict[int, list[Tag]] = {}
        for r in rows:
            tag = Tag(id=r["id"], name=r["name"], color=r["color"],
                       created_at=r["created_at"])
            result.setdefault(r["item_id"], []).append(tag)
        return result

    def get_items_by_tag(self, tag_id: int, limit: int = 50,
                         offset: int = 0) -> list[ClipboardItem]:
        """Get items filtered by tag."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT c.* FROM clipboard_items c
                   JOIN item_tags it ON c.id = it.item_id
                   WHERE it.tag_id = ?
                   ORDER BY c.is_pinned DESC, c.created_at DESC
                   LIMIT ? OFFSET ?""",
                (tag_id, limit, offset),
            ).fetchall()
        items = [self._row_to_item(r) for r in rows]
        self._attach_tags(items)
        return items

    # ── 项目空间操作 ──

    def get_projects(self) -> list[dict]:
        """Get all projects."""
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def create_project(self, name: str, icon: str = "📁", color: str = "#4A90D9") -> int:
        """Create a new project, return its id."""
        with self._conn() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO projects (name, icon, color) VALUES (?, ?, ?)",
                    (name, icon, color),
                )
                return cur.lastrowid  # type: ignore
            except sqlite3.IntegrityError:
                raise ValueError(f"Project '{name}' already exists")

    def delete_project(self, project_id: int) -> None:
        """Delete a project (items keep their project string)."""
        with self._conn() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def search_with_filters(self, query: Optional[str] = None,
                            tag_ids: Optional[list[int]] = None,
                            group_id: Optional[int] = None,
                            category: Optional[str] = None,
                            project: Optional[str] = None,
                            limit: int = 50) -> list[ClipboardItem]:
        """Combined search + tag + group + category filter."""
        conditions: list[str] = []
        params: list = []

        # FTS or LIKE search
        use_fts = False
        if query:
            try:
                with self._conn() as conn:
                    conn.execute("SELECT 1 FROM clipboard_fts LIMIT 0")
                use_fts = True
            except sqlite3.OperationalError:
                use_fts = False

        if use_fts and query:
            base = """SELECT c.* FROM clipboard_items c
                      JOIN clipboard_fts f ON c.id = f.rowid"""
            conditions.append("clipboard_fts MATCH ?")
            params.append(query)
        else:
            base = "SELECT c.* FROM clipboard_items c"
            if query:
                conditions.append("c.content_text LIKE ?")
                params.append(f"%{query}%")

        # Tag filter: item must have ALL specified tags
        if tag_ids:
            for tag_id in tag_ids:
                base += f" JOIN item_tags it{tag_id} ON c.id = it{tag_id}.item_id"
                conditions.append(f"it{tag_id}.tag_id = ?")
                params.append(tag_id)

        # Group filter
        if group_id is not None:
            conditions.append("c.group_id = ?")
            params.append(group_id)

        # Category filter
        if category and category != "ALL":
            conditions.append("c.category = ?")
            params.append(category)

        # Project filter
        if project and project != "all":
            conditions.append("c.project = ?")
            params.append(project)

        where = " AND ".join(conditions) if conditions else "1=1"
        order = "ORDER BY rank" if (use_fts and query) else "ORDER BY c.is_pinned DESC, c.created_at DESC"

        sql = f"{base} WHERE {where} {order} LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [self._row_to_item(r) for r in rows]
        self._attach_tags(items)
        return items
