# The "cockpit" set: a cartoon Boeing 767-200 flight deck, 1983 (layout.COCKPIT).
# Shots 5, 6, 8, 10: golden sunset flight (light "interior_golden"); shot 19: the same deck as a DAYLIGHT FLIGHT SIMULATOR
# in a dark hall (light "interior"). Blender coordinates: z up, nose toward -Y, captain (left seat) at +X, FO at -X.
#   floor z 0, seats at x +-0.55 / y 0.1 (cards at y ~0.25, heads z 1.25-1.6), instrument panel face y -0.95,
#   glareshield top z 1.12 (lip at y -0.78), windscreen base y -1.43 z 1.17 -> top y -1.19 z 1.83 (raked),
#   side walls x +-1.7, rear bulkhead y 2.25, ceiling z 2.2, overhead panel sloping z 1.92 -> 2.15.
# Textures are painted by D:\gimli3d\blender\tex\cockpit\paint_cockpit.py (Pillow).
# Everything is built per render run for ONE shot, so shot-specific dressing (sim vs flight) is decided in build().
import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(os.path.dirname(HERE), "tex", "cockpit")
# world-space line radius (m): the cameras sit 0.3-4 m from the geometry, so the ink is thin and tuned per shot
INK_RADIUS = 0.004  # fallback only: animate() installs a screen-space width (see _ink_width_setup)

# story cues (PICTURE frames)
F_ALARM1, F_ALARM2, F_DARK, F_SIM, F_CRASH = 552, 584, 672, 1767, 1796
INK_NEAR_PX, INK_FAR_PX = 5.2, 3.4
CLOUD_SPEED = 70.0  # m/s toward +Y

_S = {}  # handles for animate()


def _retint(sim):
    """this set's own toon tints (one render run = one set): hotter orange lit side, deeper violet shadow side"""
    g = bpy.data.node_groups.get("ToonSurf")
    if g is None:
        return
    lit, sh = ((1.0, 0.99, 0.96), (0.46, 0.46, 0.68)) if sim else ((1.5, 0.86, 0.45), (0.30, 0.24, 0.58))
    g.nodes["LitTint"].outputs[0].default_value = (*lit, 1)
    g.nodes["ShadowTint"].outputs[0].default_value = (*sh, 1)


def T(name):
    return os.path.join(TEX, name)


# ====================================================================== mesh helpers
def _diag(v):
    return Matrix.Diagonal((v[0], v[1], v[2], 1.0))


def _frame(d, up=Vector((0, 0, 1))):
    """3x3 rotation whose columns are (right, d, up') for a beam along d"""
    d = d.normalized()
    if abs(d.dot(up)) > 0.97:
        up = Vector((0, 1, 0))
    r = d.cross(up).normalized()
    u = r.cross(d).normalized()
    return Matrix((r, d, u)).transposed()


