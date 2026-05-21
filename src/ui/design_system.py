"""Design system constants and utilities for Eleven clipboard manager."""
from __future__ import annotations

from PyQt6.QtGui import QColor, QFont


class Palette:
    """Color palette inspired by Trae/Notion - clean black and white theme."""
    
    # Backgrounds (Trae/Notion style)
    BG_PRIMARY = "#FFFFFF"        # 纯白主背景
    BG_SECONDARY = "#F7F6F3"     # 米白次级背景
    BG_TERTIARY = "#F1F0ED"       # 更浅灰
    BG_HOVER = "#F1F0ED"          # 悬停态
    BG_ACTIVE = "#E8E6E1"         # 激活态
    
    # Text (高对比度黑白)
    TEXT_PRIMARY = "#37352F"      # 近黑色（Notion默认文字色）
    TEXT_SECONDARY = "#6B6B6B"    # 次级文字
    TEXT_TERTIARY = "#9B9A97"     # 淡化文字
    TEXT_PLACEHOLDER = "#C4C4C4"  # 占位符
    
    # Accent - 纯黑色系（简洁现代）
    ACCENT = "#1A1A1A"            # 纯黑强调
    ACCENT_LIGHT = "#37352F"      # 深灰强调
    ACCENT_HOVER = "#2D2D2D"      # 悬停强调
    ACCENT_GOLD = "#C2953B"       # 金色强调
    ACCENT_GOLD_LIGHT = "#D4A84B" # 浅金色强调
    
    # Status colors (保留功能性颜色)
    STATUS_ONLINE = "#238636"      # GitHub绿
    STATUS_WARNING = "#9A6700"    # 琥珀色
    STATUS_ERROR = "#CF222E"       # 红色
    STATUS_OFFLINE = "#8B8B8B"    # 灰色
    
    # Type-specific colors (Notion风格)
    TYPE_TEXT = "#37352F"
    TYPE_IMAGE = "#5969B0"
    TYPE_WORD = "#2A4B8D"
    TYPE_EXCEL = "#217346"
    TYPE_PDF = "#C94043"
    TYPE_PPT = "#D04423"
    TYPE_ARCHIVE = "#744DDA"
    
    # Success/Error
    SUCCESS = "#238636"
    ERROR = "#CF222E"
    WARNING = "#9A6700"
    
    # Border/Shadow (Notion风格细边框)
    BORDER = "#E8E6E1"
    BORDER_HOVER = "#C4C4C4"
    BORDER_FOCUS = TEXT_PRIMARY
    SHADOW = "rgba(0, 0, 0, 0.05)"
    SHADOW_LIFT = "rgba(0, 0, 0, 0.10)"
    
    @staticmethod
    def qcolor(name: str) -> QColor:
        """Convert color name to QColor."""
        color_map = {
            'bg_primary': Palette.BG_PRIMARY,
            'bg_secondary': Palette.BG_SECONDARY,
            'bg_tertiary': Palette.BG_TERTIARY,
            'text_primary': Palette.TEXT_PRIMARY,
            'text_secondary': Palette.TEXT_SECONDARY,
            'accent': Palette.ACCENT,
            'accent_light': Palette.ACCENT_LIGHT,
            'status_online': Palette.STATUS_ONLINE,
            'status_error': Palette.STATUS_ERROR,
            'border': Palette.BORDER,
        }
        return QColor(color_map.get(name, name))


class Fonts:
    """Font definitions."""
    
    FAMILY_PRIMARY = "Microsoft YaHei"
    FAMILY_SECONDARY = "Segoe UI"
    FAMILY_EMOJI = "Segoe UI Emoji"
    
    SIZE_XS = 10
    SIZE_SM = 11
    SIZE_MD = 12
    SIZE_LG = 13
    SIZE_XL = 14
    SIZE_XXL = 18
    
    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_BOLD = 700
    
    @staticmethod
    def get_font(size: int = SIZE_MD, weight: int = WEIGHT_NORMAL, family: str = FAMILY_PRIMARY) -> QFont:
        """Create a QFont with specified properties."""
        font = QFont(family, size)
        font.setWeight(weight)
        return font


class Spacing:
    """Spacing constants."""
    
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Radius:
    """Border radius constants."""
    
    SM = 6
    MD = 8
    LG = 10
    XL = 12
    FULL = 9999


class Sizes:
    """Component size constants."""
    
    # Floating ball
    BALL_SIZE = 96
    BALL_INNER = 88
    BADGE_SIZE = 22
    
    # Panel
    PANEL_WIDTH = 380
    PANEL_HEIGHT = 520
    
    # List item
    ITEM_HEIGHT = 72
    THUMBNAIL_SIZE = 48


class Animations:
    """Animation timing constants."""
    
    FAST = 120
    NORMAL = 160
    SLOW = 240
    
    EASE_OUT = "OutCubic"
    EASE_IN = "InCubic"
    EASE_IN_OUT = "InOutCubic"


