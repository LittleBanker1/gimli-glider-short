# Paints the stylised textures of the apron set (Montreal 1983) with Pillow + numpy.
#   python -I D:\gimli3d\blender\tex\apron\paint_textures.py
# Every texture is a flat, saturated, hand-painted-looking image (no photo detail): slabs with dark joints, glass
# with mullions, signage, the fuel gauge face, decals, clouds. Output: PNG files next to this script.
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
FONTS = r"C:\Windows\Fonts"


def font(name, size, bold=False):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if bold and name.lower().startswith("bahnschrift"):
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def jit(rng, h, amt):
    r, g, b, _ = hexc(h)
    k = 1 + (rng.random() - 0.5) * 2 * amt
    return (max(0, min(255, int(r * k))), max(0, min(255, int(g * k))), max(0, min(255, int(b * k))), 255)


def save(im, name):
    im.save(os.path.join(OUT, name))
    print("wrote", name, im.size)


# ------------------------------------------------------------------ concrete apron slabs (1024 px = 20 m, 4x4 slabs)
def concrete():
    rng = random.Random(3)
    N, S = 1024, 256
    im = Image.new("RGBA", (N, N), hexc("#d3cbb9"))
    d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            c = jit(rng, "#d3cbb9", 0.05)
            # warm / cool slab variation
            if rng.random() < 0.3:
                c = (c[0] - 6, c[1] - 2, c[2] + 6, 255)
            d.rectangle([i * S, j * S, i * S + S - 1, j * S + S - 1], fill=c)
    # aggregate speckles
    for _ in range(9000):
        x, y = rng.randrange(N), rng.randrange(N)
        r = rng.choice([1, 1, 1, 2])
        c = jit(rng, rng.choice(["#b9b09d", "#e2dccd", "#a89f8c"]), 0.05)
        d.ellipse([x, y, x + r, y + r], fill=c)
    # soft blotches (worn patches)
    blot = Image.new("L", (N, N), 0)
    bd = ImageDraw.Draw(blot)
    for _ in range(26):
        x, y = rng.randrange(N), rng.randrange(N)
        rx, ry = rng.randint(30, 110), rng.randint(20, 70)
        bd.ellipse([x - rx, y - ry, x + rx, y + ry], fill=rng.randint(25, 60))
    blot = blot.filter(ImageFilter.GaussianBlur(14))
    dark = Image.new("RGBA", (N, N), hexc("#9d937f"))
    im = Image.composite(dark, im, blot)
    d = ImageDraw.Draw(im)
    # hairline cracks
    for _ in range(22):
        x, y = rng.randrange(N), rng.randrange(N)
        pts = [(x, y)]
        for _k in range(rng.randint(3, 7)):
            x += rng.randint(-30, 30); y += rng.randint(-30, 30); pts.append((x, y))
        d.line(pts, fill=hexc("#857b69"), width=2)
    # joints: dark groove + light lip (seamless: joints sit on the tile border)
    for k in range(5):
        p = k * S
        for off, col, w in ((0, "#6f6656", 5), (4, "#e6e0d2", 2)):
            d.line([(p + off - 2, 0), (p + off - 2, N)], fill=hexc(col), width=w)
            d.line([(0, p + off - 2), (N, p + off - 2)], fill=hexc(col), width=w)
    # tar sealant blobs along joints
    for _ in range(40):
        k = rng.randrange(5) * S
        t = rng.randrange(N)
        x, y = (k, t) if rng.random() < 0.5 else (t, k)
        d.ellipse([x - 6, y - 4, x + 6, y + 4], fill=hexc("#4b4540"))
    save(im.convert("RGB"), "concrete.png")


