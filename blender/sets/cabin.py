# "cabin" set: Air Canada 767 economy cabin at sunset (shot 7). 14 rows of 2-3-2 seats, early-80s fabric, overhead bins with
# PSU strips, window row with sunset sky + blinds + real sun patches (left wall casts shadows), fake light shafts,
# patterned carpet, galley bulkhead behind row 0, curtain bulkhead in front of row 13. Textures: tex/cabin (paint_cabin.py).
# Coordinates: z up, rows advance toward -Y (nose), row r seat back at y = 10 - 0.86 r, aisles x = +-1.05.
import math
import os
import random

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(os.path.dirname(HERE), "tex", "cabin")
INK_RADIUS = {"default": 0.007}

ROWS, ROW0, PITCH = 14, 10.0, 0.86
SEATS = [-2.05, -1.55, -0.5, 0.0, 0.5, 1.55, 2.05]
WALL, CEIL = 2.45, 2.3
Y_BACK, Y_FRONT = 11.2, -7.0
SUN_DIR = Vector((0.55, 0.78, -0.30)).normalized()   # direction the light travels (from the left windows, aft, down)


def tex(n):
    p = os.path.join(TEX, n)
    if not os.path.exists(p):
        import subprocess
        subprocess.run([r"C:\Users\plamb\AppData\Local\Programs\Python\Python312\python.exe", "-I",
                        os.path.join(TEX, "paint_cabin.py")], check=False)
    return p


# ------------------------------------------------------------------------------------------ mesh builder
class MB:
    """accumulates bevelled boxes (with a material index and per-face UVs) into ONE mesh"""

    def __init__(self, name):
        self.name, self.bm, self.mats = name, bmesh.new(), []
        self.uvl = self.bm.loops.layers.uv.new("UV")

    def mat(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def box(self, mn, mx, m, bevel=0.0, size=0.5, uvf=None, seg=2):
        bm = self.bm
        mi = self.mat(m)
        before = set(bm.faces)
        r = bmesh.ops.create_cube(bm, size=1.0)
        vs = r["verts"]
        for v in vs:
            v.co = Vector(((v.co.x + .5) * (mx[0] - mn[0]) + mn[0], (v.co.y + .5) * (mx[1] - mn[1]) + mn[1],
                           (v.co.z + .5) * (mx[2] - mn[2]) + mn[2]))
        if bevel > 0:
            es = list({e for v in vs for e in v.link_edges})
            bmesh.ops.bevel(bm, geom=es, offset=min(bevel, 0.45 * min(mx[i] - mn[i] for i in range(3))),
                            segments=seg, affect="EDGES")
        fs = [f for f in bm.faces if f not in before]
        for f in fs:
            f.material_index = mi
            f.smooth = False
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                co = l.vert.co
                if uvf:
                    l[self.uvl].uv = uvf(co, n, ax)
                else:
                    u, v = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
                    l[self.uvl].uv = (u / size, v / size)

    def build(self, col, loc=(0, 0, 0), shadow=True, name=None):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name or self.name, me)
        o.location = loc
        col.objects.link(o)
        o.visible_shadow = shadow
        return o


def inst(obj, col, loc, name, rot_z=0.0, shadow=True):
    o = bpy.data.objects.new(name, obj.data)
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    col.objects.link(o)
    o.visible_shadow = shadow
    return o


# ------------------------------------------------------------------------------------------ materials
_emit_cache = {}


