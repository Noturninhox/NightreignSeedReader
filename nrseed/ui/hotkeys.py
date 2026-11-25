"""Teclas de atalho globais no Windows (RegisterHotKey) — funcionam com o jogo em foco."""

from __future__ import annotations

import ctypes
import sys

from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
VK = {"F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, owner: GlobalHotkeys) -> None:
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        if event_type == b"windows_generic_MSG":
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                name = self.owner.ids.get(msg.wParam)
                if name:
                    self.owner.triggered.emit(name)
                    return True, 0
        return False, 0


class GlobalHotkeys(QObject):
    triggered = pyqtSignal(str)

    def __init__(self, app) -> None:
        super().__init__()
        self.ids: dict[int, str] = {}
        self.failed: list[str] = []
        self._filter = None
        if sys.platform == "win32":
            self._filter = _Filter(self)
            app.installNativeEventFilter(self._filter)

    def register(self, keys: list[str]) -> None:
        if sys.platform != "win32":
            return
        user32 = ctypes.windll.user32
        for i, key in enumerate(keys, start=1):
            if key in VK and user32.RegisterHotKey(None, i, MOD_NOREPEAT, VK[key]):
                self.ids[i] = key
            else:
                self.failed.append(key)

    def unregister(self) -> None:
        if sys.platform != "win32":
            return
        for i in list(self.ids):
            ctypes.windll.user32.UnregisterHotKey(None, i)
        self.ids.clear()
