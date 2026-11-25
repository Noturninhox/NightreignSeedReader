"""Modo manual estilo nightreign-seed-finder.com: escolha Nightlord + mapa e marque os POIs."""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu

from nrseed.engine.detector import STD_POI_SIZE, Attribute, Condition
from nrseed.engine.manual_catalog import (
    EMPTY,
    UNSET,
    ManualFilterCatalog,
    NamedPoint,
    PoiChoice,
)
from nrseed.engine.map_info import STD_MAP_SIZE
from nrseed.render import _terrain_bg
from nrseed.ui.mapview import MapView, pil_to_pixmap

GROUP_NAMES = {
    30: "Forte",
    32: "Acampamento",
    34: "Ruínas",
    37: "Vilarejo",
    38: "Grande Igreja",
    40: "Torre do Feiticeiro",
    41: "Igreja",
    500: "Pântano (DLC)",
    501: "Vila de Ferraria (DLC)",
    535: "Forte (DLC)",
    536: "Fortaleza (DLC)",
}
SUBICON_NAMES = {
    Attribute.FIRE: "Fogo",
    Attribute.MAGIC: "Magia",
    Attribute.THUNDER: "Raio",
    Attribute.HOLY: "Sagrado",
    Condition.BLEED: "Sangramento",
    Condition.FROST: "Congelamento",
    Condition.DEATH: "Morte",
    Condition.FRENZY: "Frenesi",
    Condition.CORRUPTION: "Podridão escarlate",
    Condition.POISON: "Veneno",
    Condition.SLEEP: "Sono",
}

SIZE = 1100


