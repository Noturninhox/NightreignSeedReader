"""Cartões da barra lateral (resultado e modo manual)."""

from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw
from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nrseed.gamedata import (
    NIGHTLORDS,
    TERRAINS,
    SeedSummary,
    epithet,
    nightlord_icon_path,
    nightlord_label,
    terrain_icon_path,
    terrain_name,
)
from nrseed.ui import theme
from nrseed.ui.mapview import pil_to_pixmap
from nrseed.ui.ornate import draw_ornate_frame


@lru_cache(maxsize=32)
def portrait(nl: int | None, size: int) -> QPixmap:
    icon = Image.open(nightlord_icon_path(nl)).convert("RGBA").resize((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size + 8, size + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse((0, 0, size + 7, size + 7), outline=(120, 105, 210, 120), width=3)
    d.ellipse((1, 1, size + 6, size + 6), outline=(190, 178, 255, 255), width=2)
    canvas.alpha_composite(icon, (4, 4))
    return pil_to_pixmap(canvas)


@lru_cache(maxsize=12)
def terrain_thumb(es: int, size: int) -> QPixmap:
    img = Image.open(terrain_icon_path(es)).convert("RGBA")
    w, h = img.size
    img = img.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9))).resize((size, size), Image.LANCZOS)
    return pil_to_pixmap(img)


