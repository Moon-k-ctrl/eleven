"""System tray icon for eleven."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QCursor
from PyQt6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon, QWidget

from src.core.config import Config, StorageMode
from src.ui.design_system import Palette, Fonts
from src.utils.autostart import is_autostart_enabled, set_autostart

logger = logging.getLogger("eleven.tray")


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu."""

    toggle_panel = pyqtSignal()
    toggle_ball = pyqtSignal()
    quit_app = pyqtSignal()
    export_json = pyqtSignal()
    import_json = pyqtSignal()
    export_csv = pyqtSignal()
    import_csv = pyqtSignal()
    storage_mode_changed = pyqtSignal(StorageMode)

    # 状态颜色映射
    _STATUS_COLORS = {
        "online": QColor(Palette.STATUS_ONLINE),
        "warning": QColor(Palette.STATUS_WARNING),
        "error": QColor(Palette.STATUS_ERROR),
        "offline": QColor(Palette.STATUS_OFFLINE),
    }

    def __init__(self, config: Config, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config
        self._base_icon: Optional[QIcon] = None
        self._status = "offline"
        try:
            self._setup_icon()
            logger.info("Tray icon setup complete")
        except Exception:
            logger.error("Tray icon setup failed", exc_info=True)
        try:
            self._setup_menu()
            logger.info("Tray menu setup complete")
        except Exception:
            logger.error("Tray menu setup failed", exc_info=True)
        self._connect_signals()

    def _setup_icon(self) -> None:
        """Set up the tray icon."""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).resolve().parent.parent.parent

        icon = None
        # Prefer .png for Windows tray (more reliable than .ico in Qt)
        png_path = base_path / "assets" / "icons" / "tray-icon.png"
        if png_path.exists():
            icon = QIcon(str(png_path))
            logger.info(f"Loaded tray icon from {png_path}, null={icon.isNull()}")

        if icon is None or icon.isNull():
            ico_path = base_path / "assets" / "icons" / "icon.ico"
            if ico_path.exists():
                icon = QIcon(str(ico_path))
                logger.info(f"Loaded tray icon from {ico_path}, null={icon.isNull()}")

        if icon is None or icon.isNull():
            icon = self._generate_icon()
            logger.warning("Using generated fallback tray icon")

        self._base_icon = icon
        self.setIcon(icon)
        self.setToolTip("拾遗 - 离线 | Ctrl+Shift+V 唤出")

    @staticmethod
    def _generate_icon() -> QIcon:
        """Generate a high-quality tray icon programmatically."""
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QPainterPath

        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded rectangle background
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(2, 2, size - 4, size - 4), 12, 12)
        painter.setPen(Qt.PenStyle.NoPen)
        # 纯黑渐变背景（Notion风格）
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(2, 2, size - 2, size - 2)
        grad.setColorAt(0, QColor(Palette.ACCENT_LIGHT))
        grad.setColorAt(1, QColor(Palette.ACCENT))
        painter.setBrush(QBrush(grad))
        painter.drawPath(bg_path)

        # Clipboard body outline
        clip_rect = QRectF(16, 12, 32, 40)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(clip_rect, 4, 4)
        painter.setPen(QPen(QColor(Palette.BG_PRIMARY), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(clip_path)

        # Clipboard clip (top tab)
        tab_rect = QRectF(24, 8, 16, 8)
        tab_path = QPainterPath()
        tab_path.addRoundedRect(tab_rect, 3, 3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Palette.BG_PRIMARY))
        painter.drawPath(tab_path)

        # "11" text
        painter.setPen(QColor(Palette.BG_PRIMARY))
        font = Fonts.get_font(14, Fonts.WEIGHT_BOLD, Fonts.FAMILY_SECONDARY)
        painter.setFont(font)
        painter.drawText(clip_rect.adjusted(0, 6, 0, 0), Qt.AlignmentFlag.AlignCenter, "11")

        painter.end()
        return QIcon(pixmap)

    def _setup_menu(self) -> None:
        """Create context menu."""
        menu = QMenu()

        show_action = QAction("显示面板", menu)
        show_action.triggered.connect(self.toggle_panel.emit)
        menu.addAction(show_action)

        detail_action = QAction("打开详情面板", menu)
        detail_action.triggered.connect(self.toggle_panel.emit)
        menu.addAction(detail_action)

        ball_action = QAction("显示/隐藏悬浮球", menu)
        ball_action.triggered.connect(self.toggle_ball.emit)
        menu.addAction(ball_action)

        self._monitor_action = QAction("暂停剪贴板监听", menu)
        self._monitor_action.setCheckable(True)
        self._monitor_action.setChecked(not self._config.clipboard_enabled)
        self._monitor_action.triggered.connect(self._toggle_monitoring)
        menu.addAction(self._monitor_action)

        menu.addSeparator()

        # 数据管理子菜单
        data_menu = menu.addMenu("数据管理")

        export_json_action = QAction("导出 JSON", data_menu)
        export_json_action.triggered.connect(self.export_json.emit)
        data_menu.addAction(export_json_action)

        import_json_action = QAction("导入 JSON", data_menu)
        import_json_action.triggered.connect(self.import_json.emit)
        data_menu.addAction(import_json_action)

        data_menu.addSeparator()

        export_csv_action = QAction("导出 CSV", data_menu)
        export_csv_action.triggered.connect(self.export_csv.emit)
        data_menu.addAction(export_csv_action)

        import_csv_action = QAction("导入 CSV", data_menu)
        import_csv_action.triggered.connect(self.import_csv.emit)
        data_menu.addAction(import_csv_action)

        menu.addSeparator()

        # 存储模式子菜单
        storage_menu = menu.addMenu("存储模式")

        self._volatile_action = QAction("[V] 临时模式", storage_menu)
        self._volatile_action.setCheckable(True)
        self._volatile_action.setChecked(self._config.storage_mode == StorageMode.VOLATILE)
        self._volatile_action.triggered.connect(lambda: self._switch_storage_mode(StorageMode.VOLATILE))
        storage_menu.addAction(self._volatile_action)

        self._persistent_action = QAction("[D] 持久模式", storage_menu)
        self._persistent_action.setCheckable(True)
        self._persistent_action.setChecked(self._config.storage_mode == StorageMode.PERSISTENT)
        self._persistent_action.triggered.connect(lambda: self._switch_storage_mode(StorageMode.PERSISTENT))
        storage_menu.addAction(self._persistent_action)

        menu.addSeparator()

        # 开机自启开关
        self._autostart_action = QAction("开机自启", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(is_autostart_enabled())
        self._autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(self._autostart_action)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit_app.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.activated.connect(self._on_activated)

    def update_status(self, status: str) -> None:
        """Update tray icon with status indicator dot."""
        if self._status == status:
            return
        self._status = status
        color = self._STATUS_COLORS.get(status, self._STATUS_COLORS["offline"])

        # Generate icon with status dot overlay
        base_pixmap = self._base_icon.pixmap(32, 32) if self._base_icon else QPixmap(32, 32)
        if base_pixmap.isNull():
            base_pixmap = QPixmap(32, 32)
            base_pixmap.fill(QColor(0xB0, 0x8D, 0x57))

        combined = QPixmap(32, 32)
        combined.fill(Qt.GlobalColor.transparent)
        painter = QPainter(combined)
        painter.drawPixmap(0, 0, base_pixmap)

        # Draw status dot (bottom-right corner)
        dot_size = 10
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(32 - dot_size - 1, 32 - dot_size - 1, dot_size, dot_size)

        # Draw border around dot
        painter.setPen(QPen(QColor(30, 30, 30), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(32 - dot_size - 1, 32 - dot_size - 1, dot_size, dot_size)

        painter.end()
        self.setIcon(QIcon(combined))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        logger.info(f"Tray activated, reason={reason}")
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            try:
                self.toggle_panel.emit()
                logger.info("toggle_panel emitted")
            except Exception:
                logger.error("Tray activated handler failed", exc_info=True)

    def _toggle_autostart(self, checked: bool) -> None:
        """Toggle auto-start on boot."""
        if set_autostart(checked):
            self._autostart_action.setChecked(checked)
        else:
            # 回滚状态
            self._autostart_action.setChecked(not checked)

    def _switch_storage_mode(self, mode: StorageMode) -> None:
        """Switch storage mode with confirmation."""
        if mode == self._config.storage_mode:
            return

        desc = self._config.get_mode_switch_description(mode)
        box = QMessageBox(None)
        box.setWindowTitle("切换存储模式")
        box.setText(f"{desc}\n\n存储模式将在重启拾遗后生效。")
        box.setIcon(QMessageBox.Icon.Question)
        later_btn = box.addButton("稍后", QMessageBox.ButtonRole.RejectRole)
        restart_btn = box.addButton("立即重启", QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(later_btn)
        box.exec()

        self._config.storage_mode = mode
        self._volatile_action.setChecked(mode == StorageMode.VOLATILE)
        self._persistent_action.setChecked(mode == StorageMode.PERSISTENT)
        self.storage_mode_changed.emit(mode)

        if box.clickedButton() == restart_btn:
            import sys, os
            QApplication.quit()
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _toggle_monitoring(self, checked: bool) -> None:
        """Toggle clipboard monitoring."""
        self._config.clipboard_enabled = not checked
        self._monitor_action.setText("暂停剪贴板监听" if self._config.clipboard_enabled else "开启剪贴板监听")
        self.showMessage("拾遗", f"剪贴板监听已{'开启' if self._config.clipboard_enabled else '关闭'}")
