"""Visualizador do mapa com zoom/arraste e marcadores clicáveis (modo manual)."""

from __future__ import annotations

from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QCursor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from nrseed.ui import theme


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return QPixmap.fromImage(ImageQt(img).copy())


class Marker(QGraphicsEllipseItem):
    """Ponto clicável do modo manual."""

    def __init__(self, key, center: QPointF, radius: float, view: MapView, kind: str = "poi") -> None:
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.key = key
        self.kind = kind
        self.view = view
        self.setPos(center)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setZValue(10)
        self.icon_item: QGraphicsPixmapItem | None = None
        self.state = "idle"
        self._apply()

    def _apply(self, hover: bool = False) -> None:
        if self.kind == "boss":
            base = QColor(200, 70, 60)
        elif self.kind == "castle":
            base = QColor(120, 140, 220)
        else:
            base = QColor(theme.GOLD)
        if self.state == "set":
            pen = QPen(QColor(theme.GOLD_HI), 2.2)
            brush = QBrush(QColor(0, 0, 0, 0))
        elif self.state == "inferred":
            pen = QPen(QColor(base.red(), base.green(), base.blue(), 120), 1.4, Qt.PenStyle.DashLine)
            brush = QBrush(QColor(0, 0, 0, 0))
        else:
            pen = QPen(base.lighter(130) if hover else base, 2.0)
            fill = QColor(base)
            fill.setAlpha(110 if hover else 55)
            brush = QBrush(fill)
        self.setPen(pen)
        self.setBrush(brush)

    def set_state(self, state: str, icon: QPixmap | None = None, inferred_icon: bool = False) -> None:
        self.state = state
        if self.icon_item is not None:
            self.scene().removeItem(self.icon_item)
            self.icon_item = None
        if icon is not None:
            item = QGraphicsPixmapItem(icon)
            item.setOffset(-icon.width() / 2, -icon.height() / 2)
            item.setPos(self.pos())
            item.setZValue(9)
            item.setOpacity(0.55 if inferred_icon else 1.0)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.scene().addItem(item)
            self.icon_item = item
        self._apply()

    def hoverEnterEvent(self, e):  # noqa: N802
        self._apply(True)

    def hoverLeaveEvent(self, e):  # noqa: N802
        self._apply(False)

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self.view.marker_clicked.emit(self.key, e.screenPos(), e.button() == Qt.MouseButton.RightButton)
            e.accept()
            return
        super().mousePressEvent(e)


class MapView(QGraphicsView):
    marker_clicked = pyqtSignal(object, object, bool)  # key, QPoint global, botão direito

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor(theme.MAP_BG))
        self._pix: QGraphicsPixmapItem | None = None
        self._frame: QGraphicsRectItem | None = None
        self.markers: dict[object, Marker] = {}
        self.placeholder = ("Abra o mapa no jogo (tecla M)", "A seed aparece aqui automaticamente")
        self._auto_fit = True

    # ------------------------------------------------------------ conteúdo
    def set_image(self, img: Image.Image | None, keep_view: bool = False) -> None:
        sc = self.scene()
        old_size = self._pix.pixmap().width() if self._pix else None
        self.clear_markers()
        if self._pix:
            sc.removeItem(self._pix)
            self._pix = None
        if img is None:
            sc.setSceneRect(QRectF())
            self.viewport().update()
            return
        pm = pil_to_pixmap(img)
        self._pix = sc.addPixmap(pm)
        self._pix.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._frame = None
        m = pm.width() * 0.02
        sc.setSceneRect(QRectF(-m, -m, pm.width() + 2 * m, pm.height() + 2 * m))
        if not (keep_view and old_size == pm.width()) or self._auto_fit:
            self.fit()

    def has_image(self) -> bool:
        return self._pix is not None

    def image_width(self) -> int:
        return self._pix.pixmap().width() if self._pix else 0

    def clear_markers(self) -> None:
        for mk in self.markers.values():
            if mk.icon_item is not None:
                self.scene().removeItem(mk.icon_item)
            self.scene().removeItem(mk)
        self.markers = {}

    def add_marker(self, key, x: float, y: float, radius: float, kind: str = "poi") -> Marker:
        mk = Marker(key, QPointF(x, y), radius, self, kind)
        self.scene().addItem(mk)
        self.markers[key] = mk
        return mk

    # ------------------------------------------------------------ navegação
    def fit(self) -> None:
        if self._pix:
            self._auto_fit = True
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, e):  # noqa: N802
        if not self._pix:
            return
        factor = 1.18 if e.angleDelta().y() > 0 else 1 / 1.18
        cur = self.transform().m11()
        fit_scale = min(self.viewport().width(), self.viewport().height()) / max(1.0, self.scene().sceneRect().width())
        new = max(fit_scale * 0.9, min(cur * factor, fit_scale * 6))
        self.scale(new / cur, new / cur)
        self._auto_fit = False

    def mouseDoubleClickEvent(self, e):  # noqa: N802
        item = self.itemAt(e.position().toPoint())
        if not isinstance(item, Marker):
            self.fit()
        super().mouseDoubleClickEvent(e)

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        if self._auto_fit:
            self.fit()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        if self._pix is not None:
            return
        painter.save()
        painter.resetTransform()
        vr = self.viewport().rect()
        c = vr.center()
        # Brasão simples: círculo duplo dourado
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = min(vr.width(), vr.height()) * 0.16
        painter.setPen(QPen(QColor(theme.BORDER_HI), 1.5))
        painter.drawEllipse(QPointF(c.x(), c.y() - r * 0.6), r, r)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawEllipse(QPointF(c.x(), c.y() - r * 0.6), r * 0.82, r * 0.82)
        painter.setPen(QColor(theme.GOLD))
        painter.setFont(theme.title_font(20))
        painter.drawText(
            QRectF(vr.left(), c.y() + r * 0.6, vr.width(), 40), Qt.AlignmentFlag.AlignCenter, self.placeholder[0]
        )
        painter.setPen(QColor(theme.MUTED))
        f = painter.font()
        f.setFamily(theme.BODY_FAMILY)
        f.setPointSize(10)
        painter.setFont(f)
        painter.drawText(
            QRectF(vr.left(), c.y() + r * 0.6 + 40, vr.width(), 30), Qt.AlignmentFlag.AlignCenter, self.placeholder[1]
        )
        painter.restore()


# Evita warning de import não usado em alguns linters
_ = QGraphicsItem
