"""Tema gótico do Nightreign Seed Reader: noite roxa, lavanda e molduras ornamentadas."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication

BG = "#0b0a14"
PANEL = "#110e22"
PANEL_2 = "#18142e"
BORDER = "#342c5c"
BORDER_HI = "#7a6cc8"
GOLD = "#a99bff"  # acento principal (lavanda) — nome mantido por compatibilidade
GOLD_HI = "#e6e0ff"
TEXT = "#e9e5fa"
MUTED = "#a69fcb"
OK = "#8fd08a"
WARN = "#e2b25a"
ERR = "#e0605a"
NIGHT = "#8f86e6"
PURPLE = "#8460f0"
MAP_BG = "transparent"

TITLE_FAMILY = "Cinzel"
SERIF_FAMILY = "Cormorant Garamond"
BODY_FAMILY = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def _assets() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) / "nrseed" / "assets" if meipass else Path(__file__).resolve().parents[1] / "assets"


def asset(name: str) -> Path:
    return _assets() / name


def load_fonts() -> None:
    global TITLE_FAMILY, SERIF_FAMILY
    for fname, attr in (("Cinzel.ttf", "TITLE_FAMILY"), ("CormorantGaramond-Italic.ttf", "SERIF_FAMILY")):
        fid = QFontDatabase.addApplicationFont(str(_assets() / fname))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if fams:
            globals()[attr] = fams[0]


def title_font(size: int, weight: int = 600) -> QFont:
    f = QFont(TITLE_FAMILY, size)
    f.setWeight(QFont.Weight(weight))
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
    return f


def serif_font(size: int, italic: bool = True) -> QFont:
    f = QFont(SERIF_FAMILY, size)
    f.setItalic(italic)
    f.setWeight(QFont.Weight.Medium)
    return f


CHECK_SVG = (_assets() / "check.png").as_posix()

STYLESHEET = f"""
QWidget {{ color: {TEXT}; }}
QMainWindow {{ background: {BG}; }}
QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER_HI}; padding: 4px 6px; }}

#Header {{ background: transparent; border: none; }}
#AppTitle {{ color: {GOLD_HI}; }}
#AppSub {{ color: {MUTED}; }}

#StatusPill {{ background: rgba(10, 8, 22, 200); border: 1px solid {BORDER_HI}; border-radius: 14px; }}
#StatusText {{ color: {TEXT}; font-size: 9pt; }}

#Sidebar {{ background: transparent; border: none; }}
QFrame#Card {{ background: transparent; border: none; }}
QLabel#CardTitle {{ color: #cfc6ff; }}
QLabel#Muted {{ color: {MUTED}; font-family: "{SERIF_FAMILY}"; font-style: italic; font-size: 12pt; }}
QLabel#Big {{ color: {GOLD_HI}; }}
QLabel#Value {{ color: {TEXT}; font-size: 10pt; }}
QLabel#Event {{ color: #ff9a8a; font-size: 10pt; }}
QLabel#Night {{ color: #c3b6ff; font-family: "{SERIF_FAMILY}"; font-style: italic; font-size: 12pt; }}

QPushButton {{ background: rgba(14, 11, 30, 190); border: 1px solid {BORDER_HI}; border-radius: 4px;
               padding: 6px 14px; color: {TEXT}; }}
QPushButton:hover {{ border-color: {GOLD_HI}; color: #ffffff; background: rgba(40, 32, 84, 200); }}
QPushButton:pressed {{ background: rgba(60, 48, 120, 220); }}
QPushButton:checked {{ border-color: {GOLD_HI}; color: #ffffff; background: rgba(52, 40, 108, 210); }}
QPushButton:disabled {{ color: #5d5880; border-color: #2c2650; }}
QPushButton#Primary {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(70,54,150,220),
                       stop:1 rgba(34,26,80,220)); border: 1px solid {GOLD_HI}; color: #ffffff; font-weight: 600; }}
QPushButton#Primary:hover {{ background: rgba(92, 72, 190, 230); }}
QPushButton#Tab {{ background: transparent; border: none; border-bottom: 2px solid transparent;
                   border-radius: 0; padding: 8px 16px; color: {MUTED}; }}
QPushButton#Tab:checked {{ color: #ffffff; border-bottom: 2px solid {GOLD}; background: transparent; }}
QPushButton#Tab:hover {{ color: #ffffff; background: transparent; }}
QPushButton#Choice {{ padding: 2px; border-radius: 6px; background: rgba(10, 8, 22, 180); border: 1px solid {BORDER}; }}
QPushButton#Choice:checked {{ border: 2px solid {GOLD_HI}; background: rgba(52, 40, 108, 210); }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 6px 6px; border-radius: 4px; color: {TEXT}; }}
QListWidget::item:hover {{ background: rgba(60, 48, 120, 120); }}
QListWidget::item:selected {{ background: rgba(70, 56, 140, 170); color: #ffffff; border: 1px solid {BORDER_HI}; }}

QCheckBox {{ color: {TEXT}; spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER_HI}; border-radius: 3px; background: {BG}; }}
QCheckBox::indicator:hover {{ border-color: {GOLD_HI}; }}
QCheckBox::indicator:checked {{ background: {GOLD}; border-color: {GOLD_HI}; image: url("{CHECK_SVG}"); }}
QComboBox {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px 8px; }}
QComboBox QAbstractItemView {{ background: {PANEL_2}; border: 1px solid {BORDER_HI}; selection-background-color: #3a2f78; }}

QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER_HI}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px 6px 8px; border-radius: 3px; }}
QMenu::item:selected {{ background: #3a2f78; color: #ffffff; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 6px; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_HI}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QGraphicsView {{ background: transparent; border: none; }}
QDialog {{ background: {PANEL}; }}
QMessageBox {{ background: {PANEL}; }}
"""


def apply(app: QApplication) -> None:
    load_fonts()
    app.setStyle("Fusion")
    base = QFont(BODY_FAMILY, 10)
    app.setFont(base)
    pal = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, BG),
        (QPalette.ColorRole.Base, PANEL),
        (QPalette.ColorRole.AlternateBase, PANEL_2),
        (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Button, PANEL_2),
        (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Highlight, "#3a2f78"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        pal.setColor(role, QColor(color))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET)