def emit(name, color=None, image=None, alpha=None, grad=None, strength=1.0):
    """unlit emission material (sky, lights, signs, shafts). alpha = constant opacity; grad = (u0,u1) fade along UV.x"""
    if name in _emit_cache:
        return _emit_cache[name]
    lib = bpy.lib_ref
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    last = em.outputs[0]
    if image:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(image, check_existing=True)
        t.extension = "EXTEND"
        nt.links.new(t.outputs["Color"], em.inputs["Color"])
        al = t.outputs["Alpha"]
    else:
        em.inputs["Color"].default_value = (*lib.hex_rgb(color), 1)
        al = None
    if alpha is not None or grad is not None:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        if grad is not None:
            uv = nt.nodes.new("ShaderNodeTexCoord")
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(uv.outputs["UV"], sep.inputs[0])
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            e = ramp.color_ramp.elements
            e[0].position, e[0].color = 0.0, (grad[0], grad[0], grad[0], 1)
            e[1].position, e[1].color = 1.0, (grad[1], grad[1], grad[1], 1)
            nt.links.new(sep.outputs["X"], ramp.inputs[0])
            nt.links.new(ramp.outputs[0], mix.inputs[0])
        else:
            mix.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        last = mix.outputs[0]
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
        m.use_backface_culling = False
    nt.links.new(last, out.inputs[0])
    _emit_cache[name] = m
    return m


def fv(o):
    return o


