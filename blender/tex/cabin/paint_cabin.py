# Paints the cabin set's stylised textures (shot 7) with Pillow. Output: PNGs next to this file.
#   python -I D:\gimli3d\blender\tex\cabin\paint_cabin.py
# Everything is drawn at 2x and downsampled (clean anti-aliased cartoon shapes). Colours: early-80s airline cabin
# (navy patterned seats, red-orange headrest covers, maroon carpet with a gold lattice, cream panels).
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_B = r"C:\Windows\Fonts\arialbd.ttf"
FONT_N = r"C:\Windows\Fonts\ARIALNB.TTF"


def hx(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def canvas(w, h, col, ss=2):
    im = Image.new("RGBA", (w * ss, h * ss), hx(col) if isinstance(col, str) else col)
    return im, ImageDraw.Draw(im), ss


def save(im, name, w, h):
    im.resize((w, h), Image.LANCZOS).convert("RGB").save(os.path.join(HERE, name))
    print("wrote", name)


# ------------------------------------------------------------------ seat fabric (tile = 0.25 m)
def seat_fabric():
    W = 256
    im, d, s = canvas(W, W, "#24407c")
    S = W * s
    # horizontal weave bands
    for y in range(0, S, 8 * s):
        d.rectangle([0, y, S, y + 2 * s], fill=hx("#1d3569"))
    # a lattice of stepped diamonds (rust) with mustard centres, thin sky-blue pinstripes between
    n = 4
    step = S // n
    for i in range(n + 1):
        for j in range(n + 1):
            cx, cy = i * step + (step // 2 if j % 2 else 0), j * step
            r = int(step * 0.30)
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=hx("#c8552a"))
            r2 = int(step * 0.15)
            d.polygon([(cx, cy - r2), (cx + r2, cy), (cx, cy + r2), (cx - r2, cy)], fill=hx("#e8ad3c"))
            r3 = int(step * 0.05)
            d.rectangle([cx - r3, cy - r3, cx + r3, cy + r3], fill=hx("#24407c"))
    for j in range(n):
        y = j * step + step // 2
        d.line([(0, y), (S, y)], fill=hx("#6f97d6"), width=3 * s)
    im = im.filter(ImageFilter.GaussianBlur(0.6 * s))
    save(im, "seat_fabric.png", W, W)


# ------------------------------------------------------------------ headrest cover (whole cover = 1 tile)
def headrest():
    W, H = 256, 128
    im, d, s = canvas(W, H, "#d24a2c")
    S, T = W * s, H * s
    for y in range(0, T, 6 * s):
        d.line([(0, y), (S, y)], fill=hx("#c3401f"), width=s)
    d.rectangle([0, int(T * 0.70), S, int(T * 0.78)], fill=hx("#f1e3c8"))
    d.rectangle([0, int(T * 0.83), S, int(T * 0.86)], fill=hx("#f1e3c8"))
    save(im, "headrest.png", W, H)


# ------------------------------------------------------------------ aisle carpet runner (tile 0.6 m x 0.6 m)
def carpet_aisle():
    W = 512
    im, d, s = canvas(W, W, "#7a1c2c")
    S = W * s
    rnd = random.Random(3)
    for _ in range(9000):  # pile speckle
        x, y = rnd.randrange(S), rnd.randrange(S)
        d.rectangle([x, y, x + s, y + s], fill=hx(rnd.choice(["#6a1626", "#86243a", "#701a2b"])))
    # borders
    b = int(S * 0.07)
    d.rectangle([0, 0, b, S], fill=hx("#4a1020")); d.rectangle([S - b, 0, S, S], fill=hx("#4a1020"))
    d.rectangle([b, 0, b + 4 * s, S], fill=hx("#e2a83e")); d.rectangle([S - b - 4 * s, 0, S - b, S], fill=hx("#e2a83e"))
    # diamond lattice with gold outlines and orange cores (like an 80s casino/airline carpet)
    n = 3
    cw = (S - 2 * b) / n
    for i in range(n):
        for j in range(n * 1 + 1):
            cx = b + cw * (i + 0.5)
            cy = cw * j
            r = cw * 0.42
            pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
            d.polygon(pts, outline=hx("#e2a83e"), width=4 * s)
            r2 = r * 0.42
            d.polygon([(cx, cy - r2), (cx + r2, cy), (cx, cy + r2), (cx - r2, cy)], fill=hx("#e0682e"))
            d.ellipse([cx - 4 * s, cy - 4 * s, cx + 4 * s, cy + 4 * s], fill=hx("#f2d27a"))
            # small dots between diamonds
            for ox, oy in ((0.5, 0.5),):
                px_, py_ = cx + cw * ox, cy + cw * oy
                if px_ < S - b:
                    d.ellipse([px_ - 3 * s, py_ - 3 * s, px_ + 3 * s, py_ + 3 * s], fill=hx("#e2a83e"))
    save(im, "carpet_aisle.png", W, W)


# ------------------------------------------------------------------ floor carpet under the seats (tile 1 m)
def carpet_floor():
    W = 256
    im, d, s = canvas(W, W, "#3b2440")
    S = W * s
    rnd = random.Random(5)
    for _ in range(4000):
        x, y = rnd.randrange(S), rnd.randrange(S)
        d.rectangle([x, y, x + s, y + s], fill=hx(rnd.choice(["#33203a", "#472c4c", "#3e2643"])))
    for i in range(8):
        for j in range(8):
            cx, cy = (i + 0.5 + (0.5 if j % 2 else 0)) * S / 8, (j + 0.5) * S / 8
            d.ellipse([cx - 3 * s, cy - 3 * s, cx + 3 * s, cy + 3 * s], fill=hx("#7a4a5c"))
    save(im, "carpet_floor.png", W, W)


# ------------------------------------------------------------------ sidewall panel (tile 1.02 m x 1.02 m, 2 window bays)
def wall():
    W = 512
    im, d, s = canvas(W, W, "#ebe3d1")
    S = W * s
    rnd = random.Random(7)
    for _ in range(3000):
        x, y = rnd.randrange(S), rnd.randrange(S)
        d.rectangle([x, y, x + s, y + s], fill=hx(rnd.choice(["#e4dbc8", "#efe8d8"])))
    # panel seams at the bay boundaries (u = 0, 0.5) and a pinstripe at the sill height
    for u in (0.0, 0.5):
        x = int(u * S)
        d.rectangle([x - 2 * s, 0, x + 2 * s, S], fill=hx("#b9ad96"))
        d.rectangle([x + 2 * s, 0, x + 3 * s, S], fill=hx("#f7f2e6"))
    save(im, "wall.png", W, W)


# ------------------------------------------------------------------ lower sidewall (80s ribbed fabric, tile 0.5 m)
def dado():
    W = 256
    im, d, s = canvas(W, W, "#8c4f30")
    S = W * s
    for x in range(0, S, 10 * s):
        d.rectangle([x, 0, x + 3 * s, S], fill=hx("#7a432a"))
        d.rectangle([x + 5 * s, 0, x + 6 * s, S], fill=hx("#a0603c"))
    save(im, "dado.png", W, W)


# ------------------------------------------------------------------ bin door (one door = one tile: u along the cabin, v up the door)
def bin_door():
    W, H = 512, 256
    im, d, s = canvas(W, H, "#eee6d4")
    S, T = W * s, H * s
    # painted gradient: lighter toward the bottom lip
    for y in range(T):
        t = y / T
        d.line([(0, y), (S, y)], fill=mix(hx("#f3ecdc"), hx("#ddd2bc"), t))
    # accent stripe (rust + mustard) a third of the way up
    d.rectangle([0, int(T * 0.30), S, int(T * 0.36)], fill=hx("#c8552a"))
    d.rectangle([0, int(T * 0.38), S, int(T * 0.40)], fill=hx("#e2a83e"))
    # door edges (dark seam lines)
    d.rectangle([0, 0, 3 * s, T], fill=hx("#8f846f")); d.rectangle([S - 3 * s, 0, S, T], fill=hx("#8f846f"))
    save(im, "bin_door.png", W, H)


# ------------------------------------------------------------------ PSU strip under the bins (one row = 0.86 m = one tile in u)
def psu():
    W, H = 512, 128
    im, d, s = canvas(W, H, "#cfc6b0")
    S, T = W * s, H * s
    d.rectangle([0, 0, S, 5 * s], fill=hx("#9c917a")); d.rectangle([0, T - 5 * s, S, T], fill=hx("#9c917a"))
    # 3 reading lights + 3 gaspers + call buttons for a seat block, then a speaker grille
    for k in range(3):
        cx = int(S * (0.12 + k * 0.13)); cy = int(T * 0.36)
        d.ellipse([cx - 13 * s, cy - 13 * s, cx + 13 * s, cy + 13 * s], fill=hx("#6b6352"))
        d.ellipse([cx - 10 * s, cy - 10 * s, cx + 10 * s, cy + 10 * s], fill=hx("#efe3c2"))
        gy = int(T * 0.72)
        d.ellipse([cx - 9 * s, gy - 9 * s, cx + 9 * s, gy + 9 * s], fill=hx("#3c3a40"))
        d.ellipse([cx - 4 * s, gy - 4 * s, cx + 4 * s, gy + 4 * s], fill=hx("#9fa3ad"))
    for k in range(3):
        cx = int(S * (0.56 + k * 0.05)); cy = int(T * 0.5)
        d.rounded_rectangle([cx - 8 * s, cy - 6 * s, cx + 8 * s, cy + 6 * s], 3 * s, fill=hx("#5d6fa8" if k == 1 else "#7b7464"))
    gx = int(S * 0.78)
    for k in range(7):
        d.rectangle([gx + k * 10 * s, int(T * 0.25), gx + k * 10 * s + 4 * s, int(T * 0.75)], fill=hx("#4a4640"))
    save(im, "psu.png", W, H)


# ------------------------------------------------------------------ signs
def exit_sign():
    W, H = 512, 192
    im, d, s = canvas(W, H, "#fbf3e6")
    S, T = W * s, H * s
    d.rounded_rectangle([6 * s, 6 * s, S - 6 * s, T - 6 * s], 14 * s, outline=hx("#c81e1e"), width=6 * s)
    f = ImageFont.truetype(FONT_B, 104 * s)
    tw = d.textlength("EXIT", font=f)
    d.text(((S - tw) / 2, 8 * s), "EXIT", font=f, fill=hx("#d21f1f"))
    f2 = ImageFont.truetype(FONT_B, 40 * s)
    tw = d.textlength("SORTIE", font=f2)
    d.text(((S - tw) / 2, 124 * s), "SORTIE", font=f2, fill=hx("#d21f1f"))
    save(im, "exit_sign.png", W, H)


def belt_sign():
    W, H = 256, 128
    im, d, s = canvas(W, H, "#2a2a30")
    S, T = W * s, H * s
    # left: no-smoking pictogram, right: fasten-belt pictogram, both lit amber-white
    lit = hx("#ffe7a8")
    cx, cy, r = S * 0.27, T * 0.5, T * 0.36
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=hx("#ff5a3a"), width=6 * s)
    d.rectangle([cx - r * 0.7, cy - 6 * s, cx + r * 0.5, cy + 6 * s], fill=lit)
    d.rectangle([cx + r * 0.52, cy - 6 * s, cx + r * 0.7, cy + 6 * s], fill=hx("#ff8a3a"))
    d.line([(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)], fill=hx("#ff5a3a"), width=6 * s)
    cx = S * 0.73
    d.rounded_rectangle([cx - r * 0.75, cy - 10 * s, cx + r * 0.75, cy + 10 * s], 8 * s, fill=lit)
    d.rectangle([cx - 14 * s, cy - 16 * s, cx + 14 * s, cy + 16 * s], fill=lit)
    d.rectangle([cx - 8 * s, cy - 10 * s, cx + 8 * s, cy + 10 * s], fill=hx("#2a2a30"))
    save(im, "belt_sign.png", W, H)