# ------------------------------------------------------------------ large overlay over the apron (2048 px = 256 m)
def overlay():
    """multiply overlay: grime, rubber, oil stains. Centre of the image = world origin, +x right, +y = world +Y (up in img: -)"""
    rng = random.Random(7)
    N, M = 2048, 256.0
    k = N / M

    def P(x, y):
        return (N / 2 + x * k, N / 2 - y * k)

    L = Image.new("L", (N, N), 255)
    d = ImageDraw.Draw(L)
    # broad warm/cool patches
    big = Image.new("L", (N, N), 255)
    bd = ImageDraw.Draw(big)
    for _ in range(90):
        x, y = rng.uniform(-128, 128), rng.uniform(-128, 128)
        r = rng.uniform(6, 22)
        a, b = P(x - r, y + r * 0.6), P(x + r, y - r * 0.6)
        bd.ellipse([a, b], fill=rng.randint(205, 238))
    big = big.filter(ImageFilter.GaussianBlur(26))
    L = Image.fromarray(np.minimum(np.array(L), np.array(big)))
    d = ImageDraw.Draw(L)
    # rubber marks along the lead-in line (x = 0) where the nose wheel and the mains track
    for x0, w in ((0.0, 1.0), (-4.6, 1.6), (4.6, 1.6)):
        for _ in range(14):
            y1 = rng.uniform(-24, 70); y2 = y1 + rng.uniform(6, 30)
            xx = x0 + rng.uniform(-0.5, 0.5)
            a, b = P(xx - w * 0.3, y2), P(xx + w * 0.3, y1)
            d.rectangle([a, b], fill=rng.randint(150, 200))
    # oil stains under the parked positions (engines, APU, GSE spots, near the terminal)
    for (x, y, n, r) in ((0, -20, 8, 1.8), (7.9, -4, 6, 1.6), (-7.9, -4, 6, 1.6), (0, 22, 5, 1.4), (15, -2, 7, 1.6),
                         (-40, 40, 12, 2.2), (-50, -40, 14, 2.4), (-30, -70, 8, 2.0), (10, 14, 8, 1.6), (-12, -14, 6, 1.5),
                         (-48, 80, 10, 2.0), (30, -40, 8, 2.0)):
        for _ in range(n):
            xx, yy = x + rng.gauss(0, 3), y + rng.gauss(0, 3)
            rr = rng.uniform(0.4, 1.0) * r
            a, b = P(xx - rr, yy + rr * 0.7), P(xx + rr, yy - rr * 0.7)
            d.ellipse([a, b], fill=rng.randint(120, 185))
    L = L.filter(ImageFilter.GaussianBlur(2.2))
    save(L.convert("RGB"), "overlay.png")


# ------------------------------------------------------------------ asphalt (512 px = 8 m)
def asphalt():
    rng = random.Random(11)
    N = 512
    im = Image.new("RGB", (N, N), (96, 99, 114))
    d = ImageDraw.Draw(im)
    for _ in range(9000):
        x, y = rng.randrange(N), rng.randrange(N)
        c = rng.choice([(78, 80, 95), (118, 120, 134), (88, 90, 104), (132, 132, 140)])
        d.point((x, y), fill=c)
        if rng.random() < 0.3:
            d.point((x + 1, y), fill=c)
    blot = Image.new("L", (N, N), 0)
    bd = ImageDraw.Draw(blot)
    for _ in range(14):
        x, y = rng.randrange(N), rng.randrange(N)
        bd.ellipse([x - 60, y - 30, x + 60, y + 30], fill=rng.randint(20, 50))
    blot = blot.filter(ImageFilter.GaussianBlur(18))
    im = Image.composite(Image.new("RGB", (N, N), (70, 72, 88)), im, blot)
    d = ImageDraw.Draw(im)
    for _ in range(6):  # patch seams
        x, y = rng.randrange(N), rng.randrange(N)
        w, h = rng.randint(40, 140), rng.randint(30, 90)
        d.rectangle([x, y, x + w, y + h], outline=(60, 62, 76), width=2)
    save(im, "asphalt.png")


