# Paints every texture of the check-in hall (sets/checkin.py) with Pillow. Run:
#   C:\Users\plamb\AppData\Local\Programs\Python\Python312\python.exe -I D:\gimli3d\blender\tex\checkin\make_tex.py
# Output: PNGs next to this file. Airline-neutral: invented logo, invented flight codes, no real brand.
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
FONTS = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def save(im, name):
    im.save(os.path.join(OUT, name))
    print("wrote", name, im.size)


def hexc(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


# ------------------------------------------------------------------ floor: big polished tiles, 4 x 4 per texture
def floor():
    T = 256; N = 4; S = T * N
    rnd = random.Random(3)
    im = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(im)
    A, B = (236, 229, 216), (221, 214, 203)
    for i in range(N):
        for j in range(N):
            c = A if (i + j) % 2 == 0 else B
            jit = rnd.randint(-4, 4)
            c = tuple(max(0, min(255, v + jit)) for v in c)
            d.rectangle([i * T, j * T, i * T + T - 1, j * T + T - 1], fill=c)
            # terrazzo chips
            for _ in range(70):
                x, y = i * T + rnd.randint(6, T - 6), j * T + rnd.randint(6, T - 6)
                r = rnd.choice((1, 1, 2, 2, 3))
                cc = rnd.choice([(196, 188, 176), (205, 196, 184), (186, 196, 210), (214, 192, 170), (250, 248, 244)])
                d.ellipse([x - r, y - r, x + r, y + r], fill=cc)
            # soft polished sheen streak (diagonal, painted)
            sh = Image.new("L", (T, T), 0); sd = ImageDraw.Draw(sh)
            o = rnd.randint(-60, 60)
            sd.polygon([(o + 40, 0), (o + 110, 0), (o + 70 + T * 0.3, T), (o + T * 0.3, T)], fill=26)
            sh = sh.filter(ImageFilter.GaussianBlur(14))
            tile = im.crop((i * T, j * T, i * T + T, j * T + T))
            tile = Image.composite(Image.new("RGB", (T, T), (255, 255, 255)), tile, sh)
            im.paste(tile, (i * T, j * T))
    # grout lines
    for k in range(N + 1):
        p = k * T
        d.rectangle([p - 2, 0, p + 1, S], fill=(164, 154, 142))
        d.rectangle([0, p - 2, S, p + 1], fill=(164, 154, 142))
    save(im, "floor.png")


# ------------------------------------------------------------------ scale display: 7-segment LED
SEG = {  # segments a b c d e f g
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
    "8": "abcdefg", "9": "abcdfg", " ": "",
}


def seg_polys(x, y, w, h, t):
    """7-seg polygons for a digit with top-left (x, y), width w, height h, stroke t, slanted"""
    sl = 0.07 * w

    def P(px, py):  # slant: shift x by the height fraction
        return (px + sl * (1 - (py - y) / h), py)

    hh = h / 2
    g = t * 0.10

    def hseg(yc):
        return [P(x + t / 2 + g, yc), P(x + t + g, yc - t / 2), P(x + w - t - g, yc - t / 2), P(x + w - t / 2 - g, yc),
                P(x + w - t - g, yc + t / 2), P(x + t + g, yc + t / 2)]

    def vseg(xc, y0, y1):
        return [P(xc, y0 + g), P(xc + t / 2, y0 + t / 2 + g), P(xc + t / 2, y1 - t / 2 - g), P(xc, y1 - g),
                P(xc - t / 2, y1 - t / 2 - g), P(xc - t / 2, y0 + t / 2 + g)]

    ya, yg, yd = y + t / 2, y + hh, y + h - t / 2
    return {
        "a": hseg(ya), "g": hseg(yg), "d": hseg(yd),
        "f": vseg(x + t / 2, ya, yg), "b": vseg(x + w - t / 2, ya, yg),
        "e": vseg(x + t / 2, yg, yd), "c": vseg(x + w - t / 2, yg, yd),
    }


def display(state, name):
    W, H = 1024, 480
    bg = (8, 22, 18)
    on = (110, 255, 160)
    ghost = (14, 34, 27)
    im = Image.new("RGB", (W, H), bg)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    d, gd = ImageDraw.Draw(im), ImageDraw.Draw(glow)
    # bezel inner frame line + top status strip
    d.rounded_rectangle([10, 10, W - 11, H - 11], radius=26, outline=(30, 64, 52), width=6)
    txt = {"blank": ("  ", ""), "kg": ("23", "kg"), "lb": ("50", "lb")}[state]
    digits, unit = txt
    dw, dh, t = 236, 340, 60
    x0, y0 = 58, 84
    for k in range(2):
        ch = digits[k]
        polys = seg_polys(x0 + k * (dw + 52), y0, dw, dh, t)
        for s, poly in polys.items():
            lit = s in SEG.get(ch, "")
            d.polygon(poly, fill=on if lit else ghost)
            if lit:
                gd.polygon(poly, fill=on)
    # unit label, bold, same LED colour, big
    f = font("ariblk.ttf", 190)
    ux = x0 + 2 * (dw + 52) + 30
    if unit:
        d.text((ux, y0 + dh - 30), unit, font=f, fill=on, anchor="ls")
        gd.text((ux, y0 + dh - 30), unit, font=f, fill=on, anchor="ls")
    else:  # ghost unit box
        d.text((ux, y0 + dh - 30), "kg", font=f, fill=(14, 36, 28), anchor="ls")
    # small "scale" pictogram (suitcase on a platform) top-right, always dim-lit
    px, py = W - 120, 40
    col = (60, 150, 110)
    d.rounded_rectangle([px, py + 14, px + 70, py + 62], radius=8, outline=col, width=6)
    d.rectangle([px + 22, py, px + 48, py + 16], outline=col, width=5)
    d.rectangle([px - 10, py + 70, px + 80, py + 78], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    im = Image.blend(im, Image.eval(Image.merge("RGB", [Image.eval(c, lambda v: v) for c in glow.split()]), lambda v: v), 0.0)
    # additive glow
    from PIL import ImageChops
    im = ImageChops.add(im, glow.point(lambda v: int(v * 0.55)))
    # glass sheen
    sh = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(sh)
    sd.polygon([(0, 0), (W * 0.42, 0), (W * 0.22, H), (0, H)], fill=14)
    im = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), im, sh)
    save(im, name)


