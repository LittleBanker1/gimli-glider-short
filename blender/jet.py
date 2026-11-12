# Jet (767-200 proportions, generic early-80s livery). Nose toward -Y, up +Z, origin at fuselage centreline mid-length.
# build(ctx) -> handle, pose(handle, jet, t).  Textures are painted with numpy+Pillow into tex/jet (see gen_all()).
import os
import sys
import math
import subprocess

try:
    import bpy
    import bmesh
    from mathutils import Vector, Matrix
except ImportError:  # texture generation runs under plain python
    bpy = None
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TEXD = os.path.join(HERE, "tex", "jet")
PY = r"C:\Users\plamb\AppData\Local\Programs\Python\Python312\python.exe"
L0, L1 = -24.2, 24.3
FL = L1 - L0
NOSE_L = 8.5


# ============================================================ planform functions (numpy friendly)
def wing_LE(x): return -5.5 + (x - 1.6) * 0.66
def wing_TE(x): return np.where(x < 5.0, 4.4, 4.4 + (x - 5.0) * (6.8 / 18.8))
def stab_LE(x): return 16.8 + (x - 0.5) * 0.625
def stab_TE(x): return 22.4 + (x - 0.5) * (1.5 / 8.8)
def wing_z(x): return -1.05 + (x - 1.6) * 0.105
def stab_z(x): return 0.55 + (x - 0.5) * 0.1228


WING = dict(W=2048, H=1536, xmax=24.0, ymin=-5.6, ymax=11.4, LE=wing_LE, TE=wing_TE, xt=23.8,
            lines=[(0.13, 3.5, 22.8), (0.70, 2.8, 12.4), (0.70, 12.7, 17.0), (0.80, 17.4, 22.8), (0.60, 4.4, 17.2), (0.90, 3.0, 12.4)],
            ribs=[(12.55, 0.70, 1.0), (17.2, 0.70, 1.0), (17.2, 0.6, 0.7)] + [(x, 0.60, 0.70) for x in (6.3, 8.2, 10.1, 12.0, 13.9, 15.8)]
            + [(x, 0.0, 0.13) for x in (6, 9, 12, 15, 18, 21)])
STAB = dict(W=1024, H=832, xmax=9.4, ymin=16.5, ymax=24.2, LE=stab_LE, TE=stab_TE, xt=9.3,
            lines=[(0.68, 0.8, 9.0), (0.14, 0.8, 9.0)], ribs=[(x, 0.68, 1.0) for x in (3.0, 6.0)])


def P(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)


def dark(img, mask, k): img[mask] = (img[mask].astype(np.float32) * k).astype(np.uint8)


