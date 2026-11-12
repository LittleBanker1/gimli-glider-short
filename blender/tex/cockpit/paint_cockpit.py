# Paints every texture of the cockpit set (Pillow). Run with the system Python:
#   python -I D:\gimli3d\blender\tex\cockpit\paint_cockpit.py
# Output: PNGs next to this file. All drawing is done at 2x and downsampled for clean anti-aliased cartoon lines.
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
FONTS = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def canvas(w, h, col, ss=2):
    im = Image.new("RGBA", (w * ss, h * ss), col)
    return im, ImageDraw.Draw(im), ss


def save(im, name, w, h):
    im.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, name))


def ctext(d, xy, s, f, fill, anchor="mm", **kw):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, **kw)


WHITE, GREEN, MAG, CYAN, AMBER, RED = "#f4f6f2", "#4cf06a", "#ff4fe0", "#4fe6ff", "#ffb22a", "#ff3b30"


# ------------------------------------------------------------------ EFIS: attitude (EADI)
def eadi(name, roll=-4.0, pitch=2.5):
    S = 512
    im, d, k = canvas(S, S, "#06070b")
    big = Image.new("RGBA", (S * k * 2, S * k * 2), "#000")
    bd = ImageDraw.Draw(big)
    c = S * k
    px = 15 * k  # px per degree
    hz = c + pitch * px
    bd.rectangle([0, 0, 2 * c, hz], fill="#1f86e6")
    bd.rectangle([0, hz, 2 * c, 2 * c], fill="#a8642e")
    # subtle gradient bands
    for i in range(6):
        bd.rectangle([0, hz - (i + 1) * 40 * k, 2 * c, hz - i * 40 * k], fill=(31 + i * 4, 134 - i * 6, 230 - i * 4))
        bd.rectangle([0, hz + i * 40 * k, 2 * c, hz + (i + 1) * 40 * k], fill=(168 - i * 8, 100 - i * 5, 46 - i * 2))
    bd.line([0, hz, 2 * c, hz], fill=WHITE, width=4 * k)
    f = font("arialbd.ttf", 22 * k)
    for deg in range(-30, 35, 5):
        if deg == 0:
            continue
        y = hz - deg * px
        w = 70 * k if deg % 10 == 0 else 36 * k
        bd.line([c - w, y, c + w, y], fill=WHITE, width=3 * k)
        if deg % 10 == 0:
            ctext(bd, (c - w - 26 * k, y), str(abs(deg)), f, WHITE)
            ctext(bd, (c + w + 26 * k, y), str(abs(deg)), f, WHITE)
    big = big.rotate(roll, resample=Image.BICUBIC, center=(c, c))
    att = big.crop((c - 200 * k, c - 200 * k, c + 200 * k, c + 200 * k))
    mask = Image.new("L", att.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, att.size[0] - 1, att.size[1] - 1], 70 * k, fill=255)
    im.paste(att, (56 * k, 70 * k), mask)
    # roll scale
    cx, cy, r = 256 * k, 270 * k, 196 * k
    for a in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
        t = math.radians(a - 90)
        l = 22 * k if a % 30 == 0 else 13 * k
        d.line([cx + r * math.cos(t), cy + r * math.sin(t), cx + (r + l) * math.cos(t), cy + (r + l) * math.sin(t)], fill=WHITE, width=3 * k)
    t = math.radians(-roll - 90)
    tip = (cx + (r - 2 * k) * math.cos(t), cy + (r - 2 * k) * math.sin(t))
    n = (math.cos(t + math.pi / 2), math.sin(t + math.pi / 2))
    base = (cx + (r - 26 * k) * math.cos(t), cy + (r - 26 * k) * math.sin(t))
    d.polygon([tip, (base[0] + n[0] * 12 * k, base[1] + n[1] * 12 * k), (base[0] - n[0] * 12 * k, base[1] - n[1] * 12 * k)], fill=WHITE)
    # flight director (magenta) + aircraft symbol
    d.line([cx - 90 * k, cy + 8 * k, cx + 90 * k, cy + 8 * k], fill=MAG, width=5 * k)
    d.line([cx + 6 * k, cy - 80 * k, cx + 6 * k, cy + 90 * k], fill=MAG, width=5 * k)
    for s in (-1, 1):
        d.polygon([(cx + s * 40 * k, cy - 6 * k), (cx + s * 130 * k, cy - 6 * k), (cx + s * 130 * k, cy + 6 * k), (cx + s * 52 * k, cy + 6 * k),
                   (cx + s * 52 * k, cy + 30 * k), (cx + s * 40 * k, cy + 30 * k)], fill="#111", outline=WHITE, width=3 * k)
    d.rectangle([cx - 8 * k, cy - 8 * k, cx + 8 * k, cy + 8 * k], fill="#111", outline=WHITE, width=3 * k)
    # annunciators
    fa = font("arialbd.ttf", 24 * k)
    for x, s, col in ((110, "SPD", GREEN), (256, "HDG SEL", GREEN), (410, "ALT", GREEN)):
        ctext(d, (x * k, 36 * k), s, fa, col)
    d.rectangle([215 * k, 470 * k, 300 * k, 500 * k], outline=WHITE, width=3 * k)
    ctext(d, (257 * k, 486 * k), "CMD", fa, GREEN)
    ctext(d, (70 * k, 486 * k), "GS 452", font("arialbd.ttf", 22 * k), WHITE)
    # localiser / glideslope scales
    for i in (-2, -1, 1, 2):
        d.ellipse([cx + i * 40 * k - 6 * k, 448 * k, cx + i * 40 * k + 6 * k, 460 * k], outline=WHITE, width=2 * k)
        d.ellipse([478 * k, cy + i * 40 * k - 6 * k, 490 * k, cy + i * 40 * k + 6 * k], outline=WHITE, width=2 * k)
    d.polygon([(cx + 22 * k, 446 * k), (cx + 34 * k, 454 * k), (cx + 22 * k, 462 * k), (cx + 10 * k, 454 * k)], fill=MAG)
    d.polygon([(484 * k, cy - 52 * k), (494 * k, cy - 40 * k), (484 * k, cy - 28 * k), (474 * k, cy - 40 * k)], fill=MAG)
    save(im, name, S, S)