# ------------------------------------------------------------------------------------------ build
def build(ctx):
    lib = ctx["lib"]
    bpy.lib_ref = lib
    ink, plain = ctx["ink"], ctx["plain"]
    T = lambda n, c=None, img=None, rep=(1, 1): lib.toon(n, c, img and tex(img), rep)
    rnd = random.Random(7)

    # sun through the left windows
    sun = bpy.data.objects.get("Sun")
    if sun:
        sun.rotation_euler = SUN_DIR.to_track_quat("-Z", "Y").to_euler()

    m_fab = T("cb_fabric", None, "seat_fabric.png")
    m_head = T("cb_head", None, "headrest.png")
    m_cream = T("cb_cream", "#f4ead2")
    m_dark = T("cb_dark", "#2c2a3e")
    m_plas = T("cb_plastic", "#e2d4b4")
    m_pock = T("cb_pocket", "#1f2d6e")
    m_belt = T("cb_belt", "#e0561f")
    m_mag = T("cb_mag", "#d8344a")
    m_mag2 = T("cb_mag2", "#f2b632")
    m_metal = T("cb_metal", "#b8b4c6")
    m_vinyl = T("cb_vinyl", "#3a2a4e")
    m_wall = T("cb_wall", "#ffe6c8", "wall.png")
    m_dado = T("cb_dado", None, "dado.png")
    m_carf = T("cb_carpet_floor", None, "carpet_floor.png")
    m_cara = T("cb_carpet_aisle", None, "carpet_aisle.png")
    m_bin = T("cb_bin", None, "bin_door.png")
    m_psu = T("cb_psu", None, "psu.png")
    m_gal = T("cb_galley", None, "galley.png")
    m_bulk = T("cb_bulk", None, "bulkhead.png")
    m_curt = T("cb_curtain", None, "curtain.png")
    m_exit = emit("cb_exit", image=tex("exit_sign.png"), strength=1.0)
    m_belts = emit("cb_beltsign", image=tex("belt_sign.png"), strength=1.0)
    m_news = T("cb_news", None, "newspaper.png")
    m_cup = T("cb_cup", None, "cup.png")

    # ---------------------------------------------------------------- seat template
    S = MB("seat")
    S.box((-.03, -.30, .03), (.03, -.10, .27), m_dark)                       # pedestal
    S.box((-.215, -.52, .25), (.215, .04, .50), m_fab, bevel=.045, size=.32)   # cushion
    S.box((-.225, -.07, .46), (.225, .075, 1.12), m_fab, bevel=.05, size=.32)  # backrest
    S.box((-.20, -.085, 1.02), (.20, .09, 1.36), m_head, bevel=.045,
          uvf=lambda co, n, ax: ((co.x + .2) / .4, (co.z - 1.02) / .34))       # headrest cover
    S.box((-.15, -.10, 1.05), (.15, -.083, 1.30), m_cream, bevel=.01)          # antimacassar
    S.box((-.20, .075, .58), (.20, .10, 1.01), m_plas, bevel=.012)             # rear shell
    S.box((-.16, .10, .64), (.16, .118, .96), m_cream, bevel=.01)              # stowed tray table
    S.box((-.03, .118, .90), (.03, .13, .935), m_dark)                         # tray latch
    S.box((-.17, .10, .45), (.17, .175, .60), m_pock, bevel=.02, size=.3)      # seat-back pocket
    S.box((-.10, .112, .52), (.02, .135, .70), m_mag)                          # magazine
    S.box((.0, .112, .52), (.1, .135, .66), m_mag2)
    S.box((-.015, -.34, .50), (.015, -.12, .508), m_belt)                       # lap belt strap
    S.box((-.04, -.30, .505), (.04, -.24, .52), m_metal, bevel=.006)           # buckle
    seat_o = S.build(bpy.data.collections.new("_cbtmp"), shadow=True)
    A = MB("arm")
    A.box((-.028, -.50, .56), (.028, .06, .625), m_vinyl, bevel=.02)
    A.box((-.012, -.46, .625), (.012, -.38, .64), m_metal)                      # ashtray button
    A.box((-.02, -.12, .25), (.02, .02, .56), m_dark)
    arm_o = A.build(bpy.data.collections.new("_cbtmp2"))
    for o in (seat_o, arm_o):
        for c in list(o.users_collection):
            c.objects.unlink(o)

    rowy = [ROW0 - PITCH * r for r in range(ROWS)]
    for r, y in enumerate(rowy):
        for i, x in enumerate(SEATS):
            inst(seat_o, ink, (x, y, 0), f"seat_{r}_{i}")
        for k, x in enumerate((-2.30, -1.80, -1.30, -.75, -.25, .25, .75, 1.30, 1.80, 2.30)):
            if x in (-1.30, 1.30) or abs(x) in (.75,) and False:
                pass
            inst(arm_o, ink, (x, y, 0), f"arm_{r}_{k}")

    # ---------------------------------------------------------------- floor
    lib.box(ink, "floor", (-WALL, Y_FRONT, -.1), (WALL, Y_BACK, 0.0), m_carf).data.uv_layers.active  # placeholder replaced below
    bpy.data.objects["floor"].data.materials[0] = m_carf
    fl = bpy.data.objects["floor"]
    for p in fl.data.polygons:
        pass
    lib.box_uv(fl, 0.5)
    for s in (-1, 1):
        a = lib.box(ink, f"aisle{s}", (s * 1.05 - .27, Y_FRONT, 0.0), (s * 1.05 + .27, Y_BACK, 0.012), m_cara)
        lib.box_uv(a, 0.54)
    # rails under the seat blocks
    for x0, x1 in ((-2.32, -1.28), (-.77, .77), (1.28, 2.32)):
        for y in (ROW0 - 4.5, ROW0 - 9.0):
            pass

    # ---------------------------------------------------------------- walls with windows (left casts sun shadows)
    ys_w = [y - .25 for y in rowy]          # window centres
    HW = .17
    Z0, Z1 = .96, 1.46

    def side(s):
        sh = (s < 0)
        x_in, x_out = s * WALL, s * (WALL + .16)
        lo, hi = min(x_in, x_out), max(x_in, x_out)
        W_ = MB(f"wall{s}")
        # lower (dado + panel), upper strip
        W_.box((lo, Y_FRONT, 0), (hi, Y_BACK, .30), m_dado, size=.5)
        W_.box((lo, Y_FRONT, .30), (hi, Y_BACK, Z0), m_wall, size=1.0)
        W_.box((lo, Y_FRONT, Z1), (hi, Y_BACK, CEIL), m_wall, size=1.0)
        # pillars between windows
        edges = [Y_FRONT] + sum([[yc - HW, yc + HW] for yc in sorted(ys_w)], []) + [Y_BACK]
        for a, b in zip(edges[::2], edges[1::2]):
            W_.box((lo, a, Z0), (hi, b, Z1), m_wall, size=1.0)
        o = W_.build(ink, shadow=sh, name=f"wall{s}")
        # window frames, blinds, sky
        F = MB(f"frames{s}")
        for yc in ys_w:
            xi = x_in - s * .02
            for (a, b, c, d) in ((yc - HW - .03, Z0 - .03, yc + HW + .03, Z0), (yc - HW - .03, Z1, yc + HW + .03, Z1 + .03),
                                 (yc - HW - .03, Z0, yc - HW, Z1), (yc + HW, Z0, yc + HW + .03, Z1)):
                F.box((min(xi, x_in + s * .035), a, b), (max(xi, x_in + s * .035), c, d), m_plas, bevel=.008)
            fr = rnd.choice([0, 0, 0.3, 0.55, 1.0, 0]) if not (s < 0 and rnd.random() < .5) else rnd.choice([0, 0, .3])
            if fr > 0:
                h = (Z1 - Z0) * fr
                xx = x_in - s * .03
                F.box((min(xx, xx + s * .03), yc - HW, Z1 - h), (max(xx, xx + s * .03), yc + HW, Z1), m_cream, bevel=.005)
                F.box((min(xx, xx + s * .035), yc - HW * .4, Z1 - h - .035), (max(xx, xx + s * .035), yc + HW * .4, Z1 - h), m_plas, bevel=.01)
        F.build(ink, shadow=False, name=f"frames{s}")
        # sky behind the panes
        P = bpy.data.meshes.new(f"sky{s}")
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UV")
        for yc in ys_w:
            x = s * (WALL + .12)
            vs = [bm.verts.new((x, yc - HW, Z0)), bm.verts.new((x, yc + HW, Z0)), bm.verts.new((x, yc + HW, Z1)), bm.verts.new((x, yc - HW, Z1))]
            f = bm.faces.new(vs if s < 0 else vs[::-1])
            u0 = rnd.random() * .5
            for l, (u, v) in zip(f.loops, ((u0, 0), (u0 + .5, 0), (u0 + .5, 1), (u0, 1)) if s < 0 else ((u0 + .5, 0), (u0, 0), (u0, 1), (u0 + .5, 1))):
                l[uv].uv = (u, v)
        bm.to_mesh(P); bm.free()
        so = bpy.data.objects.new(f"sky{s}", P)
        plain.objects.link(so)
        P.materials.append(emit(f"cb_sky{s}", image=tex("sky_right.png" if s < 0 else "sky_left.png")))
        so.visible_shadow = False

    side(-1)
    side(1)

    # ---------------------------------------------------------------- ceiling, bins, PSU strips, lights
    C = MB("ceiling")
    C.box((-WALL, Y_FRONT, CEIL), (WALL, Y_BACK, CEIL + .1), emit("cb_ceil", "#e0a48e"), size=1.0)
    C.box((-.45, Y_FRONT, CEIL - .03), (.45, Y_BACK, CEIL), m_plas, bevel=.01)          # centre cove
    for yy in [Y_FRONT + 1.72 * k for k in range(1, 12)]:
        C.box((-WALL, yy - .05, CEIL - .05), (WALL, yy + .05, CEIL), m_plas, bevel=.01)
    C.build(ink, shadow=False, name="ceiling")
    blen = PITCH * 2
    for s in (-1, 1):
        B = MB(f"bins{s}")
        x_wall, x_ais = s * (WALL - .01), s * 1.5
        mn_x, mx_x = min(x_wall, x_ais), max(x_wall, x_ais)
        zb, zt = 1.9, 2.27
        face_x = x_ais

        def uvf(co, n, ax, s=s):
            if ax == 0:
                return ((co.y - Y_FRONT) / blen, (co.z - zb) / (zt - zb))
            if ax == 2:
                return (0.5, 0.5)
            return ((co.x) / 1.0, (co.z - zb) / (zt - zb))
        B.box((mn_x, Y_FRONT, zb), (mx_x, Y_BACK, zt), m_bin, bevel=.04, uvf=uvf, seg=2)
        # hinge/latch pegs and bin division strips at every second row
        n = 0
        y = Y_FRONT
        while y <= Y_BACK:
            B.box((min(x_ais, x_ais + s * .04), y - .015, zb - .02), (max(x_ais, x_ais + s * .04), y + .015, zt), m_dark, bevel=.006)
            B.box((min(x_ais, x_ais + s * .045), y + blen * .5 - .09, zb + .06), (max(x_ais, x_ais + s * .045), y + blen * .5 + .09, zb + .1), m_metal, bevel=.01)
            y += blen
        # PSU strip under the bins
        def uvp(co, n, ax):
            return ((co.y - Y_FRONT) / blen, (co.x - (s * 2.0 - .22)) / .44 if s > 0 else (co.x - (s * 2.0 - .22)) / .44)
        B.box((s * 2.0 - .22, Y_FRONT, zb - .045), (s * 2.0 + .22, Y_BACK, zb), m_psu, bevel=.005, uvf=uvp)
        B.build(ink, shadow=False, name=f"bins{s}")
    # warm cove lights (emissive) + exit signs + belt signs
    L = MB("lights")
    L.box((-.38, Y_FRONT, CEIL - .035), (-.30, Y_BACK, CEIL - .03), emit("cb_lightstrip", "#fff0c0"))
    L.box((.30, Y_FRONT, CEIL - .035), (.38, Y_BACK, CEIL - .03), emit("cb_lightstrip", "#fff0c0"))
    L.build(plain, shadow=False, name="lightstrips")
    for k, y in enumerate((2.2, 6.2, 9.8)):
        sg = MB(f"belt{k}")
        sg.box((-.2, y - .02, CEIL - .12), (.2, y + .02, CEIL - .03), m_belts, uvf=lambda co, n, ax: ((co.x + .2) / .4, (co.z - (CEIL - .12)) / .09))
        sg.build(plain, shadow=False, name=f"beltsign{k}")
    for k, y in enumerate((4.0, -2.5)):
        sg = MB(f"exit{k}")
        sg.box((-.22, y - .02, CEIL - .27), (.22, y + .02, CEIL - .03), m_exit, bevel=.008,
               uvf=lambda co, n, ax: ((co.x + .22) / .44, (co.z - (CEIL - .27)) / .24))
        sg.box((-.01, y - .01, CEIL - .03), (.01, y + .01, CEIL), m_dark)
        sg.build(plain, shadow=False, name=f"exitsign{k}")

    # ---------------------------------------------------------------- aft galley wall + curtains, front bulkhead
    G = MB("galley")
    G.box((-WALL, Y_BACK, 0), (WALL, Y_BACK + .15, CEIL), m_wall, size=1.0)
    G.box((-1.0, Y_BACK - .35, 0), (1.0, Y_BACK, 2.0), m_gal, bevel=.025,
          uvf=lambda co, n, ax: ((co.x + 1.0) / 2.0, co.z / 2.0))
    G.box((-1.04, Y_BACK - .37, 1.0), (1.04, Y_BACK - .30, 1.06), m_metal, bevel=.01)    # counter edge
    G.box((-1.02, Y_BACK - .36, 2.0), (1.02, Y_BACK - .1, 2.1), m_plas, bevel=.02)
    G.build(ink, shadow=False, name="galley")
    for s in (-1, 1):
        for dx, wd in ((1.15, .5), (1.65, .5)):
            Cu = MB("curt")
            Cu.box((s * dx - wd / 2, Y_BACK - .12, .25), (s * dx + wd / 2, Y_BACK - .06, 2.2), m_curt, bevel=.01,
                   uvf=lambda co, n, ax: ((co.x) / .5, (co.z - .25) / 1.95))
            Cu.build(ink, shadow=False, name="curtain")
    # front bulkhead with the arches mural + two curtains
    Fb = MB("front")
    Fb.box((-WALL, Y_FRONT - .15, 0), (WALL, Y_FRONT, CEIL), m_wall, size=1.0)
    Fb.box((-1.2, Y_FRONT, .2), (1.2, Y_FRONT + .05, 2.1), m_bulk, bevel=.01,
           uvf=lambda co, n, ax: ((co.x + 1.2) / 2.4, (co.z - .2) / 1.9))
    Fb.build(ink, shadow=False, name="front")
    for s in (-1, 1):
        Cu = MB("curt2")
        Cu.box((s * 1.05 - .4, Y_FRONT + .08, .15), (s * 1.05 + .4, Y_FRONT + .14, 2.2), m_curt, bevel=.01,
               uvf=lambda co, n, ax: ((co.x) / .8, (co.z - .15) / 2.05))
        Cu.build(ink, shadow=False, name="curtain2")

    # ---------------------------------------------------------------- props: newspapers, cups, hats, sills
    P = MB("props")
    for r in (3, 7, 9, 12):
        y = rowy[r]
        sx = rnd.choice([-2.05, 2.05, 1.55])
        P.box((sx - .12, y - .42, .505), (sx + .12, y - .2, .512), m_news, uvf=lambda co, n, ax: ((co.x - (sx - .12)) / .24, (co.y - (y - .42)) / .22))
    P.build(ink, shadow=True, name="props")
    cupo = MB("cup")
    cupo.box((-.03, -.03, 0), (.03, .03, .09), m_cup, bevel=.01, uvf=lambda co, n, ax: ((co.x + co.y) * 8 + .5, co.z / .09))
    cup_o = cupo.build(bpy.data.collections.new("_cbtmp3"))
    for c in list(cup_o.users_collection):
        c.objects.unlink(cup_o)
    for r in (1, 4, 6, 8, 10, 11, 13):
        s = rnd.choice([-1, 1])
        inst(cup_o, ink, (s * (WALL - .06), ys_w[r] + rnd.uniform(-.05, .05), Z0), f"cup{r}", shadow=False)
    # hat (fedora-ish) on the aisle armrest area of one far row
    H = MB("hat")
    H.box((-.14, -.14, 0), (.14, .14, .015), T("cb_hat", "#7a4a2a"), bevel=.006)
    H.box((-.08, -.08, .015), (.08, .08, .10), T("cb_hat", "#7a4a2a"), bevel=.02)
    H.box((-.082, -.082, .04), (.082, .082, .06), T("cb_hatband", "#c2362b"))
    H.build(ink, loc=(1.55, rowy[2] - .3, .512), name="hat")

    # ---------------------------------------------------------------- sun patches/shafts (fake volumetric light)
    mat_shaft = emit("cb_shaft", "#ffd08a", grad=(1.0, 0.35), strength=1.0)
    sh = bpy.data.meshes.new("shafts")
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UV")
    Ls = 5.5
    for yc in ys_w:
        x = -WALL + .02
        a = [Vector((x, yc - HW, Z0)), Vector((x, yc + HW, Z0)), Vector((x, yc + HW, Z1)), Vector((x, yc - HW, Z1))]
        # stop each shaft where it reaches the floor
        t = min(Ls, (a[0].z - .02) / -SUN_DIR.z)
        b = [p + SUN_DIR * (t * (1.0 if i < 2 else min(1.0, 1.0)) ) for i, p in enumerate(a)]
        for i in range(4):
            j = (i + 1) % 4
            vs = [bm.verts.new(a[i]), bm.verts.new(a[j]), bm.verts.new(b[j]), bm.verts.new(b[i])]
            f = bm.faces.new(vs)
            for l, u in zip(f.loops, (0, 0, 1, 1)):
                l[uv].uv = (u, 0)
    bm.to_mesh(sh); bm.free()
    sho = bpy.data.objects.new("shafts", sh)
    plain.objects.link(sho)
    sh.materials.append(mat_shaft)
    sho.visible_shadow = False
    ctx["_cabin"] = True


def animate(ctx, layer, info):
    pass
