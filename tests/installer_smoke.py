"""Testa a janela do instalador offscreen e faz uma instalação numa pasta temporária."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
from nrseed.ui import theme
theme.apply(app)
from nrseed import installer

tmp = Path(tempfile.mkdtemp())
installer.default_dir = lambda: tmp / "Programs" / installer.APP_NAME
installer._desktop = lambda: tmp / "Desktop"
w = installer.SetupWindow()
w.show()
shots = []
def snap(name): w.grab().save(f"/tmp/setup_{name}.png"); shots.append(name)
def run():
    snap("1_boasvindas"); w.btn_next.click()
    snap("2_opcoes"); w.btn_next.click()
def done():
    snap("3_concluido")
    exe = w.target / installer.APP_EXE
    print("instalado:", exe.exists(), exe.stat().st_size if exe.exists() else 0, "bytes")
    w.chk_open.setChecked(False); w.btn_next.click(); app.quit()
QTimer.singleShot(500, run); QTimer.singleShot(3500, done)
app.exec()
print("telas:", shots)