# ------------------------------------------------------------------ EFIS: map (EHSI)
def ehsi(name):
    S = 512
    im, d, k = canvas(S, S, "#05060a")
    cx, cy, R = 256 * k, 440 * k, 360 * k
    rnd = random.Random(7)
    # weather returns
    wx = Image.new("RGBA", im.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(wx)
    for i in range(14):
        x, y, r = rnd.randint(40, 200) * k, rnd.randint(120, 300) * k, rnd.randint(12, 34) * k
        wd.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(40, 200, 70, 150))
        if i % 3 == 0:
            wd.ellipse([x - r * 0.45, y - r * 0.3, x + r * 0.45, y + r * 0.3], fill=(240, 220, 50, 190))
    wx = wx.filter(ImageFilter.GaussianBlur(6 * k))
    im.alpha_composite(wx)
    f = font("arialbd.ttf", 26 * k)
    fs = font("arialbd.ttf", 20 * k)
    d.arc([cx - R, cy - R, cx + R, cy + R], 215, 325, fill=WHITE, width=4 * k)
    hdg = 275
    for a in range(-55, 56, 5):
        t = math.radians(a - 90)
        l = 22 * k if a % 10 == 0 else 12 * k
        d.line([cx + R * math.cos(t), cy + R * math.sin(t), cx + (R - l) * math.cos(t), cy + (R - l) * math.sin(t)], fill=WHITE, width=3 * k)
        val = (hdg - 5 + a) % 360  # ticks every 5 starting at a round heading
        if val % 30 == 0:
            ctext(d, (cx + (R - 48 * k) * math.cos(t), cy + (R - 48 * k) * math.sin(t)), str(val // 10), f, WHITE)
    # range arc (dashed)
    for a in range(215, 325, 8):
        d.arc([cx - 180 * k, cy - 180 * k, cx + 180 * k, cy + 180 * k], a, a + 4, fill=WHITE, width=2 * k)
    ctext(d, (cx - 150 * k, cy - 120 * k), "40", fs, WHITE)
    # route
    pts = [(cx, cy), (cx + 22 * k, cy - 170 * k), (cx + 70 * k, cy - 300 * k), (cx + 140 * k, cy - 420 * k)]
    d.line(pts, fill=MAG, width=6 * k, joint="curve")
    for i, (x, y) in enumerate(pts[1:]):
        col = MAG if i == 0 else WHITE
        s = 13 * k
        d.polygon([(x, y - s), (x + s * 0.35, y - s * 0.35), (x + s, y), (x + s * 0.35, y + s * 0.35), (x, y + s), (x - s * 0.35, y + s * 0.35), (x - s, y), (x - s * 0.35, y - s * 0.35)], fill=col)
        ctext(d, (x + 18 * k, y), ["KENLO", "RAMIX", "TOVAR"][i], fs, col, anchor="lm")
    # airports (cyan) and a VOR (green)
    for x, y, n in ((120, 210, "GIMLI"), (420, 300, "CYWG")):
        d.ellipse([x * k - 11 * k, y * k - 11 * k, x * k + 11 * k, y * k + 11 * k], outline=CYAN, width=3 * k)
        ctext(d, (x * k + 16 * k, y * k), n, fs, CYAN, anchor="lm")
    d.ellipse([350 * k - 9 * k, 160 * k - 9 * k, 350 * k + 9 * k, 160 * k + 9 * k], outline=GREEN, width=3 * k)
    # aircraft symbol + heading box
    d.polygon([(cx, cy - 26 * k), (cx + 16 * k, cy + 12 * k), (cx - 16 * k, cy + 12 * k)], outline=WHITE, width=3 * k)
    d.rectangle([cx - 70 * k, 14 * k, cx + 70 * k, 52 * k], fill="#05060a", outline=WHITE, width=3 * k)
    ctext(d, (cx, 33 * k), "TRK 275 M", fs, WHITE)
    d.polygon([(cx, 62 * k), (cx - 9 * k, 76 * k), (cx + 9 * k, 76 * k)], fill=WHITE)
    ctext(d, (14 * k, 26 * k), "GS452 TAS470", fs, WHITE, anchor="lm")
    ctext(d, (14 * k, 54 * k), "283\u00b0/ 25", fs, WHITE, anchor="lm")
    d.line([40 * k, 72 * k, 60 * k, 96 * k], fill=GREEN, width=4 * k)
    ctext(d, (498 * k, 26 * k), "KENLO", fs, MAG, anchor="rm")
    ctext(d, (498 * k, 52 * k), "0042.5z", fs, WHITE, anchor="rm")
    ctext(d, (498 * k, 78 * k), "126 NM", fs, WHITE, anchor="rm")
    save(im, name, S, S)


# ------------------------------------------------------------------ EICAS
def dial(d, k, cx, cy, r, val, vmax, label, readout, col=WHITE, red=0.93):
    a0, a1 = 150, 390  # degrees (PIL: 0 = 3 o'clock, clockwise)
    box = [cx - r, cy - r, cx + r, cy + r]
    av = a0 + (a1 - a0) * min(val / vmax, 1.0)
    d.pieslice(box, a0, av, fill="#3c414f")
    d.arc(box, a0, a1, fill=col, width=4 * k)
    for i in range(11):
        t = math.radians(a0 + (a1 - a0) * i / 10)
        d.line([cx + r * math.cos(t), cy + r * math.sin(t), cx + (r - 12 * k) * math.cos(t), cy + (r - 12 * k) * math.sin(t)], fill=col, width=3 * k)
    t = math.radians(a0 + (a1 - a0) * red)
    d.line([cx + (r + 4 * k) * math.cos(t), cy + (r + 4 * k) * math.sin(t), cx + (r - 18 * k) * math.cos(t), cy + (r - 18 * k) * math.sin(t)], fill=RED, width=6 * k)
    t = math.radians(av)
    d.line([cx, cy, cx + (r - 4 * k) * math.cos(t), cy + (r - 4 * k) * math.sin(t)], fill=WHITE, width=5 * k)
    d.rectangle([cx + 4 * k, cy - r - 4 * k, cx + r + 22 * k, cy - r + 30 * k], fill="#05060a", outline=WHITE, width=3 * k)
    ctext(d, (cx + r + 16 * k, cy - r + 13 * k), readout, font("arialbd.ttf", 26 * k), WHITE, anchor="rm")
    if label:
        ctext(d, (cx, cy + r * 0.62), label, font("arialbd.ttf", 18 * k), CYAN)


def eicas_upper(name):
    S = 512
    im, d, k = canvas(S, S, "#05060a")
    dial(d, k, 92 * k, 120 * k, 62 * k, 21.6, 110, "N1", "21.6")
    dial(d, k, 252 * k, 120 * k, 62 * k, 19.8, 110, "", "19.8")
    dial(d, k, 92 * k, 300 * k, 62 * k, 312, 1000, "EGT", "312")
    dial(d, k, 252 * k, 300 * k, 62 * k, 298, 1000, "", "298")
    f = font("arialbd.ttf", 24 * k)
    msgs = [("ENG OUT L", RED), ("ENG OUT R", RED), ("FUEL PRESS L", AMBER), ("FUEL PRESS R", AMBER), ("FUEL CONFIG", AMBER)]
    for i, (s, col) in enumerate(msgs):
        ctext(d, (348 * k, (40 + i * 34) * k), s, f, col, anchor="lm")
    d.line([340 * k, 220 * k, 505 * k, 220 * k], fill="#4a5060", width=2 * k)
    fs = font("arialbd.ttf", 20 * k)
    ctext(d, (348 * k, 250 * k), "TAT -32c", fs, WHITE, anchor="lm")
    ctext(d, (348 * k, 286 * k), "FLAPS UP", fs, WHITE, anchor="lm")
    # gear/flaps small tape
    d.rectangle([350 * k, 320 * k, 372 * k, 470 * k], outline=WHITE, width=3 * k)
    d.rectangle([353 * k, 455 * k, 369 * k, 467 * k], fill=WHITE)
    ctext(d, (400 * k, 400 * k), "TOTAL\nFUEL", fs, CYAN, anchor="lm")
    d.rectangle([390 * k, 446 * k, 500 * k, 482 * k], outline=AMBER, width=3 * k)
    ctext(d, (445 * k, 465 * k), "- - - -", f, AMBER)
    save(im, name, S, S)


def eicas_lower(name):
    S = 512
    im, d, k = canvas(S, S, "#05060a")
    dial(d, k, 92 * k, 110 * k, 58 * k, 38, 110, "N2", "38.2")
    dial(d, k, 252 * k, 110 * k, 58 * k, 35, 110, "", "35.0")
    fs = font("arialbd.ttf", 20 * k)
    f = font("arialbd.ttf", 26 * k)
    ctext(d, (172 * k, 228 * k), "FF", fs, CYAN)
    for x, v in ((92, "0.4"), (252, "0.3")):
        d.rectangle([(x - 40) * k, 210 * k, (x + 40) * k, 246 * k], outline=WHITE, width=3 * k)
        ctext(d, (x * k, 228 * k), v, f, WHITE)
    # oil tapes
    for i, (lab, hs) in enumerate((("OIL P", (0.25, 0.22)), ("OIL T", (0.55, 0.5)), ("OIL Q", (0.7, 0.7)), ("VIB", (0.6, 0.15)))):
        x0 = 360 * k + i * 0
        y = (60 + i * 64) * k
        ctext(d, (365 * k, y), lab, fs, CYAN, anchor="lm")
        for j, h in enumerate(hs):
            xx = (440 + j * 34) * k
            d.rectangle([xx, y - 24 * k, xx + 18 * k, y + 24 * k], outline=WHITE, width=2 * k)
            d.rectangle([xx + 4 * k, y + 24 * k - 48 * k * h, xx + 14 * k, y + 22 * k], fill=AMBER if h < 0.3 else WHITE)
    # fuel quantity: BLANK (the 1983 fault): dashes in amber boxes
    ctext(d, (256 * k, 330 * k), "FUEL QTY  KG", fs, CYAN)
    for x, lab in ((90, "L"), (256, "C"), (422, "R")):
        d.rectangle([(x - 70) * k, 360 * k, (x + 70) * k, 410 * k], outline=AMBER, width=4 * k)
        ctext(d, (x * k, 385 * k), "- - - -", f, AMBER)
        ctext(d, (x * k, 432 * k), lab, fs, WHITE)
    ctext(d, (256 * k, 480 * k), "FQIS FAIL", f, AMBER)
    save(im, name, S, S)


def crt_off(name):
    S = 256
    im, d, k = canvas(S, S, "#0b0f1a")
    for i in range(S * k):  # vertical gradient
        t = i / (S * k)
        d.line([0, i, S * k, i], fill=(int(12 + 14 * t), int(16 + 16 * t), int(28 + 22 * t)))
    sheen = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.polygon([(30 * k, 0), (110 * k, 0), (20 * k, 256 * k), (-60 * k, 256 * k)], fill=(150, 170, 220, 46))
    sd.polygon([(130 * k, 0), (150 * k, 0), (60 * k, 256 * k), (40 * k, 256 * k)], fill=(150, 170, 220, 30))
    sd.rounded_rectangle([150 * k, 26 * k, 236 * k, 70 * k], 10 * k, fill=(255, 180, 120, 36))  # window reflection
    sheen = sheen.filter(ImageFilter.GaussianBlur(5 * k))
    im.alpha_composite(sheen)
    save(im, name, S, S)


# ------------------------------------------------------------------ round standby gauges
def gauge(name, kind):
    S = 256
    im, d, k = canvas(S, S, "#16171c")
    cx = cy = 128 * k
    R = 120 * k
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill="#0d0e12")
    f = font("arialbd.ttf", 22 * k)
    fs = font("arialbd.ttf", 14 * k)
    if kind in ("asi", "alt", "vsi", "clock", "flaps", "brake"):
        n = {"asi": 40, "alt": 50, "vsi": 30, "clock": 60, "flaps": 20, "brake": 20}[kind]
        for i in range(n):
            t = math.radians(-90 + 360 * i / n) if kind != "flaps" and kind != "brake" else math.radians(140 + 260 * i / n)
            big = i % (5 if kind != "vsi" else 5) == 0
            l = (18 if big else 9) * k
            d.line([cx + (R - 6 * k) * math.cos(t), cy + (R - 6 * k) * math.sin(t), cx + (R - 6 * k - l) * math.cos(t), cy + (R - 6 * k - l) * math.sin(t)],
                   fill=WHITE, width=(4 if big else 2) * k)
        labels = {"asi": ["60", "100", "150", "200", "250", "300", "350", "400"], "alt": [str(i) for i in range(10)],
                  "vsi": ["0", "1", "2", "4", "6", "4", "2", "1"], "clock": ["12", "3", "6", "9"], "flaps": ["UP", "5", "15", "25", "30"],
                  "brake": ["0", "1", "2", "3", "4"]}[kind]
        for i, s in enumerate(labels):
            if kind in ("flaps", "brake"):
                t = math.radians(140 + 260 * i / (len(labels) - 1))
            else:
                t = math.radians(-90 + 360 * i / len(labels))
            ctext(d, (cx + (R - 48 * k) * math.cos(t), cy + (R - 48 * k) * math.sin(t)), s, f, WHITE)
        if kind == "asi":
            d.arc([cx - R + 10 * k, cy - R + 10 * k, cx + R - 10 * k, cy + R - 10 * k], 140, 170, fill=RED, width=8 * k)
            ctext(d, (cx, cy + 40 * k), "KNOTS", fs, WHITE)
            needle = 210
        elif kind == "alt":
            d.rectangle([cx - 46 * k, cy + 26 * k, cx + 46 * k, cy + 58 * k], fill="#000", outline="#777", width=2 * k)
            ctext(d, (cx, cy + 42 * k), "41000", font("consolab.ttf", 24 * k), WHITE)
            needle = 0
        elif kind == "vsi":
            ctext(d, (cx - 30 * k, cy), "UP", fs, WHITE)
            ctext(d, (cx - 30 * k, cy + 30 * k), "DN", fs, WHITE)
            needle = 182
        elif kind == "clock":
            d.line([cx, cy, cx + 50 * k * math.cos(math.radians(-30)), cy + 50 * k * math.sin(math.radians(-30))], fill=WHITE, width=8 * k)
            needle = 120
        elif kind == "flaps":
            ctext(d, (cx, cy + 50 * k), "FLAPS", fs, WHITE)
            needle = 140
        else:
            ctext(d, (cx, cy + 50 * k), "BRAKE", fs, WHITE)
            needle = 300
        t = math.radians(needle - 90 if kind not in ("flaps", "brake") else needle)
        d.polygon([(cx + (R - 20 * k) * math.cos(t), cy + (R - 20 * k) * math.sin(t)),
                   (cx + 7 * k * math.cos(t + 1.57), cy + 7 * k * math.sin(t + 1.57)),
                   (cx - 20 * k * math.cos(t), cy - 20 * k * math.sin(t)),
                   (cx + 7 * k * math.cos(t - 1.57), cy + 7 * k * math.sin(t - 1.57))], fill=WHITE)
        d.ellipse([cx - 10 * k, cy - 10 * k, cx + 10 * k, cy + 10 * k], fill="#333", outline=WHITE, width=2 * k)
    elif kind == "att":
        sub = Image.new("RGBA", (S * k, S * k), "#1f86e6")
        sd = ImageDraw.Draw(sub)
        sd.rectangle([0, cy + 10 * k, S * k, S * k], fill="#a8642e")
        sd.line([0, cy + 10 * k, S * k, cy + 10 * k], fill=WHITE, width=4 * k)
        for deg in (-20, -10, 10, 20):
            y = cy + 10 * k - deg * 4 * k
            sd.line([cx - 30 * k, y, cx + 30 * k, y], fill=WHITE, width=3 * k)
        sub = sub.rotate(-5, resample=Image.BICUBIC)
        mask = Image.new("L", sub.size, 0)
        ImageDraw.Draw(mask).ellipse([cx - R + 14 * k, cy - R + 14 * k, cx + R - 14 * k, cy + R - 14 * k], fill=255)
        im.paste(sub, (0, 0), mask)
        d.polygon([(cx - 70 * k, cy), (cx - 20 * k, cy), (cx, cy + 16 * k), (cx + 20 * k, cy), (cx + 70 * k, cy), (cx + 70 * k, cy + 8 * k),
                   (cx + 24 * k, cy + 8 * k), (cx, cy + 26 * k), (cx - 24 * k, cy + 8 * k), (cx - 70 * k, cy + 8 * k)], fill="#ffcf2e", outline="#111", width=2 * k)
    # glass sheen
    sheen = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sheen).ellipse([cx - R * 0.8, cy - R * 0.95, cx + R * 0.3, cy - R * 0.2], fill=(255, 255, 255, 34))
    im.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(8 * k)))
    d = ImageDraw.Draw(im)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline="#4a4c55", width=6 * k)
    save(im, name, S, S)


