"""Desenha o mapa completo de uma seed (fundo do terreno + ícones dos POIs + nomes)."""

from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from nrseed.engine.detector import (
    POI_ICONS,
    STD_POI_SIZE,
    MapDetectParam,
    MapDetector,
    get_poi_image,
)
from nrseed.engine.map_info import STD_MAP_SIZE, MapPattern
from nrseed.engine.resources import get_data_path


@lru_cache(maxsize=12)
def _terrain_bg(es: int, size: int) -> Image.Image:
    bg = Image.open(get_data_path(f"maps/{es}.jpg")).convert("RGBA").resize((size, size), Image.LANCZOS)
    # Vinheta escura nas bordas para combinar com o tema
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((-size * 0.15, -size * 0.15, size * 1.15, size * 1.15), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(size * 0.08))
    dark = Image.new("RGBA", (size, size), (8, 7, 6, 255))
    return Image.composite(bg, dark, mask)


@lru_cache(maxsize=256)
def _poi_icon(ctype: int, scale_px: int) -> Image.Image:
    img = get_poi_image(ctype, with_subicon=True)
    return img.resize((scale_px, scale_px), Image.LANCZOS)


def _is_poi(ctype: int) -> bool:
    return ctype // 100 in POI_ICONS or ctype // 1000 in POI_ICONS


def draw_pois(base: Image.Image, pattern: MapPattern) -> None:
    size = base.size[0]
    k = size / STD_MAP_SIZE[0]
    icon_px = max(8, round(STD_POI_SIZE[0] * k))
    for (x, y), c in pattern.pos_constructions.items():
        if not c.is_display or c.is_underground or not c.type or not _is_poi(c.type):
            continue
        icon = _poi_icon(c.type, icon_px)
        base.alpha_composite(icon, (round(x * k - icon_px / 2), round(y * k - icon_px / 2)))


def render_seed(detector: MapDetector, pattern_id: int, nightlord: int | None, size: int = 1100) -> Image.Image:
    """Imagem RGBA quadrada pronta para exibir no app."""
    res = detector.detect(
        MapDetectParam(map_region=(0, 0, size, size), draw_pattern_ids=[pattern_id], nightlord=nightlord)
    )
    if not res.patterns:
        raise KeyError(pattern_id)
    pattern = res.patterns[0]
    img = _terrain_bg(pattern.earth_shifting, size).copy()
    draw_pois(img, pattern)
    overlay = res.overlay_images[0]
    if overlay.size != img.size:
        overlay = overlay.resize(img.size, Image.LANCZOS)
    img.alpha_composite(overlay)
    return img


def render_overlay_only(detector: MapDetector, pattern_id: int, nightlord: int | None, size: int) -> Image.Image:
    """Somente os rótulos (transparente) — para sobrepor ao mapa dentro do jogo."""
    res = detector.detect(
        MapDetectParam(map_region=(0, 0, size, size), draw_pattern_ids=[pattern_id], nightlord=nightlord)
    )
    return res.overlay_images[0]
