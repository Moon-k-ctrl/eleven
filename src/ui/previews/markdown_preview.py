"""Markdown preview widget."""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

logger = logging.getLogger("eleven.preview.markdown")

# Dark-theme CSS for markdown rendering
MARKDOWN_CSS = """
<style>
body {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.7;
    padding: 16px;
}
h1 { color: #fff; font-size: 24px; border-bottom: 1px solid #444; padding-bottom: 8px; }
h2 { color: #fff; font-size: 20px; border-bottom: 1px solid #333; padding-bottom: 6px; }
h3 { color: #eee; font-size: 17px; }
h4 { color: #ddd; font-size: 15px; }
a { color: #4A90D9; }
code {
    background: #2a2a2a;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px;
}
pre {
    background: #2a2a2a;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    border: 1px solid #3a3a3a;
}
pre code {
    background: none;
    padding: 0;
}
blockquote {
    border-left: 3px solid #4A90D9;
    padding-left: 12px;
    color: #aaa;
    margin: 8px 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
}
th, td {
    border: 1px solid #444;
    padding: 8px 12px;
    text-align: left;
}
th {
    background: #333;
    color: #fff;
}
tr:nth-child(even) {
    background: rgba(255,255,255,0.03);
}
hr {
    border: none;
    border-top: 1px solid #444;
    margin: 16px 0;
}
ul, ol {
    padding-left: 24px;
}
li {
    margin: 4px 0;
}
img {
    max-width: 100%;
}
</style>
"""


class MarkdownPreview(QWidget):
    """Markdown renderer using the markdown library, displayed in QTextBrowser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setStyleSheet("""
            QTextBrowser {
                background: #1e1e1e;
                color: #d4d4d4;
                border: none;
            }
        """)
        layout.addWidget(self._browser)

    def load_markdown(self, text: str) -> None:
        try:
            import markdown
            extensions = [
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.nl2br',
            ]
            extension_configs = {
                'markdown.extensions.codehilite': {
                    'css_class': 'highlight',
                    'noclasses': True,
                },
            }
            html = markdown.markdown(
                text,
                extensions=extensions,
                extension_configs=extension_configs,
            )
            self._browser.setHtml(f"{MARKDOWN_CSS}{html}")
        except ImportError:
            # Fallback: plain text
            self._browser.setPlainText(text)
        except Exception as e:
            logger.error(f"Markdown render failed: {e}")
            self._browser.setPlainText(text)