# ------------------------------------------------------------------ panels
LABELS = ["FUEL", "HYD", "ELEC", "APU", "BAT", "BUS", "PACK", "BLEED", "ANTI ICE", "WIPER", "PITOT", "IRS", "AC", "DC",
          "XFEED", "PUMP", "VALVE", "ENG", "WING", "NAV", "BEACON", "STROBE", "LOGO", "DOME", "STORM", "TEST", "OFF", "ON",
          "AUTO", "MAN", "ALT", "NORM", "L", "R", "C", "FWD", "AFT", "GEN", "EMER", "RAM AIR", "TRIM", "YAW DAMP"]


def panel(name, base, S=1024, grid=(4, 4), seed=1, labels=True, flow=False):
    im, d, k = canvas(S, S, base)
    rnd = random.Random(seed)
    gx, gy = grid
    dark = tuple(max(0, int(int(base[i:i + 2], 16) * 0.55)) for i in (1, 3, 5))
    light = tuple(min(255, int(int(base[i:i + 2], 16) * 1.12) + 6) for i in (1, 3, 5))
    cw, ch = S * k / gx, S * k / gy
    fl = font("ARIALNB.TTF", 15 * k)
    for i in range(gx):
        for j in range(gy):
            x0, y0 = i * cw, j * ch
            # sub-panel: groove + highlight edge
            d.rectangle([x0 + 3 * k, y0 + 3 * k, x0 + cw - 3 * k, y0 + ch - 3 * k], outline=dark, width=4 * k)
            d.line([x0 + 7 * k, y0 + 7 * k, x0 + cw - 7 * k, y0 + 7 * k], fill=light, width=2 * k)
            for fx, fy in ((14, 14), (cw / k - 14, 14), (14, ch / k - 14), (cw / k - 14, ch / k - 14)):  # dzus fasteners
                X, Y = x0 + fx * k, y0 + fy * k
                d.ellipse([X - 6 * k, Y - 6 * k, X + 6 * k, Y + 6 * k], fill=light, outline=dark, width=2 * k)
                d.line([X - 4 * k, Y, X + 4 * k, Y], fill=dark, width=2 * k)
            if labels:
                for n in range(rnd.randint(3, 7)):
                    X = x0 + rnd.uniform(30, cw / k - 60) * k
                    Y = y0 + rnd.uniform(30, ch / k - 30) * k
                    ctext(d, (X, Y), rnd.choice(LABELS), fl, "#f2f0e8", anchor="lm")
                if flow:  # white system flow lines
                    pts = [(x0 + rnd.uniform(30, cw / k - 30) * k, y0 + rnd.uniform(30, ch / k - 30) * k) for _ in range(3)]
                    p = pts[0]
                    for q in pts[1:]:
                        d.line([p, (q[0], p[1]), q], fill="#e8e6dc", width=3 * k)
                        p = q
    save(im, name, S, S)