def gen_fuse(path):
    from PIL import Image, ImageFilter
    W, H = 4096, 2048
    u = (np.arange(W) + .5) / W; v = 1 - (np.arange(H) + .5) / H
    U, V = np.meshgrid(u, v)
    Y = U * FL + L0
    th = V * 2 * np.pi
    a = np.where(th > np.pi, 2 * np.pi - th, th)
    S = 2.5 * (a - np.pi / 2)
    img = np.zeros((H, W, 3), np.uint8); img[:] = P("#f7f5ee")
    img[S < -0.95] = P("#b4bcc9")
    body = U > 0.052
    img[(S > 0.06) & (S < 0.47) & body] = P("#d3262a")
    img[(S > -0.13) & (S < -0.05) & body] = P("#7d1822")
    img[(S > 0.51) & (S < 0.545) & body] = P("#7d1822")
    img[U < 0.052] = P("#ecebe6")
    # panel seams + rivets
    for yy in np.arange(-22, 24, 2.2):
        c = int((yy - L0) / FL * W)
        m = np.zeros((H, W), bool); m[:, c - 1:c + 1] = True
        dark(img, m & (U > 0.05), 0.80)
    for ss in (-1.55, -0.7, 1.5, 2.2, 2.9):
        m = (np.abs(S - ss) < 0.012) & (U > 0.05); dark(img, m, 0.80)
        dark(img, (np.abs(S - ss - 0.035) < 0.01) & (((Y * 11) % 1) < 0.28) & (U > 0.05), 0.68)
    # windows (superellipse, dark blue glass)
    doors = [-17.6, -8.4, 4.6, 15.2]
    wy = [y for y in np.arange(-15.9, 14.6, 0.508) if all(abs(y - d) > 0.85 for d in doors) and not (-2.2 < y < 1.9)]
    for y in wy:
        c0, c1 = int((y - 0.4 - L0) / FL * W), int((y + 0.4 - L0) / FL * W)
        dy = Y[:, c0:c1] - y; ds = S[:, c0:c1] - 0.84
        fr = (np.abs(dy / 0.215) ** 3 + np.abs(ds / 0.27) ** 3) < 1
        gl = (np.abs(dy / 0.175) ** 3 + np.abs(ds / 0.23) ** 3) < 1
        sub = img[:, c0:c1]
        sub[fr] = P("#5b6370")
        g = np.clip(0.5 + ds / 0.46 + dy / 0.8, 0, 1)[..., None]
        glass = (P("#17254a")[None, None, :] * (1 - g) + P("#4f78b8")[None, None, :] * g * 0.55).astype(np.uint8)
        sub[gl] = glass[gl]
    # doors, overwing exits, cargo doors
    def rect_outline(y0, y1, s0, s1, w=0.04, col="#59616e", fill=None):
        c0, c1 = int((y0 - 0.1 - L0) / FL * W), int((y1 + 0.1 - L0) / FL * W)
        dy = Y[:, c0:c1]; ds = S[:, c0:c1]
        out = (dy > y0) & (dy < y1) & (ds > s0) & (ds < s1)
        inn = (dy > y0 + w) & (dy < y1 - w) & (ds > s0 + w) & (ds < s1 - w)
        sub = img[:, c0:c1]
        if fill: sub[inn] = P(fill)
        sub[out & ~inn] = P(col)
        return sub, dy, ds
    for d in doors:
        sub, dy, ds = rect_outline(d - 0.46, d + 0.46, -0.55, 1.5, 0.045, fill=None)
        c = (np.abs(dy - d) ** 2 + np.abs(ds - 1.0) ** 2) < 0.19 ** 2  # door porthole
        sub[c] = P("#59616e"); sub[(np.abs(dy - d) ** 2 + np.abs(ds - 1.0) ** 2) < 0.15 ** 2] = P("#1d2c52")
        sub[(np.abs(dy - d - 0.3) < 0.07) & (np.abs(ds - 0.35) < 0.025)] = P("#59616e")   # handle
    for y in (-0.55, 1.35):
        rect_outline(y - 0.3, y + 0.3, 0.1, 1.1, 0.03)
    for y0, y1 in ((-13.4, -11.6), (3.0, 4.6)):
        rect_outline(y0, y1, -1.95, -1.0, 0.035, col="#68707d")
    # nose-gear bay on the belly
    A = a * 2.5
    bay = (Y > -16.9) & (Y < -14.7) & (A < 0.6)
    bayin = (Y > -16.86) & (Y < -14.74) & (A < 0.56)
    img[bay & ~bayin] = P("#59616e")
    # tail cone and APU hint
    img[(U > 0.985) & (S > -1.0)] = P("#8f98a6")
    out = Image.fromarray(img).filter(ImageFilter.GaussianBlur(0.7))
    out.save(path)


def gen_wing(path, top, p):
    from PIL import Image, ImageFilter
    W, H = p["W"], p["H"]
    u = (np.arange(W) + .5) / W; v = 1 - (np.arange(H) + .5) / H
    U, V = np.meshgrid(u, v)
    X = U * p["xmax"]; Y = p["ymin"] + V * (p["ymax"] - p["ymin"])
    LE = p["LE"](X); TE = p["TE"](X); CH = TE - LE
    C = (Y - LE) / CH
    img = np.zeros((H, W, 3), np.uint8); img[:] = P("#f5f3ec" if top else "#bfc7d3")
    seam = 0.87 if top else 0.78
    for (c, x0, x1) in p["lines"]:
        dark(img, (np.abs(C - c) * CH < 0.03) & (X > x0) & (X < x1), seam)
        if top:
            dark(img, (np.abs(C - c - 0.012) * CH < 0.012) & (((X * 9) % 1) < 0.3) & (X > x0) & (X < x1), 0.7)
    for (x, c0, c1) in p["ribs"]:
        dark(img, (np.abs(X - x) < 0.03) & (C > c0) & (C < c1), seam)
    if top and p is WING:
        img[(X > 2.2) & (X < 7.0) & (C > 0.30) & (C < 0.58) & (np.abs(C - 0.44) < 0.14 - (X - 2.2) * 0.012)] = P("#aeb4c0")
        img[(X > 22.5) & (C > 0.0) & (C < 1.0)] = P("#d3262a")
        img[(C > 0.0) & (C < 0.025) & (X > 3.0)] = P("#c9ced8")
    if p is STAB:
        img[(X > 9.0)] = P("#d3262a")
    if not top and p is WING:
        img[(C > 0.82) & (X > 12.7) & (X < 17) & (C < 0.9)] = P("#a9b1bf")   # flap-track shadow
    Image.fromarray(img).filter(ImageFilter.GaussianBlur(0.6)).save(path)