# ------------------------------------------------------------------ props
def newspaper():
    W, H = 256, 340
    im, d, s = canvas(W, H, "#efe9da")
    S, T = W * s, H * s
    d.rectangle([10 * s, 10 * s, S - 10 * s, 46 * s], fill=hx("#1d1b22"))  # masthead block (no words)
    d.rectangle([10 * s, 52 * s, S - 10 * s, 55 * s], fill=hx("#1d1b22"))
    for k in range(3):  # headline bars
        d.rectangle([12 * s, (64 + k * 16) * s, (200 - k * 40) * s, (74 + k * 16) * s], fill=hx("#2e2b33"))
    d.rectangle([12 * s, 118 * s, 130 * s, 200 * s], fill=hx("#8f8a86"))  # photo
    d.rectangle([20 * s, 128 * s, 120 * s, 190 * s], fill=hx("#6f6a72"))
    cols = [(12, 118, 130), (138, 118, 244)]
    for x0, y0, x1 in cols:
        y = y0 if x0 > 100 else 208
        while y < 328:
            d.rectangle([x0 * s, y * s, (x1 - (6 if (y // 7) % 5 == 4 else 0)) * s, (y + 3) * s], fill=hx("#8c877f"))
            y += 7
    save(im, "newspaper.png", W, H)


def bulkhead_graphic():
    """80s 'supergraphic' panel for the aft bulkhead: sweeping stripes in rust / orange / mustard over cream"""
    W, H = 512, 512
    im, d, s = canvas(W, H, "#efe6d2")
    S, T = W * s, H * s
    cols = ["#7a2f22", "#c8552a", "#e8873a", "#e8b84a"]
    for k, c in enumerate(cols):
        off = k * 34 * s
        pts = []
        for i in range(0, 41):
            x = S * i / 40
            y = T * 0.62 - off - math.sin(i / 40 * math.pi * 0.9) * T * 0.25
            pts.append((x, y))
        pts2 = [(x, y - 26 * s) for x, y in reversed(pts)]
        d.polygon(pts + pts2, fill=hx(c))
    save(im, "bulkhead.png", W, H)


def curtain():
    W, H = 256, 512
    im, d, s = canvas(W, H, "#1f6b78")
    S, T = W * s, H * s
    for x in range(0, S, 32 * s):
        d.rectangle([x, 0, x + 6 * s, T], fill=hx("#2a8090"))
        d.rectangle([x + 14 * s, 0, x + 16 * s, T], fill=hx("#e2a83e"))
    save(im, "curtain.png", W, H)


def galley():
    """stainless galley wall: cart bays, oven doors, latches (seen through the half-open curtain)"""
    W, H = 512, 512
    im, d, s = canvas(W, H, "#b9bcc4")
    S, T = W * s, H * s
    for i in range(4):
        x0 = int(S * (0.02 + i * 0.245)); x1 = x0 + int(S * 0.23)
        d.rectangle([x0, int(T * 0.04), x1, int(T * 0.36)], fill=hx("#a3a7b1"), outline=hx("#5d6170"), width=3 * s)
        d.rectangle([x0 + 10 * s, int(T * 0.12), x1 - 10 * s, int(T * 0.30)], fill=hx("#2d2f38"))  # oven window
        d.rectangle([x0 + 20 * s, int(T * 0.06), x1 - 20 * s, int(T * 0.09)], fill=hx("#ffb347"))  # lamp
        d.rectangle([x0, int(T * 0.52), x1, int(T * 0.98)], fill=hx("#8f939f"), outline=hx("#5d6170"), width=3 * s)
        d.rectangle([x0 + 20 * s, int(T * 0.56), x0 + 60 * s, int(T * 0.60)], fill=hx("#d22f2f"))  # cart latch
    d.rectangle([0, int(T * 0.40), S, int(T * 0.47)], fill=hx("#d9dbe0"))  # counter
    save(im, "galley.png", W, H)


def sky(name, top, mid, hor, cloud_lit, cloud_sh, sun=False):
    """what you see through a window: sky gradient, horizon band, cloud tops below (window glass is emissive)"""
    W, H = 256, 384
    im, d, s = canvas(W, H, top)
    S, T = W * s, H * s
    hzn = int(T * 0.58)
    for y in range(hzn):
        t = y / hzn
        c = mix(hx(top), hx(mid), min(1, t * 1.4)) if t < 0.7 else mix(hx(mid), hx(hor), (t - 0.7) / 0.3)
        d.line([(0, y), (S, y)], fill=c)
    d.rectangle([0, hzn, S, T], fill=hx(cloud_sh))
    rnd = random.Random(len(name))
    for k in range(26):
        cx = rnd.uniform(-0.1, 1.1) * S; cy = hzn + rnd.uniform(0.02, 0.4) * T; r = rnd.uniform(0.08, 0.2) * S
        d.ellipse([cx - r, cy - r * 0.45, cx + r, cy + r * 0.45], fill=hx(cloud_lit))
        d.ellipse([cx - r * 0.9, cy - r * 0.2, cx + r * 0.9, cy + r * 0.55], fill=hx(cloud_sh))
    if sun:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        cx, cy = S * 0.55, hzn - T * 0.10
        for k in range(30, 0, -1):
            r = k * 6 * s
            gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 236, 190, int(255 * (1 - k / 30) ** 1.6)))
        im.alpha_composite(g)
        d = ImageDraw.Draw(im)
        d.ellipse([cx - 26 * s, cy - 26 * s, cx + 26 * s, cy + 26 * s], fill=hx("#fff6dc"))
    im = im.filter(ImageFilter.GaussianBlur(1.0 * s))
    save(im, name, W, H)


def cup():
    W, H = 128, 128
    im, d, s = canvas(W, H, "#f4f0e6")
    S, T = W * s, H * s
    d.rectangle([0, int(T * 0.12), S, int(T * 0.24)], fill=hx("#c8552a"))
    d.rectangle([0, int(T * 0.26), S, int(T * 0.30)], fill=hx("#e2a83e"))
    save(im, "cup.png", W, H)


if __name__ == "__main__":
    seat_fabric(); headrest(); carpet_aisle(); carpet_floor(); wall(); dado(); bin_door(); psu()
    exit_sign(); belt_sign(); newspaper(); bulkhead_graphic(); curtain(); galley(); cup()
    sky("sky_left.png", "#3a2f6e", "#7a4f8e", "#e98a6a", "#e9a08e", "#6a5a9e")
    sky("sky_right.png", "#c8607a", "#f29a5a", "#ffd08a", "#ffd9a8", "#d98a7a", sun=True)
