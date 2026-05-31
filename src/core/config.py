"""Configuration management for eleven."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Optional


class StorageMode(str, Enum):
    """Storage mode for clipboard data."""
    VOLATILE = "volatile"      # 临时模式：重启清空
    PERSISTENT = "persistent"  # 持久模式：重启保留


# 配置文件路径
CONFIG_PATH = Path.home() / ".eleven" / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "storage_mode": StorageMode.VOLATILE.value,
    "max_items": 200,
    "max_image_size": [800, 800],
    "jpeg_quality": 85,
    "clipboard_enabled": True,  # 默认开启剪贴板监控
}

# 模式描述（用于 UI 提示）
MODE_DESCRIPTIONS = {
    StorageMode.VOLATILE: {
        "name": "临时模式",
        "desc": [
            "• 重启后数据清空",
            "• 性能更快",
            "• 无磁盘占用",
            "• 适合临时中转",
        ],
    },
    StorageMode.PERSISTENT: {
        "name": "持久模式",
        "desc": [
            "• 重启后数据保留",
            "• 可查看历史记录",
            "• 占用磁盘空间",
            "• 适合长期使用",
        ],
    },
}


class Config:
    """Application configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self._config = DEFAULT_CONFIG.copy()
        self._load()

    def _load(self) -> None:
        """Load config from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._config.update(saved)
        except Exception:
            pass  # 使用默认配置

    def _save(self) -> None:
        """Save config to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @property
    def storage_mode(self) -> StorageMode:
        """Get current storage mode."""
        return StorageMode(self._config["storage_mode"])

    @storage_mode.setter
    def storage_mode(self, mode: StorageMode) -> None:
        """Set storage mode."""
        self._config["storage_mode"] = mode.value
        self._save()

    @property
    def max_items(self) -> int:
        """Get max items limit."""
        return self._config["max_items"]

    @max_items.setter
    def max_items(self, value: int) -> None:
        """Set max items limit."""
        if not isinstance(value, int) or value < 10:
            raise ValueError("max_items must be an integer >= 10")
        if value > 10000:
            raise ValueError("max_items must be <= 10000")
        self._config["max_items"] = value
        self._save()

    @property
    def max_image_size(self) -> tuple[int, int]:
        """Get max image size."""
        size = self._config["max_image_size"]
        return (size[0], size[1])

    @property
    def jpeg_quality(self) -> int:
        """Get JPEG compression quality."""
        return self._config["jpeg_quality"]

    @property
    def clipboard_enabled(self) -> bool:
        """Whether clipboard monitoring is enabled (v3.0 Channel A)."""
        return self._config.get("clipboard_enabled", False)

    @clipboard_enabled.setter
    def clipboard_enabled(self, value: bool) -> None:
        self._config["clipboard_enabled"] = value
        self._save()

    # ── v4.0 悬浮球位置 ──

    def get_ball_position(self) -> tuple[int, int] | None:
        pos = self._config.get("ball_position")
        if pos and isinstance(pos, dict):
            return (pos.get("x", 0), pos.get("y", 0))
        return None

    def set_ball_position(self, x: int, y: int) -> None:
        self._config["ball_position"] = {"x": x, "y": y}
        self._save()

    def get_mode_description(self) -> dict:
        """Get description for current mode."""
        return MODE_DESCRIPTIONS[self.storage_mode]

    def get_mode_switch_description(self, target_mode: StorageMode) -> str:
        """Get description for switching to target mode."""
        info = MODE_DESCRIPTIONS[target_mode]
        lines = [info["name"], ""] + info["desc"]

        if target_mode == StorageMode.VOLATILE:
            lines.append("")
            lines.append("[!] 切换后将清空所有数据！")
        else:
            lines.append("")
            lines.append("[i] 切换后数据将保留")

        return "\n".join(lines)
