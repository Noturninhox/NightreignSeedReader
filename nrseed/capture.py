"""Localiza a janela do Nightreign e captura a região do mapa.

Somente leitura de pixels da tela (igual a um print/OBS). Não lê memória, não injeta código
e não abre nem altera arquivos do jogo.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

import numpy as np

GAME_EXE = "nightreign.exe"

# Região do mapa no HUD padrão, para uma janela 2560x1440 (escala proporcional em 16:9).
REF_SIZE = (2560, 1440)
REF_MAP_RECT = (1454, 228, 990, 990)

Rect = tuple[int, int, int, int]  # x, y, largura, altura (pixels físicos da tela)


@dataclass
class GameWindow:
    hwnd: int
    client: Rect  # área cliente em coordenadas de tela


def map_rect_for_client(client: Rect) -> Rect | None:
    """Converte a área cliente do jogo na região quadrada do mapa (só 16:9)."""
    x, y, w, h = client
    if w < 640 or h < 360:
        return None
    # Recorta para 16:9 centralizado (barras pretas / ultrawide com letterbox)
    if w / h > 16 / 9:
        nw = round(h * 16 / 9)
        x += (w - nw) // 2
        w = nw
    elif w / h < 16 / 9:
        nh = round(w * 9 / 16)
        y += (h - nh) // 2
        h = nh
    s = w / REF_SIZE[0]
    mx, my, mw, _ = REF_MAP_RECT
    side = round(mw * s)
    return (x + round(mx * s), y + round(my * s), side, side)


if sys.platform == "win32":
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    try:  # coordenadas físicas mesmo com escala do Windows (125%, 150%...)
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:  # noqa: BLE001
        try:
            ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
        except Exception:  # noqa: BLE001
            user32.SetProcessDPIAware()

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _exe_of(hwnd: int) -> str:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buf))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return buf.value.rsplit("\\", 1)[-1].lower()
            return ""
        finally:
            kernel32.CloseHandle(handle)

    def _client_rect(hwnd: int) -> Rect | None:
        rc = wintypes.RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(rc)):
            return None
        pt = wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        return (pt.x, pt.y, rc.right - rc.left, rc.bottom - rc.top)

    def find_game_window() -> GameWindow | None:
        found: list[int] = []

        def cb(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) and _exe_of(hwnd) == GAME_EXE:
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        if not found:
            return None
        rect = _client_rect(found[0])
        return GameWindow(found[0], rect) if rect else None

    def is_foreground(hwnd: int) -> bool:
        return user32.GetForegroundWindow() == hwnd

else:  # Linux/macOS: apenas para desenvolvimento (usa a tela inteira como "jogo")

    def find_game_window() -> GameWindow | None:
        try:
            import mss

            with mss.mss() as sct:
                m = sct.monitors[1]
                return GameWindow(0, (m["left"], m["top"], m["width"], m["height"]))
        except Exception:  # noqa: BLE001
            return None

    def is_foreground(hwnd: int) -> bool:
        return True


class ScreenGrabber:
    """Captura regiões da tela com mss (GDI). Reaproveita o contexto entre frames."""

    def __init__(self) -> None:
        self._sct = None

    def grab(self, rect: Rect) -> np.ndarray | None:
        import mss

        if self._sct is None:
            self._sct = mss.mss()
        x, y, w, h = rect
        try:
            shot = self._sct.grab({"left": x, "top": y, "width": w, "height": h})
        except Exception:  # noqa: BLE001
            self.close()
            return None
        arr = np.asarray(shot)  # BGRA
        return np.ascontiguousarray(arr[..., 2::-1])  # -> RGB

    def close(self) -> None:
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:  # noqa: BLE001
                pass
            self._sct = None
