"""Theme singleton — design system constants with dark/light mode support."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal


# ── Color palettes ──

_DARK = {
    "bgPrimary": "#080B0F",
    "bgSecondary": "#10161C",
    "bgTertiary": "#172029",
    "bgHover": "#24313B",
    "bgActive": "#2E4050",
    "bgPanel": "#0C1116",
    "bgPanelHeader": "#071016",
    "surface0": "#FA080B0F",
    "surface1": "#EB10161C",
    "surface2": "#DC182129",
    "textPrimary": "#F0F5F2",
    "textSecondary": "#A8B3BD",
    "textTertiary": "#71808F",
    "textPlaceholder": "#4A5568",
    "textInverse": "#06100D",
    "accent": "#7CE0C3",
    "accentLight": "#A8E8D8",
    "accentHover": "#54D49E",
    "accentMint": "#7CE0C3",
    "accentCyan": "#66B8C7",
    "accentGold": "#F2B84B",
    "accentGreen": "#54D49E",
    "accentGoldLight": "#FFD98A",
    "statusOnline": "#1FB84F",
    "statusWarning": "#F2B84B",
    "statusError": "#F06464",
    "statusOffline": "#71808F",
    "border": "#14E1EEE7",
    "borderHover": "#29E1EEE7",
    "lineSoft": "#14E1EEE7",
    "lineStrong": "#29E1EEE7",
    "shadow": "#61000000",
    "success": "#238636",
    "error": "#F06464",
    "typeText": "#9FCBFF",
    "typeImage": "#7CE0C3",
    "typeWord": "#9EDDE8",
    "typeExcel": "#54D49E",
    "typePdf": "#FF9A9A",
    "typePpt": "#FFD98A",
    "typeArchive": "#A8B3BD",
}

_LIGHT = {
    "bgPrimary": "#FAFBFC",
    "bgSecondary": "#FFFFFF",
    "bgTertiary": "#F0F2F5",
    "bgHover": "#E8EBF0",
    "bgActive": "#D8DDE5",
    "bgPanel": "#FFFFFF",
    "bgPanelHeader": "#F5F7FA",
    "surface0": "#05FFFFFF",
    "surface1": "#FAFFFFFF",
    "surface2": "#F0F2F5",
    "textPrimary": "#1A1D21",
    "textSecondary": "#5A6270",
    "textTertiary": "#8A92A0",
    "textPlaceholder": "#B0B8C4",
    "textInverse": "#FFFFFF",
    "accent": "#2A9D8F",
    "accentLight": "#3DB8A8",
    "accentHover": "#238B7E",
    "accentMint": "#2A9D8F",
    "accentCyan": "#3A8CA0",
    "accentGold": "#D4940A",
    "accentGreen": "#2A9D8F",
    "accentGoldLight": "#E8A820",
    "statusOnline": "#1A8A3A",
    "statusWarning": "#D4940A",
    "statusError": "#D94040",
    "statusOffline": "#8A92A0",
    "border": "#E0E4EA",
    "borderHover": "#C8CED8",
    "lineSoft": "#E8EBF0",
    "lineStrong": "#D0D5DD",
    "shadow": "#20000000",
    "success": "#1A8A3A",
    "error": "#D94040",
    "typeText": "#3A7BD5",
    "typeImage": "#2A9D8F",
    "typeWord": "#3A8CA0",
    "typeExcel": "#2A9D8F",
    "typePdf": "#D94040",
    "typePpt": "#D4940A",
    "typeArchive": "#5A6270",
}


class ThemeSingleton(QObject):
    """Design-system constants for QML with dark/light theme support."""

    themeChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "dark"  # "dark" | "light"
        self._colors = _DARK

    def setThemeMode(self, mode: str) -> None:
        """Switch theme mode ('dark' or 'light')."""
        if mode == self._mode:
            return
        self._mode = mode
        self._colors = _LIGHT if mode == "light" else _DARK
        self.themeChanged.emit()

    def getThemeMode(self) -> str:
        return self._mode

    # ── Dynamic palette properties ──

    def _color(self, key: str) -> str:
        return self._colors.get(key, "#FF00FF")

    # bg
    @pyqtProperty(str, notify=themeChanged)
    def bgPrimary(self) -> str: return self._color("bgPrimary")

    @pyqtProperty(str, notify=themeChanged)
    def bgSecondary(self) -> str: return self._color("bgSecondary")

    @pyqtProperty(str, notify=themeChanged)
    def bgTertiary(self) -> str: return self._color("bgTertiary")

    @pyqtProperty(str, notify=themeChanged)
    def bgHover(self) -> str: return self._color("bgHover")

    @pyqtProperty(str, notify=themeChanged)
    def bgActive(self) -> str: return self._color("bgActive")

    @pyqtProperty(str, notify=themeChanged)
    def bgPanel(self) -> str: return self._color("bgPanel")

    @pyqtProperty(str, notify=themeChanged)
    def bgPanelHeader(self) -> str: return self._color("bgPanelHeader")

    @pyqtProperty(str, notify=themeChanged)
    def surface0(self) -> str: return self._color("surface0")

    @pyqtProperty(str, notify=themeChanged)
    def surface1(self) -> str: return self._color("surface1")

    @pyqtProperty(str, notify=themeChanged)
    def surface2(self) -> str: return self._color("surface2")

    # text
    @pyqtProperty(str, notify=themeChanged)
    def textPrimary(self) -> str: return self._color("textPrimary")

    @pyqtProperty(str, notify=themeChanged)
    def textSecondary(self) -> str: return self._color("textSecondary")

    @pyqtProperty(str, notify=themeChanged)
    def textTertiary(self) -> str: return self._color("textTertiary")

    @pyqtProperty(str, notify=themeChanged)
    def textPlaceholder(self) -> str: return self._color("textPlaceholder")

    @pyqtProperty(str, notify=themeChanged)
    def textInverse(self) -> str: return self._color("textInverse")

    # accent
    @pyqtProperty(str, notify=themeChanged)
    def accent(self) -> str: return self._color("accent")

    @pyqtProperty(str, notify=themeChanged)
    def accentLight(self) -> str: return self._color("accentLight")

    @pyqtProperty(str, notify=themeChanged)
    def accentHover(self) -> str: return self._color("accentHover")

    @pyqtProperty(str, notify=themeChanged)
    def accentMint(self) -> str: return self._color("accentMint")

    @pyqtProperty(str, notify=themeChanged)
    def accentCyan(self) -> str: return self._color("accentCyan")

    @pyqtProperty(str, notify=themeChanged)
    def accentGold(self) -> str: return self._color("accentGold")

    @pyqtProperty(str, notify=themeChanged)
    def accentGreen(self) -> str: return self._color("accentGreen")

    @pyqtProperty(str, notify=themeChanged)
    def accentGoldLight(self) -> str: return self._color("accentGoldLight")

    # status
    @pyqtProperty(str, notify=themeChanged)
    def statusOnline(self) -> str: return self._color("statusOnline")

    @pyqtProperty(str, notify=themeChanged)
    def statusWarning(self) -> str: return self._color("statusWarning")

    @pyqtProperty(str, notify=themeChanged)
    def statusError(self) -> str: return self._color("statusError")

    @pyqtProperty(str, notify=themeChanged)
    def statusOffline(self) -> str: return self._color("statusOffline")

    # border / line
    @pyqtProperty(str, notify=themeChanged)
    def border(self) -> str: return self._color("border")

    @pyqtProperty(str, notify=themeChanged)
    def borderHover(self) -> str: return self._color("borderHover")

    @pyqtProperty(str, notify=themeChanged)
    def lineSoft(self) -> str: return self._color("lineSoft")

    @pyqtProperty(str, notify=themeChanged)
    def lineStrong(self) -> str: return self._color("lineStrong")

    @pyqtProperty(str, notify=themeChanged)
    def shadow(self) -> str: return self._color("shadow")

    @pyqtProperty(str, constant=True)
    def shadowSoft(self) -> str:
        return "0 18px 54px rgba(0,0,0,0.38)"

    @pyqtProperty(str, constant=True)
    def shadowPop(self) -> str:
        return "0 12px 28px rgba(84,212,158,0.18)"

    @pyqtProperty(str, notify=themeChanged)
    def success(self) -> str: return self._color("success")

    @pyqtProperty(str, notify=themeChanged)
    def error(self) -> str: return self._color("error")

    # type colors
    @pyqtProperty(str, notify=themeChanged)
    def typeText(self) -> str: return self._color("typeText")

    @pyqtProperty(str, notify=themeChanged)
    def typeImage(self) -> str: return self._color("typeImage")

    @pyqtProperty(str, notify=themeChanged)
    def typeWord(self) -> str: return self._color("typeWord")

    @pyqtProperty(str, notify=themeChanged)
    def typeExcel(self) -> str: return self._color("typeExcel")

    @pyqtProperty(str, notify=themeChanged)
    def typePdf(self) -> str: return self._color("typePdf")

    @pyqtProperty(str, notify=themeChanged)
    def typePpt(self) -> str: return self._color("typePpt")

    @pyqtProperty(str, notify=themeChanged)
    def typeArchive(self) -> str: return self._color("typeArchive")

    # ── Fonts (constant) ──

    @pyqtProperty(str, constant=True)
    def fontFamilyPrimary(self) -> str: return "Microsoft YaHei"

    @pyqtProperty(str, constant=True)
    def fontFamilySecondary(self) -> str: return "Segoe UI"

    @pyqtProperty(str, constant=True)
    def fontFamilyEmoji(self) -> str: return "Segoe UI Emoji"

    @pyqtProperty(int, constant=True)
    def fontSizeXS(self) -> int: return 10

    @pyqtProperty(int, constant=True)
    def fontSizeSM(self) -> int: return 11

    @pyqtProperty(int, constant=True)
    def fontSizeMD(self) -> int: return 12

    @pyqtProperty(int, constant=True)
    def fontSizeLG(self) -> int: return 13

    @pyqtProperty(int, constant=True)
    def fontSizeXL(self) -> int: return 14

    @pyqtProperty(int, constant=True)
    def fontSizeXXL(self) -> int: return 18

    @pyqtProperty(int, constant=True)
    def fontNormal(self) -> int: return 400

    @pyqtProperty(int, constant=True)
    def fontMedium(self) -> int: return 500

    @pyqtProperty(int, constant=True)
    def fontBold(self) -> int: return 700

    # ── Spacing (constant) ──

    @pyqtProperty(int, constant=True)
    def spacingXS(self) -> int: return 4

    @pyqtProperty(int, constant=True)
    def spacingSM(self) -> int: return 8

    @pyqtProperty(int, constant=True)
    def spacingMD(self) -> int: return 12

    @pyqtProperty(int, constant=True)
    def spacingLG(self) -> int: return 16

    @pyqtProperty(int, constant=True)
    def spacingXL(self) -> int: return 24

    @pyqtProperty(int, constant=True)
    def spacingXXL(self) -> int: return 32

    # ── Radius (constant) ──

    @pyqtProperty(int, constant=True)
    def radiusSM(self) -> int: return 6

    @pyqtProperty(int, constant=True)
    def radiusMD(self) -> int: return 10

    @pyqtProperty(int, constant=True)
    def radiusLG(self) -> int: return 14

    @pyqtProperty(int, constant=True)
    def radiusXL(self) -> int: return 14

    @pyqtProperty(int, constant=True)
    def radiusFull(self) -> int: return 9999

    # ── Sizes (constant) ──

    @pyqtProperty(int, constant=True)
    def panelWidth(self) -> int: return 430

    @pyqtProperty(int, constant=True)
    def panelHeight(self) -> int: return 620

    @pyqtProperty(int, constant=True)
    def itemHeight(self) -> int: return 72

    @pyqtProperty(int, constant=True)
    def thumbnailSize(self) -> int: return 48

    @pyqtProperty(int, constant=True)
    def titleBarHeight(self) -> int: return 52

    @pyqtProperty(int, constant=True)
    def searchBarHeight(self) -> int: return 36

    @pyqtProperty(int, constant=True)
    def categoryBarHeight(self) -> int: return 32

    @pyqtProperty(int, constant=True)
    def tagBarHeight(self) -> int: return 30

    # ── Animations (constant) ──

    @pyqtProperty(int, constant=True)
    def animFast(self) -> int: return 120

    @pyqtProperty(int, constant=True)
    def animNormal(self) -> int: return 160

    @pyqtProperty(int, constant=True)
    def animSlow(self) -> int: return 240

    # ── Icons (constant) ──

    @pyqtProperty(str, constant=True)
    def iconClipboard(self) -> str: return "\U0001f4cb"

    @pyqtProperty(str, constant=True)
    def iconFile(self) -> str: return "\U0001f4c4"

    @pyqtProperty(str, constant=True)
    def iconImage(self) -> str: return "\U0001f5bc️"

    @pyqtProperty(str, constant=True)
    def iconText(self) -> str: return "\U0001f4dd"

    @pyqtProperty(str, constant=True)
    def iconLink(self) -> str: return "\U0001f517"

    @pyqtProperty(str, constant=True)
    def iconPin(self) -> str: return "\U0001f4cc"

    @pyqtProperty(str, constant=True)
    def iconStar(self) -> str: return "⭐"

    @pyqtProperty(str, constant=True)
    def iconFavorite(self) -> str: return "★"

    @pyqtProperty(str, constant=True)
    def iconDelete(self) -> str: return "\U0001f5d1️"

    @pyqtProperty(str, constant=True)
    def iconCopy(self) -> str: return "\U0001f4cb"

    @pyqtProperty(str, constant=True)
    def iconSearch(self) -> str: return "\U0001f50d"

    @pyqtProperty(str, constant=True)
    def iconSettings(self) -> str: return "⚙️"

    @pyqtProperty(str, constant=True)
    def iconSourceClipboard(self) -> str: return "\U0001f4cb"

    @pyqtProperty(str, constant=True)
    def iconSourceContext(self) -> str: return "\U0001f4ce"

    @pyqtProperty(str, constant=True)
    def iconSourceDragDrop(self) -> str: return "\U0001f4e5"

    @pyqtProperty(str, constant=True)
    def iconSourceHotkey(self) -> str: return "⌨️"

    @pyqtProperty(str, constant=True)
    def iconSourceBrowser(self) -> str: return "\U0001f310"

    @pyqtProperty(str, constant=True)
    def iconSourceApi(self) -> str: return "\U0001f517"

    # ── Theme mode property ──

    @pyqtProperty(str, notify=themeChanged)
    def themeMode(self) -> str:
        return self._mode

    @pyqtProperty(bool, notify=themeChanged)
    def isDark(self) -> bool:
        return self._mode == "dark"
