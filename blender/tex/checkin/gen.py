# generates the textures of sets/checkin.py (run with system python -I)
import os
from PIL import Image, ImageDraw, ImageFont
D = os.path.dirname(os.path.abspath(__file__))
def F(s): return ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", s)
def save(im, n): im.save(os.path.join(D, n))

def disp(txt, n):
    im = Image.new("RGB", (768, 384), "#04141c"); g = ImageDraw.Draw(im)
    g.rounded_rectangle((10, 10, 757, 373), 26, outline="#0e3f4f", width=6)
    if txt:
        num, unit = txt.split()
        fn, fu = F(250), F(130)
        wn = g.textlength(num, font=fn); wu = g.textlength(unit, font=fu)
        x0 = (768 - (wn + 30 + wu)) / 2
        for r, c in ((10, "#0f6b45"), (5, "#2ee08a")):  # glow halo
            for dx in (-r, r, 0):
                for dy in (-r, r, 0):
                    g.text((x0 + dx, 40 + dy), num, font=fn, fill=c)
        g.text((x0, 40), num, font=fn, fill="#c9ffe4")
        g.text((x0 + wn + 30, 160), unit, font=fu, fill="#ffd45a")
    else:
        for i in range(0, 768, 12):  # dim idle dots
            g.line((60 + i, 192, 66 + i, 192), fill="#0a3342", width=4)
    save(im, n)
disp("", "disp0.png"); disp("23 kg", "disp1.png"); disp("50 lb", "disp2.png")

# departures board
im = Image.new("RGB", (1024, 512), "#06122e"); g = ImageDraw.Draw(im)
g.rectangle((0, 0, 1024, 76), fill="#ffc21a"); g.text((30, 8), "DEPARTURES", font=F(58), fill="#06122e")
g.text((700, 20), "12:40", font=F(44), fill="#06122e")
rows = [("FL 101", "LONDON", "12:55", "B4", "#7dffb0"), ("FL 238", "TORONTO", "13:10", "A2", "#ffffff"),
        ("FL 412", "MADRID", "13:25", "C7", "#ffffff"), ("FL 077", "TOKYO", "13:40", "D1", "#ff8a5a"),
        ("FL 560", "CAIRO", "14:05", "B9", "#ffffff"), ("FL 319", "LISBON", "14:20", "A5", "#7dffb0")]
for i, (a, b, c, d, col) in enumerate(rows):
    y = 92 + i * 69
    if i % 2 == 0: g.rectangle((0, y - 6, 1024, y + 58), fill="#0b1c47")
    g.text((24, y), a, font=F(46), fill="#ffd45a"); g.text((230, y), b, font=F(46), fill=col)
    g.text((640, y), c, font=F(46), fill=col); g.text((880, y), d, font=F(46), fill="#6fd0ff")
save(im, "board.png")

# logo panel (generic airline-neutral)
im = Image.new("RGB", (1024, 256), "#1747c9"); g = ImageDraw.Draw(im)
g.rectangle((0, 214, 1024, 256), fill="#ff4b3a"); g.rectangle((0, 200, 1024, 214), fill="#ffffff")
g.ellipse((40, 36, 176, 172), fill="#ffffff"); g.polygon([(60, 130), (150, 60), (130, 100), (160, 104), (90, 150)], fill="#ff4b3a")
g.text((210, 34), "CHECK-IN", font=F(120), fill="#ffffff")
g.text((214, 150), "BAGGAGE DROP  -  ECONOMY  -  PRIORITY", font=F(34), fill="#bfe0ff")
save(im, "logo.png")

# pictogram signs
def sign(n, draw, bg="#1747c9"):
    im = Image.new("RGB", (256, 256), bg); g = ImageDraw.Draw(im)
    g.rounded_rectangle((8, 8, 248, 248), 30, outline="#ffffff", width=6); draw(g); save(im, n)
sign("sign_plane.png", lambda g: g.polygon([(128, 40), (146, 110), (216, 150), (216, 170), (146, 150), (140, 205), (166, 224), (166, 236), (128, 226), (90, 236), (90, 224), (116, 205), (110, 150), (40, 170), (40, 150), (110, 110)], fill="#fff"))
def bag(g):
    g.rounded_rectangle((60, 90, 196, 206), 18, fill="#ffd21a"); g.rounded_rectangle((100, 52, 156, 96), 10, outline="#ffd21a", width=12)
    g.rectangle((60, 130, 196, 144), fill="#1747c9")
sign("sign_bag.png", bag, "#d6322a")
sign("sign_arrow.png", lambda g: (g.rectangle((60, 110, 160, 146), fill="#fff"), g.polygon([(150, 60), (216, 128), (150, 196)], fill="#fff")), "#16a05a")
sign("sign_info.png", lambda g: (g.ellipse((108, 44, 148, 84), fill="#fff"), g.rounded_rectangle((108, 100, 148, 214), 10, fill="#fff")), "#1c8fd8")

# luggage tag
im = Image.new("RGB", (128, 256), "#ffffff"); g = ImageDraw.Draw(im)
g.rectangle((0, 70, 128, 120), fill="#e0261b"); g.ellipse((52, 12, 76, 36), outline="#999", width=5)
for i in range(6): g.rectangle((16, 140 + i * 16, 112 - (i % 2) * 30, 148 + i * 16), fill="#222")
save(im, "tag.png")

# floor: cream tiles with fine grid and a blue guiding band
im = Image.new("RGB", (512, 512), "#e8eef7"); g = ImageDraw.Draw(im)
for i in range(0, 512, 128):
    g.line((i, 0, i, 512), fill="#b7c6de", width=3); g.line((0, i, 512, i), fill="#b7c6de", width=3)
for ix in range(4):
    for iy in range(4):
        if (ix + iy) % 2 == 0: g.rectangle((ix * 128 + 3, iy * 128 + 3, ix * 128 + 125, iy * 128 + 125), fill="#dde7f5")
save(im, "floor.png")