def cb_panel(name):
    S = 512
    base = "#5d6f83"
    im, d, k = canvas(S, S, base)
    rnd = random.Random(3)
    fl = font("ARIALNB.TTF", 9 * k)
    cols, rows = 11, 12
    for j in range(rows):
        if j % 4 == 0:
            d.rectangle([6 * k, (j * 42 + 4) * k, 506 * k, (j * 42 + 8) * k], fill="#e9e6dc")
            ctext(d, (12 * k, (j * 42 + 16) * k), rnd.choice(LABELS) + " BUS", fl, "#f4f2ea", anchor="lm")
        for i in range(cols):
            if rnd.random() < 0.08:
                continue
            x, y = (28 + i * 45) * k, (j * 42 + 30) * k
            r = 11 * k
            popped = rnd.random() < 0.05
            d.ellipse([x - r - 3 * k, y - r - 3 * k, x + r + 3 * k, y + r + 3 * k], fill="#30353f")
            d.ellipse([x - r, y - r, x + r, y + r], fill="#f0eee6" if popped else "#16171b")
            d.ellipse([x - r * 0.45, y - r * 0.45, x + r * 0.45, y + r * 0.45], fill="#2c2d33")
            ctext(d, (x, y + r + 7 * k), rnd.choice(LABELS)[:6], fl, "#f2f0e8")
    save(im, name, S, S)


