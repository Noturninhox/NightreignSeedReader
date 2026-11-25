"""Tema escuro inspirado no Elden Ring Nightreign (preto, bronze e dourado)."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication

BG = "#0a0908"
PANEL = "#12100d"
PANEL_2 = "#1a1712"
BORDER = "#3b3224"
BORDER_HI = "#6e5a36"
GOLD = "#c9a45c"
GOLD_HI = "#e8c77e"
TEXT = "#e6dcc4"
MUTED = "#8f8570"
OK = "#7fb069"
WARN = "#d9a441"
ERR = "#c0533f"
NIGHT = "#6f7fbf"

TITLE_FAMILY = "Cinzel"
BODY_FAMILY = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def _assets() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) / "nrseed" / "assets" if meipass else Path(__file__).resolve().parents[1] / "assets"


def asset(name: str) -> Path:
    return _assets() / name


def load_fonts() -> None:
    global TITLE_FAMILY
    fid = QFontDatabase.addApplicationFont(str(_assets() / "Cinzel.ttf"))
    fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
    if fams:
        TITLE_FAMILY = fams[0]


def title_font(size: int, weight: int = 600) -> QFont:
    f = QFont(TITLE_FAMILY, size)
    f.setWeight(QFont.Weight(weight))
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
    return f


CHECK_SVG = (_assets() / "check.png").as_posix()

STYLESHEET = f"""
QWidget {{ color: {TEXT}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER_HI}; padding: 4px 6px; }}

#Header {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #17140f, stop:1 {BG});
           border-bottom: 1px solid {BORDER}; }}
#AppTitle {{ color: {GOLD}; }}
#AppSub {{ color: {MUTED}; }}

#StatusPill {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 13px; padding: 3px 12px; }}
#StatusText {{ color: {TEXT}; font-size: 9pt; }}

#Sidebar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
QFrame#Card {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; }}
QLabel#CardTitle {{ color: {GOLD}; }}
QLabel#Muted {{ color: {MUTED}; font-size: 9pt; }}
QLabel#Big {{ color: {GOLD_HI}; }}
QLabel#Value {{ color: {TEXT}; font-size: 10pt; }}
QLabel#Event {{ color: #d98b6a; font-size: 10pt; }}
QLabel#Night {{ color: #a9b4e8; }}

QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 6px 12px; color: {TEXT}; }}
QPushButton:hover {{ border-color: {GOLD}; color: {GOLD_HI}; }}
QPushButton:pressed {{ background: #241f17; }}
QPushButton:checked {{ border-color: {GOLD}; color: {GOLD_HI}; background: #2a2318; }}
QPushButton:disabled {{ color: #5a5345; border-color: #2a241a; }}
QPushButton#Primary {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5a4524, stop:1 #3a2c16);
                       border: 1px solid {GOLD}; color: #f6e7c1; font-weight: 600; }}
QPushButton#Primary:hover {{ background: #6b5329; }}
QPushButton#Tab {{ background: transparent; border: none; border-bottom: 2px solid transparent;
                   border-radius: 0; padding: 8px 14px; color: {MUTED}; }}
QPushButton#Tab:checked {{ color: {GOLD_HI}; border-bottom: 2px solid {GOLD}; background: transparent; }}
QPushButton#Tab:hover {{ color: {GOLD_HI}; }}
QPushButton#Choice {{ padding: 2px; border-radius: 6px; background: #100e0b; }}
QPushButton#Choice:checked {{ border: 2px solid {GOLD}; background: #2a2318; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 6px 6px; border-radius: 4px; color: {TEXT}; }}
QListWidget::item:hover {{ background: #221d15; }}
QListWidget::item:selected {{ background: #2e2619; color: {GOLD_HI}; border: 1px solid {BORDER_HI}; }}

QCheckBox {{ color: {TEXT}; spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER_HI}; border-radius: 3px; background: {BG}; }}
QCheckBox::indicator:hover {{ border-color: {GOLD}; }}
QCheckBox::indicator:checked {{ background: {GOLD}; border-color: {GOLD_HI}; image: url("{CHECK_SVG}"); }}
QComboBox {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px 8px; }}
QComboBox QAbstractItemView {{ background: {PANEL_2}; border: 1px solid {BORDER_HI}; selection-background-color: #2e2619; }}

QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER_HI}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px 6px 8px; border-radius: 3px; }}
QMenu::item:selected {{ background: #2e2619; color: {GOLD_HI}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 6px; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_HI}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QGraphicsView {{ background: {BG}; border: none; }}
QDialog {{ background: {PANEL}; }}
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
        (QPalette.ColorRole.Highlight, "#2e2619"),
        (QPalette.ColorRole.HighlightedText, GOLD_HI),
    ):
        pal.setColor(role, QColor(color))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET)