def gen_fin(path):
    from PIL import Image, ImageFilter
    W = H = 1024
    u = (np.arange(W) + .5) / W; v = 1 - (np.arange(H) + .5) / H
    U, V = np.meshgrid(u, v)
    Y = 10.5 + U * 13.5; Z = 1.0 + V * 12.0
    img = np.zeros((H, W, 3), np.uint8); img[:] = P("#cf2428")
    b = (Z - 0.35 * (Y - 11))
    img[(b > 3.3) & (b < 4.9)] = P("#f7f5ee")
    img[(b > 4.9) & (b < 5.12)] = P("#7d1822")
    img[(b > 3.1) & (b < 3.3)] = P("#7d1822")
    dark(img, np.abs(Y - (17.6 + (Z - 1.6) * 0.18)) < 0.03, 0.62)
    dark(img, (Z > 12.2), 0.8)
    Image.fromarray(img).filter(ImageFilter.GaussianBlur(0.6)).save(path)


def gen_all():
    os.makedirs(TEXD, exist_ok=True)
    gen_fuse(os.path.join(TEXD, "fuse.png"))
    gen_wing(os.path.join(TEXD, "wing_top.png"), True, WING)
    gen_wing(os.path.join(TEXD, "wing_bot.png"), False, WING)
    gen_wing(os.path.join(TEXD, "stab_top.png"), True, STAB)
    gen_wing(os.path.join(TEXD, "stab_bot.png"), False, STAB)
    gen_fin(os.path.join(TEXD, "fin.png"))


def ensure_tex():
    names = ["fuse", "wing_top", "wing_bot", "stab_top", "stab_bot", "fin"]
    me = os.path.getmtime(os.path.abspath(__file__))
    need = [n for n in names if not os.path.exists(os.path.join(TEXD, n + ".png")) or os.path.getmtime(os.path.join(TEXD, n + ".png")) < me]
    if need:
        subprocess.check_call([PY, "-I", os.path.abspath(__file__), "--gen"])


# ============================================================ mesh helpers
def prof(y):
    if y < L0 + NOSE_L:
        s = max((y - L0) / NOSE_L, 0.0)
        og = 0.24 * math.sqrt(max(0.0, 2 * s - s * s)) + 0.76 * (1 - (1 - s) ** 2.6)
        return 2.5 * og, -0.5 * (1 - s) ** 2
    if y <= 9.0:
        return 2.5, 0.0
    t = min((y - 9.0) / 15.3, 1.0)
    return 2.5 - 2.15 * t ** 1.7, 1.5 * t * t


def surf(y, th, off=0.0):
    r, zc = prof(y)
    return Vector(((r + off) * math.sin(th), y, zc - (r + off) * math.cos(th)))


def track(d):
    d = Vector(d).normalized()
    return d.to_track_quat("Z", "X" if abs(d.y) > 0.9 else "Y").to_matrix().to_4x4()


def add_cyl(bm, p0, p1, r0, r1, seg=14, mat=0, cap=True):
    p0, p1 = Vector(p0), Vector(p1)
    n0 = len(bm.faces)
    M = Matrix.Translation((p0 + p1) / 2) @ track(p1 - p0)
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=(p1 - p0).length, matrix=M)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = mat; f.smooth = True