# ------------------------------------------------------------------ logo mark (invented, airline-neutral)
def logo_mark(size, ring=True):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=hexc("#2a55c4"))
    # orange sun
    r = S * 0.13
    d.ellipse([S * 0.60 - r, S * 0.30 - r, S * 0.60 + r, S * 0.30 + r], fill=hexc("#ffb43a"))
    # white swoosh wing (two arcs)
    pts = []
    for k in range(41):
        a = k / 40
        pts.append((S * (0.14 + 0.74 * a), S * (0.70 - 0.38 * math.sin(a * math.pi * 0.9) - 0.10 * a)))
    for k in range(40, -1, -1):
        a = k / 40
        pts.append((S * (0.14 + 0.74 * a), S * (0.70 - 0.24 * math.sin(a * math.pi * 0.9) - 0.04 * a + 0.05)))
    d.polygon(pts, fill=(255, 255, 255, 255))
    pts2 = [(S * (0.22 + 0.6 * k / 30), S * (0.84 - 0.16 * math.sin(k / 30 * math.pi * 0.9))) for k in range(31)]
    d.line(pts2, fill=hexc("#ff6a3d"), width=int(S * 0.05))
    if ring:
        d.ellipse([0, 0, S - 1, S - 1], outline=(255, 255, 255, 255), width=int(S * 0.035))
    mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).ellipse([0, 0, S - 1, S - 1], fill=255)
    im.putalpha(Image.composite(im.split()[3], Image.new("L", (S, S), 0), mask))
    return im.resize((size, size), Image.LANCZOS)


def counter_logo():
    """the logo panel on the counter front (white panel, mark + colour bands)"""
    W, H = 1024, 512
    im = Image.new("RGB", (W, H), (250, 249, 246))
    d = ImageDraw.Draw(im)
    m = logo_mark(330)
    im.paste(m, (70, 90), m)
    for k, c in enumerate(["#ff6a3d", "#ffb43a", "#2a55c4", "#1fa3a8"]):
        y = 150 + k * 62
        d.rounded_rectangle([450, y, 960 - k * 70, y + 40], radius=20, fill=hexc(c))
    d.rounded_rectangle([6, 6, W - 7, H - 7], radius=40, outline=(200, 205, 214), width=10)
    save(im, "counter_logo.png")


