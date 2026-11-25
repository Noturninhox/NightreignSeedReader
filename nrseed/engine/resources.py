from __future__ import annotations

import sys
from pathlib import Path

from nrseed.engine._compat import user_data_dir


def _base() -> Path:
    # PyInstaller extrai os dados em sys._MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) / "nrseed" / "engine" if meipass else Path(__file__).parent


def get_data_path(path: str) -> str:
    return str(_base() / "data" / path)


def get_appdata_path(filename: str) -> str:
    return str(user_data_dir() / filename)
