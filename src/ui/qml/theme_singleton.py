"""Theme singleton — all design system constants exposed as Q_PROPERTY for QML."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty


class ThemeSingleton(QObject):
    """Design-system constants for QML, registered as a QML singleton."""

    # ── Palette ──
    @pyqtProperty(str, constant=True)
    def bgPrimary(self) -> str:
        return "#080B0F"

    @pyqtProperty(str, constant=True)
    def bgSecondary(self) -> str:
        return "#10161C"

    @pyqtProperty(str, constant=True)
    def bgTertiary(self) -> str:
        return "#172029"

    @pyqtProperty(str, constant=True)
    def bgHover(self) -> str:
        return "#24313B"

    @pyqtProperty(str, constant=True)
    def bgActive(self) -> str:
        return "#2E4050"

    @pyqtProperty(str, constant=True)
    def bgPanel(self) -> str:
        return "#0C1116"

    @pyqtProperty(str, constant=True)
    def bgPanelHeader(self) -> str:
        return "#071016"

    @pyqtProperty(str, constant=True)
    def surface0(self) -> str:
        return "#FA080B0F"

    @pyqtProperty(str, constant=True)
    def surface1(self) -> str:
        return "#EB10161C"

    @pyqtProperty(str, constant=True)
    def surface2(self) -> str:
        return "#DC182129"

    @pyqtProperty(str, constant=True)
    def textPrimary(self) -> str:
        return "#F0F5F2"

    @pyqtProperty(str, constant=True)
    def textSecondary(self) -> str:
        return "#A8B3BD"

    @pyqtProperty(str, constant=True)
    def textTertiary(self) -> str:
        return "#71808F"

    @pyqtProperty(str, constant=True)
    def textPlaceholder(self) -> str:
        return "#4A5568"

    @pyqtProperty(str, constant=True)
    def textInverse(self) -> str:
        return "#06100D"

    @pyqtProperty(str, constant=True)
    def accent(self) -> str:
        return "#7CE0C3"

    @pyqtProperty(str, constant=True)
    def accentLight(self) -> str:
        return "#A8E8D8"

    @pyqtProperty(str, constant=True)
    def accentHover(self) -> str:
        return "#54D49E"

    @pyqtProperty(str, constant=True)
    def accentMint(self) -> str:
        return "#7CE0C3"

    @pyqtProperty(str, constant=True)
    def accentCyan(self) -> str:
        return "#66B8C7"

    @pyqtProperty(str, constant=True)
    def accentGold(self) -> str:
        return "#F2B84B"

    @pyqtProperty(str, constant=True)
    def accentGreen(self) -> str:
        return "#54D49E"

    @pyqtProperty(str, constant=True)
    def accentGoldLight(self) -> str:
        return "#FFD98A"

    @pyqtProperty(str, constant=True)
    def statusOnline(self) -> str:
        return "#1FB84F"

    @pyqtProperty(str, constant=True)
    def statusWarning(self) -> str:
        return "#F2B84B"

    @pyqtProperty(str, constant=True)
    def statusError(self) -> str:
        return "#F06464"

    @pyqtProperty(str, constant=True)
    def statusOffline(self) -> str:
        return "#71808F"

    @pyqtProperty(str, constant=True)
    def border(self) -> str:
        return "#14E1EEE7"

    @pyqtProperty(str, constant=True)
    def borderHover(self) -> str:
        return "#29E1EEE7"

    @pyqtProperty(str, constant=True)
    def lineSoft(self) -> str:
        return "#14E1EEE7"

    @pyqtProperty(str, constant=True)
    def lineStrong(self) -> str:
        return "#29E1EEE7"

    @pyqtProperty(str, constant=True)
    def shadow(self) -> str:
        return "#61000000"

    @pyqtProperty(str, constant=True)
    def shadowSoft(self) -> str:
        return "0 18px 54px rgba(0,0,0,0.38)"

    @pyqtProperty(str, constant=True)
    def shadowPop(self) -> str:
        return "0 12px 28px rgba(84,212,158,0.18)"

    @pyqtProperty(str, constant=True)
    def success(self) -> str:
        return "#238636"

    @pyqtProperty(str, constant=True)
    def error(self) -> str:
        return "#F06464"

    @pyqtProperty(str, constant=True)
    def typeText(self) -> str:
        return "#9FCBFF"

    @pyqtProperty(str, constant=True)
    def typeImage(self) -> str:
        return "#7CE0C3"

    @pyqtProperty(str, constant=True)
    def typeWord(self) -> str:
        return "#9EDDE8"

    @pyqtProperty(str, constant=True)
    def typeExcel(self) -> str:
        return "#54D49E"

    @pyqtProperty(str, constant=True)
    def typePdf(self) -> str:
        return "#FF9A9A"

    @pyqtProperty(str, constant=True)
    def typePpt(self) -> str:
        return "#FFD98A"

    @pyqtProperty(str, constant=True)
    def typeArchive(self) -> str:
        return "#A8B3BD"

    # ── Fonts ──
    @pyqtProperty(str, constant=True)
    def fontFamilyPrimary(self) -> str:
        return "Microsoft YaHei"

    @pyqtProperty(str, constant=True)
    def fontFamilySecondary(self) -> str:
        return "Segoe UI"

    @pyqtProperty(str, constant=True)
    def fontFamilyEmoji(self) -> str:
        return "Segoe UI Emoji"

    @pyqtProperty(int, constant=True)
    def fontSizeXS(self) -> int:
        return 10

    @pyqtProperty(int, constant=True)
    def fontSizeSM(self) -> int:
        return 11

    @pyqtProperty(int, constant=True)
    def fontSizeMD(self) -> int:
        return 12

    @pyqtProperty(int, constant=True)
    def fontSizeLG(self) -> int:
        return 13

    @pyqtProperty(int, constant=True)
    def fontSizeXL(self) -> int:
        return 14

    @pyqtProperty(int, constant=True)
    def fontSizeXXL(self) -> int:
        return 18

    @pyqtProperty(int, constant=True)
    def fontNormal(self) -> int:
        return 400

    @pyqtProperty(int, constant=True)
    def fontMedium(self) -> int:
        return 500

    @pyqtProperty(int, constant=True)
    def fontBold(self) -> int:
        return 700

    # ── Spacing ──
    @pyqtProperty(int, constant=True)
    def spacingXS(self) -> int:
        return 4

    @pyqtProperty(int, constant=True)
    def spacingSM(self) -> int:
        return 8

    @pyqtProperty(int, constant=True)
    def spacingMD(self) -> int:
        return 12

    @pyqtProperty(int, constant=True)
    def spacingLG(self) -> int:
        return 16

    @pyqtProperty(int, constant=True)
    def spacingXL(self) -> int:
        return 24

    @pyqtProperty(int, constant=True)
    def spacingXXL(self) -> int:
        return 32

    # ── Radius ──
    @pyqtProperty(int, constant=True)
    def radiusSM(self) -> int:
        return 6

    @pyqtProperty(int, constant=True)
    def radiusMD(self) -> int:
        return 10

    @pyqtProperty(int, constant=True)
    def radiusLG(self) -> int:
        return 14

    @pyqtProperty(int, constant=True)
    def radiusXL(self) -> int:
        return 14

    @pyqtProperty(int, constant=True)
    def radiusFull(self) -> int:
        return 9999

    # ── Sizes ──
    @pyqtProperty(int, constant=True)
    def panelWidth(self) -> int:
        return 430

    @pyqtProperty(int, constant=True)
    def panelHeight(self) -> int:
        return 620

    @pyqtProperty(int, constant=True)
    def itemHeight(self) -> int:
        return 72

    @pyqtProperty(int, constant=True)
    def thumbnailSize(self) -> int:
        return 48

    @pyqtProperty(int, constant=True)
    def titleBarHeight(self) -> int:
        return 52

    @pyqtProperty(int, constant=True)
    def searchBarHeight(self) -> int:
        return 36

    @pyqtProperty(int, constant=True)
    def categoryBarHeight(self) -> int:
        return 32

    @pyqtProperty(int, constant=True)
    def tagBarHeight(self) -> int:
        return 30

    # ── Animations ──
    @pyqtProperty(int, constant=True)
    def animFast(self) -> int:
        return 120

    @pyqtProperty(int, constant=True)
    def animNormal(self) -> int:
        return 160

    @pyqtProperty(int, constant=True)
    def animSlow(self) -> int:
        return 240

    # ── Icons ──
    @pyqtProperty(str, constant=True)
    def iconClipboard(self) -> str:
        return "\U0001f4cb"

    @pyqtProperty(str, constant=True)
    def iconFile(self) -> str:
        return "\U0001f4c4"

    @pyqtProperty(str, constant=True)
    def iconImage(self) -> str:
        return "\U0001f5bc️"

    @pyqtProperty(str, constant=True)
    def iconText(self) -> str:
        return "\U0001f4dd"

    @pyqtProperty(str, constant=True)
    def iconLink(self) -> str:
        return "\U0001f517"

    @pyqtProperty(str, constant=True)
    def iconPin(self) -> str:
        return "\U0001f4cc"

    @pyqtProperty(str, constant=True)
    def iconStar(self) -> str:
        return "⭐"

    @pyqtProperty(str, constant=True)
    def iconFavorite(self) -> str:
        return "★"

    @pyqtProperty(str, constant=True)
    def iconDelete(self) -> str:
        return "\U0001f5d1️"

    @pyqtProperty(str, constant=True)
    def iconCopy(self) -> str:
        return "\U0001f4cb"

    @pyqtProperty(str, constant=True)
    def iconSearch(self) -> str:
        return "\U0001f50d"

    @pyqtProperty(str, constant=True)
    def iconSettings(self) -> str:
        return "⚙️"

    @pyqtProperty(str, constant=True)
    def iconSourceClipboard(self) -> str:
        return "\U0001f4cb"

    @pyqtProperty(str, constant=True)
    def iconSourceContext(self) -> str:
        return "\U0001f4ce"

    @pyqtProperty(str, constant=True)
    def iconSourceDragDrop(self) -> str:
        return "\U0001f4e5"

    @pyqtProperty(str, constant=True)
    def iconSourceHotkey(self) -> str:
        return "⌨️"

    @pyqtProperty(str, constant=True)
    def iconSourceBrowser(self) -> str:
        return "\U0001f310"

    @pyqtProperty(str, constant=True)
    def iconSourceApi(self) -> str:
        return "\U0001f517"