def desk_screen(num, closed=False):
    W, H = 768, 432
    im = Image.new("RGB", (W, H), hexc("#14205a")[:3])
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 120], fill=hexc("#2a55c4")[:3])
    m = logo_mark(96)
    im.paste(m, (18, 12), m)
    d.text((W - 30, 62), str(num), font=font("ariblk.ttf", 104), fill=(255, 255, 255), anchor="rm")
    # check-in pictogram: person with suitcase
    px, py = 70, 170
    c = (255, 255, 255)
    d.ellipse([px + 20, py, px + 64, py + 44], fill=c)
    d.rounded_rectangle([px + 10, py + 52, px + 74, py + 170], radius=20, fill=c)
    d.rectangle([px + 18, py + 160, px + 36, py + 240], fill=c); d.rectangle([px + 48, py + 160, px + 66, py + 240], fill=c)
    d.rounded_rectangle([px + 92, py + 120, px + 172, py + 236], radius=10, fill=hexc("#ffb43a"))
    d.rectangle([px + 118, py + 100, px + 146, py + 122], outline=hexc("#ffb43a"), width=8)
    if closed:
        d.rounded_rectangle([290, 200, 720, 330], radius=30, fill=hexc("#e8413c"))
        d.ellipse([320, 215, 420, 315], outline=(255, 255, 255), width=14)
        d.line([(335, 300), (405, 230)], fill=(255, 255, 255), width=14)
        d.rectangle([450, 250, 690, 280], fill=(255, 255, 255))
    else:
        d.rounded_rectangle([290, 170, 720, 250], radius=24, fill=hexc("#3ad07a"))
        d.text((505, 210), "BAG DROP", font=font("arialbd.ttf", 54), fill=(10, 40, 20), anchor="mm")
        for k in range(3):
            d.rounded_rectangle([290, 280 + k * 44, 720 - k * 90, 306 + k * 44], radius=12, fill=(120, 150, 230))
    save(im, f"desk_{num}.png")


# ------------------------------------------------------------------ departures board
def board():
    W, H = 2048, 1024
    im = Image.new("RGB", (W, H), hexc("#101a3c")[:3])
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 150], fill=hexc("#ffc928")[:3])
    # departing plane pictogram
    plane_icon(d, 95, 76, 62, (16, 26, 60))
    d.text((170, 76), "DEPARTURES", font=font("ariblk.ttf", 96), fill=(16, 26, 60), anchor="lm")
    d.text((W - 60, 76), "10:42", font=font("consolab.ttf", 100), fill=(16, 26, 60), anchor="rm")
    hdr = font("arialbd.ttf", 44)
    cols = [40, 300, 600, 1290, 1520]
    for x, t in zip(cols, ["TIME", "FLIGHT", "DESTINATION", "GATE", "REMARKS"]):
        d.text((x, 196), t, font=hdr, fill=(140, 160, 220), anchor="lm")
    rows = [("10:55", "K7 214", "VANCOUVER", "A4", "BOARDING", "#3ad07a"),
            ("11:05", "Q3 1143", "EDMONTON", "B7", "CHECK-IN", "#ffc928"),
            ("11:20", "K7 088", "TORONTO", "A2", "ON TIME", "#ffffff"),
            ("11:35", "Z2 412", "HALIFAX", "C1", "ON TIME", "#ffffff"),
            ("11:50", "Q3 517", "WINNIPEG", "B3", "DELAYED", "#ff5a4f"),
            ("12:10", "K7 301", "CALGARY", "A9", "ON TIME", "#ffffff"),
            ("12:25", "Z2 076", "OTTAWA", "C4", "ON TIME", "#ffffff"),
            ("12:40", "Q3 230", "REGINA", "B1", "GATE OPEN", "#3ad07a")]
    f = font("consolab.ttf", 70)
    for k, (tm, fl, dest, gate, rem, rc) in enumerate(rows):
        y = 300 + k * 92
        if k % 2 == 0:
            d.rectangle([0, y - 44, W, y + 44], fill=hexc("#172552")[:3])
        d.text((cols[0], y), tm, font=f, fill=hexc("#ffc928")[:3], anchor="lm")
        d.text((cols[1], y), fl, font=f, fill=(235, 240, 255), anchor="lm")
        d.text((cols[2], y), dest, font=f, fill=(255, 255, 255), anchor="lm")
        d.text((cols[3], y), gate, font=f, fill=(235, 240, 255), anchor="lm")
        d.text((cols[4], y), rem, font=f, fill=hexc(rc)[:3], anchor="lm")
    save(im, "board.png")


