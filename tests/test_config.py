"""Tests for Config module."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.config import Config, StorageMode


class TestConfigDefaults:
    """Verify default configuration values."""

    def test_default_storage_mode(self, tmp_config: Config):
        assert tmp_config.storage_mode == StorageMode.VOLATILE

    def test_default_max_items(self, tmp_config: Config):
        assert tmp_config.max_items == 200

    def test_default_max_image_size(self, tmp_config: Config):
        assert tmp_config.max_image_size == (800, 800)

    def test_default_jpeg_quality(self, tmp_config: Config):
        assert tmp_config.jpeg_quality == 85

    def test_default_clipboard_enabled(self, tmp_config: Config):
        assert tmp_config.clipboard_enabled is False


class TestConfigPersistence:
    """Verify save/load round-trip."""

    def test_save_and_reload_storage_mode(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        c1 = Config(config_path=config_path)
        c1.storage_mode = StorageMode.PERSISTENT

        c2 = Config(config_path=config_path)
        assert c2.storage_mode == StorageMode.PERSISTENT

    def test_save_and_reload_clipboard_enabled(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        c1 = Config(config_path=config_path)
        c1.clipboard_enabled = True

        c2 = Config(config_path=config_path)
        assert c2.clipboard_enabled is True

    def test_save_and_reload_ball_position(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        c1 = Config(config_path=config_path)
        c1.set_ball_position(120, 340)

        c2 = Config(config_path=config_path)
        assert c2.get_ball_position() == (120, 340)

    def test_ball_position_default_none(self, tmp_config: Config):
        assert tmp_config.get_ball_position() is None


class TestConfigEdgeCases:
    """Edge cases and error handling."""

    def test_invalid_json_file_uses_defaults(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("NOT VALID JSON {{{", encoding="utf-8")

        c = Config(config_path=config_path)
        assert c.storage_mode == StorageMode.VOLATILE
        assert c.max_items == 200

    def test_missing_file_uses_defaults(self, tmp_path: Path):
        config_path = tmp_path / "nonexistent" / "config.json"
        c = Config(config_path=config_path)
        assert c.storage_mode == StorageMode.VOLATILE

    def test_partial_config_merges_with_defaults(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps({"max_items": 500}),
            encoding="utf-8",
        )
        c = Config(config_path=config_path)
        assert c.max_items == 500
        assert c.storage_mode == StorageMode.VOLATILE  # default preserved


class TestConfigModeDescriptions:
    """Mode description helpers."""

    def test_get_mode_description_returns_dict(self, tmp_config: Config):
        desc = tmp_config.get_mode_description()
        assert "name" in desc
        assert "desc" in desc

    def test_get_mode_switch_description_contains_warning(self, tmp_config: Config):
        text = tmp_config.get_mode_switch_description(StorageMode.VOLATILE)
        assert "清空" in text or "切换" in text

    def test_get_mode_switch_description_persistent(self, tmp_config: Config):
        text = tmp_config.get_mode_switch_description(StorageMode.PERSISTENT)
        assert "保留" in text or "持久" in text
