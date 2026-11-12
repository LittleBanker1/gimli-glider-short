# "gimli" set: RCAF Station Gimli, Manitoba, 23 July 1983 -- a decommissioned air force base turned race track, on race
# day (shots 11, 14-17, golden) and the analogy meadow west of it (shot 12, day).
#
# Two halves in one file:
#   1. a texture PAINTER that runs with the system Python + Pillow:  python -I gimli.py --paint [--force]
#      (writes D:\gimli3d\blender\tex\gimli\*.png; build() runs it automatically when a texture is missing)
#   2. the Blender builder (build / animate), see render_shot.py for the contract.
# Coordinates: Blender metres, z up, +X east, +Y north. Runway along Y (x -30..30, y -1500..1500), the jet lands toward -Y.
import json
import math
import os
import random
import subprocess
import sys

try:
    import bpy
    import bmesh
    from mathutils import Matrix, Vector
except ImportError:  # running as the painter outside Blender
    bpy = None

HERE = os.path.dirname(os.path.abspath(__file__))
BLDIR = os.path.dirname(HERE)
TEX = os.path.join(BLDIR, "tex", "gimli")
PY = r"C:\Users\plamb\AppData\Local\Programs\Python\Python312\python.exe"
FONT = r"C:\Windows\Fonts"

# Line Art radius fallback (metres). The real stroke width is set per point by a Geometry Nodes pass added in animate()
# (constant screen width: ~3.4 px near -> ~2.2 px far at 1080x1920), so this value only matters if that pass fails.
INK_RADIUS = {12: 0.012, 11: 0.08, "default": 0.03}

# ======================================================================================= 1. PAINTER (Pillow, numpy)
TEX_VERSION = 7


def _np():
    import numpy as np
    return np


def _noise(n, cells, seed, octaves=1, falloff=0.5):
    """tileable smooth value noise in [0, 1], n x n"""
    np = _np()
    from PIL import Image
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = max(2, int(cells * 2 ** o))
        g = rng.random((c, c))
        t = np.tile(g, (3, 3))
        im = Image.fromarray((t * 255).astype(np.uint8)).resize((3 * n, 3 * n), Image.BICUBIC)
        out += amp * np.asarray(im, dtype=float)[n:2 * n, n:2 * n] / 255
        tot += amp
        amp *= falloff
    out /= tot
    return (out - out.min()) / max(1e-6, out.max() - out.min())


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lerp3(a, b, t):
    np = _np()
    a, b = np.array(a, float), np.array(b, float)
    return a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]


def _wrap_draw(draw_fn, n, x, y, r):
    """call draw_fn(dx, dy) for every wrapped copy needed so a mark near an edge tiles"""
    for dx in (-n, 0, n):
        for dy in (-n, 0, n):
            if -r <= x + dx <= n + r and -r <= y + dy <= n + r:
                draw_fn(dx, dy)


def _font(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONT, name), size)


def paint_grass(path, n=2048, seed=1, dry=0.0, flowers=900, palette=None):
    """prairie grass tile (8 m): green field with blade strokes, dry patches, wildflower dots"""
    np = _np()
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    pal = palette or dict(dark="#3f7a2c", mid="#5f9e38", light="#86b847", dry="#b8a456")
    n1, n2, n3 = _noise(n, 6, seed, 3), _noise(n, 3, seed + 1, 2), _noise(n, 24, seed + 2, 2)
    col = _lerp3(_hex(pal["dark"]), _hex(pal["mid"]), np.clip(n1 * 1.4 - 0.2, 0, 1))
    col = col * (1 - 0.45 * np.clip(n3 - 0.5, 0, 1)[..., None]) + np.array(_hex(pal["light"]))[None, None] * 0.45 * np.clip(n3 - 0.5, 0, 1)[..., None]
    d = np.clip((n2 - (0.62 - dry)) * 3, 0, 1)[..., None] * 0.75
    col = col * (1 - d) + np.array(_hex(pal["dry"]))[None, None] * d
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    arr = np.asarray(im)
    for _ in range(int(n * n / 55)):
        x, y = rng.uniform(0, n), rng.uniform(0, n)
        base = arr[int(y) % n, int(x) % n].astype(float)
        k = rng.random()
        if k < 0.45:
            c = base * rng.uniform(0.55, 0.75)
        elif k < 0.85:
            c = base * rng.uniform(1.12, 1.3) + np.array([6, 8, 0])
        else:
            c = np.array(_hex("#c9b766")) * rng.uniform(0.85, 1.1)
        c = tuple(int(v) for v in np.clip(c, 0, 255))
        L = rng.uniform(5, 16) * n / 2048
        a = rng.uniform(0, math.tau)
        x2, y2 = x + math.cos(a) * L, y + math.sin(a) * L
        w = 2 if rng.random() < 0.3 else 1
        _wrap_draw(lambda dx, dy: dr.line((x + dx, y + dy, x2 + dx, y2 + dy), fill=c, width=w), n, x, y, 20)
    fl = ["#f6d23c", "#f6d23c", "#ffffff", "#9a62d8", "#4f7fe6", "#e2402e", "#f39a2a"]
    for _ in range(flowers):
        x, y = rng.uniform(0, n), rng.uniform(0, n)
        c = _hex(rng.choice(fl))
        r = rng.uniform(2.5, 5) * n / 2048
        def f(dx, dy, x=x, y=y, c=c, r=r):
            dr.ellipse((x + dx - r, y + dy - r, x + dx + r, y + dy + r), fill=c, outline=(40, 60, 25))
            dr.ellipse((x + dx - r * 0.35, y + dy - r * 0.35, x + dx + r * 0.35, y + dy + r * 0.35), fill=(250, 220, 90) if c != _hex("#f6d23c") else (150, 90, 20))
        _wrap_draw(f, n, x, y, 8)
    im.save(path)


def paint_macro(path, n=512, seed=5):
    """large-scale multiply map (values ~0.8-1.12, slight hue shifts), tileable, for the ground (~1.2 km)"""
    np = _np()
    from PIL import Image
    a, b, c = _noise(n, 5, seed, 3), _noise(n, 9, seed + 1, 2), _noise(n, 3, seed + 2, 2)
    v = 0.84 + 0.3 * a
    r = v * (0.96 + 0.1 * c)
    g = v * (1.0 + 0.04 * (b - 0.5))
    bl = v * (0.95 + 0.06 * (1 - c))
    arr = np.stack([r, g, bl], -1) / 1.15
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8)).save(path)


def paint_runway(path, kind, seed, n=2048):
    """one 60 m x 60 m runway segment (u = x -30..30, v = local y 0..60 from its south edge).
    kinds: plain, td (touchdown bars), thr (threshold keys + number), drag (drag-strip lanes + rubber), dragstart"""
    np = _np()
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(seed)
    ppm = n / 60.0
    P = lambda x, y: ((x + 30) * ppm, (60 - y) * ppm)  # metres -> pixel (image row 0 = north edge)
    base = np.array(_hex("#bdb5a5"), float)
    n1, n2 = _noise(n, 10, seed, 3), _noise(n, 40, seed + 3, 2)
    arr = base[None, None] * (0.9 + 0.16 * n1[..., None]) * (0.95 + 0.08 * n2[..., None])
    # slabs 7.5 m with their own tone
    for i in range(8):
        for j in range(8):
            t = rng.uniform(0.92, 1.07)
            warm = rng.uniform(-6, 6)
            x0, y0 = int(i * 7.5 * ppm), int(j * 7.5 * ppm)
            x1, y1 = int((i + 1) * 7.5 * ppm), int((j + 1) * 7.5 * ppm)
            arr[y0:y1, x0:x1] = arr[y0:y1, x0:x1] * t + np.array([warm, warm * 0.5, -warm])
    # speckle
    sp = np.random.default_rng(seed).random((n, n))
    arr[sp > 0.985] *= 0.78
    arr[sp < 0.01] *= 1.12
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    # repair patches (dark asphalt) and oil stains
    for _ in range(rng.randint(2, 5)):
        cx, cy = rng.uniform(-28, 28), rng.uniform(2, 58)
        w, h = rng.uniform(1.5, 6), rng.uniform(1.5, 8)
        x0, y0 = P(cx - w / 2, cy + h / 2); x1, y1 = P(cx + w / 2, cy - h / 2)
        dr.rectangle((x0, y0, x1, y1), fill=(92, 88, 86, 235), outline=(60, 56, 54, 255), width=3)
    for _ in range(rng.randint(10, 22)):
        cx, cy = rng.uniform(-28, 28), rng.uniform(1, 59)
        r = rng.uniform(0.3, 1.6) * ppm
        x, y = P(cx, cy)
        dr.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=(70, 64, 60, rng.randint(40, 110)))
    def wear(mask_alpha):  # faded paint: noise-gated alpha
        return mask_alpha
    paint = Image.new("L", (n, n), 0)
    pd = ImageDraw.Draw(paint)
    def rect(x0, y0, x1, y1, v=255):
        a, b = P(x0, y1); c, d = P(x1, y0)
        pd.rectangle((a, b, c, d), fill=v)
    fresh = Image.new("L", (n, n), 0)
    fd = ImageDraw.Draw(fresh)
    def frect(x0, y0, x1, y1, v=255):
        a, b = P(x0, y1); c, d = P(x1, y0)
        fd.rectangle((a, b, c, d), fill=v)
    # markings
    if kind in ("plain", "td"):
        rect(-0.45, 15, 0.45, 45)
    for sx in (-1, 1):
        rect(sx * 28.1 - 0.45, 0, sx * 28.1 + 0.45, 60, 200)  # edge stripes
    if kind == "td":
        for sx in (-1, 1):
            for k in range(3):
                rect(sx * 6 - 0.9 + sx * k * 2.6, 8, sx * 6 + 0.9 + sx * k * 2.6, 30)
            rect(sx * 13 - 4.5 * (sx < 0) - 0, 36, sx * 13 + 4.5 * (sx > 0), 54)  # aiming point blocks
    if kind == "thr":
        for sx in (-1, 1):
            for k in range(6):
                x = sx * (3.0 + k * 3.6)
                rect(x - 0.9, 3, x + 0.9, 33)
        im_num = Image.new("L", (int(16 * ppm), int(14 * ppm)), 0)
        nd = ImageDraw.Draw(im_num)
        nd.text((im_num.width / 2, im_num.height / 2), "36", font=_font("ariblk.ttf", int(12 * ppm)), fill=255, anchor="mm")
        x0, y0 = P(-8, 54)
        paint.paste(255, (int(x0), int(y0)), im_num)
        pd.rectangle((*P(-29, 1.2), *P(29, 0.2)), fill=230)
    if kind in ("drag", "dragstart"):
        for sx in (-1, 1):
            frect(sx * 0.9 - 0.12, 0, sx * 0.9 + 0.12, 60, 235)
            frect(sx * 19.5 - 0.15, 0, sx * 19.5 + 0.15, 60, 245)
        if kind == "dragstart":
            frect(-19.5, 20, 19.5, 20.5, 255)   # start line (cars run toward -Y)
            frect(-19.5, 23, 19.5, 23.25, 230)  # pre-stage line
    # paint wear: multiply mask by noise
    wn = _noise(n, 30, seed + 9, 3)
    pa = np.asarray(paint, float) / 255 * np.clip(0.25 + wn * 0.95, 0, 0.9)
    fa = np.asarray(fresh, float) / 255 * np.clip(0.75 + wn * 0.3, 0, 1)
    a = np.asarray(im, float)
    white = np.array(_hex("#f3efe2"), float)
    a = a * (1 - pa[..., None]) + white[None, None] * pa[..., None]
    a = a * (1 - fa[..., None]) + white[None, None] * fa[..., None]
    if kind in ("drag", "dragstart"):  # rubber: tyre streaks along the lanes, heavy behind the start line
        rub = Image.new("L", (n, n), 0)
        rd = ImageDraw.Draw(rub)
        for sx in (-1, 1):
            for lane in (5.2, 10.4, 15.2):
                for tw in (-0.8, 0.8):
                    for k in range(5):
                        xo = sx * lane + tw + rng.uniform(-0.25, 0.25)
                        y0 = 0 if kind == "drag" else rng.uniform(-2, 18)
                        y1 = 60 if kind == "drag" else rng.uniform(19, 24)
                        wv = rng.uniform(0.12, 0.3) * ppm
                        pts = []
                        for s in range(12):
                            yy = y0 + (y1 - y0) * s / 11
                            pts.append(P(xo + 0.08 * math.sin(yy * 0.3 + k), yy))
                        rd.line(pts, fill=rng.randint(40, 120) if kind == "drag" else rng.randint(120, 220), width=max(1, int(wv)))
        rub = rub.filter(ImageFilter.GaussianBlur(1.2))
        ra = np.asarray(rub, float)[..., None] / 255
        a = a * (1 - ra * 0.85) + np.array([38, 34, 36])[None, None] * ra * 0.85
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    # joints (7.5 m grid) with weeds, cracks
    jc = (88, 82, 74, 255)
    for i in range(9):
        x = i * 7.5 * ppm
        dr.line((x, 0, x, n), fill=jc, width=3)
        dr.line((0, x, n, x), fill=jc, width=3)
    weed = [(78, 128, 52), (102, 150, 60), (60, 104, 44), (130, 160, 70)]
    def tuft(x, y, s=1.0):
        for _ in range(rng.randint(4, 9)):
            a_ = rng.uniform(0, math.tau); L = rng.uniform(3, 11) * s
            c = rng.choice(weed)
            dr.line((x, y, x + math.cos(a_) * L, y + math.sin(a_) * L), fill=c + (255,), width=2)
        if rng.random() < 0.15:
            r = 2.5 * s
            dr.ellipse((x - r, y - r, x + r, y + r), fill=_hex(rng.choice(["#f6d23c", "#ffffff", "#f6d23c"])) + (255,))
    for i in range(9):
        for along in range(0, n, 3):
            if rng.random() < 0.09 * (1.6 if i in (0, 8) else 1):
                x = i * 7.5 * ppm
                if rng.random() < 0.5:
                    tuft(x + rng.uniform(-2, 2), along)
                else:
                    tuft(along, x + rng.uniform(-2, 2))
    for _ in range(rng.randint(14, 26)):  # cracks: random walks, branching
        x, y = rng.uniform(0, n), rng.uniform(0, n)
        a_ = rng.uniform(0, math.tau)
        pts = [(x, y)]
        for s in range(rng.randint(8, 30)):
            a_ += rng.uniform(-0.7, 0.7)
            x += math.cos(a_) * rng.uniform(8, 22); y += math.sin(a_) * rng.uniform(8, 22)
            pts.append((x, y))
            if rng.random() < 0.08:
                tuft(x, y, 0.8)
        dr.line(pts, fill=(70, 64, 58, 255), width=2)
        dr.line([(p[0] + 1, p[1] + 1) for p in pts], fill=(222, 214, 198, 150), width=1)
    im.save(path)