def mcp(name):
    W, H = 1024, 128
    im, d, k = canvas(W, H, "#3a414d")
    f7 = font("consolab.ttf", 44 * k)
    fl = font("arialbd.ttf", 15 * k)
    d.rectangle([0, 0, W * k, 6 * k], fill="#2a3039")
    for x, lab, val in ((150, "IAS/MACH", ".80"), (420, "HDG", "275"), (640, "V/S", "    "), (840, "ALTITUDE", "41000")):
        w = 34 * len(val) * k / 1.4 + 30 * k
        d.rectangle([x * k - w / 2, 34 * k, x * k + w / 2, 88 * k], fill="#07080b", outline="#1c1f25", width=3 * k)
        ctext(d, (x * k, 62 * k), val, f7, AMBER)
        ctext(d, (x * k, 18 * k), lab, fl, "#f2f0e8")
        d.ellipse([x * k + w / 2 + 14 * k, 40 * k, x * k + w / 2 + 56 * k, 82 * k], fill="#1a1b20", outline="#9aa0aa", width=3 * k)
    for i, lab in enumerate(("A/T", "N1", "SPD", "VNAV", "LNAV", "HDG", "ALT", "APP")):
        x = (30 + i * 125) * k
        d.rectangle([x, 98 * k, x + 70 * k, 122 * k], fill="#20242b", outline="#121418", width=2 * k)
        d.rectangle([x + 6 * k, 101 * k, x + 64 * k, 106 * k], fill=GREEN if i in (0, 3, 4) else "#3b3f47")
        ctext(d, (x + 35 * k, 115 * k), lab, fl, "#f2f0e8")
    save(im, name, W, H)


