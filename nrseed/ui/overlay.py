"""Overlay transparente sobre o mapa do jogo + seletor de região para calibração."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

from nrseed.ui import theme


def _dpr_at(x: int, y: int) -> float:
    screen = QGuiApplication.screenAt(QPoint(x, y)) or QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def physical_to_logical(rect) -> QRect:
    """mss/Win32 usam pixels físicos; Qt posiciona janelas em pixels lógicos."""
    x, y, w, h = rect
    if sys.platform != "win32":
        return QRect(x, y, w, h)
    for screen in QGuiApplication.screens():
        g = screen.geometry()
        dpr = screen.devicePixelRatio()
        phys = QRect(g.x(), g.y(), round(g.width() * dpr), round(g.height() * dpr))
        if phys.contains(x + w // 2, y + h // 2):
            return QRect(
                round(g.x() + (x - g.x()) / dpr), round(g.y() + (y - g.y()) / dpr), round(w / dpr), round(h / dpr)
            )
    return QRect(x, y, w, h)


class GameOverlay(QWidget):
    """Janela sem bordas, transparente e que ignora o mouse, colocada exatamente sobre o mapa."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._pix: QPixmap | None = None

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        if sys.platform == "win32":
            # Some da captura de tela (inclusive do nosso próprio leitor e do OBS): evita
            # que os rótulos atrapalhem a próxima leitura e evita spoiler em live.
            import ctypes

            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x11)  # WDA_EXCLUDEFROMCAPTURE

    def set_pixmap(self, pm: QPixmap | None) -> None:
        self._pix = pm
        self.update()

    def place(self, rect) -> None:
        self.setGeometry(physical_to_logical(rect))

    def paintEvent(self, e):  # noqa: N802
        if self._pix is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._pix)


class RegionSelector(QWidget):
    """Tela cheia escurecida para arrastar um quadrado em volta do mapa do jogo."""

    selected = pyqtSignal(object)  # (x, y, w, h) físico ou None

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        geo = QRect()
        for s in QGuiApplication.screens():
            geo = geo.united(s.geometry())
        self.setGeometry(geo)
        self._a: QPoint | None = None
        self._b: QPoint | None = None

    def _square(self) -> QRect | None:
        if self._a is None or self._b is None:
            return None
        side = max(abs(self._b.x() - self._a.x()), abs(self._b.y() - self._a.y()))
        x = self._a.x() if self._b.x() >= self._a.x() else self._a.x() - side
        y = self._a.y() if self._b.y() >= self._a.y() else self._a.y() - side
        return QRect(x, y, side, side)

    def paintEvent(self, e):  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        p.setPen(QColor(theme.GOLD_HI))
        p.setFont(theme.title_font(16))
        p.drawText(
            self.rect().adjusted(0, 40, 0, 0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "Abra o mapa no jogo e arraste um quadrado em volta dele  ·  Esc cancela",
        )
        sq = self._square()
        if sq:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(sq, Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p.setPen(QPen(QColor(theme.GOLD), 2))
            p.drawRect(sq)

    def mousePressEvent(self, e):  # noqa: N802
        self._a = self._b = e.position().toPoint()
        self.update()

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._a is not None:
            self._b = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802
        sq = self._square()
        self.close()
        if not sq or sq.width() < 100:
            self.selected.emit(None)
            return
        top_left = self.mapToGlobal(sq.topLeft())
        dpr = _dpr_at(top_left.x(), top_left.y()) if sys.platform == "win32" else 1.0
        screen = QGuiApplication.screenAt(top_left) or QGuiApplication.primaryScreen()
        g = screen.geometry()
        px = round(g.x() + (top_left.x() - g.x()) * dpr)
        py = round(g.y() + (top_left.y() - g.y()) * dpr)
        self.selected.emit((px, py, round(sq.width() * dpr), round(sq.height() * dpr)))

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self.close()
            self.selected.emit(None)
