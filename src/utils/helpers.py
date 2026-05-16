"""Utility functions."""
from __future__ import annotations

import hashlib
from datetime import datetime


def truncate_text(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def format_timestamp(ts: str | datetime | None) -> str:
    """Format a timestamp for display."""
    if ts is None:
        return ""
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except ValueError:
            return ts
    now = datetime.utcnow()
    delta = now - ts
    if delta.total_seconds() < 60:
        return "刚刚"
    if delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() // 60)} 分钟前"
    if delta.days == 0:
        return ts.strftime("%H:%M")
    return ts.strftime("%m-%d %H:%M")
