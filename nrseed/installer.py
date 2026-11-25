"""Instalador/desinstalador embutido no próprio executável (sem Inno Setup nem programas extras).

- Rodando como "NightreignSeedReader-Setup.exe" -> abre a janela de instalação.
- "Nightreign Seed Reader.exe --uninstall" -> desinstala (chamado pelo Windows em Configurações > Aplicativos).

Instala só para o usuário atual (não pede administrador), em %LOCALAPPDATA%\\Programs\\Nightreign Seed Reader.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from nrseed import __version__
from nrseed.ui import theme

APP_NAME = "Nightreign Seed Reader"
APP_EXE = "Nightreign Seed Reader.exe"
PUBLISHER = "Noturninhox"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NightreignSeedReader"
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


def is_setup_mode() -> bool:
    if "--setup" in sys.argv:
        return True
    return getattr(sys, "frozen", False) and "setup" in Path(sys.executable).stem.lower()


def is_uninstall_mode() -> bool:
    return "--uninstall" in sys.argv


def default_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Programs" / APP_NAME


def _desktop() -> Path:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)  # CSIDL_DESKTOPDIRECTORY
        if buf.value:
            return Path(buf.value)
    return Path.home() / "Desktop"


def _start_menu() -> Path:
    return Path(os.environ.get("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def _shortcut(link: Path, target: Path) -> None:
    if sys.platform != "win32":
        return
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:NR_LINK);"
        "$s.TargetPath=$env:NR_TARGET;$s.WorkingDirectory=$env:NR_DIR;"
        "$s.IconLocation=$env:NR_TARGET+',0';$s.Description='Nightreign Seed Reader';$s.Save()"
    )
    env = dict(os.environ, NR_LINK=str(link), NR_TARGET=str(target), NR_DIR=str(target.parent))
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                   env=env, creationflags=NO_WINDOW, check=False, timeout=30)


def _close_running_app() -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/f", "/im", APP_EXE], creationflags=NO_WINDOW,
                       capture_output=True, check=False)


def _register(install_dir: Path, size_kb: int) -> None:
    if sys.platform != "win32":
        return
    import winreg

    exe = install_dir / APP_EXE
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        for name, val in (
            ("DisplayName", APP_NAME),
            ("DisplayVersion", __version__),
            ("Publisher", PUBLISHER),
            ("DisplayIcon", f'"{exe}",0'),
            ("InstallLocation", str(install_dir)),
            ("UninstallString", f'"{exe}" --uninstall'),
            ("QuietUninstallString", f'"{exe}" --uninstall --quiet'),
        ):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)


def installed_dir() -> Path | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
            return Path(winreg.QueryValueEx(k, "InstallLocation")[0])
    except OSError:
        return None


# =============================================================== janela de instalação
class SetupWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Instalação — {APP_NAME}")
        self.setFixedSize(700, 440)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        prev = installed_dir()
        self.updating = prev is not None
        self.target = prev or default_dir()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QLabel()
        side.setFixedWidth(200)
        pm = QPixmap(str(theme.asset("installer_side.png")))
        side.setPixmap(pm.scaled(200, 440, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.SmoothTransformation))
        side.setStyleSheet(f"border-right: 1px solid {theme.BORDER};")
        root.addWidget(side)

        right = QVBoxLayout()
        right.setContentsMargins(28, 26, 24, 16)
        right.setSpacing(0)
        self.pages = QStackedWidget()
        right.addWidget(self.pages, 1)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{theme.BORDER};")
        right.addSpacing(10)
        right.addWidget(line)
        right.addSpacing(12)
        bar = QHBoxLayout()
        bar.addStretch()
        self.btn_back = QPushButton("< Voltar")
        self.btn_next = QPushButton("Avançar >")
        self.btn_next.setObjectName("Primary")
        self.btn_cancel = QPushButton("Cancelar")
        for b in (self.btn_back, self.btn_next, self.btn_cancel):
            b.setMinimumWidth(96)
            bar.addWidget(b)
        right.addLayout(bar)
        root.addLayout(right, 1)

        self.btn_back.clicked.connect(self._back)
        self.btn_next.clicked.connect(self._next)
        self.btn_cancel.clicked.connect(self.reject)

        self._build_pages()
        self._go(0)

    # ---------------------------------------------------------------- páginas
    def _title(self, text: str) -> QLabel:
        lb = QLabel(text)
        # Cinzel não tem til/acentos em todas as letras: títulos com a fonte do sistema
        f = QFont(theme.BODY_FAMILY, 15)
        f.setWeight(QFont.Weight.DemiBold)
        lb.setFont(f)
        lb.setStyleSheet(f"color:{theme.GOLD_HI};")
        lb.setWordWrap(True)
        return lb

    def _text(self, text: str, muted: bool = False) -> QLabel:
        lb = QLabel(text)
        lb.setWordWrap(True)
        lb.setStyleSheet(f"color:{theme.MUTED if muted else theme.TEXT}; font-size:10pt;")
        return lb

    def _build_pages(self) -> None:
        # 0 boas-vindas
        p = QWidget()
        v = QVBoxLayout(p)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        v.addWidget(self._title(f"Bem-vindo ao instalador do {APP_NAME}"))
        v.addWidget(self._text(
            ("Isto vai atualizar" if self.updating else "Isto vai instalar")
            + f" o {APP_NAME} {__version__} no seu computador."
        ))
        v.addWidget(self._text(
            "O app identifica a seed do mapa do ELDEN RING NIGHTREIGN lendo apenas a imagem da tela. "
            "Ele não mexe nos arquivos nem na memória do jogo."
        ))
        v.addWidget(self._text("Clique em Avançar para continuar.", muted=True))
        v.addStretch()
        self.pages.addWidget(p)

        # 1 opções
        p = QWidget()
        v = QVBoxLayout(p)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        v.addWidget(self._title("Opções de instalação"))
        v.addWidget(self._text("Pasta de instalação:", muted=True))
        row = QHBoxLayout()
        self.path_edit = QLineEdit(str(self.target))
        self.path_edit.setStyleSheet(
            f"background:{theme.PANEL_2}; border:1px solid {theme.BORDER}; border-radius:4px; padding:5px;"
        )
        browse = QPushButton("Procurar…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        v.addLayout(row)
        v.addSpacing(12)
        v.addWidget(self._text("Atalhos:", muted=True))
        self.chk_desktop = QCheckBox("Deseja criar um atalho na Área de Trabalho?")
        self.chk_desktop.setChecked(True)
        v.addWidget(self.chk_desktop)
        v.addWidget(self._text("Um atalho no Menu Iniciar é criado automaticamente.", muted=True))
        v.addStretch()
        v.addWidget(self._text("Não precisa de permissão de administrador. Ocupa cerca de 120 MB.", muted=True))
        self.pages.addWidget(p)

        # 2 instalando
        p = QWidget()
        v = QVBoxLayout(p)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        v.addWidget(self._title("Instalando…"))
        self.status = self._text("Preparando…")
        v.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(14)
        self.progress.setStyleSheet(
            f"QProgressBar{{background:{theme.PANEL_2}; border:1px solid {theme.BORDER}; border-radius:6px;}}"
            f"QProgressBar::chunk{{background:{theme.GOLD}; border-radius:5px;}}"
        )
        v.addWidget(self.progress)
        v.addStretch()
        self.pages.addWidget(p)

        # 3 concluído
        p = QWidget()
        v = QVBoxLayout(p)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        v.addWidget(self._title("Instalação concluída"))
        v.addWidget(self._text(f"O {APP_NAME} foi instalado com sucesso."))
        v.addWidget(self._text(
            "Dica: deixe o jogo em janela sem bordas e abra o mapa (tecla M). A seed aparece sozinha.",
            muted=True,
        ))
        self.chk_open = QCheckBox(f"Abrir o {APP_NAME} agora")
        self.chk_open.setChecked(True)
        v.addSpacing(6)
        v.addWidget(self.chk_open)
        v.addStretch()
        self.pages.addWidget(p)

    # ---------------------------------------------------------------- navegação
    def _go(self, idx: int) -> None:
        self.pages.setCurrentIndex(idx)
        self.btn_back.setVisible(idx == 1)
        self.btn_cancel.setVisible(idx in (0, 1))
        self.btn_next.setEnabled(idx != 2)
        self.btn_next.setVisible(idx != 2)
        self.btn_next.setText({0: "Avançar >", 1: "Atualizar" if self.updating else "Instalar", 3: "Concluir"}.get(idx, ""))
        self.btn_next.setFocus()

    def _back(self) -> None:
        self._go(max(0, self.pages.currentIndex() - 1))

    def _next(self) -> None:
        idx = self.pages.currentIndex()
        if idx == 0:
            self._go(1)
        elif idx == 1:
            self.target = Path(self.path_edit.text().strip() or str(default_dir()))
            self._go(2)
            QTimer.singleShot(100, self._install)
        elif idx == 3:
            if self.chk_open.isChecked():
                exe = self.target / APP_EXE
                if exe.exists():
                    subprocess.Popen([str(exe)], cwd=str(self.target), close_fds=True)
            self.accept()

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Escolha a pasta", str(Path(self.path_edit.text()).parent))
        if d:
            self.path_edit.setText(str(Path(d) / APP_NAME))

    def reject(self) -> None:
        if self.pages.currentIndex() == 2:
            return
        if self.pages.currentIndex() < 2:
            ans = QMessageBox.question(self, "Cancelar", "Deseja cancelar a instalação?")
            if ans != QMessageBox.StandardButton.Yes:
                return
        super().reject()

    # ---------------------------------------------------------------- instalação
    def _step(self, pct: int, text: str) -> None:
        self.progress.setValue(pct)
        self.status.setText(text)
        QApplication.processEvents()

    def _install(self) -> None:
        try:
            src = Path(sys.executable)
            dst_dir = self.target
            dst = dst_dir / APP_EXE
            self._step(5, "Fechando o app, se estiver aberto…")
            _close_running_app()
            dst_dir.mkdir(parents=True, exist_ok=True)
            self._step(10, "Copiando arquivos…")
            total = src.stat().st_size
            done = 0
            tmp = dst.with_suffix(".tmp")
            with src.open("rb") as fi, tmp.open("wb") as fo:
                while chunk := fi.read(4 * 1024 * 1024):
                    fo.write(chunk)
                    done += len(chunk)
                    self._step(10 + int(70 * done / total), "Copiando arquivos…")
            os.replace(tmp, dst)
            for extra in ("LICENSE", "README.md"):
                p = src.parent / extra
                if p.exists() and p.resolve() != (dst_dir / extra).resolve():
                    shutil.copy2(p, dst_dir / extra)
            self._step(85, "Criando atalhos…")
            _start_menu().mkdir(parents=True, exist_ok=True)
            _shortcut(_start_menu() / f"{APP_NAME}.lnk", dst)
            desktop_link = _desktop() / f"{APP_NAME}.lnk"
            if self.chk_desktop.isChecked():
                _shortcut(desktop_link, dst)
            elif desktop_link.exists():
                desktop_link.unlink()
            self._step(95, "Registrando no Windows…")
            _register(dst_dir, max(1, total // 1024))
            self._step(100, "Pronto!")
            QTimer.singleShot(300, lambda: self._go(3))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro na instalação", f"Não foi possível instalar:\n\n{exc}")
            self._go(1)


# =============================================================== desinstalação
def run_uninstall(app: QApplication) -> int:
    quiet = "--quiet" in sys.argv
    install_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else (installed_dir() or default_dir())
    if not quiet:
        ans = QMessageBox.question(
            None, f"Desinstalar {APP_NAME}",
            f"Deseja remover o {APP_NAME} do computador?\n\nO jogo não é afetado.",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return 0
    for link in (_desktop() / f"{APP_NAME}.lnk", _start_menu() / f"{APP_NAME}.lnk"):
        try:
            link.unlink(missing_ok=True)
        except OSError:
            pass
    if sys.platform == "win32":
        import winreg

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        except OSError:
            pass
        # O .exe em uso não pode se apagar: um cmd separado apaga a pasta depois que fecharmos.
        subprocess.Popen(
            f'cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{install_dir}"',
            creationflags=NO_WINDOW | 0x00000008, close_fds=True,  # DETACHED_PROCESS
        )
    if not quiet:
        QMessageBox.information(None, APP_NAME, f"O {APP_NAME} foi removido.")
    return 0


def run_setup(app: QApplication) -> int:
    w = SetupWindow()
    w.show()
    return 0 if w.exec() else 1