class Icons:
    """Icon definitions using emoji and custom symbols."""
    
    # Core icons
    CLIPBOARD = "📋"
    FILE = "📄"
    IMAGE = "🖼️"
    TEXT = "📝"
    LINK = "🔗"
    
    # Actions
    PIN = "📌"
    STAR = "⭐"
    FAVORITE = "★"
    DELETE = "🗑️"
    COPY = "📋"
    EXPORT = "📤"
    IMPORT = "📥"
    
    # Sources
    SOURCE_CLIPBOARD = "📋"
    SOURCE_CONTEXT = "📎"
    SOURCE_DRAG_DROP = "📥"
    SOURCE_HOTKEY = "⌨️"
    SOURCE_BROWSER = "🌐"
    SOURCE_API = "🔗"


class StyleTemplates:
    """Predefined style templates for common components - Trae/Notion style."""
    
    @staticmethod
    def line_edit() -> str:
        return f"""
        QLineEdit {{
            background: {Palette.BG_PRIMARY};
            border: 1px solid {Palette.BORDER};
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            color: {Palette.TEXT_PRIMARY};
            font-family: {Fonts.FAMILY_PRIMARY};
            font-size: {Fonts.SIZE_MD}px;
        }}
        QLineEdit:focus {{
            border-color: {Palette.TEXT_PRIMARY};
        }}
        QLineEdit::placeholder {{
            color: {Palette.TEXT_PLACEHOLDER};
        }}
        """
    
    @staticmethod
    def push_button_primary() -> str:
        return f"""
        QPushButton {{
            background: {Palette.TEXT_PRIMARY};
            color: {Palette.BG_PRIMARY};
            border: none;
            border-radius: {Radius.SM}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-family: {Fonts.FAMILY_PRIMARY};
            font-size: {Fonts.SIZE_SM}px;
            font-weight: {Fonts.WEIGHT_MEDIUM};
        }}
        QPushButton:hover {{
            background: {Palette.ACCENT_HOVER};
        }}
        QPushButton:pressed {{
            background: {Palette.ACCENT};
        }}
        """
    
    @staticmethod
    def push_button_secondary() -> str:
        return f"""
        QPushButton {{
            background: {Palette.BG_SECONDARY};
            color: {Palette.TEXT_PRIMARY};
            border: 1px solid {Palette.BORDER};
            border-radius: {Radius.SM}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-family: {Fonts.FAMILY_PRIMARY};
            font-size: {Fonts.SIZE_SM}px;
        }}
        QPushButton:hover {{
            background: {Palette.BG_HOVER};
        }}
        """
    
    @staticmethod
    def push_button_text() -> str:
        return f"""
        QPushButton {{
            background: transparent;
            color: {Palette.TEXT_PRIMARY};
            border: none;
            padding: {Spacing.XS}px {Spacing.SM}px;
            font-family: {Fonts.FAMILY_PRIMARY};
            font-size: {Fonts.SIZE_SM}px;
            font-weight: {Fonts.WEIGHT_MEDIUM};
        }}
        QPushButton:hover {{
            background: {Palette.BG_HOVER};
            border-radius: {Radius.SM}px;
        }}
        """
    
    @staticmethod
    def list_view() -> str:
        return f"""
        QListView {{
            background: {Palette.BG_PRIMARY};
            border: none;
            outline: none;
        }}
        QListView::item {{
            padding: {Spacing.XS}px;
            border: none;
        }}
        QListView::item:selected {{
            background: {Palette.BG_ACTIVE};
        }}
        QListView::item:hover {{
            background: {Palette.BG_HOVER};
        }}
        """
    
    @staticmethod
    def combo_box() -> str:
        return f"""
        QComboBox {{
            background: {Palette.BG_PRIMARY};
            color: {Palette.TEXT_PRIMARY};
            border: 1px solid {Palette.BORDER};
            border-radius: {Radius.SM}px;
            padding: {Spacing.XS}px {Spacing.SM}px;
            font-family: {Fonts.FAMILY_PRIMARY};
            font-size: {Fonts.SIZE_SM}px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background: {Palette.BG_PRIMARY};
            color: {Palette.TEXT_PRIMARY};
            selection-background-color: {Palette.BG_ACTIVE};
            border: 1px solid {Palette.BORDER};
        }}
        """
    
    @staticmethod
    def menu() -> str:
        return f"""
        QMenu {{
            background: {Palette.BG_PRIMARY};
            border: 1px solid {Palette.BORDER};
            color: {Palette.TEXT_PRIMARY};
            padding: {Spacing.XS}px;
            border-radius: {Radius.LG}px;
            box-shadow: 0 4px 12px {Palette.SHADOW_LIFT};
        }}
        QMenu::item {{
            padding: {Spacing.SM}px {Spacing.LG}px;
            border-radius: {Radius.SM}px;
        }}
        QMenu::item:selected {{
            background: {Palette.BG_HOVER};
        }}
        """


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B' string for use in rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def apply_design_system(widget) -> None:
    """Apply design system styles to a widget."""
    widget.setStyleSheet(
        StyleTemplates.line_edit() +
        StyleTemplates.push_button_text() +
        StyleTemplates.list_view() +
        StyleTemplates.combo_box() +
        StyleTemplates.menu()
    )