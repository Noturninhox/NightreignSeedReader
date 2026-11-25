"""Desenha o mapa completo de uma seed no estilo dos mapas da comunidade:
fundo escuro, ícones grandes, etiquetas arredondadas, círculos roxos dos dias,
ponto de início e medalhões do Nightlord e do castelo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from nrseed.engine.detector import POI_ICONS, STD_POI_SIZE, MapDetectParam, MapDetector, get_poi_image
from nrseed.engine.map_info import MapPattern
from nrseed.engine.resources import get_data_path
from nrseed.gamedata import TERRAIN_PT
from nrseed.ui.theme import asset

# ------------------------------------------------------------------ constantes do jogo
BOSS1_CTYPES = {46510, 46570, 46590, 46620, 46650, 46690, 46710, 46720, 46770, 46810, 46820,
                46860, 46880, 46910, 46950, 45510, 46550}
BOSS2_CTYPES = {46520, 46530, 46540, 46560, 46630, 46640, 46660, 46670, 46680, 46740, 46870, 46580}
CASTLE_ROOF = (328, 409)
CASTLE_BASEMENT = (355, 409)
CASTLE_CENTER = (340, 400)
ROTREW_POS = {1046300590: (477, 583), 1057300590: (600, 452), 1047300590: (423, 500)}
# Conteúdo fixo das Terras Mutáveis (igual em todas as seeds com aquele terreno; não vem nos dados
# por seed). Posições aproximadas, a partir das descrições dos guias e do próprio mapa do jogo.
FIXED_CONTENT: dict[int, list[tuple[tuple[int, int], str, str]]] = {
    1: [  # Topo da Montanha
        ((213, 203), "Favor da Montanha (cristais)", "favor"),
        ((226, 178), "Mountaintop Ice Dragon", "boss2"),
        ((236, 302), "Flying Dragon", "boss2"),
        ((306, 288), "Snowfield Troll ×2", "boss1"),
        ((252, 140), "Demi-Human Swordmaster", "boss1"),
    ],
    2: [  # Cratera
        ((350, 298), "Fire Prelates", "boss1"),
        ((380, 258), "Magma Wyrm", "boss2"),
        ((398, 282), "Altar: arma Lendária", "favor"),
    ],
    5: [  # Noklateo
        ((215, 498), "Inseto gigante", "boss1"),
        ((150, 588), "Naturalborn of the Void", "boss2"),
        ((132, 612), "Favor de Noklateo", "favor"),
    ],
}

TGH_FLOOR = {1111: ("RB", 1), 1112: ("RB", 2), 1113: ("RB", 3), 1114: ("LT", 1), 1115: ("LT", 2), 1116: ("LT", 3)}

# ------------------------------------------------------------------ estilo
PILL_BG = (24, 24, 26, 215)
PILL_RED = (176, 48, 44, 225)
PILL_PURPLE = (132, 96, 240, 205)
PILL_GOLD = (122, 92, 34, 225)
TEXT = (245, 245, 245, 255)
RING_PURPLE = (112, 70, 235, 255)
RING_YELLOW = (240, 200, 40, 255)
MEDAL_RING = (28, 38, 56, 255)


@dataclass
class Label:
    anchor: tuple[float, float]  # ponto de referência (px)
    text: str
    bg: tuple = PILL_BG
    fg: tuple = TEXT
    avoid: tuple[float, float, float, float] | None = None  # caixa do ícone que a etiqueta acompanha
    prefer: str = "below"
    big: bool = False


# ------------------------------------------------------------------ fontes
@lru_cache(maxsize=16)
def _font(px: int, weight: int = 600) -> ImageFont.FreeTypeFont:
    try:
        f = ImageFont.truetype(str(asset("Inter.ttf")), px)
        f.set_variation_by_axes([min(32, max(14, px)), weight])
        return f
    except Exception:  # noqa: BLE001
        return ImageFont.truetype(get_data_path("fonts/SourceHanSansSC-Normal.otf"), px)


# ------------------------------------------------------------------ fundo
@lru_cache(maxsize=8)
def _island_bg(es: int, size: int) -> Image.Image:
    """Mapa do jogo com o papel cinza em volta da ilha escurecido + contorno suave."""
    rgb = np.asarray(Image.open(get_data_path(f"maps/{es}.jpg")).convert("RGB"))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat, val = hsv[..., 1], hsv[..., 2]
    paper = ((sat < 38) & (val > 95)).astype(np.uint8)
    paper = cv2.morphologyEx(paper, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab = cv2.connectedComponents(paper, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    outside = np.isin(lab, list(border)).astype(np.uint8)
    # ilha = tudo que não é papel externo nem as listras de água coladas ao papel
    island = 1 - outside
    island = cv2.morphologyEx(island, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(island, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big = max(cnts, key=cv2.contourArea)
    mask = np.zeros_like(island)
    cv2.drawContours(mask, [big], -1, 1, thickness=cv2.FILLED)
    # suaviza a borda
    soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 2.2)

    img = rgb.astype(np.float32)
    dark = img * 0.24 + 8
    out = img * soft[..., None] + dark * (1 - soft[..., None])

    # contorno claro (halo) logo fora da ilha
    halo = cv2.dilate(mask, np.ones((5, 5), np.uint8)) - mask
    halo = cv2.GaussianBlur(halo.astype(np.float32), (0, 0), 1.6) * (1 - soft * 0.6)
    glow = cv2.GaussianBlur((cv2.dilate(mask, np.ones((15, 15), np.uint8)) - mask).astype(np.float32), (0, 0), 5) * (1 - soft)
    out = out + halo[..., None] * np.array([95, 96, 98], np.float32) + glow[..., None] * np.array([18, 18, 19], np.float32)
    # sem preto puro fora da ilha (a imagem do jogo tem uma borda preta fina)
    floor = np.array([30, 30, 30], np.float32)
    outside_w = (1 - soft)[..., None]
    out = out * (1 - outside_w) + np.maximum(out, floor) * outside_w

    # bordas da imagem se fundem com o fundo da janela (#1e1e1e)
    hgt, wid = out.shape[:2]
    yy, xx = np.mgrid[0:hgt, 0:wid].astype(np.float32)
    edge = np.minimum.reduce([xx, yy, wid - 1 - xx, hgt - 1 - yy]) / (wid * 0.06)
    fade = np.clip(edge, 0, 1)[..., None] ** 0.8
    out = out * fade + floor * (1 - fade)

    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)
    return res.convert("RGBA")


def _terrain_bg(es: int, size: int) -> Image.Image:
    """Fundo usado também pelo modo manual."""
    return _island_bg(es, size)


@lru_cache(maxsize=8)
def _shift_crop(es: int) -> Image.Image:
    """Recorte quadrado da região que a Terra Mutável altera (ou do castelo, no mapa normal)."""
    raw = Image.open(get_data_path(f"maps/{es}.jpg")).convert("RGB").resize((750, 750), Image.LANCZOS)
    if es != 0:
        a = np.asarray(raw).astype(np.int16)
        b = np.asarray(Image.open(get_data_path("maps/0.jpg")).convert("RGB").resize((750, 750))).astype(np.int16)
        diff = np.abs(a - b).sum(axis=2).astype(np.float32)
        diff = cv2.GaussianBlur(diff, (0, 0), 6)
        m = (diff > 60).astype(np.uint8)
        n, lab, stats, cents = cv2.connectedComponentsWithStats(m)
        if n > 1:
            i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            x, y, w, h = stats[i, :4]
            side = int(max(w, h) * 1.05) + 10
            cx, cy = x + w // 2, y + h // 2
            half = max(60, side // 2)
            return raw.crop((cx - half, cy - half, cx + half, cy + half))
    cx, cy = CASTLE_CENTER
    return raw.crop((cx - 58, cy - 58, cx + 58, cy + 58))


@lru_cache(maxsize=64)
def _icon(path: str, px: int) -> Image.Image:
    im = Image.open(get_data_path(path)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    return im


@lru_cache(maxsize=256)
def _poi_icon(ctype: int, px: int) -> Image.Image:
    return get_poi_image(ctype, with_subicon=True).resize((px, px), Image.LANCZOS)


def _paste_center(base: Image.Image, im: Image.Image, xy: tuple[float, float]) -> tuple[int, int, int, int]:
    """Cola `im` centralizado em `xy` (recortando o que sair da imagem). Devolve a caixa ocupada."""
    x, y = round(xy[0] - im.width / 2), round(xy[1] - im.height / 2)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(im.width, base.width - x), min(im.height, base.height - y)
    if ex > sx and ey > sy:
        base.alpha_composite(im.crop((sx, sy, ex, ey)), (x + sx, y + sy))
    return (x, y, x + im.width, y + im.height)


# ------------------------------------------------------------------ etiquetas
def _pill_size(lb: Label, k: float) -> tuple[int, int, list[str]]:
    font = _font(round((11.2 if lb.big else 10.2) * k))
    lines = lb.text.split("\n")
    pad_x, pad_y, gap = 6 * k, 3.4 * k, 1.5 * k
    w = max(font.getlength(s) for s in lines) + 2 * pad_x
    asc, desc = font.getmetrics()
    lh = asc + desc
    h = lh * len(lines) + gap * (len(lines) - 1) + 2 * pad_y
    return round(w), round(h), lines


def _overlap(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0, w) * max(0, h)


def _place(lb: Label, w: int, h: int, k: float, size: int, taken: list) -> tuple[int, int, int, int]:
    ax, ay = lb.anchor
    ib = lb.avoid or (ax, ay, ax, ay)
    gap = 2 * k
    cands = {
        "below": (ax - w / 2, ib[3] + gap - 4 * k),
        "right": (ib[2] + gap, ay - h / 2),
        "left": (ib[0] - gap - w, ay - h / 2),
        "above": (ax - w / 2, ib[1] - gap - h),
        "below_right": (ax - 6 * k, ib[3] - 2 * k),
        "center": (ax - w / 2, ay - h / 2),
        "day": (ax + 24 * k * 0.82, ay - h / 2),
        "day_left": (ax - 24 * k * 0.82 - w, ay - h / 2),
    }
    if lb.prefer == "day":
        order = ["day", "day_left", "above", "below"]
    else:
        order = [lb.prefer] + [c for c in ("below", "right", "left", "above", "below_right") if c != lb.prefer]
    # posições extras mais afastadas/diagonais, usadas quando as primeiras colidem
    far = 14 * k
    extra = {
        "below2": (ax - w / 2, ib[3] + gap + far),
        "above2": (ax - w / 2, ib[1] - gap - h - far),
        "right2": (ib[2] + gap + far, ay - h / 2),
        "left2": (ib[0] - gap - w - far, ay - h / 2),
        "br": (ib[2] + gap, ib[3] + gap),
        "bl": (ib[0] - gap - w, ib[3] + gap),
        "tr": (ib[2] + gap, ib[1] - gap - h),
        "tl": (ib[0] - gap - w, ib[1] - gap - h),
    }
    cands.update(extra)
    if lb.prefer not in ("day", "center"):
        order += list(extra)
    best, best_score = None, None
    for i, name in enumerate(order):
        x, y = cands[name]
        x = min(max(4, x), size - w - 4)
        y = min(max(4, y), size - h - 4)
        box = (x, y, x + w, y + h)
        score = sum(_overlap(box, t) for t in taken) + i * 0.5 * k * k
        if best_score is None or score < best_score:
            best, best_score = box, score
        if score <= i * 0.5 * k * k:
            break
    return tuple(round(v) for v in best)


def _draw_pill(d: ImageDraw.ImageDraw, box, lb: Label, lines: list[str], k: float) -> None:
    font = _font(round((11.2 if lb.big else 10.2) * k))
    d.rounded_rectangle(box, radius=round(4 * k), fill=lb.bg)
    asc, desc = font.getmetrics()
    lh = asc + desc
    y = box[1] + 3.4 * k
    for s in lines:
        d.text((box[0] + 6 * k, y), s, font=font, fill=lb.fg)
        y += lh + 1.5 * k


# ------------------------------------------------------------------ elementos especiais
def _medallion(base: Image.Image, inner: Image.Image, center, radius: float, k: float) -> None:
    r = round(radius)
    disk = inner.convert("RGBA").resize((2 * r, 2 * r), Image.LANCZOS)
    mask = Image.new("L", disk.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    shadow = Image.new("RGBA", (2 * r + 40, 2 * r + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((20, 24, 20 + 2 * r, 24 + 2 * r), fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8 * k))
    base.alpha_composite(shadow, (round(center[0] - r - 20), round(center[1] - r - 20)))
    base.paste(disk, (round(center[0] - r), round(center[1] - r)), mask)
    d = ImageDraw.Draw(base)
    w = max(2, round(5.5 * k))
    d.ellipse((center[0] - r - w / 2, center[1] - r - w / 2, center[0] + r + w / 2, center[1] + r + w / 2),
              outline=MEDAL_RING, width=w)


def _spawn(base: Image.Image, c, k: float) -> tuple:
    d = ImageDraw.Draw(base)
    r = 22 * k
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(20, 40, 30, 70), outline=RING_YELLOW, width=max(2, round(2.6 * k)))
    # falcão espectral estilizado (ponto de início)
    s = 15 * k
    left = [(0, -0.05), (-0.3, -0.42), (-1.0, -0.62), (-0.7, -0.3), (-0.95, -0.22), (-0.5, -0.02), (-0.14, 0.12)]
    tail = [(-0.14, 0.12), (-0.24, 0.66), (0, 0.5), (0.24, 0.66), (0.14, 0.12)]
    right = [(-x, y) for x, y in reversed(left)]
    pts = left + tail + right
    d.polygon([(c[0] + x * s, c[1] + y * s) for x, y in pts], fill=(120, 215, 170, 255), outline=(30, 80, 60, 255))
    hr = 0.15 * s
    d.ellipse((c[0] - hr, c[1] - 0.28 * s - hr, c[0] + hr, c[1] - 0.28 * s + hr), fill=(120, 215, 170, 255),
              outline=(30, 80, 60, 255))
    return (c[0] - r, c[1] - r, c[0] + r, c[1] + r)


def _day_circle(base: Image.Image, c, k: float) -> tuple:
    d = ImageDraw.Draw(base)
    r = 24 * k
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=RING_PURPLE, width=max(3, round(3.6 * k)))
    return (c[0] - r, c[1] - r, c[0] + r, c[1] + r)


# ------------------------------------------------------------------ principal
def render_seed(detector: MapDetector, pattern_id: int, nightlord: int | None, size: int = 1400) -> Image.Image:
    """Imagem RGBA quadrada pronta para exibir no app."""
    info = detector.info
    pattern: MapPattern | None = next((p for p in info.patterns if p.id == pattern_id), None)
    if pattern is None:
        raise KeyError(pattern_id)
    k = size / 750

    def P(p) -> tuple[float, float]:  # noqa: N802
        return (p[0] * k, p[1] * k)

    def name(i: int) -> str:
        return info.get_name(i) or str(i)

    img = _island_bg(pattern.earth_shifting, size).copy()
    d = ImageDraw.Draw(img)
    labels: list[Label] = []
    taken: list[tuple] = []

    # sobreposições de tesouro / torre do frenesi (imagens transparentes do motor)
    for path in (f"treasures/treasure_{pattern.treasure * 10 + pattern.earth_shifting}.png",
                 f"frenzy/Frenzy_{pattern.evpat_flag}.png" if pattern.event_value == 3080 else None):
        if path:
            try:
                ov = Image.open(get_data_path(path)).convert("RGBA").resize((round(800 * k),) * 2, Image.LANCZOS)
                _paste_center(img, ov, P((375, 375)))
            except FileNotFoundError:
                pass

    poi_px = round(STD_POI_SIZE[0] * k * 1.18)
    crest_px = round(30 * k)
    day2_lefttop = pattern.day2_pos_idx == 12000

    for pos, c in pattern.pos_constructions.items():
        t = c.type
        s = str(t)
        xy = P(pos)
        under = "↓ " if c.is_underground else ""

        def match(*pre) -> bool:
            return any(s.startswith(str(p)) for p in pre)  # noqa: B023

        # ícone de POI (fortes, igrejas, ruínas, acampamentos…)
        icon_box = None
        if t and c.is_display and (t // 1000 in POI_ICONS or t // 100 in POI_ICONS):
            if not c.is_underground:
                icon_box = _paste_center(img, _poi_icon(t, poi_px), xy)
                taken.append(icon_box)

        # chefes de campo
        if match(45, 46) and not match(460) and (t == 45510 or t // 1000 != 45) and t != 46780:
            n = name(t)
            if pos == CASTLE_ROOF:
                labels.append(Label(P((328, 392)), f"Telhado: {n}", bg=PILL_RED, prefer="center"))
            elif pos == CASTLE_BASEMENT:
                labels.append(Label(P((362, 428)), f"Porão: {n}", bg=PILL_RED, prefer="center"))
            else:
                box = None
                if t in BOSS1_CTYPES or t in BOSS2_CTYPES:
                    crest = _icon("icons/boss2.png" if t in BOSS2_CTYPES else "icons/boss1.png", crest_px)
                    box = _paste_center(img, crest, (xy[0], xy[1] - 2 * k))
                    taken.append(box)
                labels.append(Label(xy, under + n, avoid=box or icon_box))
        # tipo do castelo
        if match(494) and t != 49400:
            labels.append(Label(P((pos[0] - 15, pos[1] - 32)), name(t), bg=PILL_GOLD, prefer="center"))
        if match(5358, 5359, 5367, 5368):
            lines = [name(t)]
            for _p2, c2 in pattern.pos_constructions.items():
                if (match(536) and c2.type in (53700, 53710, 53720)) or (match(535) and c2.type in (53600, 53610)):
                    lines.append("↓ " + name(c2.type))
            inside = bool(match(536)) ^ day2_lefttop
            labels.append(Label(xy, "\n".join(lines), bg=(40, 90, 50, 225) if inside else PILL_RED, avoid=icon_box))
        # torre do feiticeiro (dica do enigma)
        if match(400, 5110):
            labels.append(Label(xy, name(t), fg=(200, 240, 190, 255), avoid=icon_box))
        # carruagem
        if match(4500, 4501, 51150):
            taken.append(_paste_center(img, _icon("icons/carriage.png", round(30 * k)), xy))
        # nome do chefe do POI
        if match(30, 32, 34, 38, 500, 501, 524, 525):
            labels.append(Label(xy, under + name(t), avoid=icon_box, prefer="right"))
        # evento especial
        if 200 <= t // 100 <= 215:
            box = _paste_center(img, _icon("icons/event.png", round(40 * k)), xy)
            taken.append(box)
            ev = name(pattern.event_flag)
            if pattern.event_flag in (7705, 7725):
                ev = f"{ev} {name(pattern.event_value)}"
            labels.append(Label(xy, ev, bg=PILL_RED, avoid=box))
        if match(379):
            labels.append(Label(xy, under + "Vila do Mercador", fg=(240, 210, 150, 255), avoid=icon_box))
        # chefes da torre do Grande Vazio
        if c.pos_index in TGH_FLOOR:
            side, floor = TGH_FLOOR[c.pos_index]
            base = (100, 280) if side == "LT" else (680, 530)
            inside = day2_lefttop ^ (side == "RB")
            labels.append(Label(P((base[0], base[1] + (3 - floor) * 20)), f"{floor}º andar: {name(t)}",
                                bg=(40, 90, 50, 225) if inside else PILL_RED, prefer="center"))

    # chefes e recompensas fixos da Terra Mutável
    fixed = FIXED_CONTENT.get(pattern.earth_shifting, [])
    for pos, text, kind in fixed:
        xy = P(pos)
        if kind == "favor":
            labels.append(Label(xy, text, bg=PILL_GOLD, prefer="center"))
            continue
        crest = _icon("icons/boss2.png" if kind == "boss2" else "icons/boss1.png", crest_px)
        box = _paste_center(img, crest, xy)
        taken.append(box)
        labels.append(Label(xy, text, avoid=box))

    # bênção podre
    if pos := ROTREW_POS.get(pattern.rot_rew):
        box = _paste_center(img, _icon("icons/rot_rew.png", round(30 * k)), P(pos))
        taken.append(box)
        labels.append(Label(P(pos), "Bênção", bg=PILL_RED, avoid=box))

    # ponto de início
    start = info.tgh_pos_dict.get(_start_id(pattern)) if pattern.earth_shifting == 4 else info.pos_dict.get(_start_id(pattern))
    if start:
        taken.append(_spawn(img, P(start), k))

    # círculos de cada dia (o anel é desenhado depois, por cima da etiqueta)
    rings: list[tuple[float, float]] = []
    for day, pos, boss, extra in ((1, pattern.day1_pos, pattern.day1_boss, pattern.day1_extra_boss),
                                  (2, pattern.day2_pos, pattern.day2_boss, pattern.day2_extra_boss)):
        c = P(pos)
        rings.append(c)
        text = f"Dia {day}\n{name(boss)}" + (f"\n+ {name(extra)}" if extra != -1 else "")
        r = 24 * k
        labels.append(Label(c, text, bg=PILL_PURPLE, big=True, prefer="day",
                            avoid=(c[0] - r, c[1] - r, c[0] + r, c[1] + r)))

    # medalhões
    medal_r = 62 * k
    nl_img = Image.open(get_data_path("icons/nightlord/unk.png" if nightlord is None else f"icons/nightlord/{nightlord}.png"))
    _medallion(img, nl_img, (medal_r + 26 * k, medal_r + 26 * k), medal_r, k)
    _medallion(img, _shift_crop(pattern.earth_shifting), (size - medal_r - 26 * k, medal_r + 26 * k), medal_r, k)
    taken += [(0, 0, 2 * medal_r + 52 * k, 2 * medal_r + 52 * k), (size - 2 * medal_r - 52 * k, 0, size, 2 * medal_r + 52 * k)]
    labels.append(Label((size - medal_r - 26 * k, 2 * medal_r + 40 * k), TERRAIN_PT.get(pattern.earth_shifting, ""),
                        bg=PILL_GOLD, prefer="center"))
    if pattern.earth_shifting == 4:
        labels.append(Label((size - medal_r - 26 * k, 2 * medal_r + 62 * k),
                            "1º círculo do Dia 2: " + ("superior esquerdo" if day2_lefttop else "inferior direito"),
                            bg=(40, 90, 50, 225), prefer="center"))

    if fixed:
        note = f"Chefes fixos de {TERRAIN_PT.get(pattern.earth_shifting, '')}: posição aproximada"
        labels.append(Label((size / 2, size - 22 * k), note, bg=(24, 24, 26, 170), fg=(200, 200, 205, 255), prefer="center"))

    # etiquetas: os dias e itens fixos primeiro, depois o resto evitando sobreposição
    labels.sort(key=lambda lb: {"day": 0, "center": 1}.get(lb.prefer, 2))
    d = ImageDraw.Draw(img)
    rings_taken = False
    for lb in labels:
        if lb.prefer not in ("day",) and not rings_taken:
            r = 24 * k
            taken.extend((c[0] - r, c[1] - r, c[0] + r, c[1] + r) for c in rings)
            rings_taken = True
        if not lb.text.strip():
            continue
        w, h, lines = _pill_size(lb, k)
        box = _place(lb, w, h, k, size, taken)
        taken.append(box)
        _draw_pill(d, box, lb, lines, k)
    for c in rings:
        _day_circle(img, c, k)
    return img


def _start_id(pattern: MapPattern) -> int:
    return pattern.start


def render_overlay_only(detector: MapDetector, pattern_id: int, nightlord: int | None, size: int) -> Image.Image:
    """Somente os rótulos (transparente) — para sobrepor ao mapa dentro do jogo."""
    res = detector.detect(
        MapDetectParam(map_region=(0, 0, size, size), draw_pattern_ids=[pattern_id], nightlord=nightlord)
    )
    return res.overlay_images[0]


_ = math  # usado em extensões futuras
