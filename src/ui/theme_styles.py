"""Shared PyQt6 stylesheet constants for ink-wash dark theme (水墨风)."""
from __future__ import annotations

# ── Colors ──
BG_PRIMARY = "#080B0F"
BG_SECONDARY = "#10161C"
BG_TERTIARY = "#172029"
BG_HOVER = "#24313B"
BG_ACTIVE = "#2E4050"

TEXT_PRIMARY = "#F0F5F2"
TEXT_SECONDARY = "#A8B3BD"
TEXT_TERTIARY = "#71808F"
TEXT_PLACEHOLDER = "#4A5568"

ACCENT_MINT = "#7CE0C3"
ACCENT_CYAN = "#66B8C7"
ACCENT_GOLD = "#F2B84B"

ERROR = "#F06464"
SUCCESS = "#238636"

BORDER_SOFT = "#14E1EEE7"
BORDER_STRONG = "#29E1EEE7"

# ── Dialog base stylesheet ──
DIALOG_STYLE = f"""
QDialog {{
    background: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-family: "Microsoft YaHei", "Segoe UI";
}}
QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QLineEdit {{
    background: rgba(255,255,255,0.05);
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-family: "Microsoft YaHei";
}}
QLineEdit:focus {{
    border-color: {ACCENT_MINT};
}}
QListWidget {{
    background: {BG_TERTIARY};
    border: 1px solid {BORDER_SOFT};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 2px;
    border-radius: 6px;
}}
QListWidget::item:hover {{
    background: {BG_HOVER};
}}
QListWidget::item:selected {{
    background: rgba(124, 224, 195, 0.15);
}}
QComboBox {{
    background: {BG_TERTIARY};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background: {BG_TERTIARY};
    border: 1px solid {BORDER_SOFT};
    color: {TEXT_PRIMARY};
    selection-background-color: rgba(124, 224, 195, 0.15);
}}
QCheckBox {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    background: {BG_TERTIARY};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT_MINT};
    border-color: {ACCENT_MINT};
}}
QRadioButton {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    background: {BG_TERTIARY};
}}
QRadioButton::indicator:checked {{
    background: {ACCENT_MINT};
    border-color: {ACCENT_MINT};
}}
QTextEdit, QPlainTextEdit {{
    background: {BG_TERTIARY};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    padding: 6px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(124, 224, 195, 0.2);
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(124, 224, 195, 0.4);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""

# ── Button styles ──
def btn_primary() -> str:
    return f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ACCENT_MINT}, stop:1 #69C9DC);
        color: {BG_PRIMARY};
        border: none;
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: bold;
        font-family: "Microsoft YaHei";
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #8CEAD0, stop:1 #79D3E8);
    }}
    QPushButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #6CD4B3, stop:1 #59B9CC);
    }}
    """


def btn_secondary() -> str:
    return f"""
    QPushButton {{
        background: rgba(255,255,255,0.045);
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER_SOFT};
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 13px;
        font-family: "Microsoft YaHei";
    }}
    QPushButton:hover {{
        background: rgba(124, 224, 195, 0.08);
        border-color: rgba(124, 224, 195, 0.3);
        color: {TEXT_PRIMARY};
    }}
    """


def btn_danger() -> str:
    return f"""
    QPushButton {{
        background: transparent;
        color: {ERROR};
        border: 1px solid rgba(240, 100, 100, 0.3);
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 13px;
        font-family: "Microsoft YaHei";
    }}
    QPushButton:hover {{
        background: rgba(240, 100, 100, 0.1);
        border-color: rgba(240, 100, 100, 0.5);
    }}
    """


def btn_text() -> str:
    return f"""
    QPushButton {{
        background: transparent;
        color: {TEXT_TERTIARY};
        border: none;
        padding: 4px 8px;
        font-size: 12px;
        font-family: "Microsoft YaHei";
    }}
    QPushButton:hover {{
        color: {TEXT_PRIMARY};
    }}
    """


# ── Section header style ──
SECTION_HEADER = f"""
QLabel {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
    font-weight: bold;
    font-family: "Microsoft YaHei";
    padding: 4px 0;
}}
"""

# ── Preset tag colors ──
TAG_COLORS = [
    "#7CE0C3",  # mint
    "#66B8C7",  # cyan
    "#F2B84B",  # gold
    "#9FCBFF",  # blue
    "#FF9A9A",  # red
    "#54D49E",  # green
    "#A8B3BD",  # gray
    "#FFD98A",  # light gold
    "#9EDDE8",  # light cyan
    "#C4B5FD",  # purple
]