# ------------------------------------------------------------------ hanging wayfinding signs (pictograms)
def plane_icon(d, x, y, s, col, rot=-30):
    pl = [(-100, -6), (-30, -8), (20, -60), (40, -60), (20, -8), (80, -10), (95, -30), (108, -30), (100, 0), (108, 30),
          (95, 30), (80, 10), (20, 8), (40, 60), (20, 60), (-30, 8), (-100, 6)]
    a = math.radians(rot)
    pts = [(x + s * (px * math.cos(a) - py * math.sin(a)) / 100, y + s * (px * math.sin(a) + py * math.cos(a)) / 100) for px, py in pl]
    d.polygon(pts, fill=col)


def arrow(d, x, y, s, col, dirn=1):
    pts = [(-1, -0.18), (0.2, -0.18), (0.2, -0.5), (1, 0), (0.2, 0.5), (0.2, 0.18), (-1, 0.18)]
    d.polygon([(x + dirn * px * s, y + py * s) for px, py in pts], fill=col)


def suitcase_icon(d, x, y, s, col):
    d.rounded_rectangle([x - s * 0.5, y - s * 0.32, x + s * 0.5, y + s * 0.42], radius=int(s * 0.1), fill=col)
    d.rectangle([x - s * 0.18, y - s * 0.52, x + s * 0.18, y - s * 0.32], outline=col, width=max(3, int(s * 0.08)))


def person(d, x, y, s, col, skirt=False):
    d.ellipse([x - s * 0.13, y - s * 0.62, x + s * 0.13, y - s * 0.36], fill=col)
    if skirt:
        d.polygon([(x - s * 0.17, y - s * 0.3), (x + s * 0.17, y - s * 0.3), (x + s * 0.27, y + s * 0.15), (x - s * 0.27, y + s * 0.15)], fill=col)
    else:
        d.rounded_rectangle([x - s * 0.19, y - s * 0.3, x + s * 0.19, y + s * 0.15], radius=int(s * 0.06), fill=col)
    d.rectangle([x - s * 0.13, y + s * 0.1, x - s * 0.03, y + s * 0.62], fill=col)
    d.rectangle([x + s * 0.03, y + s * 0.1, x + s * 0.13, y + s * 0.62], fill=col)


def signs():
    # sign 1: dark navy, yellow pictograms: departures + arrow, gate letters
    W, H = 1536, 384
    im = Image.new("RGB", (W, H), hexc("#1b2450")[:3]); d = ImageDraw.Draw(im)
    Y = hexc("#ffc928")[:3]
    d.rounded_rectangle([40, 52, 320, 332], radius=30, fill=Y)
    plane_icon(d, 180, 192, 120, (27, 36, 80))
    d.text((370, 192), "Gates  A  B  C", font=font("arialbd.ttf", 120), fill=(255, 255, 255), anchor="lm")
    arrow(d, 1380, 192, 110, Y, 1)
    save(im, "sign_gates.png")
    # sign 2: yellow, black pictograms: toilets, info, coffee
    im = Image.new("RGB", (W, H), hexc("#ffc928")[:3]); d = ImageDraw.Draw(im)
    K = (24, 26, 34)
    arrow(d, 160, 192, 110, K, -1)
    person(d, 400, 200, 260, K); person(d, 560, 200, 260, K, skirt=True)
    d.rectangle([476, 70, 484, 330], fill=K)
    d.ellipse([700, 62, 960, 322], fill=K); d.text((830, 192), "i", font=font("ariblk.ttf", 200), fill=hexc("#ffc928")[:3], anchor="mm")
    # coffee cup
    d.rounded_rectangle([1060, 130, 1260, 320], radius=30, fill=K)
    d.ellipse([1230, 170, 1330, 270], outline=K, width=26)
    for k in range(3):
        d.arc([1080 + k * 60, 40, 1140 + k * 60, 120], 200, 340, fill=K, width=14)
    save(im, "sign_services.png")
    # sign 3: check-in / baggage (white on blue)
    im = Image.new("RGB", (W, H), hexc("#2a55c4")[:3]); d = ImageDraw.Draw(im)
    Wt = (255, 255, 255)
    person(d, 180, 200, 260, Wt); suitcase_icon(d, 300, 255, 120, hexc("#ffc928")[:3])
    d.text((420, 192), "Check-in  12-18", font=font("arialbd.ttf", 120), fill=Wt, anchor="lm")
    arrow(d, 1400, 192, 100, Wt, -1)
    save(im, "sign_checkin.png")


