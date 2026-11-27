"""Simula a tela do jogo e verifica a leitura automática: fecha/abre mapa e troca de partida."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
from PyQt6.QtCore import QCoreApplication, QTimer

from nrseed import worker as W
from nrseed.capture import GameWindow, map_rect_for_client

app = QCoreApplication(sys.argv)
S = Path(__file__).parent / "samples"
frames = {"closed": np.full((990, 990, 3), 40, np.uint8),
          "262": np.array(Image.open(S / "262.jpg").convert("RGB").resize((990, 990))),
          "12": np.array(Image.open(S / "12.jpg").convert("RGB").resize((990, 990)))}
screen = {"now": "closed"}
W.find_game_window = lambda: GameWindow(1, (0, 0, 2560, 1440))
W.is_foreground = lambda h: True
class FakeGrab:
    def grab(self, rect): return frames[screen["now"]].copy()
    def close(self): pass
W.ScreenGrabber = FakeGrab
assert map_rect_for_client((0, 0, 2560, 1440)) == (1454, 228, 990, 990)
assert map_rect_for_client((0, 0, 1920, 1080)) == (1090, 171, 742, 742)

import time
w = W.RecognizerWorker(); results = []; statuses = []; vis = []; switched = {}
w.map_visible.connect(lambda v, r: vis.append((v, time.monotonic())))
w.result.connect(lambda r: results.append(r.candidates[0].pattern_id if r.candidates else None))
w.status.connect(lambda lvl, t: statuses.append(t))
w.start()
plan = [(0, "closed"), (1500, "262"), (5000, "closed"), (8000, "12"), (12000, "12")]
def setf(f):
    screen["now"] = f
    switched.setdefault(f, []).append(time.monotonic())
for ms, f in plan: QTimer.singleShot(ms, lambda f=f: setf(f))
QTimer.singleShot(14000, app.quit)
app.exec()
print("resultados:", results)
print("status:", " | ".join(dict.fromkeys(statuses)))
assert results == [262, 12], results
# atraso entre fechar o mapa e o overlay sumir
closed_at = switched["closed"][1]
hide = next(t for v, t in vis if not v and t > closed_at)
delay = hide - closed_at
print(f"overlay sumiu {delay*1000:.0f} ms depois de fechar o mapa")
assert delay < 0.5, delay
print("OK")