class Card(QFrame):
    """Painel translúcido com moldura gótica (cantos ornamentados e estrela embaixo)."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 16)
        lay.setSpacing(6)
        t = QLabel(title.upper())
        t.setObjectName("CardTitle")
        t.setFont(theme.title_font(10, 600))
        lay.addWidget(t)
        self.body = lay

    def paintEvent(self, e):  # noqa: N802
        p = QPainter(self)
        draw_ornate_frame(p, QRectF(self.rect()).adjusted(1, 1, -1, -8), fill_alpha=190)


def _label(text: str = "", obj: str = "Value", wrap: bool = True) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName(obj)
    lb.setWordWrap(wrap)
    lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lb


class NightlordCard(Card):
    def __init__(self) -> None:
        super().__init__("Nightlord")
        row = QHBoxLayout()
        row.setSpacing(12)
        self.pic = QLabel()
        self.pic.setFixedSize(100, 100)
        row.addWidget(self.pic)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.name = QLabel("—")
        self.name.setObjectName("Big")
        self.name.setFont(theme.title_font(18, 600))
        self.epithet = _label("", "Muted")
        self.note = _label("", "Night")
        col.addStretch()
        col.addWidget(self.name)
        col.addWidget(self.epithet)
        col.addWidget(self.note)
        col.addStretch()
        row.addLayout(col, 1)
        self.body.addLayout(row)
        self.set(None, None)

    def set(self, nl: int | None, seen: int | None, known: bool = False) -> None:
        self.pic.setPixmap(portrait(nl, 90))
        if nl is None:
            self.name.setText("Desconhecido")
            self.epithet.setText("Abra o mapa para identificar")
            self.note.setText("")
            return
        name = NIGHTLORDS.get(nl, (str(nl), ""))[0]
        self.name.setText(name)
        self.epithet.setText(epithet(nl))
        if known and seen is None:
            self.note.setText("Retrato oculto — deduzido pelo mapa")
        elif known and seen != nl:
            self.note.setText("Deduzido pelas marcações do mapa")
        else:
            self.note.setText("")


class SeedCard(Card):
    def __init__(self) -> None:
        super().__init__("Seed")
        row = QHBoxLayout()
        self.seed = QLabel("#—")
        self.seed.setObjectName("Big")
        self.seed.setFont(theme.title_font(36, 500))
        self.seed.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(self.seed)
        row.addStretch()
        self.conf = _label("", "Muted", wrap=False)
        self.conf.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.conf)
        self.body.addLayout(row)
        trow = QHBoxLayout()
        trow.setSpacing(10)
        self.thumb = QLabel()
        self.thumb.setFixedSize(40, 40)
        trow.addWidget(self.thumb)
        tcol = QVBoxLayout()
        tcol.setSpacing(0)
        self.terrain = _label("—", "Value")
        self.terrain_pt = _label("", "Muted")
        tcol.addWidget(self.terrain)
        tcol.addWidget(self.terrain_pt)
        trow.addLayout(tcol, 1)
        self.body.addLayout(trow)

    def set(self, s: SeedSummary | None, confidence: str = "") -> None:
        if s is None:
            self.seed.setText("#—")
            self.terrain.setText("—")
            self.terrain_pt.setText("")
            self.thumb.clear()
            self.conf.setText("")
            return
        self.seed.setText(f"#{s.seed_id}")
        self.terrain.setText(terrain_name(s.terrain))
        self.terrain_pt.setText(terrain_name(s.terrain, other=True))
        self.thumb.setPixmap(terrain_thumb(s.terrain, 40))
        self.conf.setText(confidence)


class InfoCard(Card):
    def __init__(self) -> None:
        super().__init__("Chefes & evento")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        def key(t):
            lb = QLabel(t)
            lb.setObjectName("Muted")
            return lb

        self.day1 = _label("—")
        self.day2 = _label("—")
        self.event = _label("—", "Event")
        d1, d2 = key("Dia 1"), key("Dia 2")
        for w in (d1, d2):
            w.setStyleSheet("color: #b9a8ff; font-weight: 600;")
        grid.addWidget(d1, 0, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.day1, 0, 1)
        grid.addWidget(d2, 1, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.day2, 1, 1)
        grid.addWidget(key("Evento"), 2, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.event, 2, 1)
        grid.setColumnStretch(1, 1)
        self.body.addLayout(grid)

    def set(self, s: SeedSummary | None) -> None:
        if s is None:
            for w in (self.day1, self.day2, self.event):
                w.setText("—")
            return
        self.day1.setText(s.day1 + (f"  +  {s.day1_extra}" if s.day1_extra else ""))
        self.day2.setText(s.day2 + (f"  +  {s.day2_extra}" if s.day2_extra else ""))
        self.event.setText(s.event or "Nenhum")


class CandidatesCard(Card):
    picked = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__("Candidatos")
        self.hint = _label("A melhor correspondência fica no topo. Clique para trocar.", "Muted")
        self.body.addWidget(self.hint)
        self.list = QListWidget()
        self.list.setIconSize(QSize(26, 26))
        self.list.setMinimumHeight(120)
        self.list.itemClicked.connect(lambda it: self.picked.emit(it.data(Qt.ItemDataRole.UserRole)))
        self.body.addWidget(self.list)

    def set(self, rows: list[tuple[int, int, str]], current: int | None) -> None:
        """rows: (seed_id, nightlord, texto extra)."""
        self.list.clear()
        for sid, nl, extra in rows:
            it = QListWidgetItem(QIcon(portrait(nl, 22)), f"#{sid}   {NIGHTLORDS.get(nl, ('?',))[0]}   {extra}")
            it.setData(Qt.ItemDataRole.UserRole, sid)
            self.list.addItem(it)
            if sid == current:
                it.setSelected(True)
        h = min(6, max(2, len(rows))) * 34 + 6
        self.list.setFixedHeight(h)


class ManualPanel(QWidget):
    """Seleção de Nightlord e mapa (Terra Mutável), igual ao início do site."""

    changed = pyqtSignal()
    clear_requested = pyqtSignal()
    from_capture = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        c1 = Card("1 · Nightlord")
        grid = QGridLayout()
        grid.setSpacing(6)
        self.nl_group = QButtonGroup(self)
        self.nl_group.setExclusive(True)
        options: list[int | None] = [None, *NIGHTLORDS.keys()]
        for i, nl in enumerate(options):
            b = QPushButton()
            b.setObjectName("Choice")
            b.setCheckable(True)
            b.setIcon(QIcon(portrait(nl, 40)))
            b.setIconSize(QSize(44, 44))
            b.setFixedSize(54, 54)
            b.setToolTip("Desconhecido / oculto" if nl is None else nightlord_label(nl))
            b.setProperty("nl", nl)
            self.nl_group.addButton(b, i)
            grid.addWidget(b, i // 4, i % 4)
        self.nl_group.button(0).setChecked(True)
        self.nl_group.buttonClicked.connect(lambda _b: self.changed.emit())
        c1.body.addLayout(grid)
        self.nl_name = _label("Desconhecido (qualquer Nightlord)", "Muted")
        c1.body.addWidget(self.nl_name)
        lay.addWidget(c1)

        c2 = Card("2 · Mapa")
        g2 = QGridLayout()
        g2.setSpacing(6)
        self.es_group = QButtonGroup(self)
        for i, es in enumerate(TERRAINS):
            b = QPushButton(terrain_name(es))
            b.setObjectName("Choice")
            b.setCheckable(True)
            b.setIcon(QIcon(terrain_thumb(es, 34)))
            b.setIconSize(QSize(34, 34))
            b.setMinimumHeight(44)
            b.setToolTip(terrain_name(es, other=True))
            b.setProperty("es", es)
            b.setStyleSheet("text-align: left; padding-left: 6px;")
            self.es_group.addButton(b, i)
            g2.addWidget(b, i // 2, i % 2)
        self.es_group.button(0).setChecked(True)
        self.es_group.buttonClicked.connect(lambda _b: self.changed.emit())
        c2.body.addLayout(g2)
        lay.addWidget(c2)

        c3 = Card("3 · Marque os POIs")
        self.help = _label(
            "Clique nos círculos do mapa e escolha o ícone que aparece no jogo "
            "(igreja, forte, ruína…). Vermelho = chefe de campo, azul = castelo. "
            "Normalmente 2–3 marcações bastam.",
            "Muted",
        )
        c3.body.addWidget(self.help)
        self.remaining = QLabel("Seeds restantes: —")
        self.remaining.setObjectName("Big")
        self.remaining.setFont(theme.title_font(13, 700))
        c3.body.addWidget(self.remaining)
        row = QHBoxLayout()
        self.btn_clear = QPushButton("Limpar marcações")
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        self.btn_capture = QPushButton("Usar última leitura")
        self.btn_capture.setToolTip("Preenche Nightlord e mapa com o que foi lido da tela")
        self.btn_capture.clicked.connect(self.from_capture.emit)
        row.addWidget(self.btn_clear)
        row.addWidget(self.btn_capture)
        c3.body.addLayout(row)
        lay.addWidget(c3)
        lay.addStretch()

    def retranslate(self) -> None:
        for b in self.es_group.buttons():
            es = b.property("es")
            b.setText(terrain_name(es))
            b.setToolTip(terrain_name(es, other=True))
        self.update_counts_text()

    def update_counts_text(self) -> None:
        nl = self.nightlord()
        self.nl_name.setText("Desconhecido (qualquer Nightlord)" if nl is None else nightlord_label(nl))
        for b in self.nl_group.buttons():
            v = b.property("nl")
            b.setToolTip("Desconhecido / oculto" if v is None else nightlord_label(v))

    def nightlord(self) -> int | None:
        b = self.nl_group.checkedButton()
        return b.property("nl") if b else None

    def terrain(self) -> int:
        b = self.es_group.checkedButton()
        return b.property("es") if b else 0

    def select(self, nl: int | None, es: int | None) -> None:
        for b in self.nl_group.buttons():
            if b.property("nl") == nl:
                b.setChecked(True)
        if es is not None:
            for b in self.es_group.buttons():
                if b.property("es") == es:
                    b.setChecked(True)

    def update_counts(self, n: int) -> None:
        nl = self.nightlord()
        self.nl_name.setText("Desconhecido (qualquer Nightlord)" if nl is None else nightlord_label(nl))
        self.remaining.setText(f"Seeds restantes: {n}")
