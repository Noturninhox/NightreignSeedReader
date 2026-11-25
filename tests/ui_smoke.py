"""Teste visual offscreen: QT_QPA_PLATFORM=offscreen python tests/ui_smoke.py <amostra> <saida.png> [manual]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
from nrseed.ui import theme
theme.apply(app)
from nrseed.ui.main_window import MainWindow
from nrseed.engine.manual_catalog import PoiChoice

sample, out = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "auto"
w = MainWindow(); w.resize(1500, 950); w.show()

def go():
    if mode.startswith("manual"):
        w.tab_manual.click()
        w.manual_panel.select(6, 1); w.manual_panel.changed.emit()
        # marca 1 POI com o valor real da seed 262 para ver o filtro reduzir
        pat = next(p for p in w.manual.catalog.info.patterns if p.id == 262)
        keys = [k for k in w.map_view.markers if not hasattr(k, "kind")]
        for k in keys[: (0 if mode == "manual0" else 1)]:
            base, sub = w.manual.catalog.value(pat, k)
            w.manual.explicit[k] = PoiChoice(base, sub)
        w.manual._refresh()
    else:
        w.req_recognize_image.emit(Image.open(sample).convert("RGB"))

def shot():
    w.grab().save(out); print("status:", w.status_text.text(), "|", w.windowTitle(), "| manual:", w.manual_panel.remaining.text()); app.quit()

QTimer.singleShot(2500, go); QTimer.singleShot(8000, shot)
app.exec()