# ------------------------------------------------------------------ luggage tag = a sliver of the jet's skin
def tag():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (246, 244, 238)); d = ImageDraw.Draw(im)
    d.rectangle([0, 300, W, 360], fill=hexc("#c8323a")[:3])
    d.rectangle([0, 368, W, 380], fill=hexc("#c8323a")[:3])
    d.rounded_rectangle([88, 150, 168, 250], radius=32, fill=hexc("#26304a")[:3])  # a cabin window
    d.ellipse([110, 40, 146, 76], outline=(150, 150, 160), width=8)  # eyelet
    for k in range(5):  # rivets
        d.ellipse([20 + k * 50, 280, 28 + k * 50, 288], fill=(190, 190, 196))
    d.rectangle([2, 2, W - 3, H - 3], outline=(170, 168, 160), width=4)
    save(im, "tag.png")


# ------------------------------------------------------------------ jet livery (outside jet), u along the fuselage (tail -> nose)
def livery():
    W, H = 4096, 512  # v: 0 = bottom of the fuselage, 0.5 = top (texture wraps around once, both sides)
    im = Image.new("RGB", (W, H), (246, 246, 244)); d = ImageDraw.Draw(im)
    # rows are around the circumference: map so that each side (v 0..0.5 and 0.5..1) carries the same stripes
    for half in (0, 1):
        base = half * 256
        def yv(f):  # f = 0 belly -> 1 crown on this side
            return base + (f * 256 if half == 0 else (1 - f) * 256)
        # grey belly
        a, b = sorted((yv(0), yv(0.22)))
        d.rectangle([0, a, W, b], fill=(196, 202, 212))
        # blue cheatline + orange pinstripe
        a, b = sorted((yv(0.38), yv(0.46)))
        d.rectangle([0, a, W, b], fill=hexc("#2a55c4")[:3])
        a, b = sorted((yv(0.47), yv(0.49)))
        d.rectangle([0, a, W, b], fill=hexc("#ff6a3d")[:3])
        # windows
        a, b = sorted((yv(0.55), yv(0.63)))
        for k in range(46):
            x = 600 + k * 66
            if 2400 < x < 2470:
                continue
            d.rounded_rectangle([x, a, x + 30, b], radius=10, fill=(38, 48, 74))
        # doors
        for x in (520, 2420, 3640):
            a2, b2 = sorted((yv(0.3), yv(0.72)))
            d.rounded_rectangle([x, a2, x + 70, b2], radius=14, outline=(120, 126, 140), width=6)
        # cockpit windows
        a, b = sorted((yv(0.62), yv(0.74)))
        d.polygon([(3880, b), (3930, a), (4010, a), (4030, b)], fill=(38, 48, 74))
    save(im, "livery.png")


def tail_logo():
    S = 512
    im = Image.new("RGB", (S, S), hexc("#2a55c4")[:3]); d = ImageDraw.Draw(im)
    m = logo_mark(380, ring=True)
    im.paste(m, (66, 66), m)
    save(im, "tail.png")


# ------------------------------------------------------------------ posters / light boxes
def poster_beach():
    W, H = 512, 768
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        c = (int(255 - 40 * t), int(140 + 60 * t), int(90 + 80 * t)) if t < 0.55 else (40, int(170 - 30 * (t - 0.55)), 200)
        d.line([(0, y), (W, y)], fill=c)
    d.ellipse([170, 200, 340, 370], fill=(255, 230, 120))
    d.rectangle([0, 420, W, 470], fill=(30, 150, 200))
    d.polygon([(0, 600), (W, 560), (W, H), (0, H)], fill=(250, 214, 150))
    # palm
    d.line([(380, 620), (360, 520), (330, 380)], fill=(110, 70, 40), width=18)
    for a in range(0, 360, 50):
        r = math.radians(a)
        d.polygon([(330, 380), (330 + 130 * math.cos(r) - 20, 380 + 70 * math.sin(r)), (330 + 130 * math.cos(r) + 20, 380 + 70 * math.sin(r) + 15)], fill=(40, 150, 70))
    d.rectangle([0, 0, W, 110], fill=(255, 255, 255))
    m = logo_mark(80); im.paste(m, (20, 15), m)
    d.text((120, 55), "FLY SOUTH", font=font("ariblk.ttf", 64), fill=hexc("#2a55c4")[:3], anchor="lm")
    save(im, "poster_beach.png")