def paint_shoulder(path, n=1024, seed=21):
    """old asphalt shoulder tile (6 m): dark, cracked, grass creeping in"""
    np = _np()
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    n1, n2 = _noise(n, 8, seed, 3), _noise(n, 30, seed + 1, 2)
    arr = _lerp3(_hex("#57534f"), _hex("#7a7268"), n1) * (0.92 + 0.12 * n2[..., None])
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for _ in range(40):
        x, y = rng.uniform(0, n), rng.uniform(0, n)
        a_ = rng.uniform(0, math.tau); pts = [(x, y)]
        for s in range(rng.randint(5, 18)):
            a_ += rng.uniform(-0.8, 0.8); x += math.cos(a_) * 14; y += math.sin(a_) * 14; pts.append((x, y))
        dr.line(pts, fill=(40, 38, 36), width=2)
        for p in pts[::2]:
            for _ in range(3):
                a2 = rng.uniform(0, math.tau)
                dr.line((p[0], p[1], p[0] + math.cos(a2) * 8, p[1] + math.sin(a2) * 8), fill=rng.choice([(86, 130, 52), (110, 150, 60)]), width=2)
    im.save(path)


def paint_corrugated(path, n=512, seed=31, base="#8f9a8c", rib=16, rust=0.5, horizontal=False):
    """corrugated metal (tile 4 m): ribs, faded paint, rust streaks"""
    np = _np()
    from PIL import Image
    rng = np.random.default_rng(seed)
    x = np.arange(n)
    ribs = 0.88 + 0.16 * (0.5 + 0.5 * np.sin(x / n * rib * math.tau))
    ribs = np.tile(ribs[None, :], (n, 1))
    if horizontal:
        ribs = ribs.T
    n1 = _noise(n, 6, seed, 3)
    col = np.array(_hex(base), float)[None, None] * ribs[..., None] * (0.9 + 0.18 * n1[..., None])
    # vertical rust streaks
    streak = np.zeros((n, n))
    for _ in range(int(14 * rust)):
        cx = rng.integers(0, n); w = rng.integers(3, 12); top = rng.integers(0, n // 2); L = rng.integers(n // 4, n)
        yy = np.arange(n)
        prof = np.clip(1 - np.abs(yy - top - L / 2) / (L / 2), 0, 1) ** 0.7
        for dx in range(-w, w + 1):
            streak[:, (cx + dx) % n] = np.maximum(streak[:, (cx + dx) % n], prof * (1 - abs(dx) / (w + 1)) * rng.uniform(0.4, 0.9))
    if horizontal:
        streak = streak.T
    rustc = np.array(_hex("#9a5a32"), float)
    col = col * (1 - streak[..., None] * 0.7) + rustc[None, None] * streak[..., None] * 0.7
    # seams every 1/2 tile
    for s in (0, n // 2):
        if horizontal:
            col[:, s:s + 2] *= 0.55
        else:
            col[s:s + 2, :] *= 0.55
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(path)


def paint_door(path, w=1024, h=512, seed=41, base="#7f8e96"):
    """hangar door facade: 8 sliding panels, a band of small window panes (some broken), stencil number"""
    np = _np()
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    n1 = _noise(max(w, h), 8, seed, 3)[:h, :w]
    col = np.array(_hex(base), float)[None, None] * (0.86 + 0.2 * n1[..., None])
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    pw = w / 8
    for i in range(8):
        x0 = i * pw
        dr.rectangle((x0, 0, x0 + pw, h), outline=(48, 54, 62, 255), width=4)
        # vertical ribs
        for k in range(1, 10):
            xx = x0 + k * pw / 10
            dr.line((xx, h * 0.33, xx, h), fill=(60, 68, 76, 120), width=2)
        # window band: 2 rows x 5 panes
        for r in range(2):
            for c in range(5):
                px0 = x0 + 8 + c * (pw - 16) / 5; py0 = h * 0.08 + r * h * 0.11
                px1 = px0 + (pw - 16) / 5 - 5; py1 = py0 + h * 0.1
                broken = rng.random() < 0.22
                fill = (38, 44, 66, 255) if broken else (150, 190, 214, 255)
                dr.rectangle((px0, py0, px1, py1), fill=fill, outline=(40, 44, 50, 255), width=2)
                if not broken:
                    dr.line((px0 + 3, py1 - 3, px0 + (px1 - px0) * 0.5, py0 + 3), fill=(230, 245, 255, 200), width=2)
        # rust bleed below windows, dents
        for _ in range(3):
            xx = x0 + rng.uniform(10, pw - 10)
            dr.line((xx, h * 0.31, xx + rng.uniform(-3, 3), h * rng.uniform(0.45, 0.8)), fill=(140, 82, 46, 90), width=rng.randint(3, 8))
    dr.rectangle((0, h * 0.31, w, h * 0.33), fill=(52, 58, 66, 255))
    dr.rectangle((0, h - 14, w, h), fill=(58, 52, 46, 255))
    im.save(path)


def paint_sign(path, text, w=1024, h=256, bg="#d8382e", fg="#ffffff", font="ROCKEB.TTF", border="#1c1a22", sub=None, stripes=None, check=False):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), _hex(bg))
    dr = ImageDraw.Draw(im)
    if stripes:
        for i, c in enumerate(stripes):
            dr.rectangle((0, h * (0.08 + 0.06 * i), w, h * (0.12 + 0.06 * i)), fill=_hex(c))
            dr.rectangle((0, h * (0.88 - 0.06 * i), w, h * (0.92 - 0.06 * i)), fill=_hex(c))
    if check:
        s = h // 4
        for yy in range(0, h, s):
            for xx in range(0, w, s):
                if ((xx // s) + (yy // s)) % 2 == 0 and (xx < h or xx >= w - h):
                    dr.rectangle((xx, yy, xx + s, yy + s), fill=(20, 20, 24))
                elif (xx < h or xx >= w - h):
                    dr.rectangle((xx, yy, xx + s, yy + s), fill=(245, 245, 240))
    size = int(h * (0.5 if sub else 0.62))
    f = _font(font, size)
    while dr.textlength(text, font=f) > w * (0.62 if check else 0.88) and size > 10:
        size -= 4; f = _font(font, size)
    dr.text((w / 2, h * (0.42 if sub else 0.5)), text, font=f, fill=_hex(fg), anchor="mm", stroke_width=max(2, size // 18), stroke_fill=_hex(border))
    if sub:
        dr.text((w / 2, h * 0.8), sub, font=_font("arialbd.ttf", int(h * 0.17)), fill=_hex(fg), anchor="mm")
    dr.rectangle((0, 0, w - 1, h - 1), outline=_hex(border), width=max(4, h // 40))
    im.save(path)


def paint_number(path, num, bg="#ffffff", fg="#16121e", n=256):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((6, 6, n - 6, n - 6), fill=_hex(bg) + (255,), outline=(22, 18, 30, 255), width=8)
    dr.text((n / 2, n / 2 + 4), str(num), font=_font("ariblk.ttf", int(n * 0.55)), fill=_hex(fg), anchor="mm")
    im.save(path)


def paint_cloud(path, seed, golden, w=1024, h=512):
    """stylised cumulus card: lobes, lit top / shaded belly, thin ink contour, alpha"""
    np = _np()
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(seed)
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    base_y = h * 0.78
    lobes = []
    x = w * 0.08
    while x < w * 0.92:
        r = rng.uniform(0.09, 0.2) * w * (1.25 if 0.3 < x / w < 0.7 else 0.8)
        r = min(r, base_y * 0.9)
        cy = base_y - r * rng.uniform(0.35, 0.8)
        lobes.append((x, cy, r))
        x += r * rng.uniform(0.7, 1.05)
    for _ in range(3):  # top puffs
        lx, ly, lr = rng.choice(lobes[1:-1] or lobes)
        lobes.append((lx + rng.uniform(-lr, lr) * 0.5, ly - lr * 0.55, lr * rng.uniform(0.55, 0.8)))
    for (cx, cy, r) in lobes:
        md.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    md.rectangle((lobes[0][0], base_y - h * 0.08, lobes[-4][0] if len(lobes) > 4 else w * 0.9, base_y), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.5)).point(lambda v: 255 if v > 128 else 0)
    m = np.asarray(mask, float) / 255
    yy = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    # shading: distance from top edge of the mask per column + per-lobe highlight
    shade = np.clip((yy * h - (base_y - h * 0.45)) / (h * 0.38), 0, 1)
    if golden:
        lit, mid, sh, ink = _hex("#ffd7ae"), _hex("#f0a08f"), _hex("#9c86c4"), (60, 40, 86)
    else:
        lit, mid, sh, ink = _hex("#fdfbf6"), _hex("#e3e7f4"), _hex("#bcc6e8"), (96, 110, 160)
    t1 = np.clip(shade * 1.6, 0, 1)
    col = _lerp3(lit, mid, t1)
    t2 = np.clip(shade * 1.6 - 0.75, 0, 1)
    col = col * (1 - t2[..., None]) + np.array(sh)[None, None] * t2[..., None]
    # lobe rims: brighten upper-left of each lobe
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    hl = Image.new("L", (w, h), 0)
    hd = ImageDraw.Draw(hl)
    for (cx, cy, r) in lobes:
        hd.ellipse((cx - r * 0.75, cy - r * 0.9, cx + r * 0.35, cy - r * 0.1), fill=120)
    hl = hl.filter(ImageFilter.GaussianBlur(w * 0.02))
    ha = np.asarray(hl, float)[..., None] / 255
    col = np.asarray(img, float) * (1 - ha * 0.6) + np.array(lit)[None, None] * ha * 0.6
    # contour: mask edge
    er = np.asarray(mask.filter(ImageFilter.MinFilter(5)), float) / 255
    edge = np.clip(m - er, 0, 1)[..., None]
    col = col * (1 - edge * 0.85) + np.array(ink)[None, None] * edge * 0.85
    rgba = np.dstack([np.clip(col, 0, 255), m * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)


def paint_sun(path, n=512):
    np = _np()
    from PIL import Image
    yy, xx = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    disc = np.clip((0.2 - r) * 120, 0, 1)
    glow = np.clip(1 - r, 0, 1) ** 2.4 * 0.75
    a = np.clip(disc + glow, 0, 1)
    col = np.stack([np.full_like(r, 255), 236 - 40 * (1 - disc), 190 - 80 * (1 - disc)], -1)
    Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA").save(path)


def paint_treeline(path, w=2048, h=256, seed=51):
    """horizon ring strip: bumpy tree-line silhouette (white, alpha), tileable along u"""
    np = _np()
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    im = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(im)
    x = 0
    while x < w + 40:
        r = rng.uniform(6, 22)
        top = h * rng.uniform(0.25, 0.7) if rng.random() < 0.85 else h * rng.uniform(0.05, 0.25)
        if rng.random() < 0.12:  # gaps (fields)
            top = h * 0.82
        for dx in (-w, 0, w):
            dr.ellipse((x - r + dx, top - r, x + r + dx, top + r), fill=255)
            dr.rectangle((x - r + dx, top, x + r + dx, h), fill=255)
        x += r * rng.uniform(0.6, 1.2)
    a = np.asarray(im, float) / 255
    sh = _noise(w, 40, seed, 2)[:h, :]
    v = 0.85 + 0.25 * sh
    rgba = np.dstack([v * 255, v * 255, v * 255, a * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)


def paint_field(path, kind, n=512, seed=61):
    """farm field tile (40 m): rows of crop"""
    np = _np()
    from PIL import Image
    cols = {"wheat": ("#d9b14a", "#b98c2e"), "canola": ("#f2d22a", "#c9b020"), "flax": ("#7f95d8", "#5f78c0"),
            "pasture": ("#79b04a", "#5e9638"), "plowed": ("#8a6446", "#6e4c34"), "hay": ("#cdbb72", "#a99752"),
            "barley": ("#c8c06a", "#a8a050")}
    a, b = cols[kind]
    x = np.arange(n)
    rows = 0.5 + 0.5 * np.sin(x / n * 40 * math.tau)
    t = np.tile(rows[None, :], (n, 1)) * 0.7 + _noise(n, 12, seed, 2) * 0.3
    col = _lerp3(_hex(a), _hex(b), t) * (0.92 + 0.12 * _noise(n, 4, seed + 1, 2)[..., None])
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(path)


def paint_water(path, n=512, seed=71, golden=True):
    np = _np()
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    base = _hex("#5a62b0") if golden else _hex("#3f7fd0")
    col = np.array(base, float)[None, None] * (0.9 + 0.15 * _noise(n, 6, seed, 2)[..., None])
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    glint = (255, 196, 150) if golden else (220, 236, 255)
    for _ in range(260):
        x, y = rng.uniform(0, n), rng.uniform(0, n)
        L = rng.uniform(4, 22)
        dr.line((x, y, x + L, y), fill=glint, width=1)
    im.save(path)


def paint_rv(path, w=1024, h=256, scheme=("#7a4a2a", "#d9822b", "#f2c230"), seed=81):
    """motorhome / camper side: cream body, 70s stripes, windows, door"""
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    im = Image.new("RGB", (w, h), _hex("#f1eadb"))
    dr = ImageDraw.Draw(im)
    y = h * 0.52
    for i, c in enumerate(scheme):
        dr.polygon([(0, y + i * 14), (w, y + i * 14 - 30), (w, y + i * 14 - 30 + 12), (0, y + i * 14 + 12)], fill=_hex(c))
    dr.rectangle((0, h * 0.86, w, h), fill=_hex("#5d554c"))
    for k in range(3):
        x0 = w * (0.12 + 0.28 * k) + rng.uniform(-10, 10)
        dr.rounded_rectangle((x0, h * 0.18, x0 + w * 0.16, h * 0.42), 10, fill=_hex("#2f3d5c"), outline=_hex("#26222a"), width=4)
        dr.line((x0 + 10, h * 0.38, x0 + w * 0.07, h * 0.21), fill=_hex("#9fb8d8"), width=5)
        dr.line((x0, h * 0.42 + 4, x0 + w * 0.16, h * 0.42 + 4), fill=_hex("#8a8a8a"), width=6)
    dr.rounded_rectangle((w * 0.83, h * 0.16, w * 0.92, h * 0.84), 6, fill=_hex("#e3dccb"), outline=_hex("#26222a"), width=4)
    dr.rectangle((w * 0.845, h * 0.2, w * 0.905, h * 0.38), fill=_hex("#2f3d5c"))
    dr.rectangle((0, 0, w - 1, h - 1), outline=_hex("#26222a"), width=4)
    im.save(path)


def paint_bricks(path, n=512, base="#b5654a", seed=91):
    """brick / block wall tile (3 m)"""
    np = _np()
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    im = Image.new("RGB", (n, n), (150, 140, 128))
    dr = ImageDraw.Draw(im)
    bh = n / 16; bw = n / 6
    b = np.array(_hex(base))
    for r in range(16):
        off = (r % 2) * bw / 2
        for c in range(-1, 7):
            t = rng.uniform(0.85, 1.12)
            col = tuple(int(v) for v in np.clip(b * t, 0, 255))
            dr.rectangle((c * bw + off + 2, r * bh + 2, c * bw + off + bw - 2, r * bh + bh - 2), fill=col)
    im.save(path)


def paint_tower_windows(path, w=512, h=256):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), _hex("#3c5a7a"))
    dr = ImageDraw.Draw(im)
    for k in range(6):
        x0 = k * w / 6
        dr.rectangle((x0, 0, x0 + w / 6, h), outline=_hex("#2a2730"), width=10)
        dr.line((x0 + 18, h - 30, x0 + w / 6 - 30, 30), fill=_hex("#9cc3e0"), width=8)
        if k in (1, 4):
            dr.polygon([(x0 + 30, 40), (x0 + 60, 120), (x0 + 45, 200), (x0 + 10, 150)], fill=_hex("#151824"))
    im.save(path)


TEXTURES = {}


def _tex_jobs():
    j = {}
    j["grass_prairie.png"] = lambda p: paint_grass(p, seed=1, dry=0.12, flowers=1100)
    j["grass_meadow.png"] = lambda p: paint_grass(p, seed=2, dry=-0.1, flowers=1500,
                                                  palette=dict(dark="#3c8a2e", mid="#5aa83c", light="#8cc84a", dry="#b8b05a"))
    j["macro.png"] = lambda p: paint_macro(p)
    for k, kind in enumerate(["plain", "plain", "plain", "td", "thr", "drag", "dragstart"]):
        j[f"rw_{kind}{k}.png"] = (lambda kind, k: (lambda p: paint_runway(p, kind, 100 + k)))(kind, k)
    j["shoulder.png"] = lambda p: paint_shoulder(p)
    j["corr_wall.png"] = lambda p: paint_corrugated(p, base="#8c9b8a", seed=31)
    j["corr_wall2.png"] = lambda p: paint_corrugated(p, base="#a8a092", seed=32)
    j["corr_roof.png"] = lambda p: paint_corrugated(p, base="#7d8186", seed=33, rib=24, rust=1.0, horizontal=True)
    j["corr_red.png"] = lambda p: paint_corrugated(p, base="#b0433a", seed=34, rib=20, rust=0.6)
    j["hangar_door.png"] = lambda p: paint_door(p, seed=41, base="#7f9096")
    j["hangar_door2.png"] = lambda p: paint_door(p, seed=42, base="#9a9a86")
    signs = {
        "sign_raceday": dict(text="RACE DAY", bg="#d8382e", sub="GIMLI  JULY 23", stripes=["#f2c230"]),
        "sign_pits": dict(text="PITS", bg="#2f62c8", fg="#ffffff"),
        "sign_finish": dict(text="FINISH", bg="#ffffff", fg="#16121e", check=True),
        "sign_start": dict(text="START", bg="#f2c230", fg="#16121e", check=True),
        "sign_snack": dict(text="SNACK BAR", bg="#f2c230", fg="#c8323a", sub="HOT DOGS 50c  FRIES  POP"),
        "sign_dragstrip": dict(text="DRAG STRIP", bg="#16121e", fg="#f2c230", stripes=["#d8382e"]),
        "sign_spect": dict(text="SPECTATORS", bg="#2f9a55", fg="#ffffff"),
        "sign_rcaf": dict(text="GIMLI", bg="#c9c2b0", fg="#3c4a6a", font="ariblk.ttf", sub="INDUSTRIAL PARK - FORMER RCAF STATION"),
        "sign_hangar2": dict(text="2", bg="#8f9a8c", fg="#e9e4d4", font="ariblk.ttf"),
        "sign_hangar3": dict(text="3", bg="#a8a092", fg="#e9e4d4", font="ariblk.ttf"),
        "sign_club": dict(text="SPORTS CAR CLUB", bg="#ffffff", fg="#2f62c8", sub="FAMILY DAY  -  WELCOME", stripes=["#d8382e", "#2f62c8"]),
        "sign_fuel": dict(text="FUEL", bg="#d8382e", fg="#ffffff"),
        "sign_noparking": dict(text="NO PARKING", bg="#ffffff", fg="#d8382e"),
        "sign_bingo": dict(text="LAKESIDE CAMP", bg="#3f6fb5", fg="#ffffff", sub="BAIT  ICE  FIREWOOD"),
    }
    for name, kw in signs.items():
        j[name + ".png"] = (lambda kw: (lambda p: paint_sign(p, **kw)))(kw)
    for i, num in enumerate([7, 12, 23, 3, 44, 18, 9, 31, 5, 61]):
        j[f"num{i}.png"] = (lambda num: (lambda p: paint_number(p, num)))(num)
    for s in range(4):
        j[f"cloud_g{s}.png"] = (lambda s: (lambda p: paint_cloud(p, 200 + s, True)))(s)
        j[f"cloud_d{s}.png"] = (lambda s: (lambda p: paint_cloud(p, 300 + s, False)))(s)
    j["sun.png"] = lambda p: paint_sun(p)
    j["treeline.png"] = lambda p: paint_treeline(p)
    for k in ["wheat", "canola", "flax", "pasture", "plowed", "hay", "barley"]:
        j[f"field_{k}.png"] = (lambda k: (lambda p: paint_field(p, k)))(k)
    j["water_g.png"] = lambda p: paint_water(p, golden=True)
    j["water_d.png"] = lambda p: paint_water(p, golden=False)
    j["rv_a.png"] = lambda p: paint_rv(p, scheme=("#7a4a2a", "#d9822b", "#f2c230"), seed=81)
    j["rv_b.png"] = lambda p: paint_rv(p, scheme=("#2f62a8", "#58a0d8", "#9ad0f0"), seed=82)
    j["rv_c.png"] = lambda p: paint_rv(p, scheme=("#2f7a3a", "#78b04a", "#e0d060"), seed=83)
    j["bricks.png"] = lambda p: paint_bricks(p)
    j["blocks.png"] = lambda p: paint_bricks(p, base="#cfc6b2", seed=92)
    j["tower_win.png"] = lambda p: paint_tower_windows(p)
    return j


def paint_all(force=False):
    os.makedirs(TEX, exist_ok=True)
    stamp = os.path.join(TEX, "version.txt")
    if os.path.exists(stamp) and open(stamp).read().strip() != str(TEX_VERSION):
        force = True
    for name, fn in _tex_jobs().items():
        p = os.path.join(TEX, name)
        if force or not os.path.exists(p):
            fn(p)
            print("painted", name, flush=True)
    open(stamp, "w").write(str(TEX_VERSION))


if __name__ == "__main__" and bpy is None:
    paint_all("--force" in sys.argv)
    sys.exit(0)
KENNEY = r"D:\gimli3d\kenney"
KIT_RECOLOR = {"nature-kit": {
    "leafsGreen": "#3fb02a", "leafsDark": "#1f8a3a", "leafsFall": "#e8832a", "grass": "#7ccc34", "woodBark": "#7a4a2c",
    "woodBarkDark": "#5a3820", "woodBirch": "#efe6d2", "woodInner": "#d8b080", "wood": "#a8733a", "woodDark": "#6a4528",
    "dirt": "#8f8a82", "stone": "#a6a39a", "colorPurple": "#8a4cd8", "colorYellow": "#f6c22a", "colorRed": "#d8382e",
    "colorRedDark": "#b02a28", "colorWhite": "#fffaf0"},
    "racing-kit": {"red": "#d8382e", "grey": "#e9e6dc", "road": "#3a3840", "pylon": "#f2a32a"}}

# ======================================================================================== 2. BUILDER (shared helpers)
_S = {}
# ================================================================ small utilities
def V(*a):
    return Vector(a)


def tex(name):
    return os.path.join(TEX, name)


def img(name):
    return bpy.data.images.load(tex(name), check_existing=True)


class Mats:
    """material cache: toon colours (lib.toon), textured toon, emissive and alpha-cut materials"""

    def __init__(self, lib):
        self.lib = lib

    def c(self, hexcol, ao=False):
        return self.lib.toon("gm_" + hexcol.lstrip("#") + ("_ao" if ao else ""), hexcol, ao=ao)

    def t(self, name, image, size=(1.0, 1.0), tint=None, ao=False):
        """textured toon; the batch UVs are in metres, so size = metres covered by one texture repeat"""
        m = bpy.data.materials.get("gm_" + name)
        if m:
            return m
        m = self.lib.toon("gm_" + name, tint, image=tex(image), repeat=(1.0 / size[0], 1.0 / size[1]), ao=ao)
        return m

    def emit(self, name, hexcol, strength=1.0):
        m = bpy.data.materials.get("gm_e_" + name)
        if m:
            return m
        m = bpy.data.materials.new("gm_e_" + name); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
        e.inputs[0].default_value = (*self.lib.hex_rgb(hexcol), 1); e.inputs[1].default_value = strength
        nt.links.new(e.outputs[0], o.inputs[0])
        return m

    def cutout(self, name, image, size=(1.0, 1.0), tint=None):
        """toon with the image alpha as a hard cut (chain-link fence)"""
        m = bpy.data.materials.get("gm_" + name)
        if m:
            return m
        m = bpy.data.materials.new("gm_" + name); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear(); L = nt.links
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = self.lib.toon_group()
        uv = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.0 / size[0], 1.0 / size[1], 1)
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(image)
        L.new(uv.outputs["UV"], mp.inputs[0]); L.new(mp.outputs[0], t.inputs[0])
        g.inputs["Albedo"].default_value = (*self.lib.hex_rgb(tint or "#a9b2bc"), 1)
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        cut = nt.nodes.new("ShaderNodeMath"); cut.operation = "GREATER_THAN"; cut.inputs[1].default_value = 0.5
        L.new(t.outputs["Alpha"], cut.inputs[0]); L.new(cut.outputs[0], mix.inputs[0])
        L.new(tr.outputs[0], mix.inputs[1]); L.new(g.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], o.inputs[0])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
        m.use_backface_culling = False
        return m

    def card(self, name, image, alpha_blend=True, mult=1.0):
        """unlit picture with alpha (cloud cards)"""
        m = bpy.data.materials.get("gm_" + name)
        if m:
            return m
        m = bpy.data.materials.new("gm_" + name); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear(); L = nt.links
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(image); t.extension = "CLIP"
        e = nt.nodes.new("ShaderNodeEmission"); e.inputs[1].default_value = mult
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        L.new(t.outputs["Color"], e.inputs[0]); L.new(t.outputs["Alpha"], mix.inputs[0])
        L.new(tr.outputs[0], mix.inputs[1]); L.new(e.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], o.inputs[0])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED" if alpha_blend else "DITHERED"
        m.use_backface_culling = False
        return m


# ================================================================ mesh batches
class Batch:
    """accumulates primitives (world-space, optional transform stack) into one bmesh -> one object.
    UVs: explicit, or box-projected in metres (so textured materials set their repeat in metres)."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.verify()
        self.mats = []
        self.T = Matrix.Identity(4)
        self._stack = []

    # transform stack -------------------------------------------------------
    def push(self, T):
        self._stack.append(self.T); self.T = self.T @ T
        return self

    def pop(self):
        self.T = self._stack.pop()

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _v(self, p):
        return self.bm.verts.new(self.T @ Vector(p))

    def _uvbox(self, f, scale=1.0):
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co
            u, v = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            if (ax == 0 and n.x < 0) or (ax == 1 and n.y > 0):
                u = -u
            l[self.uv].uv = (u / scale, v / scale)

    def _face(self, vs, mat, uvs=None, smooth=False, uvscale=1.0):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self._mi(mat); f.smooth = smooth
        f.normal_update()
        if uvs:
            for l, uv in zip(f.loops, uvs):
                l[self.uv].uv = uv
        else:
            self._uvbox(f, uvscale)
        return f

    def _orient(self, faces, centre):
        for f in faces:
            if f is None:
                continue
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - centre) < 0:
                f.normal_flip()

    # primitives ------------------------------------------------------------
    def quad(self, pts, mat, uvs=None, uvscale=1.0):
        vs = [self._v(p) for p in pts]
        return self._face(vs, mat, uvs, uvscale=uvscale)

    def box(self, mn, mx, mat, mats=None, uvscale=1.0):
        """axis box in local coords; mats = dict(top=, bottom=, px=, nx=, py=, ny=) per-side overrides"""
        x0, y0, z0 = mn; x1, y1, z1 = mx
        c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        v = [self._v(p) for p in c]
        sides = dict(bottom=(0, 3, 2, 1), top=(4, 5, 6, 7), ny=(0, 1, 5, 4), px=(1, 2, 6, 5), py=(2, 3, 7, 6), nx=(3, 0, 4, 7))
        fs = []
        for k, idx in sides.items():
            m = (mats or {}).get(k, mat)
            fs.append(self._face([v[i] for i in idx], m, uvscale=uvscale))
        self._orient(fs, sum((x.co for x in v), Vector()) / 8)
        return fs

    def obox(self, centre, size, mat, yaw=0.0, mats=None, pitch=0.0):
        """box of size (sx, sy, sz) centred at centre, rotated by yaw (about z) then pitch (about local x)"""
        T = Matrix.Translation(Vector(centre)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "X")
        self.push(T)
        sx, sy, sz = size
        fs = self.box((-sx / 2, -sy / 2, -sz / 2), (sx / 2, sy / 2, sz / 2), mat, mats)
        self.pop()
        return fs

    def cyl(self, p0, p1, r0, r1=None, mat=None, seg=16, caps=True, cap_mat=None, smooth=True, ell=1.0):
        """cylinder / cone frustum from p0 to p1 (local coords); ell squashes the section along the 2nd axis"""
        r1 = r0 if r1 is None else r1
        p0, p1 = Vector(p0), Vector(p1)
        ax = (p1 - p0)
        if ax.length < 1e-6:
            return []
        ax.normalize()
        a = ax.orthogonal().normalized(); b = ax.cross(a).normalized()
        if abs(ax.z) < 0.9:  # keep the ellipse axis vertical for horizontal cylinders
            b = Vector((0, 0, 1)); b = (b - ax * b.dot(ax)).normalized(); a = b.cross(ax).normalized()
        ring0, ring1 = [], []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            d = a * math.cos(t) + b * math.sin(t) * ell
            ring0.append(self._v(p0 + d * r0)); ring1.append(self._v(p1 + d * r1))
        fs = []
        L = (p1 - p0).length
        for i in range(seg):
            j = (i + 1) % seg
            uvs = [(i / seg * 2 * math.pi * r0, 0), (j / seg * 2 * math.pi * r0 if j else 2 * math.pi * r0, 0),
                   ((j / seg if j else 1.0) * 2 * math.pi * r1, L), (i / seg * 2 * math.pi * r1, L)]
            fs.append(self._face([ring0[i], ring0[j], ring1[j], ring1[i]], mat, uvs=uvs, smooth=smooth))
        if caps:
            cm = cap_mat or mat
            if r0 > 1e-4:
                fs.append(self._face(ring0[::-1], cm))
            if r1 > 1e-4:
                fs.append(self._face(ring1, cm))
        self._orient(fs, self.T @ ((p0 + p1) / 2))
        return fs

    def disc(self, centre, normal, r, mat, seg=24, uv_unit=False):
        """flat disc facing `normal`; uv_unit maps the disc to the whole 0..1 image (dial faces)"""
        n = Vector(normal).normalized()
        a = n.orthogonal().normalized()
        if abs(n.z) < 0.9:
            up = Vector((0, 0, 1)); a = up.cross(n).normalized()  # a = image +u (right), b = image +v (up)
        b = n.cross(a).normalized()
        vs, uvs = [], []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            vs.append(self._v(Vector(centre) + (a * math.cos(t) + b * math.sin(t)) * r))
            uvs.append((0.5 + 0.5 * math.cos(t), 0.5 + 0.5 * math.sin(t)))
        f = self._face(vs, mat, uvs if uv_unit else None)
        if f and (self.T.to_3x3() @ n).dot(f.normal) < 0:
            f.normal_flip()
        return f

    def prism(self, profile, z0, z1, mat, axis="z", cap_mat=None):
        """extrude a convex/concave 2D profile (list of (u, v)) along an axis between z0 and z1.
        axis 'z': profile in (x, y); 'x': profile in (y, z); 'y': profile in (x, z)"""
        def P(u, v, w):
            return {"z": (u, v, w), "x": (w, u, v), "y": (u, w, v)}[axis]
        b = [self._v(P(u, v, z0)) for u, v in profile]
        t = [self._v(P(u, v, z1)) for u, v in profile]
        fs = []
        n = len(profile)
        for i in range(n):
            j = (i + 1) % n
            fs.append(self._face([b[i], b[j], t[j], t[i]], mat))
        fs.append(self._face(b[::-1], cap_mat or mat)); fs.append(self._face(t, cap_mat or mat))
        # orientation: profile assumed counter-clockwise in its (u, v) plane; fix with the centroid otherwise
        c = sum((x.co for x in b + t), Vector()) / (2 * n)
        self._orient(fs[:n], c)
        cap_axis = self.T.to_3x3() @ Vector(P(0, 0, 1))
        for f, s in ((fs[n], -1), (fs[n + 1], 1)):
            if f and f.normal.dot(cap_axis) * s < 0:
                f.normal_flip()
        return fs

    def tube(self, pts, r, mat, seg=8, caps=True):
        """tube along a polyline (local coords) with parallel-transported rings"""
        pts = [Vector(p) for p in pts]
        if len(pts) < 2:
            return
        rings = []
        prev_a = None
        for k, p in enumerate(pts):
            if k == 0:
                t = pts[1] - pts[0]
            elif k == len(pts) - 1:
                t = pts[-1] - pts[-2]
            else:
                t = (pts[k + 1] - pts[k]).normalized() + (pts[k] - pts[k - 1]).normalized()
            t.normalize()
            if prev_a is None:
                a = t.orthogonal().normalized()
            else:
                a = (prev_a - t * prev_a.dot(t)).normalized()
            b = t.cross(a)
            prev_a = a
            rings.append([self._v(p + (a * math.cos(2 * math.pi * i / seg) + b * math.sin(2 * math.pi * i / seg)) * r) for i in range(seg)])
        for k in range(len(rings) - 1):
            for i in range(seg):
                j = (i + 1) % seg
                f = self._face([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]], mat, smooth=True)
                if f:
                    c = (self.T @ (pts[k] + pts[k + 1])) / 2
                    if f.normal.dot(f.calc_center_median() - c) < 0:
                        f.normal_flip()
        if caps:
            for ring, k, s in ((rings[0], 0, -1), (rings[-1], -1, 1)):
                f = self._face(ring, mat)
                if f:
                    d = (pts[1] - pts[0]) if k == 0 else (pts[-1] - pts[-2])
                    if f.normal.dot(self.T.to_3x3() @ d) * s < 0:
                        f.normal_flip()

    def dome(self, centre, r, mat, seg=12, rings=4, zscale=1.0):
        """upper hemisphere"""
        c = Vector(centre)
        rows = []
        for k in range(rings):
            th = (math.pi / 2) * k / rings
            rows.append([self._v(c + Vector((math.cos(2 * math.pi * i / seg) * math.cos(th) * r,
                                              math.sin(2 * math.pi * i / seg) * math.cos(th) * r, math.sin(th) * r * zscale))) for i in range(seg)])
        top = self._v(c + Vector((0, 0, r * zscale)))
        fs = []
        for k in range(rings - 1):
            for i in range(seg):
                j = (i + 1) % seg
                fs.append(self._face([rows[k][i], rows[k][j], rows[k + 1][j], rows[k + 1][i]], mat, smooth=True))
        for i in range(seg):
            j = (i + 1) % seg
            fs.append(self._face([rows[-1][i], rows[-1][j], top], mat, smooth=True))
        fs.append(self._face(rows[0][::-1], mat))
        self._orient(fs, self.T @ c)

    def build(self, col, name=None):
        me = bpy.data.meshes.new(name or self.name)
        self.bm.to_mesh(me); self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name or self.name, me)
        col.objects.link(o)
        return o


# ================================================================ Kenney imports (all kits, both folder layouts)
_kcache = {}


def kit_roots(lib, kit, model, recolor=None):
    key = (kit, model)
    if key in _kcache:
        return _kcache[key]
    base = os.path.join(KENNEY, kit, "Models")
    path = os.path.join(base, "GLB format", model + ".glb")
    if not os.path.exists(path):
        path = os.path.join(base, "GLTF format", model + ".glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    rc = dict(KIT_RECOLOR.get(kit, {}))
    rc.update(recolor or {})
    for o in new:
        for s in getattr(o, "material_slots", []):
            if s.material and not s.material.name.startswith("T_"):
                base = s.material.name.split(".")[0]
                s.material = lib.to_toon(s.material, {s.material.name: rc[base]} if base in rc else None)
    tmpl = bpy.data.collections.get("_templates") or bpy.data.collections.new("_templates")
    for o in new:
        lib.link(o, tmpl)
    roots = [o for o in new if o.parent is None]
    _kcache[key] = roots
    return roots


def kit(lib, col, kitname, model, loc, rot_z=0.0, scale=1.0, recolor=None, mat_all=None, body_mat=None):
    """place a Kenney model (linked duplicate). mat_all: override every slot; body_mat: override the slots of the
    object named 'body' (car paint variants)"""
    made = []
    for r in kit_roots(lib, kitname, model, recolor):
        d = lib._dup_tree(r, col)
        d.location = loc; d.rotation_euler = (0, 0, rot_z)
        d.scale = (scale, scale, scale) if not isinstance(scale, tuple) else scale
        made.append(d)
        stack = [d]
        while stack:
            o = stack.pop(); stack.extend(o.children)
            if o.type != "MESH":
                continue
            if mat_all is not None:
                for s in o.material_slots:
                    s.link = "OBJECT"; s.material = mat_all
            elif body_mat is not None:
                for s in o.material_slots:
                    s.link = "OBJECT"; s.material = body_mat
    return made

def _ink_width_setup():
    """screen-constant ink: a geometry-nodes modifier on the shared Line Art object sets every stroke point's
    radius to  W_px(d) * d * tan(fov/2) / 1920  (d = distance to the camera); W from 3.4 px near to 2.3 px far"""
    ink = bpy.data.objects.get("Ink")
    if ink is None or ink.modifiers.get("GimliInkWidth"):
        return
    ng = bpy.data.node_groups.new("GimliInkWidth", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    cam = N.new("GeometryNodeInputActiveCamera")
    oi = N.new("GeometryNodeObjectInfo"); oi.transform_space = "ORIGINAL"
    pos = N.new("GeometryNodeInputPosition")
    dist = N.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"
    px = N.new("ShaderNodeMapRange"); px.interpolation_type = "SMOOTHSTEP"
    px.inputs[1].default_value = 4.0; px.inputs[2].default_value = 140.0
    px.inputs[3].default_value = 3.4; px.inputs[4].default_value = 2.3
    m1 = N.new("ShaderNodeMath"); m1.operation = "MULTIPLY"
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
    kv = N.new("ShaderNodeValue"); kv.name = "K"; kv.outputs[0].default_value = math.tan(math.radians(20)) / 1920
    scr = N.new("GeometryNodeSetCurveRadius")
    L.new(cam.outputs[0], oi.inputs[0]); L.new(oi.outputs["Location"], dist.inputs[0]); L.new(pos.outputs[0], dist.inputs[1])
    L.new(dist.outputs["Value"], px.inputs[0])
    L.new(dist.outputs["Value"], m1.inputs[0]); L.new(px.outputs[0], m1.inputs[1])
    L.new(m1.outputs[0], m2.inputs[0]); L.new(kv.outputs[0], m2.inputs[1])
    L.new(gi.outputs[0], scr.inputs[0]); L.new(m2.outputs[0], scr.inputs["Radius"]); L.new(scr.outputs[0], go.inputs[0])
    mod = ink.modifiers.new("GimliInkWidth", "NODES"); mod.node_group = ng
    _S["ink_k"] = kv



# ================================================================ Kenney with real-size fitting
_dims = {}


def kit_dims(lib, kitname, model):
    """(min, max) corner of the template in Blender axes (cached)"""
    key = (kitname, model)
    if key in _dims:
        return _dims[key]
    roots = kit_roots(lib, kitname, model)
    bpy.context.view_layer.update()
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    stack = list(roots)
    while stack:
        o = stack.pop(); stack.extend(o.children)
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector((min(mn.x, w.x), min(mn.y, w.y), min(mn.z, w.z)))
            mx = Vector((max(mx.x, w.x), max(mx.y, w.y), max(mx.z, w.z)))
    _dims[key] = (mn, mx)
    return _dims[key]


def fit(lib, col, kitname, model, loc, yaw=0.0, length=None, height=None, width=None, scale=None, mat_all=None, recolor=None):
    """Kenney model, base centre at loc, scaled so its long horizontal side = length / height = height / x-size = width.
    yaw: rotation about z (0 = the model as imported)."""
    mn, mx = kit_dims(lib, kitname, model)
    sz = mx - mn
    if scale is None:
        if length:
            scale = length / max(sz.x, sz.y)
        elif height:
            scale = height / sz.z
        elif width:
            scale = width / sz.x
        else:
            scale = 1.0
    c = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    R = Matrix.Rotation(yaw, 3, "Z")
    rl = Vector(loc) - R @ (c * scale)
    made = kit(lib, col, kitname, model, rl, yaw, scale, recolor=recolor, mat_all=mat_all)
    for d in made:
        d.rotation_mode = "XYZ"
        d.rotation_euler = (0, 0, yaw)
    return made


# ================================================================ small builders
def side_uv(B, f, pattern, u1=1.0):
    if f is None:
        return
    for l, (u, v) in zip(f.loops, pattern):
        l[B.uv].uv = (u * u1, v)


SIDE = [(0, 0), (1, 0), (1, 1), (0, 1)]


def poly_pyramid(B, cx, cy, z0, z1, hw, hl, mat, mat2=None):
    pts = [(cx - hw, cy - hl, z0), (cx + hw, cy - hl, z0), (cx + hw, cy + hl, z0), (cx - hw, cy + hl, z0)]
    ap = (cx, cy, z1)
    for i in range(4):
        B._face([B._v(pts[i]), B._v(pts[(i + 1) % 4]), B._v(ap)], mat if (mat2 is None or i % 2 == 0) else mat2)


def canopy(B, M, x, y, yaw, col1, col2, size=3.0, tall=2.4):
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    h = size / 2
    leg = M.c("#cfd3d8")
    for sx in (-h, h):
        for sy in (-h, h):
            B.cyl((sx, sy, 0), (sx, sy, tall), 0.04, mat=leg, seg=6)
    poly_pyramid(B, 0, 0, tall, tall + 0.8, h + 0.15, h + 0.15, M.c(col1), M.c(col2))
    # valance
    for sx, sy, ww, ll in ((0, h + 0.15, h + 0.15, 0.02), (0, -h - 0.15, h + 0.15, 0.02), (h + 0.15, 0, 0.02, h + 0.15), (-h - 0.15, 0, 0.02, h + 0.15)):
        B.box((sx - ww, sy - ll, tall - 0.28), (sx + ww, sy + ll, tall), M.c(col2))
    B.pop()


def table_chairs(B, M, x, y, yaw, cols):
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    B.box((-0.9, -0.4, 0.72), (0.9, 0.4, 0.76), M.c("#f2efe6"))
    for sx in (-0.8, 0.8):
        for sy in (-0.32, 0.32):
            B.box((sx - 0.025, sy - 0.025, 0), (sx + 0.025, sy + 0.025, 0.72), M.c("#9aa2ac"))
    for i, (cx, cy, r) in enumerate(((0, 0.9, 0), (0.8, -0.9, 0.5), (-0.7, -0.9, -0.4))):
        lawn_chair(B, M, cx, cy, r, cols[i % len(cols)])
    B.box((-0.3, -0.2, 0.76), (0.1, 0.1, 1.0), M.c("#e0402c"))  # cooler on the table
    B.pop()


def lawn_chair(B, M, x, y, yaw, colr):
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    m = M.c(colr)
    fr = M.c("#d4d8de")
    B.box((-0.25, -0.25, 0.28), (0.25, 0.22, 0.34), m)
    B.obox((0, 0.24, 0.55), (0.5, 0.05, 0.55), m, pitch=-0.25)
    for sx in (-0.24, 0.24):
        B.box((sx - 0.015, -0.24, 0), (sx + 0.015, -0.2, 0.3), fr)
        B.box((sx - 0.015, 0.2, 0), (sx + 0.015, 0.24, 0.3), fr)
        B.box((sx - 0.02, -0.25, 0.3), (sx + 0.02, 0.2, 0.34), fr)
    B.pop()


def tyre_stack(B, M, x, y, n=3, white=False, r=0.48):
    blk = M.c("#1c1a20"); wh = M.c("#f1efe8"); hub = M.c("#4a4852")
    for k in range(n):
        m = wh if (white and k % 2 == 1) else blk
        B.cyl((x, y, k * 0.24), (x, y, k * 0.24 + 0.23), r, mat=m, seg=14)
        B.disc((x, y, k * 0.24 + 0.231), (0, 0, 1), r * 0.55, hub, seg=12)


def jersey(B, M, x, y0, y1, mat, mat2=None):
    prof = [(-0.3, 0), (0.3, 0), (0.22, 0.28), (0.09, 0.82), (-0.09, 0.82), (-0.22, 0.28)]
    n = max(1, int(abs(y1 - y0) / 3.0))
    L = (y1 - y0) / n
    for k in range(n):
        m = mat if (mat2 is None or k % 2 == 0) else mat2
        B.push(Matrix.Translation((x, 0, 0)))
        B.prism(prof, y0 + k * L + 0.03, y0 + (k + 1) * L - 0.03, m, axis="y")
        B.pop()


def pole(B, M, x, y, h, flag=None, fc="#d8382e", yaw=0.0):
    B.cyl((x, y, 0), (x, y, h), 0.05, 0.035, mat=M.c("#e8e6e0"), seg=6)
    if flag:
        B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
        B.quad([(0.04, 0, h - 0.1), (1.25, 0.1, h - 0.15), (1.2, 0.12, h - 0.85), (0.04, 0, h - 0.8)], flag, uvs=[(0, 1), (1, 1), (1, 0), (0, 0)])
        B.quad([(0.04, 0, h - 0.8), (1.2, 0.12, h - 0.85), (1.25, 0.1, h - 0.15), (0.04, 0, h - 0.1)], flag, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        B.pop()


def sign_board(B, M, x, y, yaw, texname, w=4.0, h=1.0, z=1.2, posts=True):
    m = M.t(texname, texname + ".png", (1, 1))
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    B.quad([(-w / 2, 0, z), (w / 2, 0, z), (w / 2, 0, z + h), (-w / 2, 0, z + h)], m, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    B.quad([(w / 2, 0.03, z), (-w / 2, 0.03, z), (-w / 2, 0.03, z + h), (w / 2, 0.03, z + h)], M.c("#8a8e96"), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    if posts:
        for sx in (-w / 2 + 0.15, w / 2 - 0.15):
            B.box((sx - 0.04, -0.04, 0), (sx + 0.04, 0.04, z + h), M.c("#5a5e66"))
    B.pop()


def bunting(B, M, p0, p1, sag=0.7, cols=("#d8382e", "#f2c230", "#2f62c8", "#ffffff", "#2f9a55"), n=None):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    n = n or max(4, int(L / 0.9))
    d = (p1 - p0).normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    pts = []
    for k in range(n + 1):
        t = k / n
        p = p0.lerp(p1, t); p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    B.tube(pts, 0.012, M.c("#3a3640"), seg=4, caps=False)
    for k in range(n):
        a, b = pts[k], pts[k + 1]
        m = (a + b) / 2
        B._face([B._v(a + side * 0.0), B._v(b), B._v(m + Vector((0, 0, -0.42)))], M.c(cols[k % len(cols)]))


def wheel(B, M, p, r=0.36, w=0.25, axis=(1, 0, 0)):
    a = Vector(axis)
    B.cyl(Vector(p) - a * w / 2, Vector(p) + a * w / 2, r, mat=M.c("#1c1a20"), seg=12, cap_mat=M.c("#a8aeb8"))


def box_trailer(B, M, x, y, yaw, bodymat, length=6.5, width=2.3, h=2.2):
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    B.box((-width / 2, -length / 2, 0.5), (width / 2, length / 2, 0.5 + h), bodymat)
    B.box((-width / 2 - 0.02, -length / 2, 0.45), (width / 2 + 0.02, length / 2, 0.55), M.c("#6a6e76"))
    B.cyl((0, -length / 2, 0.6), (0, -length / 2 - 1.6, 0.55), 0.05, mat=M.c("#3a3a40"), seg=6)
    for sy in (-0.6, 0.4):
        for sx in (-1, 1):
            wheel(B, M, (sx * (width / 2 + 0.02), sy, 0.4), 0.4, 0.28)
    B.pop()


def flatbed_with_car(B, M, x, y, yaw, lib, col, car, carcol):
    """tow truck bed trailer with a race car on top (the car is a Kenney model)"""
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    B.box((-1.25, -3.6, 0.55), (1.25, 3.6, 0.72), M.c("#2a2a30"))
    B.box((-1.3, -3.6, 0.72), (1.3, 3.6, 0.8), M.c("#9a6a3a"))
    for sy in (-0.2, 1.0):
        for sx in (-1, 1):
            wheel(B, M, (sx * 1.3, sy, 0.42), 0.42, 0.3)
    B.cyl((0, -3.6, 0.65), (0, -5.2, 0.55), 0.05, mat=M.c("#3a3a40"), seg=6)
    B.box((-1.25, 3.4, 0.8), (1.25, 3.6, 1.5), M.c(col))
    B.pop()
    yawc = yaw
    fit(lib, col_ink(), "racing-kit", car, (x, y, 0.8), yaw=yawc, length=4.6)


_COL = {}


def col_ink():
    return _COL["ink"]


def rv(B, M, x, y, yaw, texname, length=8.0, width=2.5, h=2.7):
    """motorhome: textured side walls, cab, wheels"""
    mt = M.t(texname, texname + ".png", (1, 1))
    cream = M.c("#efe8d8")
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    fs = B.box((-width / 2, -length / 2, 0.55), (width / 2, length / 2, 0.55 + h), cream, mats=dict(px=mt, nx=mt))
    side_uv(B, fs[3], [(0, 0), (1, 0), (1, 1), (0, 1)])
    side_uv(B, fs[5], [(1, 0), (0, 0), (0, 1), (1, 1)])
    # cab nose (front is -Y)
    B.box((-width / 2 + 0.05, -length / 2 - 1.8, 0.7), (width / 2 - 0.05, -length / 2 + 0.05, 2.0), cream)
    B.quad([(-width / 2 + 0.2, -length / 2 - 1.81, 1.3), (width / 2 - 0.2, -length / 2 - 1.81, 1.3), (width / 2 - 0.2, -length / 2 - 1.81, 1.9), (-width / 2 + 0.2, -length / 2 - 1.81, 1.9)], M.c("#34486a"))
    B.box((-width / 2, -length / 2 - 1.9, 0.5), (width / 2, -length / 2 - 1.7, 0.75), M.c("#8a8e96"))
    B.box((-0.5, -1.0, 0.55 + h), (0.5, 0.1, 0.55 + h + 0.28), M.c("#e6e6e0"))   # roof AC
    B.box((-width / 2, length / 2 - 0.05, 0.4), (width / 2, length / 2 + 0.1, 0.65), M.c("#8a8e96"))
    for sy in (-length / 2 + 0.2, length / 2 - 1.6):
        for sx in (-1, 1):
            wheel(B, M, (sx * (width / 2 + 0.02), sy, 0.5), 0.5, 0.3)
    B.pop()


def camper_trailer(B, M, x, y, yaw, mat_body, length=5.5):
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    B.box((-1.1, -length / 2, 0.5), (1.1, length / 2, 2.5), mat_body)
    B.box((-1.05, -length / 2, 2.5), (1.05, length / 2, 2.62), M.c("#f4f1e8"))
    B.box((-1.12, -0.7, 1.4), (1.12, 0.7, 2.1), M.c("#34486a"))
    B.cyl((0, -length / 2, 0.55), (0, -length / 2 - 1.4, 0.5), 0.05, mat=M.c("#3a3a40"), seg=6)
    for sx in (-1, 1):
        wheel(B, M, (sx * 1.15, 0.3, 0.38), 0.38, 0.22)
    B.pop()


def arch_roof_profile(w, h, n=10):
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((math.cos(a) * w / 2, math.sin(a) * h))
    return pts


def hangar(B, M, cx, cy, W, D, H, wallmat, doormat, roofmat, doorface=1):
    """W along Y, D along X; door wall faces +X"""
    x0, x1 = cx - D / 2, cx + D / 2
    y0, y1 = cy - W / 2, cy + W / 2
    fs = B.box((x0, y0, 0), (x1, y1, H), wallmat, mats=dict(px=doormat))
    side_uv(B, fs[3], [(0, 0), (2, 0), (2, 1), (0, 1)])  # px face: (y0,z0)(y1,z0)(y1,z1)(y0,z1)
    # barrel roof along Y: profile in (x, z) around cx
    prof = [(p[0] * D / 2 / (D / 2) + 0, p[1]) for p in arch_roof_profile(D, 4.5, 12)]
    B.push(Matrix.Translation((cx, 0, H)))
    B.prism(prof, y0 - 0.5, y1 + 0.5, roofmat, axis="y")
    B.pop()
    # door frame trims
    B.box((x1 + 0.02, y0, 0), (x1 + 0.35, y0 + 0.9, H + 0.6), M.c("#5c6068"))
    B.box((x1 + 0.02, y1 - 0.9, 0), (x1 + 0.35, y1, H + 0.6), M.c("#5c6068"))
    B.box((x1 + 0.02, y0, H - 0.4), (x1 + 0.35, y1, H + 0.6), M.c("#5c6068"))


def grandstand(B, M, cx, cy, L, tiers=6):
    """own bleachers (the Kenney grandstand imports as a flat untextured slab): stepped concrete, coloured seat strips,
    corrugated back wall and a red roof; faces -X (the track)"""
    conc = M.c("#c9c2b4"); wall = M.t("corr_wall2", "corr_wall2.png", (4, 4)); red = M.c("#d8382e"); wh = M.c("#f4f1e8")
    y0, y1 = cy - L / 2, cy + L / 2
    cols = ["#2f62c8", "#f2c230", "#d8382e", "#2f9a55", "#e8832a"]
    for k in range(tiers):
        xa, xb = cx + k * 1.1, cx + (k + 1) * 1.1
        h = 0.55 * (k + 1)
        B.box((xa, y0, 0), (xb, y1, h), conc)
        n = int(L / 2.0)
        for j in range(n):
            ya, yb = y0 + j * L / n, y0 + (j + 1) * L / n
            B.box((xa + 0.15, ya + 0.05, h), (xa + 0.65, yb - 0.05, h + 0.12), M.c(cols[(j + k) % 5]))
            B.box((xa + 0.15, ya + 0.05, h + 0.12), (xa + 0.25, yb - 0.05, h + 0.55), M.c(cols[(j + k) % 5]))
    xb = cx + tiers * 1.1
    B.box((xb, y0, 0), (xb + 0.3, y1, 6.3), wall)
    B.box((cx - 0.4, y0, 6.2), (xb + 0.6, y1, 6.5), red)
    B.box((cx - 0.5, y0, 6.0), (cx - 0.3, y1, 6.7), wh)
    for j in range(int(L / 6) + 1):
        yy = y0 + j * (L / max(1, int(L / 6)))
        B.box((cx - 0.3, yy - 0.1, 0), (cx - 0.1, yy + 0.1, 6.2), M.c("#3d4150"))
    B.box((cx - 0.3, y0, 0.9), (cx - 0.2, y1, 1.0), M.c("#3d4150"))


def tower(B, M, x, y):
    brick = M.t("bricks", "bricks.png", (3, 3))
    B.box((x - 6, y - 6, 0), (x + 6, y + 6, 5), brick)
    B.box((x - 6.4, y - 6.4, 5), (x + 6.4, y + 6.4, 5.5), M.c("#d8d2c0"))
    B.box((x - 2.2, y - 2.2, 5.5), (x + 2.2, y + 2.2, 17), M.c("#e9e4d4"))
    for k in range(4):
        B.box((x - 2.25, y - 2.25, 6.5 + k * 2.6), (x + 2.25, y + 2.25, 7.0 + k * 2.6), M.c("#c8372c" if k % 2 == 0 else "#f4f1e8"))
    B.box((x - 4.2, y - 4.2, 17), (x + 4.2, y + 4.2, 18.0), M.c("#4a4e58"))
    glass = M.t("tower_win", "tower_win.png", (1, 1))
    fs = B.box((x - 3.6, y - 3.6, 18), (x + 3.6, y + 3.6, 21), M.c("#e9e4d4"), mats=dict(px=glass, nx=glass, py=glass, ny=glass))
    for f in fs[2:]:
        side_uv(B, f, [(0, 0), (1, 0), (1, 1), (0, 1)])
    B.box((x - 4.4, y - 4.4, 21), (x + 4.4, y + 4.4, 21.6), M.c("#c8372c"))
    B.cyl((x, y, 21.6), (x, y, 27), 0.08, mat=M.c("#8a8e96"), seg=6)
    B.cyl((x + 1.5, y, 21.6), (x + 1.5, y, 24), 0.05, mat=M.c("#8a8e96"), seg=6)
    B.dome((x, y, 27), 0.35, M.c("#e0402c"), seg=8, rings=3)
    # radar dish
    B.cyl((x - 2.5, y, 21.6), (x - 2.5, y, 23), 0.06, mat=M.c("#8a8e96"), seg=6)
    B.cyl((x - 2.5, y, 23), (x - 2.5, y - 0.4, 23.0), 1.0, 0.05, mat=M.c("#d8d8d0"), seg=14)


def silo(B, M, x, y, r, h, body, cap):
    B.cyl((x, y, 0), (x, y, h), r, mat=M.c(body), seg=14)
    B.dome((x, y, h), r, M.c(cap), seg=14, rings=4, zscale=0.7)


def barn(B, M, x, y, yaw, W=16, D=11, H=7):
    red = M.t("corr_red", "corr_red.png", (4, 4))
    B.push(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z"))
    B.box((-W / 2, -D / 2, 0), (W / 2, D / 2, H), red)
    B.prism([(-W / 2 - 0.4, H), (W / 2 + 0.4, H), (W / 2 + 0.4, H), (0, H + 3.5)], -D / 2 - 0.5, D / 2 + 0.5, M.c("#e9e4d4"), axis="y") if False else None
    B.prism([(-D / 2 - 0.5, 0), (D / 2 + 0.5, 0), (0, 3.6)], -W / 2 - 0.3, W / 2 + 0.3, M.c("#efe9da"), axis="x")  # gable roof (profile in y,z along x)
    B.box((-1.8, -D / 2 - 0.02, 0), (1.8, -D / 2 + 0.03, 4.2), M.c("#f4f1e8"))
    B.pop()


# ================================================================ build
def ensure_textures():
    stamp = os.path.join(TEX, "version.txt")
    ok = os.path.exists(stamp) and open(stamp).read().strip() == str(TEX_VERSION) and os.path.exists(os.path.join(TEX, "tower_win.png"))
    if not ok:
        subprocess.run([PY, "-I", os.path.join(HERE, "gimli.py"), "--paint"], check=True)


def build(ctx):
    ensure_textures()
    try:
        bpy.context.preferences.system.anisotropic_filter = '16'
    except Exception:
        pass
    lib = ctx["lib"]
    ink, plain = ctx["ink"], ctx["plain"]
    _COL["ink"] = ink
    shot, light = ctx["shot"], ctx["light"]
    golden = light.startswith("golden")
    M = Mats(lib)
    rng = random.Random(1983)
    _S["cars"] = []
    ctx["M"] = M
    _ground(ctx, M, rng)
    _runway(ctx, M, rng)
    if shot == 12:   # the meadow shot only sees the meadow, the far hangar row and the runway edge
        _vegetation(ctx, M, rng)
        _far(ctx, M, rng)
        _meadow(ctx, M, rng)
        _hangars(ctx, M, rng)
    else:
        _paddock(ctx, M, rng)
        _camp(ctx, M, rng)
        _crash_dressing(ctx, M, rng)
        _foreground(ctx, M, rng)
        _track_gear(ctx, M, rng)
        _hangars(ctx, M, rng)
        _vegetation(ctx, M, rng)
        _far(ctx, M, rng)
    _sky(ctx, M, rng, golden)


def _ground(ctx, M, rng):
    plain = ctx["plain"]
    g = M.t("grass", "grass_prairie.png", (1, 1))
    B = Batch("ground")
    B.quad([(-4000, -4000, -0.15), (900, -4000, -0.15), (900, 4000, -0.15), (-4000, 4000, -0.15)], g,
           uvs=[(-500, -500), (112.5, -500), (112.5, 500), (-500, 500)])
    # lake Winnipeg to the east + beach
    w = M.t("water", "water_g.png" if ctx["light"].startswith("golden") else "water_d.png", (1, 1))
    B.quad([(940, -4000, -0.6), (6000, -4000, -0.6), (6000, 4000, -0.6), (940, 4000, -0.6)], w, uvs=[(0, 0), (170, 0), (170, 266), (0, 266)])
    sand = M.c("#e8cf8a")
    B.quad([(880, -4000, -0.3), (945, -4000, -0.3), (945, 4000, -0.3), (880, 4000, -0.3)], sand, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    B.quad([(900, -4000, -0.2), (900, 4000, -0.2), (880, 4000, -0.2), (880, -4000, -0.2)], M.c("#9ec45a"), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # crop fields around the base (rectangles, 40 m texture tiles)
    kinds = ["wheat", "canola", "flax", "pasture", "plowed", "hay", "barley"]
    fields = [(-620, -300, 380, 520), (-620, 330, 400, 520), (-950, -50, 260, 700), (-600, 900, 500, 400), (400, -600, 400, 420),
              (400, 560, 360, 520), (260, -1100, 500, 400), (-560, -900, 520, 400), (200, 1100, 500, 500), (-300, 1500, 520, 500), (480, 100, 300, 360)]
    for k, (cx, cy, w_, l_) in enumerate(fields):
        mt = M.t("field_" + kinds[k % 7], f"field_{kinds[k % 7]}.png", (1, 1))
        z = -0.1 + 0.005 * k
        B.quad([(cx - w_ / 2, cy - l_ / 2, z), (cx + w_ / 2, cy - l_ / 2, z), (cx + w_ / 2, cy + l_ / 2, z), (cx - w_ / 2, cy + l_ / 2, z)], mt,
               uvs=[(0, 0), (w_ / 40, 0), (w_ / 40, l_ / 40), (0, l_ / 40)] if k % 2 else [(0, 0), (0, w_ / 40), (l_ / 40, w_ / 40), (l_ / 40, 0)])
    o = B.build(plain, "ground")
    o.visible_shadow = False
    # horizon tree line ring (not toward the lake)
    tl = bpy.data.materials.get("gm_treeline")
    if tl is None:
        tl = M.cutout("treeline", "treeline.png", (1, 1), tint="#3f7a3a")
    B = Batch("treering")
    R, H, N = 2200, 46, 120
    for k in range(N):
        a0, a1 = 2 * math.pi * k / N, 2 * math.pi * (k + 1) / N
        am = (a0 + a1) / 2
        if abs(am) < 0.5 or abs(am - 2 * math.pi) < 0.5:  # east = lake
            continue
        P = lambda a, z: (math.cos(a) * R, math.sin(a) * R, z)
        u0, u1 = k * 0.0, 2 * math.pi * R / N / 500.0
        B.quad([P(a0, -0.3), P(a1, -0.3), P(a1, H), P(a0, H)], tl, uvs=[(k * u1, 0), ((k + 1) * u1, 0), ((k + 1) * u1, 1), (k * u1, 1)])
    o = B.build(plain, "treering")
    o.visible_shadow = False


def _seg_tex(M, name, idx):
    return M.t(f"rw{name}{idx}", f"rw_{name}{idx}.png", (1, 1))


def _runway(ctx, M, rng):
    ink, plain = ctx["ink"], ctx["plain"]
    B = Batch("runway")
    pl = [0, 1, 2]
    for k in range(50):
        y0 = -1500 + 60 * k
        if 1440 <= y0 + 0.1 < 1500:
            kind = ("thr", 4)
        elif 240 <= y0 < 300 or 480 <= y0 < 540:
            kind = ("td", 3)
        elif -240 <= y0 < -180:
            kind = ("dragstart", 6)
        elif -420 <= y0 < -60 or (-540 <= y0 < -420):
            kind = ("drag", 5)
        elif y0 == -1500:
            kind = ("thr", 4)
        else:
            kind = ("plain", rng.choice(pl))
        mt = _seg_tex(M, *kind)
        B.quad([(-30, y0, 0.0), (30, y0, 0.0), (30, y0 + 60, 0.0), (-30, y0 + 60, 0.0)], mt, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # shoulders both sides (old asphalt), 8 m wide
    sh = M.t("shoulder", "shoulder.png", (1, 1))
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 30, sx * 38))
        B.quad([(x0, -1500, -0.01), (x1, -1500, -0.01), (x1, 1500, -0.01), (x0, 1500, -0.01)], sh, uvs=[(0, 0), (8 / 6, 0), (8 / 6, 500), (0, 500)])
    # paddock pad (east) and hangar apron (west)
    pad = M.t("pad", "rw_plain1.png", (1, 1))
    for (xa, xb, ya, yb) in ((38, 150, -380, -150), (38, 100, -150, 330), (-250, -62, -290, 420)):
        B.quad([(xa, ya, -0.02), (xb, ya, -0.02), (xb, yb, -0.02), (xa, yb, -0.02)], pad,
               uvs=[(0, 0), ((xb - xa) / 60, 0), ((xb - xa) / 60, (yb - ya) / 60), (0, (yb - ya) / 60)])
    # taxi link at y=-60 .. connecting the hangar apron
    B.quad([(-62, -70, -0.02), (-30, -70, -0.02), (-30, -10, -0.02), (-62, -10, -0.02)], pad, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    o = B.build(plain, "runway")
    o.visible_shadow = False
    for m in o.data.materials:   # nearest sampling: with TAA it supersamples, so the markings stay crisp at grazing angles
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE":
                n.interpolation = "Closest"


def _kcar(ctx, name, loc, yaw, length=4.4, kit_="car-kit"):
    return fit(ctx["lib"], ctx["ink"], kit_, name, loc, yaw=yaw, length=length)


CARS = ["sedan", "sedan-sports", "hatchback-sports", "suv", "suv-luxury", "taxi", "van", "truck", "delivery", "station" ]


def _paddock(ctx, M, rng):
    ink, plain, lib = ctx["ink"], ctx["plain"], ctx["lib"]
    B = Batch("paddock")
    px, py = 55.0, -260.0
    # --- motorhomes & camper trailers, back rows (east)
    rvs = ["rv_a", "rv_b", "rv_c"]
    for k, (x, y, yaw) in enumerate([(118, -330, 1.57), (118, -308, 1.57 + 0.1), (121, -283, 1.45), (117, -258, 1.65), (120, -233, 1.55), (118, -208, 1.6),
                                     (122, -182, 1.5), (104, -350, 0.05), (84, -352, -0.1), (128, -300, 1.57)]):
        rv(B, M, x, y, yaw, rvs[k % 3], length=rng.uniform(6.5, 9.0))
    for k, (x, y, yaw) in enumerate([(98, -290, 1.3), (100, -240, 1.9), (95, -200, 1.6), (103, -320, 1.4)]):
        camper_trailer(B, M, x, y, yaw, M.c(["#f1eadb", "#e8d9a8", "#cfe0e8", "#e9c9b8"][k]))
    # --- box trailers + flatbeds with race cars
    for k, (x, y, yaw) in enumerate([(80, -218, 1.57), (80, -246, 1.6), (80, -274, 1.55), (80, -302, 1.58)]):
        box_trailer(B, M, x, y, yaw, M.c(["#f4f1e8", "#2f62c8", "#d8382e", "#f2c230"][k]))
    rc = ["raceCarRed", "raceCarOrange", "raceCarGreen", "raceCarWhite"]
    for k, (x, y, yaw) in enumerate([(64, -326, 1.57), (64, -340, 1.57)]):
        flatbed_with_car(B, M, x, y, yaw, lib, ["#2f62c8", "#d8382e"][k], rc[k], None)
    # tow trucks (car-kit truck-flat / tractor) pulling
    for k, (x, y, yaw) in enumerate([(80 + 0, -206, 1.57 + math.pi), (56, -315, 1.57 + math.pi + 0.05), (70, -170, 0.0)]):
        fit(lib, ink, "car-kit", ["truck-flat", "truck", "tractor-police"][k], (x, y, 0), yaw=yaw, length=6.0)
    # --- parked cars (kenney)
    spots = []
    for r_ in range(4):
        for c_ in range(7):
            spots.append((46 + r_ * 5.0 + rng.uniform(-0.6, 0.6), -190 - c_ * 11.5 + rng.uniform(-1, 1)))
    for k, (x, y) in enumerate(spots[::2]):
        nm = CARS[k % len(CARS)] if CARS[k % len(CARS)] != "station" else "sedan"
        fit(lib, ink, "car-kit", nm, (x, y, 0), yaw=(math.pi / 2 if k % 3 else -math.pi / 2) + rng.uniform(-0.12, 0.12), length=rng.uniform(4.0, 4.8))
    # emergency vehicles near the jet (shots 16-17) and along the runway edge
    fit(lib, ink, "car-kit", "firetruck", (23, -60, 0), yaw=0.5, length=8.0)
    fit(lib, ink, "car-kit", "ambulance", (27, -82, 0), yaw=2.4, length=5.6)
    fit(lib, ink, "car-kit", "police", (36, -118, 0), yaw=1.2, length=4.8)
    fit(lib, ink, "car-kit", "firetruck", (-36, -170, 0), yaw=-1.2, length=8.0)
    # --- tents, canopies, tables
    for k in range(18):
        x = rng.uniform(40, 76); y = rng.uniform(-330, -170)
        cs = [("#d8382e", "#ffffff"), ("#2f62c8", "#ffffff"), ("#f2c230", "#d8382e"), ("#2f9a55", "#ffffff"), ("#e8832a", "#ffffff"), ("#7a4cc0", "#f2efe6")][k % 6]
        canopy(B, M, x, y, rng.uniform(-0.3, 0.3), cs[0], cs[1], size=rng.choice([3.0, 3.0, 4.5]))
        table_chairs(B, M, x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), rng.uniform(0, 3), ["#d8382e", "#2f62c8", "#f2c230", "#2f9a55"])
    for k, (x, y, nm) in enumerate([(52, -225, "tent"), (47, -250, "tentLong"), (56, -300, "tentRoof"), (49, -330, "tent"), (60, -190, "tentLong")]):
        fit(lib, ink, "racing-kit", nm, (x, y, 0), yaw=1.57 + (k - 2) * 0.1, length=[5.0, 7.5, 6, 5, 7.5][k])
    for k in range(8):
        x, y = rng.uniform(42, 90), rng.uniform(-350, -160)
        fit(lib, ink, "nature-kit", ["tent_detailedOpen", "tent_smallOpen", "tent_detailedClosed", "tent_smallClosed"][k % 4], (x, y, 0), yaw=rng.uniform(0, 6.28), length=3.8,
            mat_all=None)
    # --- grandstands
    grandstand(B, M, 44, -150, 26)
    grandstand(B, M, 44, -358, 22)
    fit(lib, ink, "racing-kit", "pitsOffice", (44, -105, 0), yaw=3.14159, length=10)
    # --- signs, flags, banners
    sg = [("sign_raceday", 36.5, -255, 6.0), ("sign_snack", 60, -180, 4.5), ("sign_pits", 38, -300, 4.0), ("sign_club", 37, -225, 6.0),
          ("sign_dragstrip", 36.5, -190, 5.5), ("sign_spect", 36.5, -330, 4.5), ("sign_fuel", 70, -345, 3.0), ("sign_bingo", 90, -170, 5.0),
          ("sign_noparking", 36, -120, 3.0), ("sign_finish", 36.5, -415, 5.0)]
    for nm, x, y, w in sg:
        sign_board(B, M, x, y, -1.57 if x < 50 else 1.57 + 0.1, nm, w=w, h=w / 4.0 if w > 3.5 else 1.0, z=1.3)
    fl = [M.t("flagch", "sign_finish.png", (1, 1)), M.c("#d8382e"), M.c("#2f62c8"), M.c("#f2c230"), M.c("#2f9a55"), M.c("#ffffff")]
    for k in range(60):
        y = -430 + k * 7.5
        pole(B, M, 32.5, y, 6.0 + (k % 3) * 0.7, flag=fl[k % len(fl)], yaw=0.2 + 0.2 * math.sin(k))
    # bunting between pole pairs along the crowd edge and around the paddock
    for k in range(0, 56, 1):
        y = -430 + k * 7.5
        bunting(B, M, (32.5, y, 5.6 + (k % 3) * 0.7), (32.5, y + 7.5, 5.6 + ((k + 1) % 3) * 0.7), sag=0.9)
    for k in range(10):
        a = (48 + 3 * k, -165, 3.2); b = (48 + 3 * k + 3, -165, 3.2)
    for (p0, p1) in (((40, -170, 4.2), (110, -176, 4.2)), ((40, -340, 4.2), (110, -334, 4.2)), ((40, -170, 4.2), (40, -340, 4.2))):
        B.cyl((p0[0], p0[1], 0), p0, 0.07, mat=M.c("#e8e6e0"), seg=6); B.cyl((p1[0], p1[1], 0), p1, 0.07, mat=M.c("#e8e6e0"), seg=6)
        bunting(B, M, p0, p1, sag=2.0, n=30)
    # coolers, picnic bits, tyres
    for k in range(40):
        x, y = rng.uniform(40, 90), rng.uniform(-340, -170)
        c = rng.choice(["#e0402c", "#2f62c8", "#f2f0e8", "#2f9a55", "#f2c230"])
        B.obox((x, y, 0.2), (0.7, 0.4, 0.4), M.c(c), yaw=rng.uniform(0, 3))
        B.obox((x, y, 0.42), (0.72, 0.42, 0.06), M.c("#f2f0e8"), yaw=0)
    for k in range(34):
        lawn_chair(B, M, rng.uniform(40, 90), rng.uniform(-345, -165), rng.uniform(0, 6.28), rng.choice(["#d8382e", "#2f62c8", "#f2c230", "#2f9a55", "#e8832a", "#ffffff"]))
    # big banner arch over the paddock entrance
    for sy in (-198, -222):
        B.box((36.5 - 0.15, sy - 0.15, 0), (36.5 + 0.15, sy + 0.15, 7.2), M.c("#3d4150"))
    B.box((36.5 - 0.2, -222, 5.2), (36.5 + 0.2, -198, 7.0), M.t("arch", "sign_raceday.png", (1, 1)))
    o = B.build(ink, "paddock")
    # light posts (racing kit)
    for y in (-380, -300, -220, -140):
        fit(lib, ink, "racing-kit", "lightPostLarge", (35, y, 0), yaw=0, height=11)
    # cones and barrels along the paddock edge
    for k in range(30):
        fit(lib, ink, "car-kit", "cone", (34.8, -420 + k * 10, 0), height=0.7)
    # spectator road fence
    for k in range(40):
        fit(lib, ink, "racing-kit", "fenceStraight", (151, -380 + k * 6, 0), yaw=1.57, length=6.0) if k < 0 else None


def _track_gear(ctx, M, rng):
    ink, plain, lib = ctx["ink"], ctx["plain"], ctx["lib"]
    B = Batch("trackgear")
    steel = M.c("#c9ced6"); red = M.c("#d8382e"); wh = M.c("#f4f1e8"); blue = M.c("#2f62c8")
    # drag-strip guard rail down the centreline: W-beam on posts, red/white striped, low (the jet straddles it)
    n = 0
    y = -100.0
    while y > -420:
        y1 = y - 4.0
        B.box((-0.12, y1, 0.42), (0.12, y, 0.72), red if n % 2 == 0 else wh)
        B.box((-0.1, y1, 0.3), (0.1, y, 0.4), steel)
        B.box((-0.07, y - 2.05, 0), (0.07, y - 1.95, 0.45), M.c("#6a6e78"))
        n += 1
        y = y1
    # ends: sloped terminal
    for yy, d in ((-100.0, 1), (-420.0, -1)):
        B.prism([(-0.22, 0), (0.22, 0), (0.22, 0.75), (-0.22, 0.75)], yy, yy + d * 1.5, red, axis="y")
        for k in range(2):
            tyre_stack(B, M, -0.6 + k * 1.2, yy + d * 3.0, 3, white=True, r=0.5)
    # jersey barriers on both edges of the drag lanes (inside the crowd fence)
    for sx in (31.2,):
        jersey(B, M, sx, -430, -120, wh, blue)
    jersey(B, M, 31.2, -100, 80, wh, red)
    jersey(B, M, -31.2, -430, -100, wh, red)
    # tyre stacks: along the east edge, at lane starts, around the start line
    for k in range(26):
        tyre_stack(B, M, 29.4, -420 + k * 12.5, n=3 if k % 2 == 0 else 4, white=(k % 3 == 0))
    for k in range(10):
        tyre_stack(B, M, -29.3, -420 + k * 30, n=3, white=True)
    for k in range(6):
        x = 8 + k * 2.4
        tyre_stack(B, M, x, -214 + rng.uniform(-1, 1), n=2, white=True, r=0.4) if False else None
    # start-light tree on the east side of the lanes at the start line y=-221
    pxx, pyy = 19.2, -221.0
    B.box((pxx - 0.12, pyy - 0.12, 0), (pxx + 0.12, pyy + 0.12, 3.2), M.c("#3d4150"))
    B.box((pxx - 0.3, pyy - 0.12, 0.5), (pxx - 0.12, pyy + 0.12, 3.2), M.c("#e8e6e0"))
    for k, c in enumerate(["#f2c230", "#f2c230", "#f2c230", "#2f9a55", "#d8382e"]):
        B.box((pxx - 0.45, pyy - 0.2, 1.0 + k * 0.45), (pxx - 0.3, pyy + 0.2, 1.35 + k * 0.45), M.c("#16121e"))
        B.disc((pxx - 0.455, pyy, 1.175 + k * 0.45), (-1, 0, 0), 0.14, M.emit("lt" + c, c, 3.0), seg=12)
    # start / finish lines are painted; add a timing booth and a big finish arch at y = -430
    B.box((24, -433, 0), (27, -429, 3.0), M.c("#e9e4d4"))
    B.box((23.8, -433.2, 3.0), (27.2, -428.8, 3.3), red)
    # photographers' marshal posts
    for y in (-150, -250, -350):
        B.box((-34, y - 1, 0), (-32, y + 1, 2.4), M.c("#f4f1e8"))
        B.box((-34.2, y - 1.2, 2.4), (-31.8, y + 1.2, 2.7), blue)
    o = B.build(ink, "trackgear")
    # cones on the lanes
    for k in range(12):
        fit(lib, ink, "car-kit", "cone", (-1.6 if k % 2 else 1.6, -104 - k * 22, 0), height=0.7)
    # emergency crews around the stopped jet (kept off the cameras' centre lines)
    for nm, loc, yw, ln in (("firetruck", (-14, -50), -0.4, 8.0), ("ambulance", (-3, -64), 0.5, 5.6), ("police", (-27, -34), -0.9, 4.8),
                            ("firetruck", (-31, -92), 1.2, 8.0), ("ambulance", (-24, -112), 2.4, 5.6), ("police", (-38, -78), 0.3, 4.8),
                            ("tractor-shovel", (-20, 20), 0.8, 5.0)):
        fit(lib, ink, "car-kit", nm, (loc[0], loc[1], 0), yaw=yw, length=ln)
    # runway edge lights (blue) and the jet's rubber streaks from the touchdown to the stop
    B2 = Batch("rwylights")
    lit = M.emit("edgeblue", "#5ab0ff", 3.0)
    for yy in range(-480, 1500, 30):
        for sx in (-29.2, 29.2):
            B2.box((sx - 0.12, yy - 0.12, 0), (sx + 0.12, yy + 0.12, 0.3), M.c("#d8d8d0"))
            B2.box((sx - 0.1, yy - 0.1, 0.3), (sx + 0.1, yy + 0.1, 0.4), lit)
    B2.build(ink, "rwylights")
    B3 = Batch("rubber")
    rub = M.c("#1d1a22")
    for sx in (-5.4, -4.6, 4.6, 5.4):
        y0 = 262.0
        while y0 > -122:
            L = rng.uniform(14, 40)
            y1 = max(-122.0, y0 - L)
            w = 0.38
            B3.quad([(sx - w / 2, y0, 0.012), (sx + w / 2, y0, 0.012), (sx + w / 2, y1, 0.012), (sx - w / 2, y1, 0.012)], rub, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
            y0 = y1 - rng.uniform(0, 6)
    for k in range(6):  # heavy touchdown smear
        B3.quad([(-6.2 + k * 0.1, 266 - k * 2.0, 0.013), (-3.8 + k * 0.1, 266 - k * 2.0, 0.013), (-3.8, 255 - k * 2, 0.013), (-6.2, 255 - k * 2, 0.013)], rub, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        B3.quad([(6.2 - k * 0.1, 266 - k * 2.0, 0.013), (3.8 - k * 0.1, 266 - k * 2.0, 0.013), (3.8, 255 - k * 2, 0.013), (6.2, 255 - k * 2, 0.013)], rub, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    ob = B3.build(ctx["plain"], "rubber"); ob.visible_shadow = False
    # race cars: animated in shot 14 (lanes x = 4 + (i % 3) * 5 (+1.5 for i > 2)), driving toward -Y
    names = ["raceCarRed", "raceCarOrange", "raceCarGreen", "raceCarWhite", "raceCarRed"]
    paint = {"raceCarRed": {"red": "#e8141c", "grey": "#fff6e0"}, "raceCarOrange": {"pylon": "#ff7a00", "grey": "#20202c"},
             "raceCarGreen": {"grass": "#12b84c", "grey": "#ffe23a"}, "raceCarWhite": {"grey": "#2a6cf0"}}
    for nm in paint:  # fresh saturated templates (the flatbed cars imported earlier keep the stock colours)
        _kcache.pop(("racing-kit", nm), None); _dims.pop(("racing-kit", nm), None)
        kit_roots(lib, "racing-kit", nm, recolor=paint[nm])
    for i in range(5):
        lx = 4 + (i % 3) * 5 + (1.5 if i > 2 else 0)
        cs = fit(lib, ink, "racing-kit", names[i], (lx, -300, 0), yaw=_S.get("car_yaw", 0.0), length=5.4)
        _S["cars"].append((cs, lx, i))
    _S["car_roots"] = [c for c in _S["cars"]]


def _hangars(ctx, M, rng):
    ink, lib = ctx["ink"], ctx["lib"]
    hx = layout_hx(ctx)
    B = Batch("hangars")
    walls = [M.t("corr_wall", "corr_wall.png", (4, 4)), M.t("corr_wall2", "corr_wall2.png", (4, 4))]
    roof = M.t("corr_roof", "corr_roof.png", (4, 4))
    doors = [M.t("hangar_door", "hangar_door.png", (1, 1)), M.t("hangar_door2", "hangar_door2.png", (1, 1))]
    for k, (cy, W, D, H) in enumerate([(-215, 62, 46, 13), (-130, 54, 40, 11), (-52, 70, 48, 14), (36, 58, 42, 12), (120, 64, 46, 13), (205, 66, 46, 14), (292, 56, 40, 11), (380, 70, 48, 13)]):
        hangar(B, M, hx + rng.uniform(-6, 6), cy, W, D, H, walls[k % 2], doors[k % 2], roof)
    # sign numbers on gables
    sign_board(B, M, hx + 26, -184, 0.0, "sign_hangar2", w=3, h=3, z=9, posts=False)
    sign_board(B, M, hx + 24, -16, 1.57, "sign_rcaf", w=14, h=3.5, z=9, posts=False)
    tower(B, M, -105, 90)
    # a few old planes' remains / fuel tanks / sheds around
    for k in range(7):
        x, y = rng.uniform(-240, -80), rng.uniform(-280, 160)
        if abs(x - hx) < 40:
            continue
        B.box((x - 2, y - 1.5, 0), (x + 2, y + 1.5, 2.6), M.t("corr_wall2", "corr_wall2.png", (4, 4)))
        B.box((x - 2.2, y - 1.7, 2.6), (x + 2.2, y + 1.7, 2.9), M.c("#8a5a3a"))
    for k in range(12):
        x, y = rng.uniform(-240, -70), rng.uniform(-280, 170)
        fit(lib, ink, "city-kit-industrial", ["detail-tank", "detail-tank-large", "shipping-container-a", "shipping-container-b", "shipping-container-c"][k % 5], (x, y, 0),
            yaw=rng.uniform(0, 6.28), length=rng.uniform(5, 8) if k % 5 > 1 else None, height=3.5 if k % 5 < 2 else None)
    for k in range(10):
        tyre_stack(B, M, rng.uniform(-240, -70), rng.uniform(-260, 150), n=4)
    # barrels / drums near hangars
    o = B.build(ink, "hangars")
    # old light posts & fences along the hangar apron
    for k in range(20):
        fit(lib, ink, "racing-kit", "fenceStraight", (-62, -290 + k * 6.0, 0), yaw=1.57, length=6.0)


def layout_hx(ctx):
    return ctx["layout"].GIMLI["hangars_x"]


def _tree(ctx, nm, loc, h, yaw=0.0, plainc=False):
    return fit(ctx["lib"], ctx["plain"] if plainc else ctx["ink"], "nature-kit", nm, loc, yaw=yaw, height=h)


def _vegetation(ctx, M, rng):
    ink, plain, lib = ctx["ink"], ctx["plain"], ctx["lib"]
    # poplar windbreak rows
    rows = [(-100, -330, 1500), (-190, -300, 900), (150, -300, 900), (-60, 560, 1400), (330, -1000, 1500)]
    for (x, y0, y1) in rows[:3]:
        y = y0
        while y < y1:
            near = abs(y) < 700
            _tree(ctx, "tree_thin", (x + rng.uniform(-3, 3), y, 0), rng.uniform(13, 19), rng.uniform(0, 6.28), plainc=not near)
            y += rng.uniform(7, 11)
    # scattered prairie trees and bushes
    for k in range(60):
        x, y = rng.uniform(-420, 330), rng.uniform(-500, 800)
        if -45 < x < 45 or (35 < x < 160 and -440 < y < -90) or (-300 < x < -50 and -300 < y < 190):
            continue
        _tree(ctx, rng.choice(["tree_oak", "tree_default", "tree_detailed", "tree_fat"]), (x, y, 0), rng.uniform(7, 12), rng.uniform(0, 6.28), plainc=abs(y) > 600)
    for k in range(70):
        x = rng.choice([-1, 1]) * rng.uniform(40, 120); y = rng.uniform(-450, 400)
        if 35 < x < 160 and -440 < y < -90:
            continue
        fit(lib, plain, "nature-kit", rng.choice(["plant_bushLarge", "plant_bush", "plant_bushDetailed"]), (x, y, 0), yaw=rng.uniform(0, 6.28), height=rng.uniform(1.0, 1.8))
    # runway edge weeds / tall grass and wildflowers (instances)
    fl = ["flower_yellowA", "flower_yellowB", "flower_purpleA", "flower_purpleB", "flower_redA", "flower_redC", "flower_yellowC", "flower_purpleC"]
    for k in range(520 if ctx["shot"] != 11 else 160):
        sx = rng.choice([-1, 1])
        x = sx * rng.uniform(31, 70)
        y = rng.uniform(-500, 420)
        if 35 < x < 160 and -380 < y < -150 and rng.random() < 0.9:
            continue
        if rng.random() < 0.5:
            fit(lib, plain, "nature-kit", rng.choice(["grass_large", "grass_leafsLarge", "grass"]), (x, y, 0), yaw=rng.uniform(0, 6.28), height=rng.uniform(0.5, 1.0))
        else:
            fit(lib, plain, "nature-kit", rng.choice(fl), (x, y, 0), yaw=rng.uniform(0, 6.28), height=rng.uniform(0.45, 0.8))
    # tufts through the runway cracks near the tracks (near-camera detail)
    for k in range(80):
        y = rng.uniform(-440, 60); x = rng.choice([-1, 1]) * rng.uniform(22, 29.3)
        fit(lib, plain, "nature-kit", rng.choice(["grass", "grass_large", "flower_yellowA"]), (x, y, 0), yaw=rng.uniform(0, 6.28), height=rng.uniform(0.3, 0.7))
    # power line along x = 175 (east of the paddock)
    px = 175.0
    pts = []
    B = Batch("powerline")
    wood = M.c("#6a4a32")
    for k in range(-14, 17):
        y = k * 60.0
        B.cyl((px, y, 0), (px, y, 11), 0.2, 0.15, mat=wood, seg=6)
        B.box((px - 1.6, y - 0.1, 10.3), (px + 1.6, y + 0.1, 10.5), wood)
        pts.append(y)
    for a, b in zip(pts, pts[1:]):
        for dx in (-1.5, 0.0, 1.5):
            ptsw = []
            for i in range(9):
                t = i / 8
                ptsw.append((px + dx, a + (b - a) * t, 10.4 - 1.3 * 4 * t * (1 - t)))
            B.tube(ptsw, 0.04, M.c("#2a2830"), seg=4, caps=False)
    B.build(plain, "powerline")


def _far(ctx, M, rng):
    ink, plain, lib = ctx["ink"], ctx["plain"], ctx["lib"]
    B = Batch("farm")
    # farmstead west-south-west and one north-east
    for (fx, fy, yaw) in ((-640, -320, 0.3), (420, 760, -0.4), (-700, 700, 1.0)):
        barn(B, M, fx, fy, yaw)
        silo(B, M, fx + 18, fy + 6, 3.2, 17, "#cfd5da", "#8a96a2")
        silo(B, M, fx + 25, fy - 2, 3.2, 17, "#cfd5da", "#8a96a2")
        silo(B, M, fx + 21, fy + 14, 2.4, 12, "#bfc8cc", "#a35a3a")
        B.box((fx - 35, fy - 6, 0), (fx - 25, fy + 4, 4.5), M.c("#efe3c4"))
        B.prism([(-5.4, 0), (5.4, 0), (0, 2.8)], fx - 35.4, fx - 24.6, M.c("#b0433a"), axis="x") if False else None
        B.box((fx - 35.5, fy - 6.5, 4.5), (fx - 24.5, fy + 4.5, 5.3), M.c("#b0433a"))
        for k in range(14):
            a = k * 0.45
            _tree(ctx, "tree_default", (fx - 10 + math.cos(a) * 50, fy + math.sin(a) * 40, 0), rng.uniform(8, 12), plainc=True)
    B.build(plain, "farm")
    # round hay bales on the near field east of the runway and hills
    for k in range(10):
        x, y = rng.uniform(-420, -330), rng.uniform(250, 500)
        B2 = None
    # grain elevator / water tower far north
    fit(lib, plain, "city-kit-industrial", "water-tower", (60, 1250, 0), height=22) if False else None


def _meadow(ctx, M, rng):
    """shot 12 field (-150, 460): meadow patch, rolling hill line, fence, trees, flowers, rocks"""
    ink, plain, lib = ctx["ink"], ctx["plain"], ctx["lib"]
    fx, fy, _ = ctx["layout"].GIMLI["field"]
    mg = M.t("meadow", "grass_meadow.png", (1, 1))
    me = bpy.data.meshes.new("meadow")
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    nx, ny = 36, 30
    x0, x1, y0, y1 = fx - 260, fx + 100, fy - 60, fy + 360

    def hgt(x, y):
        h = 0.0
        u = (y - (fy + 40)) / 200.0
        if u > 0:
            h += 9.0 * math.sin(min(u, 1.0) * math.pi / 2) * (1 - 0.5 * max(0, u - 1))
        h += 1.4 * math.sin(x * 0.03 + 1) * math.sin(y * 0.021) * min(1, max(0, (y - fy + 30) / 100))
        return h
    vs = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            vs[(i, j)] = bm.verts.new((x, y, 0.03 + max(0, hgt(x, y))))
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new([vs[(i, j)], vs[(i + 1, j)], vs[(i + 1, j + 1)], vs[(i, j + 1)]])
            f.material_index = 0; f.smooth = True
            for l in f.loops:
                l[uvl].uv = (l.vert.co.x / 6.0, l.vert.co.y / 6.0)
    bm.to_mesh(me); bm.free()
    me.materials.append(mg)
    o = bpy.data.objects.new("meadow", me); plain.objects.link(o); o.visible_shadow = False
    # hill-top trees and a shelter belt on the ridge
    for k in range(26):
        x = fx - 250 + k * 12 + rng.uniform(-5, 5); y = fy + 150 + rng.uniform(-20, 40)
        _tree(ctx, rng.choice(["tree_oak", "tree_default", "tree_detailed", "tree_fat"]), (x, y, hgt(x, y)), rng.uniform(7, 11), rng.uniform(0, 6.28))
    # fence: zig-zag of Kenney fence pieces across the meadow, plus a gate
    for k in range(22):
        x = fx - 70 + k * 4.0
        fit(lib, ink, "nature-kit", "fence_simple", (x, fy + 12.0, 0), yaw=0.0, length=4.0)
    for k in range(14):
        fit(lib, ink, "nature-kit", "fence_simple", (fx - 70, fy + 12 - k * 4.0, 0), yaw=1.5708, length=4.0)
    fit(lib, ink, "nature-kit", "fence_gate", (fx - 130, fy + 12, 0), length=4.0) if False else None
    # trees around: left cluster and right line, some close to the camera
    for (dx, dy, h) in ((-26, 16, 10), (-34, 30, 12), (-18, 40, 9), (30, 20, 11), (42, 38, 13), (22, 55, 9), (-48, 8, 8), (55, 8, 10), (-62, 52, 12), (68, 60, 10)):
        _tree(ctx, rng.choice(["tree_oak", "tree_default", "tree_detailed", "tree_fat", "tree_tall"]), (fx + dx, fy + dy, hgt(fx + dx, fy + dy)), h, rng.uniform(0, 6.28))
    # near-field dressing: flowers, tall grass, rocks, bushes
    fl = ["flower_yellowA", "flower_yellowB", "flower_purpleA", "flower_purpleB", "flower_redA", "flower_redB", "flower_yellowC", "flower_purpleC", "flower_redC"]
    for k in range(480):
        dx = rng.gauss(0, 17); dy = rng.uniform(-12, 70)
        x, y = fx + dx, fy + dy
        if abs(dx) < 1.0 and -6 < dy < 6:
            continue
        r = rng.random()
        z = max(0, hgt(x, y))
        if r < 0.5:
            fit(lib, plain, "nature-kit", rng.choice(fl), (x, y, z), yaw=rng.uniform(0, 6.28), height=rng.uniform(0.5, 1.0))
        elif r < 0.9:
            fit(lib, plain, "nature-kit", rng.choice(["grass_large", "grass_leafsLarge", "grass_leafs"]), (x, y, z), yaw=rng.uniform(0, 6.28), height=rng.uniform(0.6, 1.3))
        else:
            fit(lib, plain, "nature-kit", rng.choice(["plant_bushLarge", "plant_bush", "plant_flatTall"]), (x, y, z), yaw=rng.uniform(0, 6.28), height=rng.uniform(0.9, 1.6))
    for k in range(26):
        dx = rng.gauss(0, 14); dy = rng.uniform(-8, 60)
        fit(lib, ink, "nature-kit", rng.choice(["rock_largeA", "rock_largeB", "rock_smallC", "rock_smallA", "stone_largeA", "rock_tallA"]),
            (fx + dx, fy + dy, 0), yaw=rng.uniform(0, 6.28), length=rng.uniform(0.5, 1.5))
    fit(lib, ink, "nature-kit", "stump_roundDetailed", (fx + 4, fy + 4.5, 0), height=0.6)
    fit(lib, ink, "nature-kit", "log_large", (fx - 6, fy + 9, 0), yaw=0.4, length=3.2)
    # field-edge road / grain truck + old windbreak so the meadow is not alone
    fit(lib, ink, "car-kit", "tractor", (fx + 52, fy + 64, hgt(fx + 52, fy + 64)), yaw=2.4, length=4.4)


def _sky(ctx, M, rng, golden):
    plain = ctx["plain"]
    n = 0
    for k in range(18):
        az = rng.uniform(0, math.tau)
        dist = rng.uniform(1500, 3200)
        el = math.radians(rng.uniform(3, 17))
        c = Vector((math.cos(az) * dist, math.sin(az) * dist, math.tan(el) * dist))
        w = rng.uniform(380, 800) * dist / 2000
        mat = M.card(f"cloud{'g' if golden else 'd'}{k % 4}", f"cloud_{'g' if golden else 'd'}{k % 4}.png")
        B = Batch("cloud")
        nrm = Vector((-math.cos(az), -math.sin(az), 0))
        t = Vector((-nrm.y, nrm.x, 0))
        B.quad([c - t * w / 2 - Vector((0, 0, w / 4)), c + t * w / 2 - Vector((0, 0, w / 4)), c + t * w / 2 + Vector((0, 0, w / 4)), c - t * w / 2 + Vector((0, 0, w / 4))],
               mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        o = B.build(plain, f"cloud{k}")
        o.visible_shadow = False
    # sun glow card
    sun = bpy.data.objects.get("Sun")
    if sun is not None:
        d = (sun.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        c = d * 3500
        r = 520 if golden else 380
        nrm = -d
        t = Vector((-nrm.y, nrm.x, 0)).normalized()
        u = nrm.cross(t).normalized()
        B = Batch("sunglow")
        B.quad([c - t * r - u * r, c + t * r - u * r, c + t * r + u * r, c - t * r + u * r], M.card("sunglow", "sun.png", mult=1.0), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        o = B.build(plain, "sunglow"); o.visible_shadow = False


# ================================================================ animate
def animate(ctx, layer, info):
    if not _S.get("_init"):
        _S["_init"] = True
        _ink_width_setup()
    k = _S.get("ink_k")
    if k is not None:
        k.outputs[0].default_value = math.tan(math.radians(layer["cam"]["fov"]) / 2) / 1920.0
    f, shot = info["f"], ctx["shot"]
    for cars, lx, i in _S.get("cars", []):
        y = -300.0 - (f - 1318 - 11 * i)
        vis = shot == 14 and -460 < y < 140
        for c in cars:
            c.hide_render = not vis
            c.hide_viewport = not vis
        if vis:
            _move_car(cars, y)


def _move_car(cars, y):
    base = _S.setdefault("car_base", {})
    for c in cars:
        if c.name not in base:
            base[c.name] = c.location.y + 300.0
        c.location.y = base[c.name] + y


def _camp(ctx, M, rng):
    """spectator camp along the east edge of the runway (y -100 .. +700) and ad boards on the west edge"""
    ink, lib = ctx["ink"], ctx["lib"]
    B = Batch("camp")
    cs = [("#d8382e", "#ffffff"), ("#2f62c8", "#ffffff"), ("#f2c230", "#d8382e"), ("#2f9a55", "#ffffff"), ("#e8832a", "#ffffff"), ("#7a4cc0", "#f2efe6")]
    y = -92.0
    k = 0
    while y < 720:
        r = rng.random()
        x = rng.uniform(42, 80)
        if any((x - cx) ** 2 + (y - cy) ** 2 < 26 ** 2 for cx, cy in ((46, 120), (44, 318), (23, -280))):
            y += 12
            continue
        if r < 0.38:
            c = cs[k % 6]
            canopy(B, M, x, y, rng.uniform(-0.3, 0.3), c[0], c[1], size=rng.choice([3.0, 4.5]))
            table_chairs(B, M, x + 0.2, y, rng.uniform(0, 3), ["#d8382e", "#2f62c8", "#f2c230", "#2f9a55"])
        elif r < 0.7:
            nm = rng.choice(["sedan", "sedan-sports", "hatchback-sports", "suv", "suv-luxury", "taxi", "van", "truck", "delivery"])
            fit(lib, ink, "car-kit", nm, (x, y, 0), yaw=rng.choice([1.57, -1.57]) + rng.uniform(-0.15, 0.15), length=rng.uniform(4.0, 4.8))
            if rng.random() < 0.6:
                lawn_chair(B, M, x - 2.4, y + rng.uniform(-1, 1), rng.uniform(0, 6), rng.choice(["#d8382e", "#2f62c8", "#f2c230", "#2f9a55"]))
        elif r < 0.85:
            rv(B, M, x + 12, y, 1.57 + rng.uniform(-0.1, 0.1), ["rv_a", "rv_b", "rv_c"][k % 3], length=rng.uniform(6.5, 9.0))
        else:
            fit(lib, ink, "racing-kit", rng.choice(["tent", "tentLong", "tentRoof"]), (x, y, 0), yaw=1.57, length=6.0)
        if k % 3 == 0:
            pole(B, M, 33.5, y, 6.5, flag=M.c(["#d8382e", "#2f62c8", "#f2c230", "#2f9a55"][k % 4]), yaw=0.3)
        y += rng.uniform(9, 17)
        k += 1
    jersey(B, M, 31.2, 80, 560, M.c("#f4f1e8"), M.c("#2f62c8"))
    for kk in range(30):
        tyre_stack(B, M, 29.4, 80 + kk * 16, n=3, white=(kk % 3 == 0))
    # ad boards on the west edge facing the track, with bunting (seen across the lanes in shots 14-17)
    names = ["sign_raceday", "sign_club", "sign_snack", "sign_dragstrip", "sign_spect", "sign_pits", "sign_fuel", "sign_bingo"]
    for i in range(16):
        yy = -420 + i * 38
        sign_board(B, M, -35.5, yy, 1.57, names[i % 8], w=7.0, h=1.9, z=1.1)
    for i in range(15):
        bunting(B, M, (-36.5, -420 + i * 38, 3.6), (-36.5, -420 + (i + 1) * 38, 3.6), sag=1.6, n=30)
    for i in range(16):
        B.cyl((-36.5, -420 + i * 38, 0), (-36.5, -420 + i * 38, 3.6), 0.08, mat=M.c("#e8e6e0"), seg=6)
    B.build(ink, "camp")


def _foreground(ctx, M, rng):
    """near-camera clutter at the frame edges of shot 14 (camera path ~ (25,-282) -> (20,-314), looking -X/+Y)"""
    ink, plain, lib = ctx["ink"], ctx["plain"], ctx["lib"]
    r2 = random.Random(77)
    B = Batch("fgclutter")
    cams = [((25.0, -282.0), (-0.6176, 0.786)), ((22.3, -278.5), (-0.6176, 0.786)), ((20.8, -298.0), (-0.68, 0.73)), ((20.0, -314.0), (-0.7433, 0.669))]
    cones = []; tufts = []
    n = 0
    for (cx, cy), (dx, dy) in cams:
        rx, ry = dy, -dx
        for d in (5.5, 7.5, 10.0, 13.0, 17.0):
            for side in (-1, 1):
                off = side * d * r2.uniform(0.13, 0.2)
                x = cx + dx * d + rx * off; y = cy + dy * d + ry * off
                if x < 17.4 or x > 30:
                    continue
                kind = n % 5; n += 1
                if kind in (0, 3):
                    tyre_stack(B, M, x, y, n=2 + n % 3, white=(n % 2 == 0), r=0.5)
                elif kind == 1:
                    cl = r2.choice(["#e0402c", "#2f62c8", "#f2f0e8", "#2f9a55"])
                    B.obox((x, y, 0.27), (0.5, 0.32, 0.27), M.c(cl), yaw=r2.uniform(0, 3))
                    B.obox((x, y, 0.56), (0.52, 0.34, 0.05), M.c("#f2f0e8"), yaw=0)
                elif kind == 2:
                    cones.append((x, y))
                else:
                    pts = [(x + 1.3 * math.sin(i * 0.8), y - i * 1.4, 0.07 + 0.02 * (i % 2)) for i in range(8)]
                    B.tube(pts, 0.06, M.c(["#e8c030", "#d8382e", "#16121e"][n % 3]), seg=6)
                for q in range(3):
                    tufts.append((x + r2.uniform(-1.8, 1.8), y + r2.uniform(-1.8, 1.8)))
    B.build(ink, "fgclutter")
    for (x, y) in cones:
        fit(lib, ink, "car-kit", "cone", (x, y, 0), height=0.8, yaw=r2.uniform(0, 6))
    for (x, y) in tufts:
        if x < 17.4 or x > 30:
            continue
        fit(lib, plain, "nature-kit", r2.choice(["grass_large", "grass_leafsLarge", "grass", "flower_yellowA", "flower_redA"]), (x, y, 0), yaw=r2.uniform(0, 6.28), height=r2.uniform(0.4, 0.9))


def _crash_dressing(ctx, M, rng):
    """debris, cones, foam and hoses on the drag strip around where the jet stops (y -60 .. -200)"""
    ink, lib = ctx["ink"], ctx["lib"]
    B = Batch("debris")
    foam = M.c("#f4f1ea"); dark = M.c("#26232b"); metal = M.c("#c9ced6"); orange = M.c("#e8832a")
    for k in range(0):  # (panels removed: flat boards read as untextured placeholders)
        x, y = rng.uniform(-18, 18), rng.uniform(-200, -60)
        if abs(x) < 1.0:
            continue
        B.obox((x, y, 0.06), (rng.uniform(0.25, 0.7), rng.uniform(0.25, 0.6), 0.04), [dark, M.c("#d8382e"), M.c("#e8832a")][k % 3], yaw=rng.uniform(0, 3.14), pitch=rng.uniform(-0.2, 0.2))
    for k in range(8):
        x, y = rng.uniform(-12, 12), rng.uniform(-170, -80)
        B.cyl((x, y, 0.0), (x, y, 0.22), 0.45, mat=dark, seg=10)
    for k in range(2):  # fire hoses
        x0, y0 = rng.uniform(-24, -10), rng.uniform(-130, -60)
        pts = [(x0 + i * 2.5, y0 - i * 1.5 + math.sin(i * 1.2 + k) * 1.2, 0.08) for i in range(5)]
        B.tube(pts, 0.07, M.c("#c8402a"), seg=6)
    B.build(ink, "debris")
    for k in range(34):
        fit(lib, ink, "car-kit", "cone", (rng.uniform(-22, 22), rng.uniform(-205, -50), 0), height=0.72, yaw=rng.uniform(0, 6))
    for k in range(6):
        fit(lib, ink, "racing-kit", rng.choice(["barrierRed", "barrierWhite"]), (rng.choice([-1, 1]) * rng.uniform(8, 20), rng.uniform(-190, -60), 0), yaw=rng.uniform(1.2, 1.9), length=3.2)