def add_box(bm, c, size, mat=0, M=None):
    n0 = len(bm.faces)
    T = Matrix.Translation(c) @ (M if M is not None else Matrix.Identity(4)) @ Matrix.Diagonal((size[0], size[1], size[2], 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=T)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = mat


def add_ell(bm, c, rad, mat=0, seg=16):
    n0 = len(bm.faces)
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=1.0,
                              matrix=Matrix.Translation(c) @ Matrix.Diagonal((rad[0], rad[1], rad[2], 1)))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = mat; f.smooth = True


def loft(bm, rings, closed_ring=True):
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    M = len(vr[0])
    for a, b in zip(vr[:-1], vr[1:]):
        for k in range(M):
            k2 = (k + 1) % M
            try:
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
            except ValueError:
                pass
    return vr


class B:
    def __init__(self, ctx, root):
        self.ctx, self.root, self.all = ctx, root, []

    def obj(self, name, bm, mats, plain=False, parent=None, loc=(0, 0, 0), recalc=True):
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        (self.ctx["plain"] if plain else self.ctx["ink"]).objects.link(o)
        o.parent = parent or self.root; o.location = loc
        self.all.append(o)
        return o

    def empty(self, name, parent=None, loc=(0, 0, 0)):
        e = bpy.data.objects.new(name, None); self.ctx["ink"].objects.link(e)
        e.parent = parent or self.root; e.location = loc
        return e


def airfoil_ring(le, chord, tfrac, up, back, n=9):
    ss = [(1 - math.cos(math.pi * k / n)) / 2 for k in range(n + 1)]

    def yt(s): return 5 * tfrac * (0.2969 * math.sqrt(s) - 0.126 * s - 0.3516 * s * s + 0.2843 * s ** 3 - 0.1015 * s ** 4)
    top = [le + back * (chord * s) + up * (chord * yt(s)) for s in reversed(ss)]
    bot = [le + back * (chord * s) - up * (chord * yt(s) * 0.8) for s in ss[1:]]
    return top + bot


def cap_ring(bm, ring):
    try:
        bm.faces.new(ring)
    except ValueError:
        pass