def poster_mountain():
    W, H = 512, 768
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(60 + 120 * t), int(100 + 110 * t), int(210 + 30 * t)))
    d.polygon([(-40, 560), (170, 260), (300, 420), (390, 300), (560, 560)], fill=(90, 80, 150))
    d.polygon([(170, 260), (215, 320), (190, 330), (160, 310), (130, 318)], fill=(250, 250, 255))
    d.polygon([(390, 300), (430, 350), (405, 350), (380, 340)], fill=(250, 250, 255))
    d.rectangle([0, 560, W, H], fill=(40, 140, 90))
    d.ellipse([60, 600, 460, 700], fill=(60, 160, 220))
    for x in (40, 110, 420, 480):
        d.polygon([(x, 520), (x - 30, 640), (x + 30, 640)], fill=(20, 100, 60))
    d.rectangle([0, 0, W, 110], fill=(255, 255, 255))
    m = logo_mark(80); im.paste(m, (20, 15), m)
    d.text((120, 55), "GO WEST", font=font("ariblk.ttf", 64), fill=hexc("#ff6a3d")[:3], anchor="lm")
    save(im, "poster_mountain.png")


# ------------------------------------------------------------------ small things
def belt():
    W, H = 256, 256
    im = Image.new("RGB", (W, H), (40, 42, 50)); d = ImageDraw.Draw(im)
    for k in range(8):
        d.rectangle([0, k * 32, W, k * 32 + 4], fill=(70, 74, 86))
    save(im, "belt.png")


def wood():
    W, H = 512, 512
    rnd = random.Random(5)
    im = Image.new("RGB", (W, H), (201, 136, 78)); d = ImageDraw.Draw(im)
    for k in range(16):  # vertical slats
        x = k * 32
        c = (201 + rnd.randint(-10, 10), 136 + rnd.randint(-10, 8), 78 + rnd.randint(-8, 8))
        d.rectangle([x, 0, x + 31, H], fill=c)
        for _ in range(6):
            y = rnd.randint(0, H); d.line([(x + rnd.randint(4, 26), y), (x + rnd.randint(4, 26), y + rnd.randint(40, 120))], fill=(c[0] - 18, c[1] - 16, c[2] - 12), width=2)
        d.rectangle([x + 29, 0, x + 31, H], fill=(120, 72, 40))
    save(im, "wood.png")


def glass():
    W, H = 512, 512
    im = Image.new("RGBA", (W, H), (200, 230, 255, 18)); d = ImageDraw.Draw(im)
    for x0, w, a in ((40, 70, 60), (150, 24, 50), (330, 110, 40), (470, 20, 50)):
        d.polygon([(x0, 0), (x0 + w, 0), (x0 + w - 200, H), (x0 - 200, H)], fill=(255, 255, 255, a))
    save(im, "glass.png")


def clock():
    S = 256
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([4, 4, S - 5, S - 5], fill=(250, 250, 248), outline=(30, 34, 50), width=14)
    for k in range(12):
        a = math.radians(k * 30)
        r0, r1 = 92, 108
        d.line([(128 + r0 * math.sin(a), 128 - r0 * math.cos(a)), (128 + r1 * math.sin(a), 128 - r1 * math.cos(a))], fill=(30, 34, 50), width=8)
    d.line([(128, 128), (128 + 60 * math.sin(math.radians(321)), 128 - 60 * math.cos(math.radians(321)))], fill=(30, 34, 50), width=12)
    d.line([(128, 128), (128 + 88 * math.sin(math.radians(252)), 128 - 88 * math.cos(math.radians(252)))], fill=(30, 34, 50), width=8)
    d.ellipse([118, 118, 138, 138], fill=(220, 50, 50))
    save(im, "clock.png")


if __name__ == "__main__":
    floor()
    display("blank", "disp_blank.png"); display("kg", "disp_23kg.png"); display("lb", "disp_50lb.png")
    counter_logo(); desk_screen(14); desk_screen(15); desk_screen(13, closed=True)
    board(); signs(); tag(); livery(); tail_logo(); poster_beach(); poster_mountain(); belt(); wood(); glass(); clock()