def lining(name, base="#e3d6bd", S=512, seams=2):
    im, d, k = canvas(S, S, base)
    rnd = random.Random(5)
    dk = tuple(int(int(base[i:i + 2], 16) * 0.8) for i in (1, 3, 5))
    for i in range(1500):
        x, y = rnd.uniform(0, S) * k, rnd.uniform(0, S) * k
        c = rnd.choice([0.96, 1.03])
        col = tuple(min(255, int(int(base[j:j + 2], 16) * c)) for j in (1, 3, 5))
        d.ellipse([x, y, x + 3 * k, y + 3 * k], fill=col)
    for s in range(seams):
        x = (s + 0.5) * S * k / seams
        d.line([x, 0, x, S * k], fill=dk, width=3 * k)
        for y in range(10, S, 32):
            d.ellipse([x + 8 * k, y * k, x + 13 * k, y * k + 5 * k], fill=dk)
    d.line([0, S * k * 0.5, S * k, S * k * 0.5], fill=dk, width=2 * k)
    save(im, name, S, S)


def leather(name, base=(150, 78, 40)):
    S = 512
    im, d, k = canvas(S, S, base)
    n = 4
    cw = S * k / n
    hi = tuple(min(255, int(c * 1.22)) for c in base)
    lo = tuple(int(c * 0.62) for c in base)
    for i in range(n):
        for j in range(n):
            x0, y0 = i * cw, j * cw
            g = Image.new("RGBA", (int(cw), int(cw)), (0, 0, 0, 0))
            gd = ImageDraw.Draw(g)
            gd.ellipse([cw * 0.12, cw * 0.1, cw * 0.78, cw * 0.62], fill=hi + (120,))
            g = g.filter(ImageFilter.GaussianBlur(cw * 0.12))
            im.alpha_composite(g, (int(x0), int(y0)))
    d = ImageDraw.Draw(im)
    for i in range(n + 1):
        d.line([i * cw, 0, i * cw, S * k], fill=lo, width=6 * k)
        d.line([0, i * cw, S * k, i * cw], fill=lo, width=6 * k)
    stitch = (232, 196, 140)
    for i in range(n + 1):
        for t in range(0, S * k, 18 * k):
            d.line([i * cw + 9 * k, t, i * cw + 9 * k, t + 9 * k], fill=stitch, width=2 * k)
            d.line([t, i * cw + 9 * k, t + 9 * k, i * cw + 9 * k], fill=stitch, width=2 * k)
    for i in range(n):
        for j in range(n):
            x, y = (i + 1) * cw, (j + 1) * cw
            d.ellipse([x - 7 * k, y - 7 * k, x + 7 * k, y + 7 * k], fill=lo)
    save(im, name, S, S)


def skin(name):
    S = 1024
    im, d, k = canvas(S, S, "#f3f0ea")
    for x in range(0, S, 256):
        d.line([x * k, 0, x * k, S * k], fill="#c9c6c4", width=3 * k)
        for y in range(8, S, 22):
            d.ellipse([(x + 8) * k, y * k, (x + 12) * k, (y + 4) * k], fill="#d4d1cd")
    for y in range(0, S, 341):
        d.line([0, y * k, S * k, y * k], fill="#c9c6c4", width=3 * k)
    save(im, name, S, S)


def carpet(name):
    S = 512
    base = (52, 62, 104)
    im, d, k = canvas(S, S, base)
    rnd = random.Random(9)
    for i in range(5000):
        x, y = rnd.uniform(0, S) * k, rnd.uniform(0, S) * k
        c = rnd.choice([(44, 52, 90), (64, 74, 120), (58, 66, 110)])
        d.rectangle([x, y, x + 3 * k, y + 3 * k], fill=c)
    for i in range(0, S, 64):
        for j in range(0, S, 64):
            d.ellipse([(i + 26) * k, (j + 26) * k, (i + 38) * k, (j + 38) * k], fill=(92, 98, 150))
    save(im, name, S, S)


def cloudsea(name):
    S = 1024
    im, d, k = canvas(S, S, "#6a5aa0")
    rnd = random.Random(11)
    puffs = [(rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(30, 90)) for _ in range(140)]
    puffs.sort(key=lambda p: p[1])
    for (x, y, r) in puffs:
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                X, Y, R = (x + ox) * k, (y + oy) * k, r * k
                d.ellipse([X - R, Y - R * 0.7, X + R, Y + R * 0.7], fill="#9a84c4")
                d.ellipse([X - R * 0.9, Y - R * 0.78, X + R * 0.8, Y + R * 0.38], fill="#e9a08f")
                d.ellipse([X - R * 0.7, Y - R * 0.74, X + R * 0.45, Y - R * 0.05], fill="#ffd0a2")
    save(im, name, S, S)


