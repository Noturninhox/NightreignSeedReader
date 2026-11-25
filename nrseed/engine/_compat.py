"""Substitutos mínimos dos módulos `core` do projeto original."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

FALLBACK_LANGUAGE = "zh_CN"
I18N_DIR = Path(__file__).parent / "i18n"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def read_cv2_image(path: str | Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    path = Path(path)
    encoded = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(encoded, flags) if encoded.size else None
    if image is None or image.size == 0:
        raise OSError(f"Cannot decode image: {path}")
    return image


def user_data_dir() -> Path:
    base = os.environ.get("APPDATA") if sys.platform == "win32" else None
    path = Path(base) / "NightreignSeedReader" if base else Path.home() / ".nightreign-seed-reader"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(name: str) -> Path:
    return I18N_DIR


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in data.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = str(v)
    return out


class Translator:
    def __init__(self, language: str) -> None:
        self.language = language if (I18N_DIR / f"{language}.yaml").exists() else "en_US"
        self._tables: dict[str, list[dict[str, str]]] = {}

    def load_dir(self, namespace: str, directory: Path) -> None:
        tables = []
        for lang in dict.fromkeys((self.language, "en_US", FALLBACK_LANGUAGE)):
            p = Path(directory) / f"{lang}.yaml"
            if p.exists():
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                data.pop("meta", None)
                tables.append(_flatten(data))
        self._tables[namespace] = tables

    def tr(self, namespace: str, key: str, **kwargs: Any) -> str:
        text = next((t[key] for t in self._tables.get(namespace, ()) if key in t), key)
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, IndexError, ValueError):
            return text


_default = Translator("pt_BR")


def translator() -> Translator:
    return _default
