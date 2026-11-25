"""Janela principal — pensada para ficar aberta no segundo monitor."""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QSettings, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from nrseed import __version__
from nrseed.gamedata import NIGHTLORDS, TERRAINS, summarize
from nrseed.ui import theme
from nrseed.ui.manual import ManualController
from nrseed.ui.mapview import MapView, pil_to_pixmap
from nrseed.ui.overlay import GameOverlay, RegionSelector
from nrseed.ui.sidebar import CandidatesCard, InfoCard, ManualPanel, NightlordCard, SeedCard
from nrseed.worker import RecognitionResult, RecognizerWorker

RENDER_SIZE = 1400
STATUS_COLORS = {"ok": theme.OK, "wait": theme.WARN, "warn": theme.WARN, "err": theme.ERR}


def confidence_text(cands) -> str:
    """Confiança pela distância entre o 1º e o 2º candidato (menor diferença = melhor)."""
    if len(cands) < 2:
        return "✓ única"
    gap = cands[1].error - cands[0].error
    if gap >= 30:
        return "✓ confiança alta"
    if gap >= 10:
        return "≈ confiança média"
    return "⚠ confira candidatos"


class MainWindow(QMainWindow):
    req_render = pyqtSignal(int, object, int, object)
    req_recognize_now = pyqtSignal()
    req_recognize_image = pyqtSignal(object)
    req_manual_rect = pyqtSignal(object)
    req_only_foreground = pyqtSignal(bool)
    req_stop = pyqtSignal()

    def __init__(self, hotkeys=None) -> None:
        super().__init__()
        self.setWindowTitle("Nightreign Seed Reader")
        self.setMinimumSize(1000, 680)
        self.settings = QSettings("Noturninhox", "NightreignSeedReader")
        self.hotkeys = hotkeys

        self.current_id: int | None = None
        self.current_nl: int | None = None
        self.current_img: Image.Image | None = None
        self.last_recognition: RecognitionResult | None = None
        self.map_rect = None
        self.map_open = False
        self.overlay_pix = None

        self._build_ui()
        self._start_worker()
        self.overlay = GameOverlay()
        self.manual = ManualController(self.map_view)
        self.manual.counts.connect(self.manual_panel.update_counts)
        self.manual.candidates_changed.connect(self._manual_candidates)
        self.manual.found.connect(self._manual_found)
        self.manual_panel.changed.connect(self._manual_setup)
        self.manual_panel.clear_requested.connect(self.manual.clear)
        self.manual_panel.from_capture.connect(self._manual_from_capture)

        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(1400, 900)
            self._prefer_second_monitor()
        if hotkeys is not None:
            hotkeys.triggered.connect(self._on_hotkey)
            hotkeys.register(["F8", "F9", "F10"])

    # =========================================================== UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ---- cabeçalho
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(64)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 0, 16, 0)
        h.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(
            QPixmap(str(theme.asset("icon.png"))).scaled(
                44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        )
        h.addWidget(logo)
        tcol = QVBoxLayout()
        tcol.setSpacing(0)
        t = QLabel("NIGHTREIGN")
        t.setObjectName("AppTitle")
        t.setFont(theme.title_font(18, 700))
        s = QLabel("LEITOR DE SEED")
        s.setObjectName("AppSub")
        s.setFont(theme.title_font(8, 600))
        tcol.addStretch()
        tcol.addWidget(t)
        tcol.addWidget(s)
        tcol.addStretch()
        h.addLayout(tcol)
        h.addSpacing(24)

        self.tab_group = QButtonGroup(self)
        self.tab_result = QPushButton("Resultado")
        self.tab_manual = QPushButton("Busca manual")
        for i, b in enumerate((self.tab_result, self.tab_manual)):
            b.setObjectName("Tab")
            b.setCheckable(True)
            b.setFont(theme.title_font(10, 700))
            self.tab_group.addButton(b, i)
            h.addWidget(b)
        self.tab_result.setChecked(True)
        self.tab_group.idClicked.connect(self._set_tab)
        h.addStretch()

        pill = QFrame()
        pill.setObjectName("StatusPill")
        pill.setFixedHeight(30)
        ph = QHBoxLayout(pill)
        ph.setContentsMargins(10, 2, 12, 2)
        ph.setSpacing(8)
        self.status_dot = QLabel("●")
        self.status_text = QLabel("Iniciando…")
        self.status_text.setObjectName("StatusText")
        ph.addWidget(self.status_dot)
        ph.addWidget(self.status_text)
        h.addWidget(pill)

        self.btn_read = QPushButton("Ler agora  (F8)")
        self.btn_read.setObjectName("Primary")
        self.btn_read.clicked.connect(self._read_now)
        h.addWidget(self.btn_read)
        self.btn_overlay = QPushButton("Overlay no jogo  (F9)")
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.setChecked(self.settings.value("overlay", False, type=bool))
        self.btn_overlay.toggled.connect(self._overlay_toggled)
        h.addWidget(self.btn_overlay)
        self.btn_menu = QPushButton("☰")
        self.btn_menu.setFixedWidth(40)
        self.btn_menu.clicked.connect(self._open_menu)
        h.addWidget(self.btn_menu)
        v.addWidget(header)

        # ---- corpo
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        v.addLayout(body, 1)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(360)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        self.side_stack = QStackedWidget()
        sv.addWidget(self.side_stack)
        body.addWidget(side)

        # página resultado
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(14, 14, 14, 14)
        pv.setSpacing(10)
        self.nl_card = NightlordCard()
        self.seed_card = SeedCard()
        self.info_card = InfoCard()
        self.cand_card = CandidatesCard()
        self.cand_card.picked.connect(self._pick_candidate)
        for w in (self.nl_card, self.seed_card, self.info_card, self.cand_card):
            pv.addWidget(w)
        row = QHBoxLayout()
        self.btn_site = QPushButton("Abrir no site")
        self.btn_site.clicked.connect(self._open_site)
        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.clicked.connect(self._copy)
        self.btn_save = QPushButton("Salvar imagem")
        self.btn_save.clicked.connect(self._save_image)
        for b in (self.btn_site, self.btn_copy, self.btn_save):
            b.setEnabled(False)
            row.addWidget(b)
        pv.addLayout(row)
        pv.addStretch()
        self.side_stack.addWidget(self._scroll(page))

        # página manual
        mpage = QWidget()
        mv = QVBoxLayout(mpage)
        mv.setContentsMargins(14, 14, 14, 14)
        mv.setSpacing(10)
        self.manual_panel = ManualPanel()
        mv.addWidget(self.manual_panel)
        self.manual_cands = CandidatesCard()
        self.manual_cands.hint.setText("Quando sobrarem poucas, clique para ver a seed.")
        self.manual_cands.picked.connect(self._manual_pick)
        self.manual_cands.hide()
        mv.addWidget(self.manual_cands)
        mv.addStretch()
        self.side_stack.addWidget(self._scroll(mpage))

        self.map_view = MapView()
        body.addWidget(self.map_view, 1)

        # ---- rodapé
        foot = QLabel(
            "F8 ler agora  ·  F9 overlay no jogo  ·  F10 próximo candidato  ·  "
            "roda do mouse = zoom  ·  arrastar = mover  ·  duplo clique = ajustar"
        )
        foot.setObjectName("Muted")
        foot.setContentsMargins(16, 6, 16, 6)
        foot.setStyleSheet(f"background:{theme.PANEL}; border-top:1px solid {theme.BORDER};")
        v.addWidget(foot)

        QShortcut(QKeySequence("F8"), self, activated=self._read_now)
        QShortcut(QKeySequence("F10"), self, activated=self._next_candidate)

    def _scroll(self, w: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sa.setWidget(w)
        return sa

    def _prefer_second_monitor(self) -> None:
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        other = next((s for s in screens if s is not primary), None)
        if other is not None:
            g = other.availableGeometry()
            self.setGeometry(g.adjusted(40, 40, -40, -40))

    # =========================================================== worker
    def _start_worker(self) -> None:
        self.thread = QThread(self)
        self.worker = RecognizerWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.rendered.connect(self._on_rendered)
        self.worker.map_visible.connect(self._on_map_visible)
        self.worker.recognizing.connect(lambda: self._on_status("wait", "Lendo o mapa…"))
        self.req_render.connect(self.worker.render)
        self.req_recognize_now.connect(self.worker.recognize_now)
        self.req_recognize_image.connect(self.worker.recognize_image)
        self.req_manual_rect.connect(self.worker.set_manual_rect)
        self.req_only_foreground.connect(self.worker.set_only_foreground)
        self.req_stop.connect(self.worker.stop)
        self.worker.ready.connect(self._worker_ready)
        self.thread.start()

    def _worker_ready(self) -> None:
        rect = self.settings.value("manual_rect")
        if rect:
            self.req_manual_rect.emit([int(x) for x in rect])
        self.req_only_foreground.emit(self.settings.value("only_foreground", True, type=bool))

    # =========================================================== eventos
    def _on_status(self, level: str, text: str) -> None:
        self.status_dot.setStyleSheet(f"color: {STATUS_COLORS.get(level, theme.MUTED)}; font-size: 12pt;")
        self.status_text.setText(text)

    def _on_result(self, res: RecognitionResult) -> None:
        self.last_recognition = res
        if not res.candidates:
            if res.terrain is None:
                self._on_status("warn", "Não reconheci o tipo de mapa — tente de novo")
            return
        best = res.candidates[0]
        rows = [(c.pattern_id, c.pattern_nightlord, f"dif. {c.error}") for c in res.candidates[:8]]
        self.cand_card.set(rows, best.pattern_id)
        self.cand_card.setVisible(True)
        conf = confidence_text(res.candidates)
        self._show_seed(best.pattern_id, res.nightlord_seen, confidence=conf, from_screen=True)
        self._on_status("ok", f"Seed #{best.pattern_id} identificada em {res.seconds:.1f}s")

    def _show_seed(self, pattern_id: int, seen_nl, confidence: str = "", from_screen: bool = False) -> None:
        pattern = next((p for p in self.manual.catalog.info.patterns if p.id == pattern_id), None)
        if pattern is None:
            return
        summary = summarize(self.manual.catalog.info, pattern)
        self.current_id = pattern_id
        self.current_nl = seen_nl if seen_nl is not None else None
        self.nl_card.set(pattern.nightlord, seen_nl, known=True)
        self.seed_card.set(summary, confidence)
        self.info_card.set(summary)
        self._summary = summary
        for b in (self.btn_copy, self.btn_save):
            b.setEnabled(True)
        self.btn_site.setEnabled(summary.site_url is not None)
        self.btn_site.setToolTip(summary.site_url or "Seeds do DLC não têm link confirmado no site")
        self.setWindowTitle(
            f"Seed #{pattern_id} · {NIGHTLORDS[pattern.nightlord][0]} · {TERRAINS[pattern.earth_shifting]}"
            " — Nightreign Seed Reader"
        )
        if self.tab_group.checkedId() != 0:
            self.tab_result.setChecked(True)
            self._set_tab(0, redraw=False)
        self.map_view.placeholder = ("Desenhando o mapa…", "")
        self.req_render.emit(pattern_id, seen_nl, RENDER_SIZE, "main")
        if self.btn_overlay.isChecked() and self.map_rect:
            self.req_render.emit(pattern_id, seen_nl, int(self.map_rect[2]), "overlay")

    def _on_rendered(self, pattern_id: int, img, context) -> None:
        if pattern_id != self.current_id:
            return
        if context == "main":
            self.current_img = img
            if self.tab_group.checkedId() == 0:
                self.map_view.set_image(img)
        else:
            self.overlay_pix = pil_to_pixmap(img)
            self.overlay.set_pixmap(self.overlay_pix)
            self._sync_overlay()

    def _on_map_visible(self, visible: bool, rect) -> None:
        self.map_open = visible
        if rect:
            changed = self.map_rect is None or tuple(rect) != tuple(self.map_rect)
            self.map_rect = rect
            if changed and self.btn_overlay.isChecked() and self.current_id is not None:
                self.req_render.emit(self.current_id, self.current_nl, int(rect[2]), "overlay")
        self._sync_overlay()

    def _sync_overlay(self) -> None:
        show = self.btn_overlay.isChecked() and self.map_open and self.map_rect and self.overlay_pix is not None
        if show:
            self.overlay.place(self.map_rect)
            self.overlay.show()
            self.overlay.raise_()
        else:
            self.overlay.hide()

    # =========================================================== ações
    def _read_now(self) -> None:
        self.req_recognize_now.emit()
        self._on_status("wait", "Aguardando o mapa aberto no jogo…")

    def _overlay_toggled(self, on: bool) -> None:
        self.settings.setValue("overlay", on)
        if on and self.current_id is not None and self.map_rect:
            self.req_render.emit(self.current_id, self.current_nl, int(self.map_rect[2]), "overlay")
        self._sync_overlay()

    def _on_hotkey(self, key: str) -> None:
        if key == "F8":
            self._read_now()
        elif key == "F9":
            self.btn_overlay.toggle()
        elif key == "F10":
            self._next_candidate()

    def _pick_candidate(self, pattern_id: int) -> None:
        seen = self.last_recognition.nightlord_seen if self.last_recognition else None
        cand = None
        if self.last_recognition:
            cand = next((c for c in self.last_recognition.candidates if c.pattern_id == pattern_id), None)
        conf = "" if cand is None else f"dif. {cand.error}"
        self._show_seed(pattern_id, seen, confidence=conf)

    def _next_candidate(self) -> None:
        lw = self.cand_card.list
        if lw.count() < 2:
            return
        row = (lw.currentRow() + 1) % lw.count()
        lw.setCurrentRow(row)
        self._pick_candidate(lw.item(row).data(Qt.ItemDataRole.UserRole))

    def _open_site(self) -> None:
        if getattr(self, "_summary", None) and self._summary.site_url:
            QDesktopServices.openUrl(QUrl(self._summary.site_url))

    def _copy(self) -> None:
        s = getattr(self, "_summary", None)
        if s:
            text = f"Nightreign seed #{s.seed_id} — {NIGHTLORDS[s.nightlord][0]} — {TERRAINS[s.terrain]}"
            text += f" — Dia 1: {s.day1} — Dia 2: {s.day2}"
            if s.event:
                text += f" — Evento: {s.event}"
            QGuiApplication.clipboard().setText(text)
            self._on_status("ok", "Copiado para a área de transferência")

    def _save_image(self) -> None:
        if self.current_img is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar mapa", f"seed_{self.current_id}.png", "PNG (*.png)")
        if path:
            self.current_img.save(path)

    def _open_menu(self) -> None:
        m = QMenu(self)
        a_cal = m.addAction("Calibrar região do mapa…")
        a_clr = m.addAction("Usar região automática (16:9)")
        a_clr.setEnabled(bool(self.settings.value("manual_rect")))
        m.addSeparator()
        a_fg = m.addAction("Só ler com o jogo em primeiro plano")
        a_fg.setCheckable(True)
        a_fg.setChecked(self.settings.value("only_foreground", True, type=bool))
        a_img = m.addAction("Reconhecer a partir de um print…")
        m.addSeparator()
        a_about = m.addAction("Sobre / segurança")
        act = m.exec(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft()))
        if act is a_cal:
            self._calibrate()
        elif act is a_clr:
            self.settings.remove("manual_rect")
            self.req_manual_rect.emit(None)
            self._on_status("ok", "Região automática restaurada")
        elif act is a_fg:
            self.settings.setValue("only_foreground", a_fg.isChecked())
            self.req_only_foreground.emit(a_fg.isChecked())
        elif act is a_img:
            path, _ = QFileDialog.getOpenFileName(self, "Escolha um print do mapa", "", "Imagens (*.png *.jpg *.jpeg *.webp *.bmp)")
            if path:
                img = Image.open(path).convert("RGB")
                w, h = img.size
                if abs(w - h) > min(w, h) * 0.05 and abs(w / h - 16 / 9) < 0.05:
                    s = w / 2560  # print da tela inteira: recorta a área do mapa
                    img = img.crop((round(1454 * s), round(228 * s), round(2444 * s), round(1218 * s)))
                self.req_recognize_image.emit(img)
        elif act is a_about:
            self._about()

    def _calibrate(self) -> None:
        self._selector = RegionSelector()
        self._selector.selected.connect(self._calibrated)
        self._selector.show()
        self._selector.activateWindow()

    def _calibrated(self, rect) -> None:
        if rect:
            self.settings.setValue("manual_rect", list(rect))
            self.req_manual_rect.emit(list(rect))
            self._on_status("ok", f"Região calibrada: {rect[2]}×{rect[3]} px")

    def _about(self) -> None:
        QMessageBox.information(
            self,
            "Sobre",
            f"<b>Nightreign Seed Reader</b> v{__version__}<br><br>"
            "Identifica a seed do mapa lendo a <b>imagem da tela</b> (como um print ou o OBS). "
            "Não lê a memória do jogo, não injeta nada e não abre nem altera arquivos do jogo.<br><br>"
            "Motor de reconhecimento e dados das seeds: <i>nightreign-overlay-helper</i> (NeuraXmy, AGPL-3.0), "
            "dados extraídos pela comunidade (thefifthmatt e outros). Não afiliado à FromSoftware/Bandai Namco.<br><br>"
            "Dica: use o jogo em <b>janela sem bordas</b> para a captura funcionar.",
        )

    # =========================================================== abas / manual
    def _set_tab(self, idx: int, redraw: bool = True) -> None:
        self.side_stack.setCurrentIndex(idx)
        if idx == 1:
            self.manual.active = True
            if redraw:
                self._manual_setup()
        else:
            self.manual.active = False
            self.map_view.placeholder = ("Abra o mapa no jogo (tecla M)", "A seed aparece aqui automaticamente")
            if redraw:
                self.map_view.set_image(self.current_img)

    def _manual_setup(self) -> None:
        self.manual.setup(self.manual_panel.terrain(), self.manual_panel.nightlord())

    def _manual_candidates(self, cands) -> None:
        if 1 < len(cands) <= 8:
            self.manual_cands.set([(p.id, p.nightlord, TERRAINS[p.earth_shifting]) for p in cands], None)
            self.manual_cands.show()
        else:
            self.manual_cands.hide()

    def _manual_pick(self, pattern_id: int) -> None:
        self._show_manual_result(pattern_id, "manual")

    def _show_manual_result(self, pattern_id: int, conf: str) -> None:
        cands = self.manual.catalog.candidates(self.manual.es, self.manual.nl, self.manual.explicit)
        rows = [(p.id, p.nightlord, TERRAINS[p.earth_shifting]) for p in cands[:8]]
        self.cand_card.set(rows, pattern_id)
        self.cand_card.setVisible(len(rows) > 1)
        self.last_recognition = None
        self._show_seed(pattern_id, self.manual_panel.nightlord(), confidence=conf)

    def _manual_found(self, pattern_id: int, nl) -> None:
        QTimer.singleShot(350, lambda: self._show_manual_result(pattern_id, "✓ manual"))

    def _manual_from_capture(self) -> None:
        r = self.last_recognition
        if r is None:
            self._on_status("warn", "Nenhuma leitura da tela ainda")
            return
        self.manual_panel.select(r.nightlord_seen, r.terrain)
        self._manual_setup()

    # =========================================================== saída
    def closeEvent(self, e):  # noqa: N802
        self.settings.setValue("geometry", self.saveGeometry())
        if self.hotkeys is not None:
            self.hotkeys.unregister()
        self.overlay.close()
        self.req_stop.emit()
        self.thread.quit()
        self.thread.wait(3000)
        super().closeEvent(e)