def runway(name, crash=False):
    W, H = 2048, 1024
    im, d, k = canvas(W, H, "#3f78f6")
    hz = 430 * k
    for i in range(hz):
        t = i / hz
        c = (int(0x3a + (0xa9 - 0x3a) * t ** 1.6), int(0x6c + (0xc8 - 0x6c) * t ** 1.6), int(0xd8 + (0xf2 - 0xd8) * t ** 1.6))
        d.line([0, i, W * k, i], fill=c)
    rnd = random.Random(4)
    for _ in range(9):  # cartoon clouds
        x, y, s = rnd.uniform(0, W) * k, rnd.uniform(60, 320) * k, rnd.uniform(40, 90) * k
        for j in range(5):
            ox, oy, r = (j - 2) * s * 0.55, -abs(j - 2) * s * 0.12 * -1 - (s * 0.25 if j == 2 else 0), s * (0.55 if j in (0, 4) else 0.8)
            d.ellipse([x + ox - r, y + oy - r * 0.8, x + ox + r, y + oy + r * 0.8], fill="#ffffff", outline="#9bb3e0", width=3 * k)
    # fields
    d.rectangle([0, hz, W * k, H * k], fill="#6fae3c")
    vx = W * k / 2
    cols = ["#7cbc44", "#9cc251", "#5f9e36", "#c8b45a", "#86b84a"]
    for i in range(-14, 15):
        x0 = vx + i * 160 * k
        d.polygon([(vx + i * 22 * k, hz), (vx + (i + 1) * 22 * k, hz), (vx + (i + 1) * 300 * k, H * k), (vx + i * 300 * k, H * k)], fill=cols[(i * 7) % 5])
    for j, y in enumerate((450, 480, 530, 610, 740, 920)):
        d.line([0, y * k, W * k, y * k], fill="#4f8a2c", width=(2 + j) * k)
    # distant trees / hangars on the horizon
    for i in range(70):
        x = rnd.uniform(0, W) * k
        r = rnd.uniform(6, 16) * k
        d.ellipse([x - r, hz - r * 1.6, x + r, hz + r * 0.2], fill="#3f7a35")
    for x in (560, 640, 1500):
        d.rectangle([x * k, hz - 26 * k, (x + 70) * k, hz], fill="#d8d2c4", outline="#555", width=2 * k)
    # runway in perspective
    def rx(y, s):  # half width at screen y
        return s * (y - hz) / (H * k - hz)
    top, bot = hz + 14 * k, H * k
    hw_b, hw_t = 520 * k, 10 * k
    d.polygon([(vx - hw_t, top), (vx + hw_t, top), (vx + hw_b, bot), (vx - hw_b, bot)], fill="#4c4f58")
    for s in (-1, 1):
        d.line([(vx + s * hw_t, top), (vx + s * hw_b, bot)], fill="#f6f4ee", width=5 * k)
    y = top
    n = 0
    while y < bot:  # centreline dashes, spaced in perspective
        t = (y - top) / (bot - top)
        L = (6 + 70 * t * t) * k
        if n % 2 == 0:
            w = (1 + 10 * t) * k
            d.rectangle([vx - w, y, vx + w, y + L], fill="#f6f4ee")
        y += L
        n += 1
    for i in range(-6, 7):  # threshold bars near the bottom
        if i == 0:
            continue
        t0, t1 = 0.78, 0.9
        ya, yb = top + (bot - top) * t0, top + (bot - top) * t1
        xa = vx + i * (hw_t + (hw_b - hw_t) * t0) / 7.5
        xb = vx + i * (hw_t + (hw_b - hw_t) * t1) / 7.5
        w0, w1 = 12 * k * t0, 12 * k * t1
        d.polygon([(xa - w0, ya), (xa + w0, ya), (xb + w1, yb), (xb - w1, yb)], fill="#f6f4ee")
    for i in range(10):  # approach lights
        y = top - 0 + (i + 1) * 1.2 * k
    if crash:
        red = Image.new("RGBA", im.size, (255, 30, 20, 120))
        im.alpha_composite(red)
        im = im.rotate(-24, resample=Image.BICUBIC, fillcolor="#6fae3c")
        d = ImageDraw.Draw(im)
    save(im, name, W, H)


def ios(name, crash=False):
    W, H = 512, 384
    im, d, k = canvas(W, H, "#0a1a2e")
    f = font("arialbd.ttf", 20 * k)
    fs = font("consolab.ttf", 16 * k)
    if not crash:
        d.rectangle([0, 0, W * k, 34 * k], fill="#1f3c66")
        ctext(d, (14 * k, 17 * k), "SIM 2  -  APPROACH  RWY 32L", f, "#f2f0e8", anchor="lm")
        for x in range(0, W, 32):
            d.line([x * k, 34 * k, x * k, H * k], fill="#14304f", width=1 * k)
        for y in range(34, H, 32):
            d.line([0, y * k, W * k, y * k], fill="#14304f", width=1 * k)
        d.polygon([(250 * k, 300 * k), (262 * k, 300 * k), (300 * k, 80 * k), (290 * k, 80 * k)], fill="#c9cdd6")
        d.line([(120 * k, 360 * k), (180 * k, 300 * k), (230 * k, 260 * k), (262 * k, 230 * k)], fill="#4cf06a", width=4 * k)
        d.polygon([(262 * k, 218 * k), (272 * k, 240 * k), (252 * k, 240 * k)], fill="#ffd23a")
        for i, s in enumerate(("IAS 145", "ALT 1200", "V/S -800", "FUEL  OK", "WIND 270/12")):
            ctext(d, (360 * k, (70 + i * 30) * k), s, fs, "#9fe8ff", anchor="lm")
        for i, s in enumerate(("FREEZE", "RESET", "MALF", "WX")):
            d.rectangle([(16 + i * 92) * k, 340 * k, (96 + i * 92) * k, 372 * k], fill="#244a7a", outline="#6fa0d8", width=2 * k)
            ctext(d, ((56 + i * 92) * k, 356 * k), s, fs, "#f2f0e8")
    else:
        d.rectangle([0, 0, W * k, H * k], fill="#c41f1f")
        for i in range(0, W * 2, 60):
            d.polygon([(i * k, 0), ((i + 30) * k, 0), ((i - 130) * k, H * k), ((i - 160) * k, H * k)], fill="#a81616")
        ctext(d, (W * k / 2, H * k / 2 - 20 * k), "CRASH", font("impact.ttf", 120 * k), "#fff4e6")
        ctext(d, (W * k / 2, H * k / 2 + 70 * k), "SIM FROZEN", font("arialbd.ttf", 30 * k), "#fff4e6")
    save(im, name, W, H)


