"""eleven - Entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.core.clipboard_manager import ClipboardManager
from src.core.config import Config, StorageMode
from src.ui.floating_panel import FloatingPanel
from src.ui.tray_icon import TrayIcon
from src.utils.import_export import (
    export_to_json, import_from_json,
    export_to_csv, import_from_csv,
)


def main() -> None:
    # 高 DPI 适配
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭面板不退出程序

    # 加载配置
    config = Config()

    manager = ClipboardManager(config=config)
    manager.start()

    panel = FloatingPanel(manager)

    # 系统托盘图标
    tray = TrayIcon(config=config)
    tray.toggle_panel.connect(panel.toggle)
    tray.quit_app.connect(app.quit)

    # 存储模式切换：需要重启程序
    def on_storage_mode_changed(mode: StorageMode):
        QMessageBox.information(
            None,
            "存储模式已切换",
            f"已切换到{'临时' if mode == StorageMode.VOLATILE else '持久'}模式。\n\n请重启程序使更改生效。",
        )

    tray.storage_mode_changed.connect(on_storage_mode_changed)

    # 导入导出功能
    def do_export_json():
        path, _ = QFileDialog.getSaveFileName(
            None, "导出 JSON", "clipboard_export.json",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            count = export_to_json(manager.db, Path(path))
            tray.showMessage("拾遗", f"已导出 {count} 条记录")

    def do_import_json():
        path, _ = QFileDialog.getOpenFileName(
            None, "导入 JSON", "",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            count = import_from_json(manager.db, Path(path))
            manager.items_changed.emit()
            tray.showMessage("拾遗", f"已导入 {count} 条记录")

    def do_export_csv():
        path, _ = QFileDialog.getSaveFileName(
            None, "导出 CSV", "clipboard_export.csv",
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if path:
            count = export_to_csv(manager.db, Path(path))
            tray.showMessage("拾遗", f"已导出 {count} 条记录")

    def do_import_csv():
        path, _ = QFileDialog.getOpenFileName(
            None, "导入 CSV", "",
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if path:
            count = import_from_csv(manager.db, Path(path))
            manager.items_changed.emit()
            tray.showMessage("拾遗", f"已导入 {count} 条记录")

    tray.export_json.connect(do_export_json)
    tray.import_json.connect(do_import_json)
    tray.export_csv.connect(do_export_csv)
    tray.import_csv.connect(do_import_csv)

    tray.show()

    # 全局快捷键 Ctrl+Shift+V
    shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), panel)
    shortcut.activated.connect(panel.toggle)

    # 初始隐藏，靠快捷键唤出
    print("[eleven] Running. Press Ctrl+Shift+V to toggle.")
    print("[eleven] Right-click tray icon for options.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
