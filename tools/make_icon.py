"""Gera o ícone do app (nrseed/assets/icon.png + icon.ico)."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

S = 1024 * 2  # supersampling
C = S // 2
GOLD = (214, 176, 98, 255)
GOLD_HI = (245, 214, 140, 255)
GOLD_DK = (120, 92, 44, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

def circle(r, **kw):
    d.ellipse((C - r, C - r, C + r, C + r), **kw)

# disco escuro com leve gradiente radial azul-noite
R = int(S * 0.47)
bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
bd = ImageDraw.Draw(bg)
for i in range(R, 0, -4):
    t = i / R
    col = (int(10 + 22 * (1 - t)), int(10 + 20 * (1 - t)), int(16 + 40 * (1 - t)), 255)
    bd.ellipse((C - i, C - i, C + i, C + i), fill=col)
img.alpha_composite(bg)

# anéis dourados
circle(R, outline=GOLD, width=int(S * 0.022))
circle(int(R * 0.90), outline=GOLD_DK, width=int(S * 0.008))
# marcações tipo bússola no anel
for k in range(24):
    a = k * math.tau / 24
    r1, r2 = R * 0.905, R * (0.955 if k % 6 == 0 else 0.93)
    w = int(S * (0.010 if k % 6 == 0 else 0.005))
    d.line((C + r1 * math.cos(a), C + r1 * math.sin(a), C + r2 * math.cos(a), C + r2 * math.sin(a)), fill=GOLD, width=w)

# lua crescente (noite)
moon = Image.new("L", (S, S), 0)
md = ImageDraw.Draw(moon)
mr = R * 0.66
md.ellipse((C - mr, C - mr, C + mr, C + mr), fill=255)
off = mr * 0.34
md.ellipse((C - mr + off, C - mr - off * 0.55, C + mr + off, C + mr - off * 0.55), fill=0)
glow = moon.filter(ImageFilter.GaussianBlur(S * 0.02))
img.paste(Image.new("RGBA", (S, S), (200, 165, 90, 90)), (0, 0), glow)
img.paste(Image.new("RGBA", (S, S), GOLD), (0, 0), moon)

# marcador de mapa (pin) com a "semente" no centro
px, py = C + R * 0.20, C + R * 0.02
pr = R * 0.26
pin = Image.new("L", (S, S), 0)
pd = ImageDraw.Draw(pin)
pd.ellipse((px - pr, py - pr, px + pr, py + pr), fill=255)
pd.polygon([(px - pr * 0.82, py + pr * 0.55), (px + pr * 0.82, py + pr * 0.55), (px, py + pr * 2.15)], fill=255)
shadow = pin.filter(ImageFilter.GaussianBlur(S * 0.012))
img.paste(Image.new("RGBA", (S, S), (0, 0, 0, 170)), (int(S * 0.006), int(S * 0.012)), shadow)
img.paste(Image.new("RGBA", (S, S), GOLD_HI), (0, 0), pin)
inner = Image.new("L", (S, S), 0)
ImageDraw.Draw(inner).ellipse((px - pr * 0.62, py - pr * 0.62, px + pr * 0.62, py + pr * 0.62), fill=255)
img.paste(Image.new("RGBA", (S, S), (14, 13, 20, 255)), (0, 0), inner)
# semente (losango) dentro do pin
sr = pr * 0.40
d.polygon([(px, py - sr), (px + sr * 0.68, py), (px, py + sr), (px - sr * 0.68, py)], fill=GOLD_HI)

out = Path(__file__).resolve().parents[1] / "nrseed" / "assets"
final = img.resize((1024, 1024), Image.LANCZOS)
final.save(out / "icon.png")
final.save(out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
m = Image.new("RGBA", (600, 260), (30, 30, 30, 255))
x = 10
for s in (256, 128, 64, 32, 16):
    m.alpha_composite(final.resize((s, s), Image.LANCZOS), (x, 2))
    x += s + 20
m.save("/tmp/icon_preview.png")
print("ok")
