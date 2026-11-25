"""Nightreign Seed Reader — identifica a seed do mapa do Elden Ring Nightreign lendo a tela."""

from __future__ import annotations

import logging
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from nrseed.engine._compat import user_data_dir


def _close_splash() -> None:
    """Fecha a tela de carregamento do .exe (PyInstaller --splash), se existir."""
    try:
        import pyi_splash  # type: ignore

        pyi_splash.close()
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(user_data_dir() / "log.txt", encoding="utf-8"), logging.StreamHandler()],
    )
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Noturninhox.NightreignSeedReader")

    app = QApplication(sys.argv)
    app.setApplicationName("Nightreign Seed Reader")

    from nrseed.ui import theme
    from nrseed.ui.hotkeys import GlobalHotkeys
    from nrseed.ui.main_window import MainWindow

    theme.apply(app)
    app.setWindowIcon(QIcon(str(theme.asset("icon.ico"))))

    from nrseed import installer

    if installer.is_uninstall_mode():
        _close_splash()
        return installer.run_uninstall(app)
    if installer.is_setup_mode():
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, _close_splash)
        return installer.run_setup(app)
    hotkeys = GlobalHotkeys(app)
    win = MainWindow(hotkeys)
    win.show()
    _close_splash()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