# ------------------------------------------------------------------ grass (512 px = 4 m)
def grass():
    rng = random.Random(5)
    N = 512
    im = Image.new("RGB", (N, N), (106, 170, 64))
    d = ImageDraw.Draw(im)
    for _ in range(5200):
        x, y = rng.randrange(N), rng.randrange(N)
        h = rng.randint(6, 16)
        c = rng.choice([(84, 146, 50), (128, 190, 74), (96, 158, 56), (142, 198, 84), (74, 132, 46)])
        d.line([(x, y), (x + rng.randint(-3, 3), y - h)], fill=c, width=2)
    for _ in range(60):  # tiny flowers
        x, y = rng.randrange(N), rng.randrange(N)
        c = rng.choice([(250, 240, 120), (255, 255, 255), (250, 210, 80)])
        d.ellipse([x, y, x + 3, y + 3], fill=c)
    # make it tile: blend edges by wrapping offsets
    a = np.array(im).astype(np.float32)
    b = np.roll(np.roll(a, N // 2, 0), N // 2, 1)
    w = np.minimum(np.linspace(0, 1, N), np.linspace(1, 0, N)) * 2
    m = np.clip(np.minimum.outer(w, w) * 3, 0, 1)[..., None]
    save(Image.fromarray((a * m + b * (1 - m)).astype(np.uint8)), "grass.png")


# ------------------------------------------------------------------ terminal curtain wall: one bay 8 m wide x 6.5 m
def glass_bay():
    rng = random.Random(2)
    W, H = 512, 416
    im = Image.new("RGB", (W, H))
    a = np.zeros((H, W, 3), np.float32)
    top, bot = np.array([126, 176, 238]), np.array([30, 72, 150])
    t = np.linspace(0, 1, H)[:, None, None]
    a[:] = top * (1 - t) + bot * t
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    # diagonal sky reflection streaks
    for k in range(5):
        x = rng.randint(-200, W)
        w = rng.randint(30, 90)
        d.polygon([(x, H), (x + w, H), (x + w + 260, 0), (x + 260, 0)], fill=(220, 236, 255, rng.randint(30, 60)))
    # a cloud reflection
    for _ in range(6):
        x, y = rng.randint(0, W), rng.randint(10, 120)
        d.ellipse([x - 50, y - 18, x + 50, y + 18], fill=(240, 246, 255, 70))
    # mullions: 4 columns x 3 rows, transoms
    cols, rows = 4, 3
    for i in range(cols + 1):
        x = int(i * W / cols)
        d.rectangle([x - 5, 0, x + 5, H], fill=(214, 220, 228, 255))
        d.line([(x + 5, 0), (x + 5, H)], fill=(120, 128, 140, 255), width=2)
    for j in range(rows + 1):
        y = int(j * H / rows)
        d.rectangle([0, y - 6, W, y + 6], fill=(214, 220, 228, 255))
        d.line([(0, y + 6), (W, y + 6)], fill=(110, 118, 132, 255), width=3)
    # blinds pulled down in a few panes (life inside)
    for _ in range(4):
        i, j = rng.randrange(cols), rng.randrange(rows)
        x0, y0 = int(i * W / cols) + 6, int(j * H / rows) + 7
        h = rng.randint(20, 70)
        d.rectangle([x0, y0, x0 + W // cols - 12, y0 + h], fill=(236, 226, 196, 255))
        for yy in range(y0, y0 + h, 6):
            d.line([(x0, yy), (x0 + W // cols - 12, yy)], fill=(200, 188, 158, 255), width=1)
    save(im, "glass_bay.png")


def ground_floor():
    """ground floor bay (8 m x 4.5 m): dark glass, a door pair, a poster; 512 x 288"""
    W, H = 512, 288
    im = Image.new("RGB", (W, H), (44, 58, 92))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 128):
        d.rectangle([x, 0, x + 8, H], fill=(170, 176, 186))
    d.rectangle([0, 0, W, 12], fill=(170, 176, 186))
    d.rectangle([0, H - 14, W, H], fill=(120, 118, 112))
    # door
    d.rectangle([180, 70, 330, H - 14], fill=(30, 40, 66))
    d.rectangle([180, 70, 330, H - 14], outline=(200, 205, 214), width=6)
    d.line([(255, 70), (255, H - 14)], fill=(200, 205, 214), width=5)
    d.rectangle([228, 160, 236, 200], fill=(230, 230, 230)); d.rectangle([274, 160, 282, 200], fill=(230, 230, 230))
    # warm interior light glow above the door
    d.rectangle([20, 30, 160, 60], fill=(250, 214, 140))
    d.rectangle([352, 30, 492, 60], fill=(250, 214, 140))
    # poster
    d.rectangle([380, 90, 470, 220], fill=(232, 90, 60)); d.rectangle([390, 100, 460, 160], fill=(250, 200, 70))
    save(im, "ground_floor.png")


def sign_band():
    """signage band, 2048 x 112 (one repeat = 64 m of fascia): white letters on a warm orange band"""
    W, H = 2048, 112
    im = Image.new("RGB", (W, H), (214, 86, 44))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=(240, 236, 226)); d.rectangle([0, H - 8, W, H], fill=(120, 44, 30))
    f = font("bahnschrift.ttf", 74, True)
    txt = ["AÉROGARE", "TERMINAL"]
    x = 60
    for k, t in enumerate(txt):
        d.text((x, 16), t, font=f, fill=(255, 250, 238))
        x += d.textlength(t, font=f) + 70
        plane_icon(d, x, 56, 30, (255, 220, 120))
        x += 130
    d.text((x, 16), "MONTRÉAL", font=f, fill=(255, 250, 238))
    x += d.textlength("MONTRÉAL", font=f) + 70
    plane_icon(d, x, 56, 30, (255, 220, 120))
    save(im, "sign_band.png")


def plane_icon(d, cx, cy, s, col):
    """simple airliner pictogram seen from above, nose to the right"""
    d.polygon([(cx - s, cy - s * 0.12), (cx + s * 0.9, cy - s * 0.12), (cx + s * 1.05, cy), (cx + s * 0.9, cy + s * 0.12), (cx - s, cy + s * 0.12)], fill=col)
    d.polygon([(cx + s * 0.1, cy), (cx - s * 0.25, cy - s * 0.95), (cx - s * 0.45, cy - s * 0.95), (cx - s * 0.2, cy)], fill=col)
    d.polygon([(cx + s * 0.1, cy), (cx - s * 0.25, cy + s * 0.95), (cx - s * 0.45, cy + s * 0.95), (cx - s * 0.2, cy)], fill=col)
    d.polygon([(cx - s * 0.75, cy), (cx - s * 0.95, cy - s * 0.4), (cx - s * 1.05, cy - s * 0.4), (cx - s * 0.95, cy)], fill=col)
    d.polygon([(cx - s * 0.75, cy), (cx - s * 0.95, cy + s * 0.4), (cx - s * 1.05, cy + s * 0.4), (cx - s * 0.95, cy)], fill=col)


def gate_sign():
    """gate number board for the jet bridge rotunda / stand sign: 256 x 256 yellow on black"""
    for n in ("12", "14", "10", "16"):
        im = Image.new("RGB", (256, 256), (24, 24, 30))
        d = ImageDraw.Draw(im)
        d.rectangle([8, 8, 247, 247], outline=(250, 200, 40), width=8)
        f = font("bahnschrift.ttf", 170, True)
        w = d.textlength(n, font=f)
        d.text(((256 - w) / 2, 20), n, font=f, fill=(250, 200, 40))
        save(im, f"gate_{n}.png")


# ------------------------------------------------------------------ hangar
def hangar_door():
    W, H = 1024, 512
    im = Image.new("RGB", (W, H), (158, 182, 206))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 16):  # ribs
        d.line([(x, 60), (x, H)], fill=(132, 156, 182), width=4)
        d.line([(x + 5, 60), (x + 5, H)], fill=(186, 206, 226), width=2)
    for x in range(0, W + 1, 128):  # door leaves
        d.rectangle([x - 4, 60, x + 4, H], fill=(70, 86, 112))
    # chequer band
    for i in range(0, W // 32):
        d.rectangle([i * 32, 0, i * 32 + 31, 29], fill=(206, 44, 44) if i % 2 == 0 else (250, 248, 240))
        d.rectangle([i * 32, 30, i * 32 + 31, 59], fill=(250, 248, 240) if i % 2 == 0 else (206, 44, 44))
    f = font("bahnschrift.ttf", 150, True)
    d.ellipse([400, 120, 624, 344], fill=(250, 200, 40), outline=(40, 40, 50), width=10)
    w = d.textlength("5", font=f)
    d.text((512 - w / 2, 135), "5", font=f, fill=(30, 30, 40))
    f2 = font("bahnschrift.ttf", 64, True)
    t = "HANGAR"
    w = d.textlength(t, font=f2)
    d.rectangle([512 - w / 2 - 20, 380, 512 + w / 2 + 20, 460], fill=(250, 248, 240))
    d.text((512 - w / 2, 386), t, font=f2, fill=(206, 44, 44))
    save(im, "hangar_door.png")


def corrugated(name, base, dark, light):
    W = 256
    im = Image.new("RGB", (W, W), hexc(base)[:3])
    d = ImageDraw.Draw(im)
    for x in range(0, W, 16):
        d.line([(x, 0), (x, W)], fill=hexc(dark)[:3], width=4)
        d.line([(x + 6, 0), (x + 6, W)], fill=hexc(light)[:3], width=3)
    save(im, name)


def jetbridge():
    """tunnel side: 512 x 128 per 8 m: corrugated metal + a window band + a red stripe"""
    W, H = 512, 128
    im = Image.new("RGB", (W, H), (214, 208, 196))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 12):
        d.line([(x, 0), (x, H)], fill=(186, 180, 168), width=3)
    d.rectangle([0, 92, W, 104], fill=(196, 64, 48))
    for x in range(24, W, 128):
        d.rounded_rectangle([x, 26, x + 80, 70], radius=10, fill=(40, 70, 120), outline=(70, 72, 80), width=4)
        d.line([(x + 10, 60), (x + 40, 32)], fill=(150, 190, 240), width=5)
    save(im, "jetbridge.png")


# ------------------------------------------------------------------ fuel truck
def gauge():
    """fuel quantity dial, 512 px. Arc: E at -135 deg ... F at +135 deg (0 = up). Needle is separate geometry."""
    N = 512
    im = Image.new("RGB", (N, N), (30, 30, 36))
    d = ImageDraw.Draw(im)
    c = N / 2
    d.ellipse([4, 4, N - 4, N - 4], fill=(200, 204, 212))           # chrome bezel
    d.ellipse([20, 20, N - 20, N - 20], fill=(150, 154, 164))
    d.ellipse([34, 34, N - 34, N - 34], fill=(250, 246, 230))       # cream face
    # coloured arc: red near E, green near F
    for a0, a1, col in ((-135, -100, (220, 50, 40)), (-100, 60, (60, 64, 76)), (60, 135, (60, 170, 80))):
        d.arc([70, 70, N - 70, N - 70], start=a0 - 90, end=a1 - 90, fill=col, width=18)
    # ticks
    for k in range(0, 41):
        a = math.radians(-135 + 270 * k / 40)
        r0 = 168 if k % 10 == 0 else (182 if k % 5 == 0 else 190)
        w = 7 if k % 10 == 0 else 4
        x0, y0 = c + math.sin(a) * r0, c - math.cos(a) * r0
        x1, y1 = c + math.sin(a) * 204, c - math.cos(a) * 204
        d.line([(x0, y0), (x1, y1)], fill=(24, 24, 30), width=w)
    f = font("bahnschrift.ttf", 54, True)
    for k, t in enumerate(["E", "¼", "½", "¾", "F"]):
        a = math.radians(-135 + 270 * k / 4)
        x, y = c + math.sin(a) * 126, c - math.cos(a) * 126
        w = d.textlength(t, font=f)
        d.text((x - w / 2, y - 34), t, font=f, fill=(24, 24, 30))
    f2 = font("bahnschrift.ttf", 40, True)
    for t, y in (("FUEL", 300), ("TANK", 344)):
        w = d.textlength(t, font=f2)
        d.text((c - w / 2, y), t, font=f2, fill=(200, 44, 36))
    # glass glint
    gl = Image.new("L", (N, N), 0)
    gd = ImageDraw.Draw(gl)
    gd.pieslice([60, 60, N - 60, N - 60], 200, 250, fill=70)
    gl = gl.filter(ImageFilter.GaussianBlur(6))
    im = Image.composite(Image.new("RGB", (N, N), (255, 255, 255)), im, gl)
    save(im, "gauge.png")


def placards():
    """decal atlas 1024 x 512: [0] hazard diamond, [1] NO SMOKING, [2] JET A-1 label, [3] UN panel,
    [4] cab door emblem, [5] tank side text strip (2 cells wide), [6] plate"""
    W, H = 1024, 512
    im = Image.new("RGB", (W, H), (242, 238, 228))
    d = ImageDraw.Draw(im)
    S = 256
    fb = font("bahnschrift.ttf", 46, True)
    # 0: flammable diamond (red, white flame, "3")
    d.rectangle([0, 0, S, S], fill=(242, 238, 228))
    d.polygon([(128, 8), (248, 128), (128, 248), (8, 128)], fill=(214, 40, 36), outline=(250, 250, 250))
    d.polygon([(128, 22), (234, 128), (128, 234), (22, 128)], outline=(250, 250, 250), width=6)
    d.polygon([(128, 52), (150, 100), (140, 96), (160, 140), (96, 140), (116, 96), (106, 100)], fill=(250, 250, 250))
    d.text((115, 160), "3", font=fb, fill=(250, 250, 250))
    # 1: NO SMOKING
    x0 = S
    d.rectangle([x0, 0, x0 + S, S], fill=(250, 250, 246))
    d.ellipse([x0 + 40, 20, x0 + 216, 196], outline=(214, 40, 36), width=16)
    d.rectangle([x0 + 80, 100, x0 + 170, 120], fill=(40, 40, 46))
    d.line([(x0 + 70, 46), (x0 + 186, 170)], fill=(214, 40, 36), width=16)
    f = font("bahnschrift.ttf", 32, True)
    d.text((x0 + 36, 206), "NO SMOKING", font=f, fill=(30, 30, 36))
    # 2: JET A-1 (blue on white)
    x0 = 2 * S
    d.rectangle([x0, 0, x0 + S, S], fill=(30, 70, 150))
    d.rectangle([x0 + 12, 12, x0 + S - 12, S - 12], outline=(250, 250, 250), width=6)
    f = font("bahnschrift.ttf", 70, True)
    d.text((x0 + 34, 50), "JET", font=f, fill=(255, 255, 255))
    d.text((x0 + 34, 130), "A-1", font=f, fill=(255, 220, 80))
    # 3: UN orange panel
    x0 = 3 * S
    d.rectangle([x0, 0, x0 + S, S], fill=(242, 238, 228))
    d.rectangle([x0 + 18, 40, x0 + S - 18, S - 40], fill=(244, 140, 30), outline=(20, 20, 20), width=8)
    d.line([(x0 + 18, 128), (x0 + S - 18, 128)], fill=(20, 20, 20), width=6)
    f = font("bahnschrift.ttf", 58, True)
    d.text((x0 + 92, 52), "30", font=f, fill=(20, 20, 20)); d.text((x0 + 66, 136), "1863", font=f, fill=(20, 20, 20))
    # 4: cab door emblem: fuel drop in a circle + "FUEL SERVICE"
    x0, y0 = 0, S
    d.rectangle([x0, y0, x0 + S, y0 + S], fill=(214, 66, 46))
    d.ellipse([x0 + 58, y0 + 18, x0 + 198, y0 + 158], fill=(250, 246, 236))
    d.polygon([(x0 + 128, y0 + 36), (x0 + 168, y0 + 104), (x0 + 88, y0 + 104)], fill=(30, 70, 150))
    d.ellipse([x0 + 88, y0 + 76, x0 + 168, y0 + 146], fill=(30, 70, 150))
    f = font("bahnschrift.ttf", 34, True)
    d.text((x0 + 22, y0 + 172), "FUEL SERVICE", font=f, fill=(255, 255, 255))
    d.text((x0 + 78, y0 + 208), "No. 4", font=f, fill=(255, 220, 120))
    # 5+6: tank side strip (512 x 256): "AVIATION FUEL" + red stripe
    x0 = S
    d.rectangle([x0, y0, x0 + 2 * S, y0 + S], fill=(244, 241, 232))
    d.rectangle([x0, y0 + 150, x0 + 2 * S, y0 + 190], fill=(214, 52, 40))
    d.rectangle([x0, y0 + 196, x0 + 2 * S, y0 + 206], fill=(30, 70, 150))
    f = font("bahnschrift.ttf", 64, True)
    d.text((x0 + 26, y0 + 50), "AVIATION FUEL", font=f, fill=(30, 70, 150))
    # 7: data plate (metal) with rivets
    x0 = 3 * S
    d.rectangle([x0, y0, x0 + S, y0 + S], fill=(190, 194, 200))
    for yy in range(y0 + 40, y0 + 230, 26):
        d.line([(x0 + 30, yy), (x0 + 220, yy)], fill=(90, 92, 100), width=5)
    for (xx, yy) in ((x0 + 12, y0 + 12), (x0 + 236, y0 + 12), (x0 + 12, y0 + 236), (x0 + 236, y0 + 236)):
        d.ellipse([xx - 6, yy - 6, xx + 6, yy + 6], fill=(120, 122, 130))
    save(im, "placards.png")


def panel():
    """the meter cabinet face around the gauge: painted metal with rivets, a valve label, warning stripes, 512 x 768"""
    W, H = 512, 768
    im = Image.new("RGB", (W, H), (236, 232, 222))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], outline=(140, 140, 146), width=14)
    for (xx, yy) in [(24, 24), (W - 24, 24), (24, H - 24), (W - 24, H - 24), (W // 2, 24), (W // 2, H - 24), (24, H // 2), (W - 24, H // 2)]:
        d.ellipse([xx - 8, yy - 8, xx + 8, yy + 8], fill=(150, 150, 158), outline=(90, 90, 96), width=2)
    # warning stripes at the bottom
    for i in range(-4, 16):
        x = i * 48
        d.polygon([(x, H - 120), (x + 24, H - 120), (x + 84, H - 40), (x + 60, H - 40)], fill=(250, 196, 30))
    d.rectangle([0, H - 120, W, H - 40], outline=(30, 30, 36), width=5)
    for i in range(-4, 16):
        x = i * 48 + 24
        d.polygon([(x, H - 120), (x + 24, H - 120), (x + 84, H - 40), (x + 60, H - 40)], fill=(30, 30, 36))
    f = font("bahnschrift.ttf", 46, True)
    d.rectangle([60, 40, W - 60, 110], fill=(214, 52, 40))
    t = "TANK LEVEL"
    w = d.textlength(t, font=f)
    d.text(((W - w) / 2, 48), t, font=f, fill=(255, 255, 255))
    f2 = font("bahnschrift.ttf", 30, True)
    d.rectangle([90, 540, W - 90, 600], fill=(30, 70, 150))
    t = "LITRES ×1000"
    w = d.textlength(t, font=f2)
    d.text(((W - w) / 2, 552), t, font=f2, fill=(255, 255, 255))
    save(im, "panel.png")


# ------------------------------------------------------------------ the other airliner's livery (side, 1024 x 256)
def livery2():
    W, H = 1024, 256
    im = Image.new("RGB", (W, H), (246, 244, 238))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 150, W, 256], fill=(206, 212, 220))
    d.rectangle([0, 112, W, 132], fill=(30, 140, 110))
    d.rectangle([0, 136, W, 142], fill=(240, 180, 40))
    for x in range(90, 900, 16):
        d.rounded_rectangle([x, 88, x + 8, 102], radius=3, fill=(40, 50, 76))
    for x in (70, 520, 880):
        d.rectangle([x, 70, x + 22, 132], outline=(120, 124, 134), width=3)
    d.polygon([(950, 80), (990, 78), (1000, 100), (950, 102)], fill=(30, 40, 60))
    save(im, "livery2.png")


# ------------------------------------------------------------------ clouds (RGBA)
def cloud(seed, name):
    rng = random.Random(seed)
    W, H = 1024, 512
    a = Image.new("L", (W, H), 0)
    ad = ImageDraw.Draw(a)
    puffs = []
    n = rng.randint(9, 14)
    for i in range(n):
        x = W * (0.12 + 0.76 * i / (n - 1)) + rng.uniform(-30, 30)
        base = H * 0.72
        r = rng.uniform(60, 130) * (1 - 0.55 * abs(i / (n - 1) - 0.5))
        y = base - r * rng.uniform(0.45, 0.95)
        puffs.append((x, y, r))
    for x, y, r in puffs:
        ad.ellipse([x - r, y - r, x + r, y + r], fill=255)
    ad.rectangle([W * 0.1, H * 0.55, W * 0.9, H * 0.72], fill=255)
    a = a.filter(ImageFilter.GaussianBlur(1.5))
    # shading: lit top white, cool lavender underside, soft core
    yy = np.linspace(0, 1, H)[:, None]
    shade = np.clip((yy - 0.42) / 0.3, 0, 1)
    top = np.array([252, 250, 244]); mid = np.array([228, 232, 246]); low = np.array([182, 194, 232])
    col = np.where(shade[..., None] < 0.5, top * (1 - shade[..., None] * 2) + mid * shade[..., None] * 2,
                   mid * (2 - shade[..., None] * 2) + low * (shade[..., None] * 2 - 1))
    col = np.broadcast_to(col, (H, W, 3)).copy()
    # puff rims: lighter crescents on top-left of each puff
    rim = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rim)
    for x, y, r in puffs:
        rd.ellipse([x - r * 0.85, y - r * 0.9, x + r * 0.55, y + r * 0.3], fill=40)
    rim = np.array(rim.filter(ImageFilter.GaussianBlur(10)))[..., None] / 255.0
    col = np.clip(col + rim * 40, 0, 255)
    # thin cool outline
    al = np.array(a).astype(np.float32) / 255
    edge = np.array(a.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
    col = col * (1 - edge[..., None] * 0.35) + np.array([120, 130, 180]) * edge[..., None] * 0.35
    out = np.dstack([col, al * 255]).astype(np.uint8)
    save(Image.fromarray(out, "RGBA"), name)


def chainlink():
    N = 128
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (150, 160, 170, 255)
    for k in range(-2, 3):
        o = k * 64
        d.line([(o, 0), (o + N, N)], fill=c, width=5)
        d.line([(o + N, 0), (o, N)], fill=c, width=5)
    save(im, "chainlink.png")


def carmaps():
    """recoloured copies of the Kenney car colormap: the body column of every car is repainted to a 1980s colour.
    Cells are 32 px; the gradient band rows 4-7 (y 128-255) and 8-11 (y 256-383) hold the body colours."""
    src = Image.open(r"D:\gimli3d\kenney\car-kit\Models\GLB format\Textures\colormap.png").convert("RGBA")
    a = np.array(src).astype(np.float32)
    pal = {"maroon": "#7c2533", "cream": "#dccb9e", "mustard": "#c89a2c", "brown": "#6e4528", "navy": "#2c3f78",
           "avocado": "#7f8c3c", "orange": "#c8642a", "skyblue": "#86a7cc", "white": "#efebe0", "red": "#bf3a2e",
           "teal": "#2f8a84", "yellow": "#f0b62e", "beige": "#c9b48a", "green": "#3f7a4a"}
    for name, h in pal.items():
        b = a.copy()
        r, g, bl, _ = hexc(h)
        tgt = np.array([r, g, bl], np.float32)
        # the body colours of the kit's cars live in band 1 (y 128-255): green x 192-255 (truck, hatchback,
        # delivery), yellow 256-319 (taxi), red 384-447 (sedan), blue 448-511 (van). Repaint them keeping the
        # cell's own vertical light gradient.
        for x0, x1 in ((192, 256), (256, 320), (384, 448), (448, 512)):
            blk = b[128:256, x0:x1, :3]
            lum = blk.mean(axis=2, keepdims=True)
            k = np.clip(lum / max(1.0, float(lum.mean())), 0.7, 1.2)
            b[128:256, x0:x1, :3] = np.clip(tgt * k, 0, 255)
        Image.fromarray(b.astype(np.uint8), "RGBA").save(os.path.join(OUT, f"car_{name}.png"))
    print("wrote car maps", len(pal))


if __name__ == "__main__":
    concrete(); overlay(); asphalt(); grass(); glass_bay(); ground_floor(); sign_band(); gate_sign()
    hangar_door(); corrugated("corr_cream.png", "#e9dfc6", "#c9bea4", "#f6efdc"); corrugated("corr_blue.png", "#7f9ccc", "#617eae", "#a1badf")
    corrugated("corr_grey.png", "#b9bcc4", "#9a9ea8", "#d4d6dc")
    jetbridge(); gauge(); placards(); panel(); livery2(); chainlink(); carmaps()
    for i in range(4):
        cloud(10 + i, f"cloud{i}.png")