# ============================================================ build
def build(ctx):
    lib = ctx["lib"]
    ensure_tex()
    root = bpy.data.objects.new("JetRoot", None); ctx["ink"].objects.link(root)
    b = B(ctx, root)
    T = lambda n, c=None, img=None: lib.toon(n, c, img)
    img = lambda n: os.path.join(TEXD, n + ".png")
    m_fuse = T("jet_fuse", None, img("fuse"))
    m_wt, m_wb = T("jet_wing_top", None, img("wing_top")), T("jet_wing_bot", None, img("wing_bot"))
    m_st, m_sb = T("jet_stab_top", None, img("stab_top")), T("jet_stab_bot", None, img("stab_bot"))
    m_fin = T("jet_fin", None, img("fin"))
    white, grey, dgrey = T("jet_white", "#f7f5ee"), T("jet_grey", "#b9c1cd"), T("jet_dgrey", "#454b58")
    red, metal, dark_m = T("jet_red", "#d3262a"), T("jet_metal", "#e1e5ec"), T("jet_dark", "#232733")
    tire, hub, duct = T("jet_tire", "#252832"), T("jet_hub", "#c3cad6"), T("jet_duct", "#6c7587")
    glass = T("jet_glass", "#16234a"); chrome = T("jet_chrome", "#d9dee7"); amber = T("jet_amber", "#f2b134")
    green, rred = T("jet_navg", "#28c26a"), T("jet_navr", "#ee3b3b")

    # ---------------- fuselage
    N = 40
    ys = [L0 + NOSE_L * s for s in (0.004, 0.015, 0.035, 0.06, 0.09, 0.13, 0.18, 0.24, 0.31, 0.39, 0.48, 0.58, 0.69, 0.81, 0.92)] + [-17.2, -12, -6, 0, 4.5, 9]
    ys += [9 + 15.3 * t for t in (0.07, 0.15, 0.25, 0.35, 0.46, 0.57, 0.67, 0.77, 0.86, 0.93, 0.98, 1.0)]
    ys = sorted(set(ys))
    ys[-1] = L1
    bm = bmesh.new()
    rings = [[surf(y, 2 * math.pi * j / N) for j in range(N)] for y in ys]
    vr = loft(bm, rings)
    cap_ring(bm, vr[0][::-1]); cap_ring(bm, vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UV")
    idx = {}
    for i, r in enumerate(vr):
        for j, vtx in enumerate(r):
            idx[vtx] = (i, j)
    for f in bm.faces:
        f.smooth = True
        js = [idx[l.vert][1] for l in f.loops]
        cap = len(f.loops) > 4
        for l in f.loops:
            i, j = idx[l.vert]
            vv = 0.5 if cap else (1.0 if (j == 0 and N - 1 in js) else j / N)
            l[uvl].uv = ((ys[i] - L0) / FL, vv)
    b.obj("fuselage", bm, [m_fuse], recalc=False)

    # ---------------- wings
    def wing(sx):
        xs = [1.6, 3.5, 5.0, 7.3, 10, 13, 16.5, 20, 22.8, 23.8]
        bm = bmesh.new(); rg = []
        for x in xs:
            le, te = float(wing_LE(x)), float(wing_TE(x))
            tf = 0.135 - (x - 1.6) / 22.2 * 0.05
            rg.append(airfoil_ring(Vector((sx * x, le, wing_z(x))), te - le, tf, Vector((0, 0, 1)), Vector((0, 1, 0))))
        vr = loft(bm, rg); cap_ring(bm, vr[0]); cap_ring(bm, vr[-1][::-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        uvl = bm.loops.layers.uv.new("UV")
        for f in bm.faces:
            f.smooth = True; f.material_index = 0 if f.normal.z >= -0.02 else 1
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (abs(c.x) / WING["xmax"], (c.y - WING["ymin"]) / (WING["ymax"] - WING["ymin"]))
        b.obj("wing", bm, [m_wt, m_wb], recalc=False)
    wing(1); wing(-1)

    def stab(sx):
        xs = [0.5, 2, 4, 6.5, 8.2, 9.3]
        bm = bmesh.new(); rg = []
        for x in xs:
            le, te = float(stab_LE(x)), float(stab_TE(x))
            tf = 0.11 - (x - 0.5) / 8.8 * 0.035
            rg.append(airfoil_ring(Vector((sx * x, le, stab_z(x))), te - le, tf, Vector((0, 0, 1)), Vector((0, 1, 0)), 7))
        vr = loft(bm, rg); cap_ring(bm, vr[0]); cap_ring(bm, vr[-1][::-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        uvl = bm.loops.layers.uv.new("UV")
        for f in bm.faces:
            f.smooth = True; f.material_index = 0 if f.normal.z >= -0.02 else 1
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (abs(c.x) / STAB["xmax"], (c.y - STAB["ymin"]) / (STAB["ymax"] - STAB["ymin"]))
        b.obj("stab", bm, [m_st, m_sb], recalc=False)
    stab(1); stab(-1)

    # vertical fin
    bm = bmesh.new(); rg = []
    for z in (1.0, 3.5, 6.0, 9.0, 12.5):
        le = 11.2 + (z - 1.6) * 0.807; te = 21.2 + (z - 1.6) * (2.0 / 10.9)
        tf = 0.12 - (z - 1) / 11.5 * 0.04
        rg.append(airfoil_ring(Vector((0, le, z)), te - le, tf, Vector((1, 0, 0)), Vector((0, 1, 0)), 8))
    vr = loft(bm, rg); cap_ring(bm, vr[0]); cap_ring(bm, vr[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UV")
    for f in bm.faces:
        f.smooth = True
        for l in f.loops:
            c = l.vert.co
            l[uvl].uv = ((c.y - 10.5) / 13.5, (c.z - 1.0) / 12.0)
    b.obj("fin", bm, [m_fin], recalc=False)

    # ---------------- details on the airframe (one grey/white misc mesh + a dark one)
    bm = bmesh.new()
    add_ell(bm, (0, 1.0, -1.75), (3.0, 6.6, 1.0), 0, 24)                 # wing-body belly fairing
    for sx in (1, -1):
        for x in (4.8, 8.2, 12.0, 15.2, 18.8):                          # flap-track fairings
            te = float(wing_TE(x))
            add_ell(bm, (sx * x, te + 0.2, wing_z(x) - 0.12), (0.14, 1.25, 0.16), 1, 10)
        add_box(bm, (sx * 23.7, float(wing_LE(23.7)) + 1.0, wing_z(23.7) + 0.12), (0.12, 0.9, 0.14), 2 if sx > 0 else 3)  # nav light blocks
    add_ell(bm, (0, 17.5, 2.45), (0.45, 1.2, 0.3), 0, 10)             # dorsal anti-collision light housing
    add_ell(bm, (0, -14.0, -2.45), (0.2, 0.3, 0.12), 2, 8)
    b.obj("misc", bm, [grey, metal, rred, green], recalc=False)
    # fix: nav colours (+x left wing red, -x right wing green)
    me = b.all[-1].data
    for p in me.polygons:
        pass
    bm = bmesh.new()
    add_cyl(bm, (0, L1 - 0.9, 1.5), (0, L1 + 0.02, 1.5), 0.36, 0.3, 14, 0)   # APU exhaust
    for sx in (1, -1):                                                         # pitot probes
        add_cyl(bm, (sx * 0.5, -21.3, 0.4), (sx * 0.62, -22.0, 0.45), 0.03, 0.015, 6, 0)
    for k, y in enumerate((-20.0, -3.0, 6.0, 12.5)):                            # small antennas
        add_box(bm, (0, y, 2.5 + (0.0 if k else 0.0)), (0.04, 0.5, 0.35 if k else 0.25), 0)
    b.obj("bits", bm, [dgrey], recalc=True)

    # cockpit windows
    bm = bmesh.new(); bmf = bmesh.new()
    def patch(bmx, y0, y1, t0, t1, off, nu=3, nv=3):
        g = [[bmx.verts.new(surf(y0 + (y1 - y0) * i / nu, t0 + (t1 - t0) * k / nv, off)) for k in range(nv + 1)] for i in range(nu + 1)]
        for i in range(nu):
            for k in range(nv):
                bmx.faces.new((g[i][k], g[i][k + 1], g[i + 1][k + 1], g[i + 1][k]))
    for sgn in (1, -1):
        def T_(t): return t if sgn > 0 else 2 * math.pi - t
        for (y0, y1, t0, t1) in ((-22.0, -21.0, 2.45, 2.95), (-20.7, -19.95, 1.72, 2.2), (-19.8, -19.1, 1.72, 2.2)):
            a_, b_ = T_(t0), T_(t1)
            patch(bm, y0, y1, a_, b_, 0.02)
            patch(bmf, y0 - 0.07, y1 + 0.07, min(a_, b_) - 0.04, max(a_, b_) + 0.04, 0.012)
    for bmx in (bm, bmf):
        bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces)
        for f in bmx.faces: f.smooth = True
    b.obj("cockpit_glass", bm, [glass], plain=True, recalc=False)
    b.obj("cockpit_frames", bmf, [dgrey], recalc=False)

    # ---------------- engines
    def engine(sx):
        ex, yl, ez = sx * 7.3, -7.2, -2.0
        N2 = 28
        bm = bmesh.new()
        # (ey, r, mat) outer surface front->back; mats: 0 lip metal, 1 red ring, 2 white cowl, 3 core grey, 4 plug dark
        outer = [(0.0, 1.16, 0), (0.05, 1.24, 0), (0.22, 1.29, 0), (0.45, 1.31, 1), (0.95, 1.33, 1), (1.4, 1.33, 2), (3.4, 1.28, 2),
                 (4.8, 1.12, 2), (5.15, 1.0, 2), (5.15, 0.82, 3), (6.0, 0.64, 3), (6.9, 0.46, 3), (6.95, 0.38, 4)]
        duct_p = [(0.0, 1.16, 5), (0.25, 1.1, 5), (0.8, 1.04, 5), (1.7, 1.0, 5)]
        def lath(pts, flip):
            rr = [[Vector((r * math.cos(2 * math.pi * j / N2), yl + ey - yl * 0 + 0, r * math.sin(2 * math.pi * j / N2))) for j in range(N2)] for (ey, r, _) in pts]
            vr = [[bm.verts.new(p) for p in r] for r in rr]
            for i in range(len(pts) - 1):
                for j in range(N2):
                    j2 = (j + 1) % N2
                    q = (vr[i][j], vr[i + 1][j], vr[i + 1][j2], vr[i][j2])
                    f = bm.faces.new(q[::-1] if flip else q); f.material_index = pts[i + 1][2]; f.smooth = True
        # engine axis at origin of this mesh = (0, 0, 0); we offset the object. y in mesh = ey (lip at 0)
        def lath2(pts, flip):
            vr = [[bm.verts.new((r * math.cos(2 * math.pi * j / N2), ey, r * math.sin(2 * math.pi * j / N2))) for j in range(N2)] for (ey, r, _) in pts]
            for i in range(len(pts) - 1):
                for j in range(N2):
                    j2 = (j + 1) % N2
                    q = (vr[i][j], vr[i + 1][j], vr[i + 1][j2], vr[i][j2])
                    f = bm.faces.new(q[::-1] if flip else q); f.material_index = pts[i + 1][2]; f.smooth = True
        lath2(outer, False); lath2(duct_p, True)
        add_cyl(bm, (0, 6.95, 0), (0, 7.7, 0), 0.38, 0.0, 12, 4)   # exhaust plug cone
        add_cyl(bm, (0, 1.72, 0), (0, 1.9, 0), 1.0, 1.0, 20, 4)    # dark disc behind the fan
        eo = b.obj("nacelle", bm, [metal, red, white, grey, dark_m, duct], loc=(ex, yl, ez), recalc=False)
        # pylon
        bp = bmesh.new()
        add_box(bp, (ex, yl + 3.0, ez + 1.15), (0.3, 5.2, 0.9), 0)
        add_box(bp, (ex * 0.99, yl + 5.2, ez + 1.3), (0.28, 3.0, 0.6), 0)
        po = b.obj("pylon", bp, [white], loc=(0, 0, 0))
        # fan
        bf = bmesh.new()
        for k in range(17):
            ph = 2 * math.pi * k / 17
            M = Matrix.Rotation(ph, 4, "Y") @ Matrix.Translation((0.66, 0, 0)) @ Matrix.Rotation(math.radians(30), 4, "X")
            add_box(bf, (0, 0, 0), (0.72, 0.17, 0.035), 0, M)
        add_cyl(bf, (0, 0.2, 0), (0, 0.05, 0), 0.34, 0.34, 18, 1)
        add_cyl(bf, (0, 0.05, 0), (0, -0.85, 0), 0.34, 0.02, 18, 1)
        fo = b.obj("fan", bf, [metal, white], loc=(ex, yl + 1.5, ez), recalc=True)
        return fo
    fans = [engine(1), engine(-1)]

    # ---------------- landing gear
    wm = bpy.data.meshes.new("wheel")
    bw = bmesh.new()
    add_cyl(bw, (-0.21, 0, 0), (0.21, 0, 0), 0.55, 0.55, 22, 0)
    add_cyl(bw, (-0.23, 0, 0), (0.23, 0, 0), 0.32, 0.32, 16, 1)
    add_cyl(bw, (-0.235, 0, 0), (0.235, 0, 0), 0.1, 0.1, 10, 2)
    bw.to_mesh(wm); bw.free()
    for mm in (tire, hub, red):
        wm.materials.append(mm)
    gear_objs = {"main": [], "nose": []}

    def wheel(parent, loc, scale, key):
        o = bpy.data.objects.new("wheel", wm); ctx["ink"].objects.link(o)
        o.parent = parent; o.location = loc; o.scale = (scale, scale, scale)
        b.all.append(o); gear_objs[key].append(o)

    def gobj(o, key):
        gear_objs[key].append(o)

    mains = []
    for sx in (1, -1):
        piv = b.empty("main_pivot", loc=(sx * 5.3, 3.2, -0.75))
        bm = bmesh.new()
        add_cyl(bm, (0, 0, 0.1), (0, 0, -1.05), 0.21, 0.19, 14, 0)               # upper strut
        add_cyl(bm, (0, 0, -0.95), (0, 0, -1.75), 0.125, 0.125, 12, 1)           # oleo
        add_box(bm, (0, 0, -1.9), (0.22, 1.6, 0.26), 0)                          # bogie beam
        for dy in (-0.75, 0.75):
            add_cyl(bm, (-0.7, dy, -2.0), (0.7, dy, -2.0), 0.09, 0.09, 8, 1)     # axles
        add_box(bm, (0.0, -0.45, -1.2), (0.09, 0.12, 0.95), 2, Matrix.Rotation(0.5, 4, "X"))   # drag brace
        add_box(bm, (0.12, 0.15, -1.45), (0.07, 0.5, 0.08), 2)                   # torque link
        add_box(bm, (0.2 * sx, 0.0, -1.0), (0.05, 1.4, 1.5), 3)                  # strut door
        add_box(bm, (0, 0.0, -0.1), (0.5, 0.9, 0.3), 0)                          # trunnion block
        po = b.obj("main_gear", bm, [grey, chrome, dgrey, white], parent=piv)
        gobj(po, "main")
        for dy in (-0.75, 0.75):
            for dx in (-0.62, 0.62):
                wheel(piv, (dx, dy, -2.0), 1.0, "main")
        mains.append(piv)
    nose = b.empty("nose_pivot", loc=(0, -16.3, -2.1))
    bm = bmesh.new()
    add_cyl(bm, (0, 0, 0.1), (0, 0, -0.6), 0.15, 0.13, 12, 0)
    add_cyl(bm, (0, 0, -0.5), (0, 0, -0.95), 0.09, 0.09, 10, 1)
    add_cyl(bm, (-0.42, 0, -0.72), (0.42, 0, -0.72), 0.07, 0.07, 8, 1)
    add_box(bm, (0.0, 0.2, -0.35), (0.07, 0.4, 0.07), 2, Matrix.Rotation(0.4, 4, "X"))
    add_box(bm, (0.0, 0.0, 0.0), (0.7, 0.9, 0.12), 3)
    no = b.obj("nose_gear", bm, [grey, chrome, dgrey, white], parent=nose)
    gobj(no, "nose")
    for dx in (-0.36, 0.36):
        wheel(nose, (dx, 0, -0.72), 0.86, "nose")

    # ---------------- RAT
    rat = b.empty("rat_pivot", loc=(-1.3, -3.5, -2.08))
    bm = bmesh.new()
    add_cyl(bm, (0, 0, 0), (0, 0, -0.85), 0.07, 0.05, 8, 0)
    add_box(bm, (0, 0.0, -0.05), (0.5, 0.7, 0.1), 1)
    ro = b.obj("rat_strut", bm, [dgrey, grey], parent=rat)
    bm = bmesh.new()
    for k in range(2):
        add_box(bm, (0, 0, 0), (0.95, 0.06, 0.16), 0, Matrix.Rotation(k * math.pi / 2, 4, "Y") @ Matrix.Rotation(0.3, 4, "X"))
    add_cyl(bm, (0, 0.14, 0), (0, -0.2, 0), 0.1, 0.1, 10, 1)
    rp = b.obj("rat_prop", bm, [amber, dgrey], parent=rat, loc=(0, -0.05, -0.9))

    return dict(root=root, all=b.all, fans=fans, mains=mains, nose=nose, rat=rat, rat_prop=rp, rat_objs=[ro, rp],
                gear_objs=gear_objs, state={})


def _hide(h, objs, hide):
    for o in objs:
        if h["state"].get(o.name) != hide:
            h["state"][o.name] = hide
            o.hide_render = hide; o.hide_viewport = hide


def pose(h, jet, t):
    lib = __import__("lib")
    vis = bool(jet["visible"]) and jet.get("scrap", 0) <= 0.5
    _hide(h, h["all"] + [h["root"]], not vis)
    if not vis:
        return
    h["root"].matrix_world = lib.obj_matrix(jet["m"])
    g = jet.get("gear", 1.0); ns = jet.get("nose", 0.0); rat = jet.get("rat", 0.0); spin = jet.get("spin", 0.0)
    for piv, sx in zip(h["mains"], (1, -1)):
        piv.rotation_euler = (0, (1 - g) * 1.5 * sx, 0)
    h["nose"].rotation_euler = (-(1 - g) * 1.5 + ns * 1.1, 0, 0)
    _hide(h, h["gear_objs"]["main"], g < 0.02)
    _hide(h, h["gear_objs"]["nose"], g < 0.02)
    h["rat"].rotation_euler = ((1 - min(1.0, rat)) * 1.5, 0, 0)
    _hide(h, h["rat_objs"], rat < 0.02)
    h["rat_prop"].rotation_euler = (0, t * 35.0 * rat, 0)
    for f in h["fans"]:
        f.rotation_euler = (0, t * (1.0 + 7.0 * spin), 0)
    bpy.context.view_layer.update()


if __name__ == "__main__" and "--gen" in sys.argv:
    gen_all()
