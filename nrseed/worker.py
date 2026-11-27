"""Thread de reconhecimento: captura a tela, detecta o mapa aberto e identifica a seed."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from nrseed.capture import ScreenGrabber, find_game_window, is_foreground, map_rect_for_client
from nrseed.engine.detector import MapDetector
from nrseed.engine.stability import MapStability, map_stability_sample
from nrseed.engine.localization import load_names
from nrseed.render import render_overlay, render_seed

log = logging.getLogger(__name__)

TICK_MS = 100  # 10 leituras por segundo (a checagem do mapa custa ~5 ms)
WINDOW_REFRESH_S = 2.0
MAP_CLOSED_GRACE_S = 1.5  # para reiniciar a leitura
HIDE_AFTER_MISSES = 2  # overlay some após 2 quadros seguidos sem mapa (~0,2 s)


@dataclass
class Candidate:
    pattern_id: int
    nightlord: int | None  # Nightlord lido na tela (None = oculto/desconhecido)
    pattern_nightlord: int
    terrain: int
    error: int
    score: int


@dataclass
class RecognitionResult:
    terrain: int | None
    nightlord_seen: int | None
    candidates: list[Candidate] = field(default_factory=list)
    seconds: float = 0.0
    snapshot: np.ndarray | None = None


class RecognizerWorker(QObject):
    status = pyqtSignal(str, str)  # (nível: ok/wait/warn/err, texto)
    map_visible = pyqtSignal(bool, object)  # visível?, rect do mapa na tela
    recognizing = pyqtSignal()
    result = pyqtSignal(object)  # RecognitionResult
    rendered = pyqtSignal(int, object, object)  # pattern_id, PIL image, contexto
    ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.detector: MapDetector | None = None
        self.grabber: ScreenGrabber | None = None
        self.timer: QTimer | None = None
        self.stability = MapStability()
        self.enabled = True
        self.only_foreground = True
        self.manual_rect: tuple[int, int, int, int] | None = None
        self.force_nightlord: int | None = None
        self._window = None
        self._window_checked = 0.0
        self._last_full_at = 0.0
        self._done_this_open = False
        self._force = False
        self._last_status: tuple[str, str] | None = None
        self._visible = False
        self._misses = 0
        self.names_language = "pt_BR"

    # ---------------------------------------------------------------- ciclo de vida
    @pyqtSlot()
    def start(self) -> None:
        self._emit_status("wait", "Carregando motor de reconhecimento…")
        self.detector = MapDetector(language="pt_BR")
        self.detector.info.name_dict = load_names(self.names_language)
        self.detector.draw_header = False
        self.grabber = ScreenGrabber()
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_MS)
        self.ready.emit()

    @pyqtSlot()
    def stop(self) -> None:
        if self.timer:
            self.timer.stop()
        if self.grabber:
            self.grabber.close()

    # ---------------------------------------------------------------- comandos da UI
    @pyqtSlot()
    def recognize_now(self) -> None:
        self._force = True
        self._done_this_open = False
        self.stability.reset()

    @pyqtSlot(bool)
    def set_enabled(self, on: bool) -> None:
        self.enabled = on

    @pyqtSlot(bool)
    def set_only_foreground(self, on: bool) -> None:
        self.only_foreground = on

    @pyqtSlot(object)
    def set_manual_rect(self, rect) -> None:
        self.manual_rect = tuple(rect) if rect else None
        self.stability.reset()

    @pyqtSlot(object)
    def set_force_nightlord(self, nl) -> None:
        self.force_nightlord = nl

    @pyqtSlot(str)
    def set_names_language(self, lang: str) -> None:
        self.names_language = lang
        if self.detector is not None:
            self.detector.info.name_dict = load_names(lang)

    @pyqtSlot(int, object, int, object)
    def render(self, pattern_id: int, nightlord, size: int, context) -> None:
        """context: 'main' (mapa completo) ou ('overlay', w) (só rótulos)."""
        if self.detector is None:
            return
        try:
            if context == "main":
                img = render_seed(self.detector, pattern_id, nightlord, size)
            else:
                img = render_overlay(self.detector, pattern_id, nightlord, size)
            self.rendered.emit(pattern_id, img, context)
        except Exception:  # noqa: BLE001
            log.exception("Falha ao desenhar seed %s", pattern_id)

    @pyqtSlot(object)
    def recognize_image(self, img) -> None:
        """Reconhece uma imagem (print colado/arquivo) em vez da tela."""
        if self.detector is None:
            return
        self.recognizing.emit()
        self.result.emit(self._recognize(np.asarray(img.convert("RGB")) if isinstance(img, Image.Image) else img))

    # ---------------------------------------------------------------- loop
    def _emit_status(self, level: str, text: str) -> None:
        if (level, text) != self._last_status:
            self._last_status = (level, text)
            self.status.emit(level, text)

    def _set_visible(self, visible: bool, rect) -> None:
        if visible != self._visible:
            self._visible = visible
            self.map_visible.emit(visible, rect)

    def _map_rect(self):
        if self.manual_rect:
            return self.manual_rect
        now = time.monotonic()
        if self._window is None or now - self._window_checked > WINDOW_REFRESH_S:
            self._window = find_game_window()
            self._window_checked = now
        if self._window is None:
            return None
        return map_rect_for_client(self._window.client)

    def _tick(self) -> None:
        if not self.enabled or self.detector is None:
            return
        rect = self._map_rect()
        if rect is None:
            self._set_visible(False, None)
            if self._window is None and not self.manual_rect:
                self._emit_status("err", "Jogo não encontrado — abra o ELDEN RING NIGHTREIGN (janela/sem bordas)")
            else:
                self._emit_status("warn", "Janela do jogo pequena ou fora de 16:9 — calibre a região do mapa")
            return
        if self.only_foreground and self._window is not None and not self.manual_rect:
            if not is_foreground(self._window.hwnd):
                self._set_visible(False, rect)
                self._emit_status("wait", "Jogo em segundo plano — aguardando")
                return

        img = self.grabber.grab(rect)
        if img is None:
            self._emit_status("warn", "Falha ao capturar a tela")
            return
        now = time.monotonic()
        full_err = self.detector._match_full_map(img)
        is_full = full_err <= self.detector.config.full_map_error_threshold

        if is_full:
            self._last_full_at = now
            self._misses = 0
            self._set_visible(True, rect)
        else:
            self._misses += 1
            if self._misses >= HIDE_AFTER_MISSES:
                self._set_visible(False, rect)  # some quase na hora em que o mapa fecha
        if not is_full and now - self._last_full_at > MAP_CLOSED_GRACE_S:
            if self._done_this_open and not self._force:
                self._done_this_open = False  # mapa fechado: na próxima abertura lê de novo
            self.stability.reset()
            self._emit_status("ok", "Jogo encontrado — abra o mapa (M) para ler a seed")
            return

        if self._done_this_open and not self._force:
            return
        sample = map_stability_sample(img) if is_full else None
        cfg = self.detector.config
        if not self.stability.observe(
            sample, now, is_full, cfg.map_stability_change_threshold, cfg.map_stability_duration
        ):
            if is_full:
                self._emit_status("wait", "Mapa detectado — segurando a imagem estável…")
            return

        self.recognizing.emit()
        self._emit_status("wait", "Lendo o mapa…")
        res = self._recognize(img)
        self._done_this_open = True
        self._force = False
        self.result.emit(res)
        if res.candidates:
            self._emit_status("ok", f"Seed #{res.candidates[0].pattern_id} identificada")
        else:
            self._emit_status("warn", "Não consegui identificar — tente de novo ou use o modo manual")

    def _recognize(self, img: np.ndarray) -> RecognitionResult:
        t = time.perf_counter()
        det = self.detector
        random.seed(42)
        es, es_score = det._match_earth_shifting(img)
        if det.config.earth_shifting_algorithm == "ncc" and es_score < det.config.earth_shifting_ncc_threshold:
            es = None
        out = RecognitionResult(terrain=es, nightlord_seen=None, snapshot=img)
        if es is None:
            out.seconds = time.perf_counter() - t
            return out
        nl, _ = det._match_nightlord(np.asarray(Image.fromarray(img).resize((750, 750))))
        out.nightlord_seen = nl
        results = det._match_map_pattern(img, es, topk=10, force_nightlord=self.force_nightlord)
        for r in results:
            out.candidates.append(
                Candidate(r.pattern.id, r.nightlord, r.pattern.nightlord, r.pattern.earth_shifting, r.error, r.score)
            )
        out.seconds = time.perf_counter() - t
        return out