class ManualController(QObject):
    counts = pyqtSignal(int)
    candidates_changed = pyqtSignal(list)  # list[MapPattern]
    found = pyqtSignal(int, object)  # pattern_id, nightlord

    def __init__(self, view: MapView) -> None:
        super().__init__()
        self.view = view
        self.catalog = ManualFilterCatalog.load("pt_BR")
        self.es = 0
        self.nl: int | None = None
        self.explicit: dict[object, PoiChoice] = {}
        self.view.marker_clicked.connect(self._on_marker)
        self.active = False

    # ------------------------------------------------------------ estado
    def setup(self, es: int, nl: int | None, keep: bool = False) -> None:
        changed = (es, nl) != (self.es, self.nl)
        self.es, self.nl = es, nl
        if changed or not keep:
            self.explicit = {}
        self.redraw()

    def clear(self) -> None:
        self.explicit = {}
        self.redraw()

    def redraw(self) -> None:
        self.view.placeholder = ("Modo manual", "Escolha o Nightlord e o mapa")
        self.view.set_image(_terrain_bg(self.es, SIZE), keep_view=True)
        k = SIZE / STD_MAP_SIZE[0]
        r = STD_POI_SIZE[0] * k * 0.42
        for key in self.catalog.filter_positions(self.es, self.nl):
            if isinstance(key, NamedPoint):
                x, y = key.pos
                dx = -r * 1.6 if key.kind == "castle" else 0
                self.view.add_marker(key, x * k + dx, y * k, r * (0.75 if key.kind == "boss" else 0.9), key.kind)
            else:
                x, y = key
                self.view.add_marker(key, x * k, y * k, r, "poi")
        self._refresh()

    def _icon_for(self, choice: PoiChoice, scale: float = 1.0) -> Image.Image | None:
        if choice.base == EMPTY:
            return None
        img = self.catalog.base_image(choice.base).copy()
        if choice.subicon not in (UNSET, None):
            sub = self.catalog.subicon_image(choice.subicon)
            s = int(img.size[0] * 0.42)
            img.alpha_composite(sub.resize((s, s), Image.LANCZOS), (img.size[0] - s, img.size[1] - s))
        px = max(10, int(STD_POI_SIZE[0] * SIZE / STD_MAP_SIZE[0] * scale))
        return img.resize((px, px), Image.LANCZOS)

    def _refresh(self) -> None:
        cands = self.catalog.candidates(self.es, self.nl, self.explicit)
        positions = list(self.view.markers)
        inferred = self.catalog.inferred(cands, positions, self.explicit)
        for key, mk in self.view.markers.items():
            choice = self.explicit.get(key)
            if choice is not None:
                if isinstance(key, NamedPoint):
                    mk.set_state("set")
                    name = self.catalog.info.get_name(choice.base) if choice.base != EMPTY else "Nenhum"
                    mk.setToolTip(f"Marcado: {name}")
                else:
                    icon = self._icon_for(choice)
                    mk.set_state("set", pil_to_pixmap(icon) if icon else None)
                    mk.setToolTip(f"Marcado: {GROUP_NAMES.get(choice.base, 'Vazio')}")
            elif key in inferred and not isinstance(key, NamedPoint):
                icon = self._icon_for(inferred[key], 0.9)
                mk.set_state("inferred", pil_to_pixmap(icon) if icon else None, inferred_icon=True)
                mk.setToolTip("Todas as seeds restantes têm isto aqui")
            else:
                mk.set_state("idle")
                mk.setToolTip("Chefe de campo" if getattr(key, "kind", "") == "boss" else
                              "Castelo" if getattr(key, "kind", "") == "castle" else "Clique para marcar o POI")
        self.counts.emit(len(cands))
        self.candidates_changed.emit(cands)
        if len(cands) == 1 and self.explicit:
            self.found.emit(cands[0].id, self.nl if self.nl is not None else cands[0].nightlord)

    # ------------------------------------------------------------ menus
    def _on_marker(self, key, global_pos, right: bool) -> None:
        if right:
            self.explicit.pop(key, None)
            self._refresh()
            return
        menu = QMenu()
        title = menu.addAction("O que aparece aqui no jogo?")
        title.setEnabled(False)
        menu.addSeparator()
        if isinstance(key, NamedPoint):
            for val in self.catalog.named_options(self.es, self.nl, self.explicit, key):
                text = "Nenhum" if val == EMPTY else (self.catalog.info.get_name(val) or str(val))
                act = menu.addAction(text)
                act.setData(PoiChoice(val, None))
        else:
            for base in self.catalog.base_options(self.es, self.nl, self.explicit, key):
                if base == EMPTY:
                    act = menu.addAction("Vazio (nada aqui)")
                    act.setData(("base", EMPTY))
                    continue
                subs = self.catalog.subicon_options(self.es, self.nl, self.explicit, key, base)
                icon = QIcon(pil_to_pixmap(self.catalog.base_image(base).resize((36, 36), Image.LANCZOS)))
                name = GROUP_NAMES.get(base, str(base))
                if len(subs) <= 1:
                    act = menu.addAction(icon, name)
                    act.setData(("base", base, subs[0] if subs else None))
                else:
                    sm = menu.addMenu(icon, name)
                    any_act = sm.addAction("Qualquer variante")
                    any_act.setData(("base", base, UNSET))
                    sm.addSeparator()
                    for sub in subs:
                        if sub is None:
                            a = sm.addAction("Sem ícone de elemento")
                        else:
                            si = QIcon(pil_to_pixmap(self.catalog.subicon_image(sub).resize((22, 22), Image.LANCZOS)))
                            a = sm.addAction(si, SUBICON_NAMES.get(sub, str(sub)))
                        a.setData(("base", base, sub))
        if key in self.explicit:
            menu.addSeparator()
            rm = menu.addAction("Remover marcação")
            rm.setData("remove")
        act = menu.exec(global_pos)
        if act is None or act.data() is None:
            return
        data = act.data()
        if data == "remove":
            self.explicit.pop(key, None)
        elif isinstance(data, PoiChoice):
            self.explicit[key] = data
        elif data[0] == "base":
            base = data[1]
            sub = data[2] if len(data) > 2 else None
            self.explicit[key] = PoiChoice(base, None if base == EMPTY else sub)
        self._refresh()
