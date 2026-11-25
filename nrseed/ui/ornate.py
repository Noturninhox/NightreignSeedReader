"""Visual gótico: fundo com a arte do app e molduras ornamentadas (cantos e estrela)."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget

from nrseed.ui import theme

# Posição do anel (portal) dentro da arte original background.jpg (em pixels da imagem)
ART_RING_CENTER = (964.0, 860.0)
ART_RING_RADIUS = 350.0  # até a ponta dos espinhos


def star4(p: QPainter, c: QPointF, r: float, color: QColor) -> None:
    """Estrela de 4 pontas (ornamento das molduras)."""
    path = QPainterPath()
    pts = []
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.28
        pts.append(QPointF(c.x() + rr * math.cos(a), c.y() + rr * math.sin(a)))
    path.moveTo(pts[0])
    for q in pts[1:]:
        path.lineTo(q)
    path.closeSubpath()
    glow = QRadialGradient(c, r * 1.6)
    g = QColor(color)
    g.setAlpha(90)
    glow.setColorAt(0, g)
    glow.setColorAt(1, QColor(0, 0, 0, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(glow))
    p.drawEllipse(c, r * 1.6, r * 1.6)
    p.setBrush(color)
    p.drawPath(path)


def _corner(p: QPainter, x: float, y: float, sx: int, sy: int, size: float, pen: QPen) -> None:
    """Floreio de canto: duas hastes, curva interna e um losango."""
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    L = size
    # hastes duplas ao longo das bordas
    p.drawLine(QPointF(x, y + sy * L), QPointF(x, y))
    p.drawLine(QPointF(x, y), QPointF(x + sx * L, y))
    p.drawLine(QPointF(x + sx * 4, y + sy * L * 0.7), QPointF(x + sx * 4, y + sy * 4))
    p.drawLine(QPointF(x + sx * 4, y + sy * 4), QPointF(x + sx * L * 0.7, y + sy * 4))
    # curva (voluta)
    path = QPainterPath(QPointF(x + sx * L * 0.55, y + sy * 4))
    path.cubicTo(QPointF(x + sx * L * 0.35, y + sy * 12), QPointF(x + sx * 12, y + sy * L * 0.35),
                 QPointF(x + sx * 4, y + sy * L * 0.55))
    p.drawPath(path)
    # losango na ponta
    d = 2.6
    c = QPointF(x + sx * 9, y + sy * 9)
    p.setBrush(pen.color())
    p.drawPolygon([QPointF(c.x(), c.y() - d), QPointF(c.x() + d, c.y()), QPointF(c.x(), c.y() + d),
                   QPointF(c.x() - d, c.y())])


def draw_ornate_frame(p: QPainter, r: QRectF, fill_alpha: int = 200, star_bottom: bool = True,
                      corner: float = 22, strong: bool = False) -> None:
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if fill_alpha:
        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0, QColor(18, 15, 36, fill_alpha))
        grad.setColorAt(1, QColor(9, 8, 20, fill_alpha))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(r, 3, 3)
    line = QColor(theme.BORDER_HI)
    line.setAlpha(170 if strong else 120)
    p.setPen(QPen(line, 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(r, 3, 3)
    inner = QColor(theme.BORDER_HI)
    inner.setAlpha(45)
    p.setPen(QPen(inner, 1.0))
    p.drawRect(r.adjusted(4, 4, -4, -4))
    accent = QColor(theme.GOLD)
    accent.setAlpha(220)
    pen = QPen(accent, 1.2)
    _corner(p, r.left() + 1, r.top() + 1, 1, 1, corner, pen)
    _corner(p, r.right() - 1, r.top() + 1, -1, 1, corner, pen)
    _corner(p, r.left() + 1, r.bottom() - 1, 1, -1, corner, pen)
    _corner(p, r.right() - 1, r.bottom() - 1, -1, -1, corner, pen)
    if star_bottom:
        star4(p, QPointF(r.center().x(), r.bottom()), 7, QColor(theme.GOLD_HI))
    p.restore()


class OrnateBackground(QWidget):
    """Widget raiz: pinta a arte cobrindo a janela + escurecimentos + moldura da janela."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("root")
        self._art = QPixmap(str(theme.asset("background.jpg")))
        self._scaled: QPixmap | None = None
        self._scaled_for = None
        self.anchor_widget: QWidget | None = None  # o anel é centralizado neste widget (o mapa)
        self.dim = 0.0  # 0..1 escurece a arte (quando o mapa está aberto)
        self._ring = None

    def ring_rect(self) -> QRectF | None:
        """Retângulo do anel da arte, em coordenadas deste widget."""
        return self._ring

    def _layout_art(self) -> tuple[float, float, float]:
        """A arte cobre a área do mapa (do mapa até a borda direita), centralizada nela."""
        W, H = self.width(), self.height()
        iw, ih = self._art.width(), self._art.height()
        left = 0
        if self.anchor_widget is not None and self.anchor_widget.isVisible():
            left = self.anchor_widget.mapTo(self, self.anchor_widget.rect().topLeft()).x()
        area_w = max(1, W - left)
        s = max(H / ih, area_w / iw)
        ox = left + (area_w - iw * s) / 2
        oy = (H - ih * s) * 0.45
        return s, ox, oy

    def paintEvent(self, e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        W, H = self.width(), self.height()
        if not self._art.isNull():
            s, ox, oy = self._layout_art()
            key = (round(self._art.width() * s), round(self._art.height() * s))
            if self._scaled_for != key:
                self._scaled = self._art.scaled(key[0], key[1], Qt.AspectRatioMode.IgnoreAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
                self._scaled_for = key
            p.drawPixmap(round(ox), round(oy), self._scaled)
            # à esquerda da arte (atrás da lateral): continua com um espelho escurecido
            if ox > 0:
                aw = self._scaled.width()
                p.save()
                p.translate(round(ox), 0)
                p.scale(-1, 1)
                p.drawPixmap(0, round(oy), self._scaled)
                p.restore()
                g = QLinearGradient(0, 0, ox, 0)
                g.setColorAt(0, QColor(6, 5, 14, 200))
                g.setColorAt(1, QColor(6, 5, 14, 90))
                p.fillRect(QRectF(0, 0, ox, H), QBrush(g))
                _ = aw
            r = ART_RING_RADIUS * s
            self._ring = QRectF(ox + ART_RING_CENTER[0] * s - r, oy + ART_RING_CENTER[1] * s - r, 2 * r, 2 * r)
        else:
            p.fillRect(self.rect(), QColor(theme.BG))
        # escurece em cima (cabeçalho) e embaixo (rodapé)
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(4, 3, 10, 225))
        g.setColorAt(0.09, QColor(4, 3, 10, 60))
        g.setColorAt(0.85, QColor(4, 3, 10, 30))
        g.setColorAt(1.0, QColor(4, 3, 10, 200))
        p.fillRect(self.rect(), QBrush(g))
        if self.dim > 0:
            p.fillRect(self.rect(), QColor(4, 3, 10, int(170 * self.dim)))
        # moldura fina da janela com cantos ornamentados
        draw_ornate_frame(p, QRectF(5, 5, W - 10, H - 10), fill_alpha=0, star_bottom=True, corner=34)