def slip(name):
    W, H = 256, 340
    im, d, k = canvas(W, H, "#fbf7ea")
    for y in range(60, H, 28):
        d.line([10 * k, y * k, 246 * k, y * k], fill="#b9cbe6", width=2 * k)
    d.line([40 * k, 0, 40 * k, H * k], fill="#e89a9a", width=2 * k)
    fh = font("segoepr.ttf", 30 * k)
    ink = "#243a8e"
    ctext(d, (60 * k, 82 * k), "7682 L", fh, ink, anchor="lm")
    ctext(d, (52 * k, 138 * k), "x 1.77", fh, ink, anchor="lm")
    d.line([50 * k, 166 * k, 220 * k, 166 * k], fill=ink, width=3 * k)
    ctext(d, (60 * k, 196 * k), "13597", fh, ink, anchor="lm")
    ctext(d, (52 * k, 262 * k), "22300 kg", font("segoeprb.ttf", 30 * k), "#c4271f", anchor="lm")
    d.ellipse([40 * k, 236 * k, 230 * k, 292 * k], outline="#c4271f", width=3 * k)
    save(im, name, W, H)


def glow(name):
    S = 256
    im = Image.new("L", (S, S), 0)
    px = im.load()
    for y in range(S):
        for x in range(S):
            r = math.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5) / (S / 2)
            v = max(0.0, 1 - r) ** 2.2
            px[x, y] = int(255 * v)
    Image.merge("RGBA", (Image.new("L", (S, S), 255),) * 3 + (im,)).save(os.path.join(OUT, name))


def binders(name):
    W, H = 512, 256
    im, d, k = canvas(W, H, "#2a2a30")
    rnd = random.Random(2)
    cols = ["#c8323a", "#2f5fb8", "#f0c419", "#3a9a4a", "#efeae0", "#e0782a", "#6a3fa0", "#1d2b55"]
    x = 0
    fl = font("ARIALNB.TTF", 14 * k)
    while x < W:
        w = rnd.randint(24, 46)
        c = rnd.choice(cols)
        h = rnd.randint(200, 250)
        d.rectangle([x * k, (H - h) * k, (x + w - 2) * k, H * k], fill=c, outline="#16161a", width=2 * k)
        d.rectangle([(x + 4) * k, (H - h + 30) * k, (x + w - 6) * k, (H - h + 70) * k], fill="#f4f1e8")
        d.ellipse([(x + w / 2 - 6) * k, (H - 40) * k, (x + w / 2 + 6) * k, (H - 28) * k], fill="#16161a")
        x += w
    save(im, name, W, H)


def placard(name, text, bg, fg, W=256, H=96):
    im, d, k = canvas(W, H, bg)
    d.rectangle([4 * k, 4 * k, (W - 4) * k, (H - 4) * k], outline=fg, width=4 * k)
    ctext(d, (W * k / 2, H * k / 2), text, font("arialbd.ttf", int(H * 0.36) * k), fg)
    save(im, name, W, H)


def hazard(name):
    W, H = 512, 64
    im, d, k = canvas(W, H, "#f2c418")
    for i in range(-2, 20):
        x = i * 48 * k
        d.polygon([(x, 0), (x + 24 * k, 0), (x + 24 * k + H * k, H * k), (x + H * k, H * k)], fill="#1a1a1e")
    save(im, name, W, H)


def sim_cab(name):
    S = 512
    im, d, k = canvas(S, S, "#4a505c")
    for x in range(0, S, 128):
        d.line([x * k, 0, x * k, S * k], fill="#2f343d", width=4 * k)
        for y in range(10, S, 40):
            d.ellipse([(x + 10) * k, y * k, (x + 18) * k, (y + 8) * k], fill="#6a707c")
    for y in range(0, S, 170):
        d.line([0, y * k, S * k, y * k], fill="#2f343d", width=4 * k)
    save(im, name, S, S)


if __name__ == "__main__":
    eadi("adi_on.png")
    ehsi("hsi_on.png")
    eicas_upper("eicas_up_on.png")
    eicas_lower("eicas_lo_on.png")
    crt_off("crt_off.png")
    for kind in ("asi", "alt", "vsi", "clock", "att", "flaps", "brake"):
        gauge(f"g_{kind}.png", kind)
    panel("panel.png", "#5a6e86", grid=(4, 4), seed=1)
    panel("overhead.png", "#5f738c", grid=(3, 5), seed=4, flow=True)
    panel("pedestal.png", "#4e6079", grid=(2, 4), seed=7)
    cb_panel("cb.png")
    mcp("mcp.png")
    lining("lining.png")
    lining("lining_dark.png", base="#b9ad98", seams=1)
    leather("leather.png")
    leather("leather_blue.png", base=(64, 82, 128))
    skin("skin.png")
    carpet("carpet.png")
    cloudsea("cloudsea.png")
    runway("runway.png")
    runway("runway_crash.png", crash=True)
    ios("ios_on.png")
    ios("ios_crash.png", crash=True)
    slip("slip.png")
    glow("glow.png")
    binders("binders.png")
    placard("plac_door.png", "FLIGHT DECK", "#f2c418", "#1a1a1e")
    placard("plac_ext.png", "FIRE EXT", "#c4271f", "#fff4e6")
    hazard("hazard.png")
    sim_cab("simcab.png")
    print("painted", len([f for f in os.listdir(OUT) if f.endswith(".png")]), "textures in", OUT)