class MB:
    """merges many primitives into one mesh object (one draw call, materials per face)"""

    def __init__(self, name, M=None):
        self.name, self.bm, self.mats = name, bmesh.new(), []
        self.M = M or Matrix.Identity(4)

    def _tag(self, verts, mat, smooth=False):
        if mat not in self.mats:
            self.mats.append(mat)
        mi = self.mats.index(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = mi
            if smooth and len(f.verts) == 4:
                f.smooth = True
        return faces

    def box(self, mn, mx, mat):
        mn, mx = Vector(mn), Vector(mx)
        m = self.M @ Matrix.Translation((mn + mx) / 2) @ _diag(mx - mn)
        return self._tag(bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"], mat)

    def obox(self, c, size, rot, mat):
        m = self.M @ Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ _diag(size)
        return self._tag(bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"], mat)

    def beam(self, p0, p1, w, h, mat, up=Vector((0, 0, 1))):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        m = self.M @ Matrix.Translation((p0 + p1) / 2) @ _frame(d, up).to_4x4() @ _diag((w, d.length, h))
        return self._tag(bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"], mat)

    def cyl(self, p0, p1, r, mat, seg=12, r2=None, cap=True):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        q = d.normalized().to_track_quat("Z", "Y")
        m = self.M @ Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4()
        v = bmesh.ops.create_cone(self.bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r,
                                  radius2=r if r2 is None else r2, depth=d.length, matrix=m)["verts"]
        return self._tag(v, mat, smooth=True)

    def sphere(self, c, radii, mat, seg=12):
        m = self.M @ Matrix.Translation(c) @ _diag(radii)
        v = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(4, seg // 2), radius=1.0, matrix=m)["verts"]
        faces = self._tag(v, mat)
        for f in faces:
            f.smooth = True
        return faces

    def obj(self, col, uv=0.5, bevel=0.0, seg=2):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        col.objects.link(o)
        uvproj(o, uv)
        if bevel > 0:
            b = o.modifiers.new("bevel", "BEVEL")
            b.width, b.segments, b.limit_method = bevel, seg, "ANGLE"
            b.angle_limit = math.radians(50)
            b.harden_normals = False
        return o


def uvproj(o, size=0.5):
    """box-project UVs (metres / size) so text on textures reads the right way from the viewer's side"""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new()
    uv = me.uv_layers.active.data
    Z = Vector((0, 0, 1))
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 2:
                u, v = co.x, co.y * (1 if n.z > 0 else -1)
            else:
                na = Vector((0, 0, 0))
                na[ax] = 1 if n[ax] > 0 else -1
                r = Z.cross(na)
                u, v = co.dot(r), co.z
            uv[li].uv = (u / size, v / size)


def quad(col, name, c, right, up, w, h, mat, uvr=(0, 0, 1, 1)):
    """textured rectangle facing right x up, UV 0..1 (or the sub-rectangle uvr)"""
    c, right, up = Vector(c), Vector(right).normalized(), Vector(up).normalized()
    vs = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in vs], [], [(0, 1, 2, 3)])
    me.uv_layers.new()
    u0, v0, u1, v1 = uvr
    for k, (u, v) in enumerate([(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
        me.uv_layers.active.data[k].uv = (u, v)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def disc(col, name, c, right, up, r, mat, seg=32):
    c, right, up = Vector(c), Vector(right).normalized(), Vector(up).normalized()
    vs = [tuple(c)] + [tuple(c + (right * math.cos(a) + up * math.sin(a)) * r) for a in (2 * math.pi * i / seg for i in range(seg))]
    faces = [(0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], faces)
    me.uv_layers.new()
    uv = me.uv_layers.active.data
    for p in me.polygons:
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            if vi == 0:
                uv[li].uv = (0.5, 0.5)
            else:
                a = 2 * math.pi * (vi - 1) / seg
                uv[li].uv = (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a))
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


# ====================================================================== materials
def tm(lib, name, color=None, img=None, rep=(1, 1)):
    return lib.toon("ck_" + name, color, T(img) if img else None, rep)


def emis(name, color=(1, 1, 1), strength=1.0, img=None):
    """unlit emissive (screens, lamps). Nodes 'Tex' (optional) and 'Em' are animated."""
    m = bpy.data.materials.get("cke_" + name)
    if m:
        return m
    m = bpy.data.materials.new("cke_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "Em"
    em.inputs["Strength"].default_value = strength
    col = color if len(color) == 4 else (*color, 1)
    if img:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.name = "Tex"
        tex.image = bpy.data.images.load(T(img), check_existing=True)
        tex.extension = "EXTEND"
        mul = nt.nodes.new("ShaderNodeMix")
        mul.name = "Tint"
        mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
        mul.inputs[0].default_value = 1
        mul.inputs[7].default_value = col
        nt.links.new(tex.outputs[0], mul.inputs[6])
        nt.links.new(mul.outputs[2], em.inputs[0])
    else:
        em.inputs[0].default_value = col
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def glow_mat(name, color, strength=1.0):
    """additive soft glow sprite (glow.png alpha x colour x 'Gain')"""
    m = bpy.data.materials.get("ckg_" + name)
    if m:
        return m
    m = bpy.data.materials.new("ckg_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(T("glow.png"), check_existing=True)
    tex.extension = "CLIP"
    gain = nt.nodes.new("ShaderNodeMath")
    gain.name = "Gain"
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = strength
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*color, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tex.outputs["Alpha"], gain.inputs[0])
    nt.links.new(gain.outputs[0], em.inputs["Strength"])
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs[0])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    m.use_backface_culling = False
    return m


def glow_sprite(col, name, c, size, color, strength=1.0):
    m = glow_mat(name, color, strength)
    o = quad(col, "glow_" + name, (0, 0, 0), (1, 0, 0), (0, 1, 0), size, size, m)
    o.location = c
    o.visible_shadow = False
    _S.setdefault("sprites", []).append(o)
    return o


def no_shadow(o):
    o.visible_shadow = False
    return o


# ====================================================================== build
def build(ctx):
    lib = ctx["lib"]
    ink, plain = ctx["ink"], ctx["plain"]
    shot = ctx["shot"]
    sim = shot == 19 or ctx["light"] == "interior"
    _S.clear()
    _S["sim"] = sim
    rnd = random.Random(1983)

    # ---------------------------------------------------------------- palette
    _retint(sim)
    LINE, LINE_DK = ("#9a7ea0", "#74607e") if not sim else ("#7f94cc", "#5f74b0")
    M = dict(
        lining=tm(lib, "lining", LINE, "lining.png"),
        lining_dk=tm(lib, "lining_dk", LINE_DK, "lining_dark.png"),
        carpet=tm(lib, "carpet", "#6a6078" if not sim else "#7a8296", "carpet.png"),
        panel=tm(lib, "panel", "#7d7f92" if not sim else "#9aa0b4", "panel.png"),
        pedestal=tm(lib, "pedestal", "#7d7f92" if not sim else "#9aa0b4", "pedestal.png"),
        overhead=tm(lib, "overhead", "#8a8c9e" if not sim else "#a4aabc", "overhead.png"),
        glare=tm(lib, "glare", "#1c2030"),
        lip=tm(lib, "lip", "#1d2130"),
        frame=tm(lib, "frame", "#262a36"),
        bezel=tm(lib, "bezel", "#202228"),
        black=tm(lib, "black", "#141518"),
        metal=tm(lib, "metal", "#a9aebd"),
        darkmetal=tm(lib, "darkmetal", "#30343e"),
        white=tm(lib, "white", "#f3f0e8"),
        leather=tm(lib, "leather", "#98703e", "leather.png"),
        leather_plain=tm(lib, "leather_plain", "#7a3a1a"),
        seatbase=tm(lib, "seatbase", "#262830"),
        strap=tm(lib, "strap", "#2c3c66"),
        red=tm(lib, "red", "#d8332c"),
        yellow=tm(lib, "yellow", "#f2c418"),
        navy=tm(lib, "navy", "#1f2a4a"),
        gold=tm(lib, "gold", "#e8b83a"),
        door=tm(lib, "door", "#5c5a68"),
        wood=tm(lib, "brownbag", "#7a4a26"),
        tan=tm(lib, "tan", "#c9a36a"),
        skin=tm(lib, "skin", "#b9b2cc" if not sim else "#b8c6e0", "simcab.png" if sim else "skin.png"),
        rubber=tm(lib, "rubber", "#23252b"),
        green=tm(lib, "green", "#3f8f52"),
        cup=tm(lib, "cup", "#f6f1e6"),
        coffee=tm(lib, "coffee", "#5b351c"),
        paper=tm(lib, "paper", "#f7f3e6"),
        clip=tm(lib, "clip", "#8a6a44"),
    )
    _S["M"] = M

    _shell(lib, ink, plain, M, sim)
    _nose(lib, ink, plain, M, sim)
    _panel(lib, ink, plain, M, sim)
    _pedestal(lib, ink, plain, M, rnd)
    _consoles(lib, ink, plain, M)
    for s in (1, -1):
        _seat(ink, M, s)
        _yoke(ink, plain, M, s)
    _overhead(lib, ink, plain, M, rnd)
    _rear(lib, ink, plain, M, sim, rnd)
    if sim:
        _sim_hall(lib, ink, plain, M)
    else:
        _outside(lib, plain)
    _lights(sim, shot)
    _sun(shot, sim)


# ---------------------------------------------------------------- shell
def _shell(lib, ink, plain, M, sim):
    sh = MB("shell")
    L = M["lining"]
    sh.box((-1.8, -1.6, -0.12), (1.8, 2.35, 0.0), M["carpet"])
    for s in (1, -1):
        x0, x1 = (1.7, 1.8) if s > 0 else (-1.8, -1.7)
        sh.box((x0, -1.0, -0.1), (x1, 2.35, 1.05), L)          # below the side windows
        sh.box((x0, -1.0, 1.62), (x1, 2.35, 2.35), L)          # above
        sh.box((x0, 0.15, 1.0), (x1, 2.35, 1.66), L)           # solid wall behind the windows
        sh.box((x0, -0.40, 1.0), (x1, -0.30, 1.66), M["frame"])  # post between No.2 and No.3 windows
        sh.box((x0, -1.02, 1.0), (x1, -0.92, 1.66), M["frame"])  # front post
        # window reveals (dark rims inside the openings)
        for ya, yb, top in ((-0.92, -0.40, 1.62), (-0.30, 0.15, 1.62)):
            xi = 1.66 * s
            sh.box((min(xi, 1.7 * s), ya, 1.02), (max(xi, 1.7 * s), yb, 1.06), M["frame"])
            sh.box((min(xi, 1.7 * s), ya, top - 0.03), (max(xi, 1.7 * s), yb, top + 0.01), M["frame"])
        # corner block above the corner panes, corner sill/header beams
        sh.box((min(1.2 * s, 1.8 * s), -1.5, 1.62), (max(1.2 * s, 1.8 * s), -0.95, 2.35), L)
        sh.beam((1.2 * s, -1.43, 1.165), (1.72 * s, -0.97, 1.165), 0.09, 0.09, M["frame"])
        sh.beam((1.2 * s, -1.27, 1.625), (1.72 * s, -0.97, 1.625), 0.09, 0.07, M["frame"])
        # sliding-window crank handle (No.2 window)
        sh.cyl((1.66 * s, -0.66, 1.12), (1.6 * s, -0.66, 1.12), 0.025, M["black"], 10)
        sh.box((min(1.6 * s, 1.56 * s), -0.69, 1.1), (max(1.6 * s, 1.56 * s), -0.55, 1.14), M["metal"])
    sh.box((-1.8, 2.25, -0.1), (1.8, 2.35, 2.35), L)            # rear bulkhead
    sh.box((-1.8, -0.5, 2.2), (1.8, 2.35, 2.32), L)             # ceiling
    # brow: from the windscreen header up to the ceiling (interior lining)
    a = math.atan2(0.40, 0.78)
    sh.obox((0, -0.83, 2.04), (3.6, 0.9, 0.10), (a, 0, 0), L)
    # windscreen frame: sill, header, three raked posts
    fr = M["frame"]
    sh.beam((-1.25, -1.43, 1.165), (1.25, -1.43, 1.165), 0.10, 0.09, fr)
    sh.beam((-1.25, -1.19, 1.835), (1.25, -1.19, 1.835), 0.10, 0.09, fr)
    for x in (-1.2, 0.0, 1.2):
        sh.beam((x, -1.45, 1.12), (x, -1.18, 1.88), 0.09, 0.10, fr)
    o = sh.obj(ink, uv=0.5, bevel=0.012)
    # ceiling dressing: dome lights, gasper vents, grab handles (plain: small)
    dd = MB("ceiling_bits")
    for x in (-1.15, 1.15):
        dd.cyl((x, 1.2, 2.2), (x, 1.2, 2.17), 0.09, M["frame"], 20)
        for y in (0.7, 1.7):
            dd.cyl((x * 0.8, y, 2.2), (x * 0.8, y, 2.165), 0.035, M["metal"], 12)
            dd.cyl((x * 0.8, y, 2.166), (x * 0.8, y, 2.16), 0.016, M["black"], 10)
    dd.obj(ink, uv=0.5)
    for x in (-1.15, 1.15):
        no_shadow(disc(plain, "dome", (x, 1.2, 2.168), (1, 0, 0), (0, -1, 0), 0.07, emis("dome", (1.0, 0.92, 0.78), 1.0)))
    _S["shell"] = o


# ---------------------------------------------------------------- nose skin (seen from the shot 5 / 19 cameras)
def _nose(lib, ink, plain, M, sim):
    NU, NV = 28, 16
    bm = bmesh.new()
    rows = []
    for j in range(NV + 1):
        t = j / NV
        y = -1.43 - 2.3 * t
        zt = 1.17 - 0.62 * t ** 1.5
        w = 1.85 * (1 - 0.68 * t * t)
        row = []
        for i in range(NU + 1):
            u = -1 + 2 * i / NU
            a = abs(u)
            s = min(1.0, max(0.0, (a - 0.55) / 0.45))
            f = s * s * (3 - 2 * s)
            z = zt - (zt + 0.4) * f
            row.append(bm.verts.new((u * w, y, z)))
        rows.append(row)
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("nose")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M["skin"])
    o = bpy.data.objects.new("nose", me)
    ink.objects.link(o)
    uvproj(o, 1.2)
    # exterior windscreen frame band, wipers, rain nozzles, crown skin
    ex = MB("nose_bits")
    dark = M["rubber"]
    ex.beam((-1.3, -1.47, 1.15), (1.3, -1.47, 1.15), 0.06, 0.05, dark)
    for s in (1, -1):
        # wiper parked along the sill: pivot, arm, blade
        px = 0.95 * s
        ex.cyl((px, -1.5, 1.12), (px, -1.5, 1.17), 0.03, M["black"], 12)
        ex.beam((px, -1.49, 1.175), (0.3 * s, -1.47, 1.2), 0.025, 0.018, M["black"])
        ex.beam((0.85 * s, -1.465, 1.205), (0.22 * s, -1.445, 1.215), 0.02, 0.03, dark)
    ex.box((-0.35, -1.62, 1.09), (-0.25, -1.55, 1.12), M["metal"])  # rain repellent nozzle
    ex.box((0.25, -1.62, 1.09), (0.35, -1.55, 1.12), M["metal"])
    a = math.atan2(0.42, 0.8)
    ex.obox((0, -0.83, 2.16), (3.7, 0.96, 0.06), (a, 0, 0), M["skin"])  # crown skin over the brow
    if sim:  # simulator cab: hazard stripe and cable bundles under the windscreen
        ex.beam((-1.6, -1.6, 1.0), (1.6, -1.6, 1.0), 0.02, 0.06, M["yellow"])
        for k, x in enumerate((-1.1, -0.9, 0.7, 0.95)):
            ex.cyl((x, -1.55, 1.05), (x + 0.1, -2.6, 0.2), 0.025 + 0.01 * (k % 2), M["black"], 8)
    ex.obj(ink, uv=0.5)
    if sim:
        hz = tm(lib, "hazard", None, "hazard.png")
        quad(ink, "sim_hazard", (0, -1.66, 0.98), (1, 0, 0), (0, -0.35, 0.94), 2.4, 0.07, hz)
    _S["nose"] = o


# ---------------------------------------------------------------- instrument panel + glareshield
SCREENS = [  # name, x, z, on-texture
    ("adi_c", 0.62, 0.745, "adi_on.png"), ("hsi_c", 0.62, 0.515, "hsi_on.png"),
    ("eicas_u", 0.0, 0.745, "eicas_up_on.png"), ("eicas_l", 0.0, 0.515, "eicas_lo_on.png"),
    ("adi_f", -0.62, 0.745, "adi_on.png"), ("hsi_f", -0.62, 0.515, "hsi_on.png"),
]


def _panel(lib, ink, plain, M, sim):
    pb = MB("panel")
    YF = -0.95  # panel face
    pb.box((-1.8, -1.45, -0.1), (1.8, YF, 0.96), M["panel"])
    # glareshield box + padded lip
    pb.box((-1.5, -1.44, 0.96), (1.5, -0.80, 1.12), M["glare"])
    pb.cyl((-1.5, -0.80, 1.08), (1.5, -0.80, 1.08), 0.045, M["lip"], 14)
    for s in (1, -1):
        pb.sphere((1.5 * s, -0.80, 1.08), (0.045, 0.045, 0.045), M["lip"], 10)
    # glareshield face (pilot side): MCP housing, EFIS control panels, master caution / warning housings
    GY = -0.80
    pb.box((-0.48, GY, 0.962), (0.48, GY + 0.025, 1.035), M["darkmetal"])
    for s in (1, -1):
        x0, x1 = sorted((0.58 * s, 0.98 * s))
        pb.box((x0, GY, 0.965), (x1, GY + 0.02, 1.035), M["darkmetal"])
        for k in range(4):
            x = s * (0.64 + k * 0.1)
            pb.cyl((x, GY + 0.02, 1.0), (x, GY + 0.04, 1.0), 0.013, M["black"], 10)
        x0, x1 = sorted((1.04 * s, 1.30 * s))
        pb.box((x0, GY, 0.965), (x1, GY + 0.015, 1.035), M["bezel"])
    # instrument bezels around the six screens (frame of four bars, recessed glass)
    for name, x, z, _ in SCREENS:
        pb.box((x - 0.125, YF, z - 0.125), (x + 0.125, YF + 0.022, z + 0.125), M["bezel"])
        for (a, b) in (((-0.118, 0.1), (0.118, 0.118)), ((-0.118, -0.118), (0.118, -0.1)),
                       ((-0.118, -0.1), (-0.1, 0.1)), ((0.1, -0.1), (0.118, 0.1))):
            pb.box((x + a[0], YF + 0.022, z + a[1]), (x + b[0], YF + 0.034, z + b[1]), M["black"])
        for kx in (-0.095, 0.095):
            pb.cyl((x + kx, YF + 0.022, z - 0.112), (x + kx, YF + 0.036, z - 0.112), 0.009, M["metal"], 8)
    # round standby gauges: bezel cylinders (faces are textured discs)
    gauges = [(0.85, 0.745, 0.058, "g_asi.png"), (0.39, 0.745, 0.058, "g_alt.png"), (0.39, 0.515, 0.05, "g_vsi.png"),
              (0.85, 0.515, 0.05, "g_brake.png"), (1.08, 0.745, 0.045, "g_clock.png"), (1.08, 0.53, 0.045, "g_flaps.png"),
              (-0.85, 0.745, 0.058, "g_alt.png"), (-0.39, 0.745, 0.058, "g_asi.png"), (-0.39, 0.515, 0.05, "g_vsi.png"),
              (-0.85, 0.515, 0.05, "g_brake.png"), (-1.08, 0.745, 0.045, "g_clock.png"),
              (0.215, 0.80, 0.062, "g_att.png"), (0.215, 0.645, 0.045, "g_asi.png"), (0.215, 0.53, 0.045, "g_alt.png")]
    for x, z, r, _ in gauges:
        pb.cyl((x, YF, z), (x, YF + 0.03, z), r + 0.012, M["bezel"], 24)
        pb.cyl((x, YF + 0.03, z), (x, YF + 0.034, z), r + 0.012, M["black"], 24, r2=r + 0.004, cap=False)
    # landing-gear lever panel (FO side of the centre panel): lever slot, wheel-shaped knob, three gear lights
    gx = -0.235
    pb.box((gx - 0.07, YF, 0.56), (gx + 0.07, YF + 0.012, 0.86), M["darkmetal"])
    pb.box((gx - 0.012, YF + 0.012, 0.6), (gx + 0.012, YF + 0.05, 0.72), M["metal"])
    pb.cyl((gx - 0.04, YF + 0.06, 0.62), (gx + 0.04, YF + 0.06, 0.62), 0.032, M["white"], 16)
    pb.cyl((gx, YF + 0.012, 0.47), (gx, YF + 0.04, 0.47), 0.03, M["black"], 14)  # autobrake selector
    # annunciator strip above the screens + misc knobs
    for k in range(9):
        x = -0.4 + k * 0.1
        pb.box((x - 0.03, YF, 0.905), (x + 0.03, YF + 0.01, 0.935), M["bezel"])
    o = pb.obj(ink, uv=0.6, bevel=0.006)
    # lower knee panels and rudder pedals (seen from nowhere, cheap)
    # textured faces: screens, gauge discs, MCP
    scr = {}
    for name, x, z, img in SCREENS:
        mat = emis("scr_" + name, (1, 1, 1), 1.0, img)
        q = quad(plain, "scr_" + name, (x, YF + 0.0225, z), (-1, 0, 0), (0, 0, 1), 0.2, 0.2, mat)
        no_shadow(q)
        scr[name] = (mat, img)
    _S["screens"] = scr
    for i, (x, z, r, img) in enumerate(gauges):
        no_shadow(disc(plain, f"gauge{i}", (x, YF + 0.031, z), (-1, 0, 0), (0, 0, 1), r, emis("g_" + img[:-4], (0.92, 0.92, 0.9), 1.0, img)))
    mcp = emis("mcp", (1, 1, 1), 1.0, "mcp.png")
    no_shadow(quad(plain, "mcp_face", (0, GY + 0.0255, 0.9985), (-1, 0, 0), (0, 0, 1), 0.94, 0.07, mcp))
    # annunciators (a few lit)
    cols = [(0.3, 0.9, 0.4), (1.0, 0.7, 0.2), (0.25, 0.25, 0.28), (0.3, 0.6, 1.0), (0.25, 0.25, 0.28)]
    for k in range(9):
        c = cols[k % 5]
        no_shadow(quad(plain, f"ann{k}", (-0.4 + k * 0.1, YF + 0.0105, 0.92), (-1, 0, 0), (0, 0, 1), 0.05, 0.022, emis(f"ann{k % 5}", c, 1.0)))
    # gear lights: three green DOWN
    for k, (dx, dz) in enumerate(((0, 0.835), (-0.03, 0.795), (0.03, 0.795))):
        no_shadow(quad(plain, f"gearl{k}", (gx + dx, YF + 0.0125, dz), (-1, 0, 0), (0, 0, 1), 0.026, 0.02, emis("gearlight", (0.3, 0.95, 0.45), 1.0)))
    # master CAUTION (amber) and WARNING (red) lights, one pair per pilot
    lights = []
    for s, who in ((1, "c"), (-1, "f")):
        for kind, x, col in (("caution", 1.10, (1.0, 0.62, 0.12)), ("warning", 1.235, (1.0, 0.16, 0.1))):
            mat = emis(f"{kind}_{who}", col, 0.12)
            q = quad(plain, f"{kind}_{who}", (x * s, GY + 0.0155, 1.0), (-1, 0, 0), (0, 0, 1), 0.1, 0.055, mat)
            no_shadow(q)
            g = glow_sprite(plain, f"{kind}_{who}", Vector((x * s, GY + 0.05, 1.0)), 0.34, col, 0.0)
            lights.append(dict(kind=kind, side=who, mat=mat, glow=g, col=col))
    _S["alarms"] = lights
    # the fuel slip on its clipboard, left on the glareshield (shot 6 sees it)
    cb = MB("clipboard")
    cx, cy = 0.07, -1.02
    cb.obox((cx, cy, 1.124), (0.24, 0.32, 0.008), (0, 0, 0.18), M["clip"])
    cb.obox((cx + 0.025, cy - 0.14, 1.132), (0.11, 0.035, 0.012), (0, 0, 0.18), M["metal"])
    cb.obj(ink, uv=0.3)
    sl = tm(lib, "slip", None, "slip.png")
    q = quad(plain, "slip", (cx, cy + 0.01, 1.1295), (math.cos(0.18), math.sin(0.18), 0), (-math.sin(0.18), math.cos(0.18), 0), 0.2, 0.265, sl)
    q.rotation_euler = (0, 0, 0)
    _S["panel"] = o


# ---------------------------------------------------------------- centre pedestal + throttle quadrant
def _pedestal(lib, ink, plain, M, rnd):
    pd = MB("pedestal")
    P = M["pedestal"]
    pd.box((-0.24, -0.95, 0.0), (0.24, 0.42, 0.62), P)
    pd.box((-0.25, -0.95, 0.0), (0.25, 0.44, 0.08), M["darkmetal"])
    # throttle quadrant hump
    pd.cyl((-0.2, -0.68, 0.56), (0.2, -0.68, 0.56), 0.19, M["darkmetal"], 24)
    for x in (-0.11, -0.03, 0.03, 0.11):
        pd.box((x - 0.006, -0.82, 0.74), (x + 0.006, -0.55, 0.752), M["black"])
    # thrust levers (black knobs), speed brake (left), flap lever (right), fuel control switches (red)
    for x in (-0.07, 0.07):
        pd.beam((x, -0.66, 0.70), (x, -0.76, 0.90), 0.016, 0.022, M["metal"])
        pd.cyl((x - 0.045, -0.765, 0.905), (x + 0.045, -0.765, 0.905), 0.024, M["black"], 14)
    pd.beam((0.17, -0.64, 0.72), (0.17, -0.70, 0.86), 0.012, 0.018, M["metal"])
    pd.box((0.15, -0.725, 0.85), (0.19, -0.68, 0.89), M["white"])
    pd.beam((-0.17, -0.62, 0.72), (-0.17, -0.62, 0.84), 0.012, 0.018, M["metal"])
    pd.box((-0.205, -0.66, 0.83), (-0.135, -0.58, 0.865), M["white"])
    for x in (-0.06, 0.06):
        pd.box((x - 0.015, -0.47, 0.62), (x + 0.015, -0.43, 0.70), M["black"])
        pd.cyl((x, -0.45, 0.70), (x, -0.45, 0.73), 0.018, M["red"], 10)
    # aft pedestal: radio heads and knobs
    rows = [-0.32, -0.16, 0.0, 0.15, 0.30]
    for k, y in enumerate(rows):
        pd.box((-0.22, y - 0.065, 0.62), (0.22, y + 0.065, 0.632), M["darkmetal"])
        for x in (-0.16, 0.16):
            pd.cyl((x, y, 0.632), (x, y, 0.655), 0.02, M["black"], 12)
            pd.cyl((x, y, 0.655), (x, y, 0.668), 0.012, M["black"], 10)
    o = pd.obj(ink, uv=0.5, bevel=0.004)
    for k, y in enumerate(rows):
        col = (1.0, 0.7, 0.2) if k % 2 == 0 else (0.35, 1.0, 0.5)
        no_shadow(quad(plain, f"radio{k}", (0, y, 0.6335), (1, 0, 0), (0, 1, 0), 0.2, 0.04, emis(f"radio{k % 2}", col, 1.0)))
    _S["pedestal"] = o


# ---------------------------------------------------------------- side consoles (cup, tiller, oxygen box, charts)
def _consoles(lib, ink, plain, M):
    cs = MB("consoles")
    for s in (1, -1):
        x0, x1 = sorted((1.36 * s, 1.7 * s))
        cs.box((x0, -0.95, 0.0), (x1, 0.4, 0.64), M["pedestal"])
        cs.box((x0 - 0.01, -0.95, 0.64), (x1, 0.4, 0.66), M["darkmetal"])
        # cup holder + coffee cup
        cx = 1.5 * s
        cs.cyl((cx, 0.22, 0.66), (cx, 0.22, 0.68), 0.05, M["metal"], 16)
        cs.cyl((cx, 0.22, 0.68), (cx, 0.22, 0.77), 0.038, M["cup"], 16, r2=0.042)
        cs.cyl((cx, 0.22, 0.765), (cx, 0.22, 0.768), 0.036, M["coffee"], 16)
        cs.beam((cx + 0.04 * s, 0.22, 0.75), (cx + 0.06 * s, 0.22, 0.71), 0.012, 0.012, M["cup"])
        # oxygen mask box (red PUSH tab)
        cs.box((min(1.44 * s, 1.66 * s), -0.15, 0.66), (max(1.44 * s, 1.66 * s), 0.05, 0.75), M["darkmetal"])
        cs.box((min(1.5 * s, 1.58 * s), -0.16, 0.69), (max(1.5 * s, 1.58 * s), -0.15, 0.72), M["red"])
        # ashtray (1983)
        cs.box((min(1.42 * s, 1.52 * s), 0.3, 0.66), (max(1.42 * s, 1.52 * s), 0.38, 0.68), M["metal"])
        # chart clipped to the sidewall under the window
        cs.obox((1.69 * s, -0.62, 0.86), (0.01, 0.28, 0.2), (0, 0, 0), M["paper"])
        cs.box((min(1.685 * s, 1.67 * s), -0.7, 0.95), (max(1.685 * s, 1.67 * s), -0.54, 0.97), M["metal"])
    # nose-wheel tiller (captain side)
    cs.cyl((1.5, -0.62, 0.66), (1.5, -0.62, 0.72), 0.02, M["darkmetal"], 10)
    cs.cyl((1.5, -0.62, 0.72), (1.5, -0.62, 0.745), 0.075, M["black"], 20)
    cs.beam((1.5, -0.62, 0.745), (1.5, -0.55, 0.79), 0.018, 0.018, M["black"])
    cs.obj(ink, uv=0.5, bevel=0.004)


# ---------------------------------------------------------------- seats
def _seat(ink, M, s):
    sb = MB(f"seat_{'c' if s > 0 else 'f'}")
    cx, cy = 0.55 * s, 0.1
    Lt = M["leather"]
    for dx in (-0.12, 0.12):
        sb.box((cx + dx - 0.02, -0.55, 0.0), (cx + dx + 0.02, 0.65, 0.035), M["metal"])
    sb.box((cx - 0.16, cy - 0.22, 0.03), (cx + 0.16, cy + 0.2, 0.36), M["seatbase"])
    sb.box((cx - 0.27, cy - 0.30, 0.36), (cx + 0.27, cy + 0.26, 0.50), Lt)
    sb.cyl((cx - 0.27, cy - 0.30, 0.43), (cx + 0.27, cy - 0.30, 0.43), 0.07, Lt, 14)
    tilt = math.radians(12)
    up = Vector((0, math.sin(tilt), math.cos(tilt)))
    base = Vector((cx, cy + 0.33, 0.50))
    c = base + up * 0.43
    sb.obox(c, (0.52, 0.13, 0.86), (-tilt, 0, 0), Lt)
    for dx in (-0.27, 0.27):  # bolsters
        sb.obox(c + Vector((dx, -0.04, 0.0)), (0.07, 0.16, 0.76), (-tilt, 0, 0), Lt)
    hc = base + up * 0.98 + Vector((0, 0.02, 0))
    sb.obox(hc, (0.34, 0.13, 0.22), (-tilt, 0, 0), Lt)
    sb.obox(base + up * 0.88 + Vector((0, 0.03, 0)), (0.12, 0.08, 0.1), (-tilt, 0, 0), M["seatbase"])
    # armrests on posts
    for dx in (-0.33, 0.33):
        sb.box((cx + dx - 0.035, cy - 0.1, 0.70), (cx + dx + 0.035, cy + 0.32, 0.76), M["leather_plain"])
        sb.box((cx + dx - 0.015, cy + 0.24, 0.5), (cx + dx + 0.015, cy + 0.3, 0.70), M["seatbase"])
    # shoulder harness over the top of the backrest + lap belt buckles
    for dx in (-0.14, 0.14):
        p0 = base + up * 0.86 + Vector((cx * 0 + dx, -0.075, 0))
        sb.beam(p0, p0 + Vector((0, 0.05, 0.08)), 0.05, 0.012, M["strap"])
    sb.box((cx - 0.3, cy + 0.05, 0.5), (cx - 0.27, cy + 0.15, 0.58), M["strap"])
    sb.box((cx + 0.27, cy + 0.05, 0.5), (cx + 0.3, cy + 0.15, 0.58), M["strap"])
    sb.obj(ink, uv=0.3, bevel=0.018, seg=3)


# ---------------------------------------------------------------- control columns + yokes
def _yoke(ink, plain, M, s):
    yb = MB(f"yoke_{'c' if s > 0 else 'f'}")
    cx = 0.55 * s
    yb.cyl((cx, -0.8, 0.0), (cx, -0.8, 0.12), 0.07, M["rubber"], 14, r2=0.045)
    yb.beam((cx, -0.8, 0.05), (cx, -0.67, 0.80), 0.07, 0.07, M["darkmetal"])
    yb.box((cx - 0.05, -0.70, 0.78), (cx + 0.05, -0.62, 0.86), M["darkmetal"])
    yb.beam((cx - 0.17, -0.64, 0.835), (cx + 0.17, -0.64, 0.835), 0.04, 0.035, M["black"])
    for d in (-1, 1):
        yb.cyl((cx + 0.17 * d, -0.64, 0.82), (cx + 0.2 * d, -0.62, 0.99), 0.024, M["black"], 12)
        yb.sphere((cx + 0.2 * d, -0.62, 0.995), (0.026, 0.026, 0.02), M["black"], 10)
        yb.box((cx + 0.17 * d - 0.012, -0.665, 0.93), (cx + 0.17 * d + 0.012, -0.64, 0.95), M["red"])  # disconnect button
    yb.box((cx - 0.075, -0.615, 0.855), (cx + 0.075, -0.6, 0.94), M["darkmetal"])  # checklist holder
    yb.obj(ink, uv=0.3, bevel=0.005)
    ck = quad(plain, f"checklist_{s}", (cx, -0.599, 0.897), (-1, 0, 0), (0, 0, 1), 0.13, 0.075, emis("checklist", (0.93, 0.92, 0.86), 1.0))
    no_shadow(ck)


# ---------------------------------------------------------------- overhead panel with switch arrays
def _overhead(lib, ink, plain, M, rnd):
    y0, z0, y1, z1 = -1.15, 1.93, 0.55, 2.15
    a = math.atan2(z1 - z0, y1 - y0)
    L = math.hypot(y1 - y0, z1 - z0)
    ob = MB("overhead")
    ob.obox(((0, (y0 + y1) / 2, (z0 + z1) / 2 + 0.03)), (1.14, L, 0.06), (a, 0, 0), M["overhead"])
    for s in (1, -1):  # side trims
        ob.obox(((0.585 * s, (y0 + y1) / 2, (z0 + z1) / 2 + 0.02)), (0.03, L, 0.09), (a, 0, 0), M["frame"])
    o = ob.obj(ink, uv=0.55, bevel=0.005)
    # local frame on the underside: e_a across (-X), e_b along the slope, e_h out of the panel (down/back)
    eb = Vector((0, math.cos(a), math.sin(a)))
    eh = Vector((0, math.sin(a), -math.cos(a)))
    ea = Vector((-1, 0, 0))
    F = Matrix((ea, eb, eh)).transposed().to_4x4()
    F.translation = Vector((0, y0, z0))
    sw = MB("ovh_switches", F)
    lights = MB("ovh_lights", F)
    lit_mats = [emis("ovl_amber", (1.0, 0.66, 0.2), 1.0), emis("ovl_green", (0.35, 1.0, 0.5), 1.0),
                emis("ovl_blue", (0.35, 0.65, 1.0), 1.0), emis("ovl_white", (0.95, 0.95, 0.9), 1.0)]
    dim = emis("ovl_dim", (0.22, 0.22, 0.26), 1.0)
    rows = 9
    for r in range(rows):
        b = 0.1 + r * (L - 0.2) / (rows - 1)
        for cidx, ac in enumerate((-0.37, 0.0, 0.37)):
            kind = rnd.choice(["toggle", "toggle", "toggle", "knob", "lights", "guard"])
            if kind in ("toggle", "guard"):
                n = rnd.randint(3, 6)
                for i in range(n):
                    aa = ac + (i - (n - 1) / 2) * 0.05
                    sw.cyl((aa, b, 0.0), (aa, b, 0.008), 0.011, M["black"], 10)
                    tip = Vector((aa, b + rnd.choice((-0.012, 0.012)), 0.036))
                    sw.cyl((aa, b, 0.006), tip, 0.0035, M["metal"], 6)
                    sw.sphere(tip, (0.0055, 0.0055, 0.0055), M["metal"], 6)
                    if kind == "guard" and i % 2 == 0:
                        sw.box((aa - 0.017, b - 0.022, 0.0), (aa + 0.017, b + 0.022, 0.03), M["red"])
            elif kind == "knob":
                for i in range(3):
                    aa = ac + (i - 1) * 0.075
                    sw.cyl((aa, b, 0.0), (aa, b, 0.02), 0.019, M["black"], 14)
                    sw.box((aa - 0.003, b - 0.019, 0.02), (aa + 0.003, b + 0.002, 0.024), M["white"])
            else:
                for i in range(4):
                    aa = ac + (i - 1.5) * 0.06
                    m = rnd.choice(lit_mats) if rnd.random() < 0.45 else dim
                    lights.box((aa - 0.022, b - 0.014, 0.0), (aa + 0.022, b + 0.014, 0.008), m)
    no_shadow(sw.obj(plain, uv=0.3))
    no_shadow(lights.obj(plain, uv=0.3))
    _S["overhead"] = o


# ---------------------------------------------------------------- rear bulkhead, corners (jackets, CB panels, binders)
def _rear(lib, ink, plain, M, sim, rnd):
    rb = MB("rear")
    Y = 2.25
    # door with frame, handle, peephole, kick plate
    rb.box((-0.48, Y - 0.03, 0.0), (0.48, Y, 2.04), M["frame"])
    rb.box((-0.42, Y - 0.05, 0.02), (0.42, Y - 0.02, 1.98), M["door"])
    rb.box((-0.42, Y - 0.055, 0.02), (0.42, Y - 0.05, 0.22), M["metal"])
    rb.box((0.28, Y - 0.08, 1.0), (0.38, Y - 0.05, 1.03), M["metal"])
    rb.cyl((0.3, Y - 0.05, 1.015), (0.3, Y - 0.09, 1.015), 0.02, M["metal"], 10)
    rb.cyl((0.0, Y - 0.05, 1.55), (0.0, Y - 0.06, 1.55), 0.022, M["black"], 12)
    # stowage cabinets under the CB panels on both sidewalls
    for s in (1, -1):
        x0, x1 = sorted((1.42 * s, 1.7 * s))
        rb.box((x0, 0.75, 0.0), (x1, Y, 0.9), M["lining_dk"])
        rb.box((x0 - 0.005 if s > 0 else x0, 1.0, 0.85), (x0 + 0.005 if s > 0 else x1, 1.5, 0.87), M["metal"])
        rb.box((x0, 0.75, 0.9), (x1, Y, 0.92), M["darkmetal"])
        # CB panel frame on the sidewall
        xf = 1.7 * s
        rb.box(sorted((xf, xf - 0.02 * s))[0:1] + [0.8, 0.94], sorted((xf, xf - 0.02 * s))[1:2] + [2.22, 1.98], M["frame"]) if False else None
    for s in (1, -1):
        xf0, xf1 = sorted((1.68 * s, 1.7 * s))
        rb.box((xf0, 0.78, 0.94), (xf1, 2.22, 0.96), M["frame"])
        rb.box((xf0, 0.78, 1.96), (xf1, 2.22, 1.98), M["frame"])
    if not sim:
        for s in (1, -1):
            # observer jump seat folded flat against the bulkhead
            jx = 0.78 * s
            rb.box((jx - 0.2, Y - 0.12, 0.45), (jx + 0.2, Y - 0.02, 1.15), M["leather_plain"] if s > 0 else M["strap"])
            rb.box((jx - 0.2, Y - 0.14, 0.42), (jx + 0.2, Y - 0.02, 0.47), M["seatbase"])
            for dx in (-0.1, 0.1):
                rb.box((jx + dx - 0.02, Y - 0.135, 0.6), (jx + dx + 0.02, Y - 0.12, 1.12), M["red"])
            # coat hook + pilot jacket (navy, four gold stripes on the sleeve) + cap on a shelf
            hx = 1.18 * s
            rb.cyl((hx, Y, 1.92), (hx, Y - 0.07, 1.93), 0.012, M["metal"], 8)
            rb.obox((hx, Y - 0.06, 1.55), (0.36, 0.07, 0.62), (0, 0, 0), M["navy"])
            rb.obox((hx, Y - 0.07, 1.86), (0.2, 0.07, 0.08), (0, 0, 0), M["navy"])
            rb.obox((hx - 0.14 * s, Y - 0.1, 1.46), (0.1, 0.06, 0.52), (0, 0.12 * s, 0), M["navy"])
            for k in range(4):
                rb.obox((hx - 0.15 * s, Y - 0.135, 1.24 + k * 0.03), (0.105, 0.012, 0.012), (0, 0.12 * s, 0), M["gold"])
            for k in range(3):
                rb.cyl((hx + 0.03, Y - 0.095, 1.38 + k * 0.1), (hx + 0.03, Y - 0.1, 1.38 + k * 0.1), 0.012, M["gold"], 8)
            # shelf with the cap and a row of manuals
            sx0, sx1 = sorted((0.45 * s, 1.0 * s))
            rb.box((sx0, Y - 0.25, 1.98), (sx1, Y, 2.0), M["darkmetal"])
            capx = 0.62 * s
            rb.cyl((capx, Y - 0.13, 2.0), (capx, Y - 0.13, 2.08), 0.1, M["navy"], 18, r2=0.115)
            rb.obox((capx, Y - 0.24, 2.01), (0.16, 0.08, 0.012), (0.2, 0, 0), M["black"])
            rb.box((capx - 0.03, Y - 0.235, 2.04), (capx + 0.03, Y - 0.225, 2.075), M["gold"])
            # fire extinguisher (red) in its bracket, crash axe
            if s > 0:
                rb.cyl((1.52, Y - 0.08, 0.95), (1.52, Y - 0.08, 1.32), 0.06, M["red"], 16)
                rb.cyl((1.52, Y - 0.08, 1.32), (1.52, Y - 0.08, 1.38), 0.02, M["black"], 10)
                rb.beam((1.52, Y - 0.08, 1.38), (1.45, Y - 0.12, 1.2), 0.012, 0.012, M["black"])
                rb.box((1.45, Y - 0.03, 1.05), (1.59, Y, 1.08), M["darkmetal"])
            else:
                rb.beam((-1.52, Y - 0.04, 0.98), (-1.52, Y - 0.04, 1.42), 0.03, 0.03, M["red"])
                rb.obox((-1.52, Y - 0.05, 1.42), (0.14, 0.02, 0.05), (0, 0, 0), M["darkmetal"])
            # flight bag on the floor by the seat
            bx = 1.25 * s
            rb.box((bx - 0.2, 0.7, 0.0), (bx + 0.2, 0.92, 0.36), M["wood"])
            rb.box((bx - 0.21, 0.69, 0.3), (bx + 0.21, 0.93, 0.32), M["tan"])
            rb.beam((bx - 0.08, 0.81, 0.36), (bx + 0.08, 0.81, 0.36), 0.03, 0.03, M["wood"])
            # headset hanging on the sidewall
            hy = 0.55
            rb.cyl((1.69 * s, hy, 1.28), (1.66 * s, hy, 1.28), 0.012, M["metal"], 8)
            rb.cyl((1.64 * s, hy - 0.08, 1.2), (1.64 * s, hy - 0.08, 1.16), 0.05, M["black"], 14)
            rb.cyl((1.64 * s, hy + 0.08, 1.2), (1.64 * s, hy + 0.08, 1.16), 0.05, M["black"], 14)
            rb.beam((1.64 * s, hy - 0.08, 1.22), (1.64 * s, hy, 1.29), 0.02, 0.02, M["black"])
            rb.beam((1.64 * s, hy, 1.29), (1.64 * s, hy + 0.08, 1.22), 0.02, 0.02, M["black"])
    else:
        # simulator: instructor operating station (IOS) behind the captain + a red warning beacon
        rb.box((0.35, 1.68, 0.0), (1.66, Y, 0.72), M["darkmetal"])
        rb.box((0.33, 1.65, 0.72), (1.68, Y, 0.76), M["black"])
        for k, (mx, rz) in enumerate(((0.72, -0.18), (1.28, 0.18))):
            rb.obox((mx, 2.02, 1.02), (0.48, 0.05, 0.36), (math.radians(-8), 0, rz), M["bezel"])
            rb.obox((mx, 2.06, 0.8), (0.1, 0.06, 0.08), (0, 0, rz), M["bezel"])
        rb.obox((1.0, 1.82, 0.775), (0.46, 0.16, 0.025), (0, 0, 0), M["bezel"])
        rb.cyl((1.0, Y, 2.0), (1.0, Y - 0.06, 2.0), 0.05, M["black"], 14)
        for s in (1, -1):
            hx = 1.18 * s
            if s < 0:
                rb.obox((hx, Y - 0.06, 1.55), (0.36, 0.07, 0.62), (0, 0, 0), M["navy"])
    rb.obj(ink, uv=0.5, bevel=0.006)
    # CB panels (textured), binders, placards
    cbm = tm(lib, "cb", None, "cb.png")
    for s in (1, -1):
        q = quad(ink, f"cbpanel{s}", (1.678 * s, 1.5, 1.46), (0, s, 0), (0, 0, 1), 1.44, 1.0, cbm, (0, 0, 2.88, 2.0))
    if not sim:
        bnd = tm(lib, "binders", None, "binders.png")
        for s in (1, -1):
            quad(ink, f"binders{s}", (0.72 * s, Y - 0.2, 2.1), (-1, 0, 0), (0, 0, 1), 0.52, 0.2, bnd, (0, 0, 1, 0.8)) if False else None
            # binders standing on the cabinet tops along the sidewall
            q = quad(ink, f"binders_side{s}", (1.6 * s, 1.55, 1.05), (0, s, 0), (0, 0, 1), 1.0, 0.25, bnd)
    pl = tm(lib, "plac_door", None, "plac_door.png")
    quad(ink, "plac_door", (0, Y - 0.051, 1.72), (-1, 0, 0), (0, 0, 1), 0.3, 0.11, pl)
    if not sim:
        pe = tm(lib, "plac_ext", None, "plac_ext.png")
        quad(ink, "plac_ext", (1.52, Y - 0.005, 1.48), (-1, 0, 0), (0, 0, 1), 0.2, 0.075, pe)
    if sim:
        ios = []
        for k, (mx, rz) in enumerate(((0.72, -0.18), (1.28, 0.18))):
            mat = emis(f"ios{k}", (1, 1, 1), 1.0, "ios_on.png")
            c = Vector((mx, 2.02, 1.02)) + Euler((math.radians(-8), 0, rz)).to_matrix() @ Vector((0, -0.0255, 0))
            R = Euler((math.radians(-8), 0, rz)).to_matrix()
            q = quad(plain, f"ios{k}", c, R @ Vector((-1, 0, 0)), R @ Vector((0, 0, 1)), 0.44, 0.33, mat)
            no_shadow(q)
            ios.append(mat)
        _S["ios"] = ios
        bm = emis("beacon", (1.0, 0.15, 0.1), 0.15)
        no_shadow(disc(plain, "beacon", (1.0, Y - 0.061, 2.0), (-1, 0, 0), (0, 0, 1), 0.048, bm))
        _S["beacon"] = (bm, glow_sprite(plain, "beacon", Vector((1.0, Y - 0.12, 2.0)), 0.7, (1.0, 0.15, 0.1), 0.0))


# ---------------------------------------------------------------- outside: cloud sea + a few toon clouds (golden)
def _outside(lib, plain):
    sea_m = tm(lib, "cloudsea", None, "cloudsea.png")
    sea = quad(plain, "cloudsea", (0, 0, -150), (1, 0, 0), (0, 1, 0), 9000, 9000, sea_m, (0, 0, 9000 / 420, 9000 / 420))
    no_shadow(sea)
    _S["sea"] = sea
    cm = MB("clouds")
    lit = tm(lib, "cloud", "#ffe9d8")
    rnd = random.Random(5)
    clouds = []
    for i in range(14):
        cx = rnd.uniform(-1800, 1800)
        cy = rnd.uniform(-3200, 400)
        if abs(cx) < 200 and cy > -600:
            cx += 600
        cz = rnd.uniform(-150, -95)
        s = rnd.uniform(40, 110)
        for k in range(rnd.randint(3, 6)):
            r = s * rnd.uniform(0.45, 0.9)
            cm.sphere((cx + rnd.uniform(-1, 1) * s, cy + rnd.uniform(-0.6, 0.6) * s, cz + r * 0.3), (r, r * 0.9, r * 0.6), lit, 14)
        clouds.append(cy)
    o = cm.obj(plain, uv=50)
    no_shadow(o)
    _S["clouds"] = o


# ---------------------------------------------------------------- simulator hall + projection screen (shot 19)
def _sim_hall(lib, ink, plain, M):
    hall = MB("simhall")
    dk = emis("hall", (0.035, 0.04, 0.07), 1.0)
    hall.box((-9, -9, -3.0), (9, -8.9, 7), dk)
    hall.box((-9, 8.9, -3.0), (9, 9, 7), dk)
    hall.box((-9, -9, -3.0), (-8.9, 9, 7), dk)
    hall.box((8.9, -9, -3.0), (9, 9, 7), dk)
    hall.box((-9, -9, 6.9), (9, 9, 7), dk)
    hall.box((-9, -9, -3.0), (9, 9, -2.9), dk)
    no_shadow(hall.obj(plain, uv=2))
    # projection screen: a cylinder section in front of the cab, runway image
    bm = bmesh.new()
    R, cy, N = 3.4, -0.3, 40
    a0, a1 = math.radians(-80), math.radians(80)
    vs = []
    for i in range(N + 1):
        a = a0 + (a1 - a0) * i / N
        x, y = R * math.sin(a), cy - R * math.cos(a)
        vs.append((bm.verts.new((x, y, -0.4)), bm.verts.new((x, y, 3.2))))
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(N):
        f = bm.faces.new((vs[i][0], vs[i + 1][0], vs[i + 1][1], vs[i][1]))
        for l, (u, v) in zip(f.loops, ((i / N, 0), ((i + 1) / N, 0), ((i + 1) / N, 1), (i / N, 1))):
            l[uvl].uv = (u, v)
    me = bpy.data.meshes.new("projscreen")
    bm.to_mesh(me)
    bm.free()
    pm = emis("projection", (1, 1, 1), 1.0, "runway.png")
    me.materials.append(pm)
    o = bpy.data.objects.new("projscreen", me)
    plain.objects.link(o)
    no_shadow(o)
    _S["projection"] = pm


# ---------------------------------------------------------------- practical lights
def _light(name, kind, loc, energy, color, size=0.05, rot=None, spot=None, shadow=True):
    ld = bpy.data.lights.new(name, kind)
    ld.energy, ld.color = energy, color
    if kind == "AREA":
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size if isinstance(size, (int, float)) else size[0], size if isinstance(size, (int, float)) else size[1]
    else:
        ld.shadow_soft_size = size
    if kind == "SPOT" and spot:
        ld.spot_size, ld.spot_blend = math.radians(spot), 0.6
    if hasattr(ld, "use_shadow"):
        ld.use_shadow = shadow
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if rot is not None:
        o.rotation_euler = Vector(rot).to_track_quat("-Z", "Y").to_euler()
    return o


def _lights(sim, shot):
    L = {}
    warm = (1.0, 0.82, 0.6)
    # panel flood from under the glareshield lip
    L["flood"] = _light("ck_flood", "AREA", (0, -0.86, 0.93), 6.0, warm, (2.6, 0.04), rot=(0, -0.55, -1))
    # chart lights over the rear corners (warm pools on CB panels, jackets, binders)
    for s in (1, -1):
        L[f"chart{s}"] = _light(f"ck_chart{s}", "SPOT", (1.25 * s, 1.35, 2.14), 22.0, (1.0, 0.72, 0.42), 0.05, rot=(0.25 * s, 0.55, -1), spot=75)
    # dome glow on the ceiling (cool fill, weak)
    L["dome"] = _light("ck_dome", "POINT", (0, 1.2, 2.0), 6.0, (0.75, 0.82, 1.0), 0.3, shadow=False)
    # screen spill toward the pilots
    for k, x in enumerate((0.62, 0.0, -0.62)):
        L[f"scr{k}"] = _light(f"ck_scr{k}", "AREA", (x, -0.9, 0.64), 1.5, (0.55, 0.75, 1.0), (0.25, 0.4), rot=(0, 1, 0.15), shadow=False)
    # caution / warning light spill
    for s, who in ((1, "c"), (-1, "f")):
        L[f"amber_{who}"] = _light(f"ck_amber_{who}", "POINT", (1.1 * s, -0.72, 1.02), 0.0, (1.0, 0.6, 0.15), 0.03, shadow=False)
        L[f"red_{who}"] = _light(f"ck_red_{who}", "POINT", (1.235 * s, -0.72, 1.02), 0.0, (1.0, 0.12, 0.08), 0.03, shadow=False)
    if sim:
        L["beacon"] = _light("ck_beacon", "POINT", (1.0, 2.1, 1.95), 0.0, (1.0, 0.12, 0.08), 0.05, shadow=False)
        L["ios"] = _light("ck_ios", "AREA", (1.0, 1.85, 1.05), 4.0, (0.6, 0.8, 1.0), (0.9, 0.3), rot=(0, -1, 0), shadow=False)
    _S["lights"] = L


def _sun(shot, sim):
    """re-aim the scene sun for the cockpit: low sunset ahead (golden) / the projection's glow ahead (sim)"""
    sun = bpy.data.objects.get("Sun")
    if not sun:
        return
    dirs = {5: (-0.167, -0.956, 0.242), 6: (0.12, -0.96, 0.25), 8: (-0.64, -0.73, 0.24), 10: (0.67, -0.70, 0.24), 19: (0.12, -0.9, 0.42)}
    d = Vector(dirs.get(shot, (0.0, -0.96, 0.26))).normalized()
    sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if not sim:  # the sunset rakes straight in through the open windscreen: unshadowed so every aft-facing surface glows
        sun.data.use_shadow = False
        sun.data.energy = 6.0
    else:
        sun.data.energy = 3.0
        for L in (_S.get("lights") or {}).values():
            pass


# ====================================================================== animate
def _blink(f, period=8):
    return int(math.floor(f / period)) % 2 == 0


def _ink_width_setup():
    """screen-constant ink (same recipe as apron.py): stroke radius = W_px(d) * d * tan(fov/2) / 1920"""
    ink = bpy.data.objects.get("Ink")
    if ink is None or ink.modifiers.get("CockpitInkWidth"):
        return
    ng = bpy.data.node_groups.new("CockpitInkWidth", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    cam = N.new("GeometryNodeInputActiveCamera")
    oi = N.new("GeometryNodeObjectInfo"); oi.transform_space = "ORIGINAL"
    pos = N.new("GeometryNodeInputPosition")
    dist = N.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"
    px = N.new("ShaderNodeMapRange"); px.interpolation_type = "SMOOTHSTEP"
    px.inputs[1].default_value = 0.4; px.inputs[2].default_value = 6.0
    px.inputs[3].default_value = INK_NEAR_PX; px.inputs[4].default_value = INK_FAR_PX
    m1 = N.new("ShaderNodeMath"); m1.operation = "MULTIPLY"
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
    kv = N.new("ShaderNodeValue"); kv.outputs[0].default_value = math.tan(math.radians(20)) / 1920
    scr = N.new("GeometryNodeSetCurveRadius")
    L.new(cam.outputs[0], oi.inputs[0]); L.new(oi.outputs["Location"], dist.inputs[0]); L.new(pos.outputs[0], dist.inputs[1])
    L.new(dist.outputs["Value"], px.inputs[0])
    L.new(dist.outputs["Value"], m1.inputs[0]); L.new(px.outputs[0], m1.inputs[1])
    L.new(m1.outputs[0], m2.inputs[0]); L.new(kv.outputs[0], m2.inputs[1])
    L.new(gi.outputs[0], scr.inputs[0]); L.new(m2.outputs[0], scr.inputs["Radius"]); L.new(scr.outputs[0], go.inputs[0])
    mod = ink.modifiers.new("CockpitInkWidth", "NODES"); mod.node_group = ng
    _S["ink_k"] = kv


def animate(ctx, layer, info):
    f = info["f"]
    _ink_width_setup()
    if _S.get("ink_k") is not None:
        _S["ink_k"].outputs[0].default_value = math.tan(math.radians(layer["cam"]["fov"]) / 2) / 1920.0
    shot = layer.get("id", ctx["shot"])
    sim = _S.get("sim", False)
    L = _S.get("lights", {})
    # --- EFIS screens
    on, k = True, 1.0
    if not sim:
        if shot in (8, 10):
            on = False
        elif shot == 6:
            fi = int(math.floor(f))
            if f >= F_DARK + 3:
                on = False
            elif f >= F_DARK:
                on, k = True, [0.55, 0.3, 0.12][min(2, fi - F_DARK)]
            elif f >= F_DARK - 5:
                k = 0.45 if fi % 2 else 1.0  # power flicker before the screens die
    for name, (mat, img) in _S.get("screens", {}).items():
        tex = mat.node_tree.nodes["Tex"]
        want = img if on else "crt_off.png"
        if tex.image is None or os.path.basename(tex.image.filepath) != want:
            tex.image = bpy.data.images.load(T(want), check_existing=True)
        mat.node_tree.nodes["Em"].inputs["Strength"].default_value = (k if on else 1.0)
    for i in range(3):
        if f"scr{i}" in L:
            L[f"scr{i}"].data.energy = 1.5 * k if on else 0.0
    if "flood" in L:
        L["flood"].data.energy = 6.0 * (k if on else 0.35)
    # --- master caution / warning
    amber = {"c": False, "f": False}
    red = {"c": False, "f": False}
    if not sim:
        if shot == 5:
            amber["c"] = f >= F_ALARM1 and _blink(f - F_ALARM1)
            amber["f"] = f >= F_ALARM2 and _blink(f - F_ALARM1)
        elif shot == 6:
            amber["c"] = amber["f"] = _blink(f - F_ALARM1)
    else:
        if f >= F_CRASH:
            red["c"] = red["f"] = True
        elif f >= F_SIM:
            red["c"] = red["f"] = _blink(f - F_SIM)
    for a in _S.get("alarms", []):
        st = (amber if a["kind"] == "caution" else red)[a["side"]]
        a["mat"].node_tree.nodes["Em"].inputs["Strength"].default_value = 1.15 if st else 0.12
        a["glow"].data.materials[0].node_tree.nodes["Gain"].inputs[1].default_value = 1.4 if st else 0.0
    for who in ("c", "f"):
        if f"amber_{who}" in L:
            L[f"amber_{who}"].data.energy = 4.0 if amber[who] else 0.0
            L[f"red_{who}"].data.energy = 5.0 if red[who] else 0.0
    # --- simulator: beacon, IOS monitors, projection at the crash
    if sim:
        bon = f >= F_SIM and (f >= F_CRASH or _blink(f - F_SIM))
        if "beacon" in _S:
            bm, g = _S["beacon"]
            bm.node_tree.nodes["Em"].inputs["Strength"].default_value = 1.2 if bon else 0.15
            g.data.materials[0].node_tree.nodes["Gain"].inputs[1].default_value = 1.6 if bon else 0.0
        if "beacon" in L:
            L["beacon"].data.energy = 30.0 if bon else 0.0
        crash = f >= F_CRASH
        for mat in _S.get("ios", []):
            want = "ios_crash.png" if crash else "ios_on.png"
            tex = mat.node_tree.nodes["Tex"]
            if os.path.basename(tex.image.filepath) != want:
                tex.image = bpy.data.images.load(T(want), check_existing=True)
            mat.node_tree.nodes["Em"].inputs["Strength"].default_value = (1.0 if not crash or _blink(f - F_CRASH, 6) else 0.6)
        if "projection" in _S:
            tex = _S["projection"].node_tree.nodes["Tex"]
            want = "runway_crash.png" if crash else "runway.png"
            if os.path.basename(tex.image.filepath) != want:
                tex.image = bpy.data.images.load(T(want), check_existing=True)
    # --- clouds scroll toward +Y (the jet flies toward -Y)
    t = f / 30.0
    if "sea" in _S:
        _S["sea"].location.y = (CLOUD_SPEED * t) % 420.0
    if "clouds" in _S:
        _S["clouds"].location.y = ((CLOUD_SPEED * t + 1800) % 3600) - 1800
    # --- glow sprites face the camera
    cam = bpy.context.scene.camera
    if cam is not None:
        cp = cam.matrix_world.translation
        for o in _S.get("sprites", []):
            o.rotation_euler = (cp - o.location).to_track_quat("Z", "Y").to_euler()
