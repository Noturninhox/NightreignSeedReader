"""Gera a arte lateral da janela de instalação (nrseed/assets/installer_side.png)."""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ICON = Image.open(ROOT / "nrseed/assets/icon.png").convert("RGBA")
CINZEL = str(ROOT / "nrseed/assets/Cinzel.ttf")
GOLD, GOLD_HI, MUTED = (214, 176, 98), (240, 210, 140), (150, 138, 112)


def font(px, weight=700):
    f = ImageFont.truetype(CINZEL, px)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def bg(w, h):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line((0, y, w, y), fill=(int(14 + 8 * (1 - t)), int(13 + 7 * (1 - t)), int(20 + 26 * (1 - t))))
    rnd = random.Random(7)
    for _ in range(int(w * h / 900)):
        x, y = rnd.random() * w, rnd.random() * h * 0.7
        a = rnd.randint(60, 170)
        r = rnd.choice((0.5, 0.8, 1.2)) * w / 164
        d.ellipse((x - r, y - r, x + r, y + r), fill=(a, a, int(a * 1.1)))
    return img


def big(w, h):
    s = w / 164
    img = bg(w, h)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = w / 2, h * 0.36, w * 0.42
    gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 160, 80, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(18 * s))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    size = int(w * 0.72)
    img.alpha_composite(ICON.resize((size, size), Image.LANCZOS), (int(cx - size / 2), int(cy - size / 2)))
    d = ImageDraw.Draw(img)
    def center(text, y, f, fill):
        tw = d.textlength(text, font=f)
        d.text(((w - tw) / 2, y), text, font=f, fill=fill)
    center("NIGHTREIGN", h * 0.64, font(int(21 * s)), GOLD_HI)
    center("SEED READER", h * 0.64 + 27 * s, font(int(12.5 * s), 600), GOLD)
    d.line((w * 0.22, h * 0.64 + 48 * s, w * 0.78, h * 0.64 + 48 * s), fill=(110, 90, 50), width=max(1, int(s)))
    center("leitor de seed por tela", h * 0.64 + 56 * s, font(int(8.5 * s), 500), MUTED)
    d.rectangle((0, 0, w - 1, h - 1), outline=(70, 58, 36), width=max(1, int(s)))
    return img.convert("RGB")


def small(w, h):
    img = bg(w, h).convert("RGBA")
    m = int(min(w, h) * 0.06)
    size = min(w, h) - 2 * m
    img.alpha_composite(ICON.resize((size, size), Image.LANCZOS), ((w - size) // 2, (h - size) // 2))
    return img.convert("RGB")


big(400, 840).save(ROOT / "nrseed/assets/installer_side.png")
print("ok")
