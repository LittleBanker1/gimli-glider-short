# APRON set: Montreal airport, 1983, sunny day (shots 2, 3, 4, 18, 20).
# The jet (another module) is parked at the origin, nose toward -Y; its LEFT side is +X (the fuel truck, the captain
# and the fueler are there), the terminal is 70 m away on the -X side (facade plane x = -70 facing +X).
# Built from primitives (bmesh batches with metre box-UVs), Pillow-painted textures in tex\apron (see
# paint_textures.py there) and Kenney kits (cars, trees, cones). All surfaces use the shared ToonSurf look.
# animate(): the fuel-gauge needle (full -> half, picture frames 484-498 in shot 4), screen-constant ink width
# (a geometry-nodes modifier on the shared Line Art object: radius ~ distance to camera), and hoses/cables that
# are fitted to the real jet geometry by ray casts on the first frame.
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

INK_RADIUS = 0.02  # fallback only: animate() replaces it with a screen-space width (see _ink_width)
TEX = r"D:\gimli3d\blender\tex\apron"
KENNEY = r"D:\gimli3d\kenney"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_BLACK = r"C:\Windows\Fonts\ariblk.ttf"

# ---------------------------------------------------------------- layout of this set (Blender metres)
TRUCK_X = (14.6, 16.9)          # fuel truck body sides (layout.APRON fuel_truck ~ (15.7, -0.5))
TRUCK_Y = (-5.1, 2.4)           # rear deck end .. front bumper (it faces aft, +Y)
GAUGE = Vector((15.17, -4.85, 1.53))   # dial centre: the shot-4 insert camera looks straight at it
GAUGE_N = Vector((math.cos(math.radians(-15)), math.sin(math.radians(-15)), 0.0))  # dial normal (toward +X, yawed to the camera)
TERM_X = -70.0                  # terminal facade plane
TERM_Y = (-112.0, 112.0)
NOSE_GEAR_Y = -18.6
MAIN_GEAR = (4.6, 3.2)

_S = {}  # runtime state shared between build() and animate()


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
        return self.lib.toon("ap_" + hexcol.lstrip("#") + ("_ao" if ao else ""), hexcol, ao=ao)

    def t(self, name, image, size=(1.0, 1.0), tint=None, ao=False):
        """textured toon; the batch UVs are in metres, so size = metres covered by one texture repeat"""
        m = bpy.data.materials.get("ap_" + name)
        if m:
            return m
        m = self.lib.toon("ap_" + name, tint, image=tex(image), repeat=(1.0 / size[0], 1.0 / size[1]), ao=ao)
        return m

    def emit(self, name, hexcol, strength=1.0):
        m = bpy.data.materials.get("ap_e_" + name)
        if m:
            return m
        m = bpy.data.materials.new("ap_e_" + name); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
        e.inputs[0].default_value = (*self.lib.hex_rgb(hexcol), 1); e.inputs[1].default_value = strength
        nt.links.new(e.outputs[0], o.inputs[0])
        return m

    def cutout(self, name, image, size=(1.0, 1.0), tint=None):
        """toon with the image alpha as a hard cut (chain-link fence)"""
        m = bpy.data.materials.get("ap_" + name)
        if m:
            return m
        m = bpy.data.materials.new("ap_" + name); m.use_nodes = True
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
        m = bpy.data.materials.get("ap_" + name)
        if m:
            return m
        m = bpy.data.materials.new("ap_" + name); m.use_nodes = True
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


def text_mesh(col, body, size, mat, loc, rot=(0, 0, 0), font=FONT_BOLD, extrude=0.0, align="CENTER", name="txt"):
    """3D text converted to a mesh object (flat or extruded); rot = euler (radians)"""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = "CENTER"
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    me.materials.clear(); me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o.location = loc; o.rotation_euler = rot
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
    for o in new:
        for s in getattr(o, "material_slots", []):
            if s.material and not s.material.name.startswith("T_"):
                s.material = lib.to_toon(s.material, recolor)
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


def car_paint(lib, colour):
    """variant of the Kenney car colormap material with a repainted body column"""
    name = "ap_car_" + colour
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = lib.toon_group()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(f"car_{colour}.png"); t.interpolation = "Closest"
    nt.links.new(t.outputs[0], g.inputs["Albedo"]); nt.links.new(g.outputs[0], o.inputs[0])
    return m


# ================================================================ build
def build(ctx):
    lib = ctx["lib"]
    ink, plain, shot = ctx["ink"], ctx["plain"], ctx["shot"]
    M = Mats(lib)
    rng = random.Random(1983)
    _S.clear()
    _S["shot"] = shot
    P = dict(  # palette
        white="#f4f0e6", cream="#ece2c8", red="#d8432c", dred="#9c2a22", yellow="#f4b72c", orange="#ef7a28",
        blue="#2f62b0", navy="#25305e", sky="#6f9fe0", grey="#a3a8b2", lgrey="#c9ccd2", dgrey="#4b4f5b",
        black="#27252d", tyre="#2b2a31", chrome="#d3d7de", glass="#2c4778", green="#3f8a4a", teal="#2f8a84",
        concrete="#e7dfcc", brown="#7a4a2c",
    )
    C = {k: M.c(v) for k, v in P.items()}

    _ground(ctx, M, C, P)
    _markings(ctx, M, C, P)
    _terminal(ctx, M, C, P, rng)
    _jetbridges(ctx, M, C, P)
    _tower_and_north(ctx, M, C, P, rng)
    _fuel_truck(ctx, M, C, P)
    _gse(ctx, M, C, P, rng)
    _light_masts(ctx, M, C, P)
    _other_jet(ctx, M, C, P)
    _far(ctx, M, C, P, rng)
    _clouds(ctx, M)


# ---------------------------------------------------------------- ground
def _ground(ctx, M, C, P):
    lib, ink, plain = ctx["lib"], ctx["ink"], ctx["plain"]
    # apron concrete: tile (20 m) x overlay (256 m, centred on the origin) + AO
    m = bpy.data.materials.new("ap_apron"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); L = nt.links
    o = nt.nodes.new("ShaderNodeOutputMaterial"); g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = lib.toon_group()
    uv = nt.nodes.new("ShaderNodeTexCoord")
    m1 = nt.nodes.new("ShaderNodeMapping"); m1.inputs["Scale"].default_value = (1 / 20, 1 / 20, 1)
    t1 = nt.nodes.new("ShaderNodeTexImage"); t1.image = img("concrete.png")
    m2 = nt.nodes.new("ShaderNodeMapping"); m2.inputs["Scale"].default_value = (1 / 256, 1 / 256, 1); m2.inputs["Location"].default_value = (0.5, 0.5, 0)
    t2 = nt.nodes.new("ShaderNodeTexImage"); t2.image = img("overlay.png"); t2.extension = "EXTEND"
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
    L.new(uv.outputs["UV"], m1.inputs[0]); L.new(m1.outputs[0], t1.inputs[0])
    L.new(uv.outputs["UV"], m2.inputs[0]); L.new(m2.outputs[0], t2.inputs[0])
    L.new(t1.outputs[0], mul.inputs[6]); L.new(t2.outputs[0], mul.inputs[7]); L.new(mul.outputs[2], g.inputs["Albedo"])
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 1.2
    L.new(ao.outputs["AO"], g.inputs["AO"]); L.new(g.outputs[0], o.inputs[0])
    B = Batch("apron_ground")
    # apron slab: x -100..72, y -160..100 (UV in metres, origin-centred)
    B.quad([(-100, -160, 0), (72, -160, 0), (72, 100, 0), (-100, 100, 0)], m,
           uvs=[(-100, -160), (72, -160), (72, 100), (-100, 100)])
    B.build(ink)
    # grass everywhere else (slightly lower), with large mowing variation
    gm = M.t("grass", "grass.png", (4, 4), tint="#ffffff")
    G = Batch("grass")
    R = 3000
    G.quad([(-R, -R, -0.04), (R, -R, -0.04), (R, R, -0.04), (-R, R, -0.04)], gm, uvs=[(-R, -R), (R, -R), (R, R), (-R, R)])
    G.build(plain)
    # asphalt: service road along the terminal, taxiway north of the apron, the runway far north, car park
    am = M.t("asphalt", "asphalt.png", (8, 8), tint="#ffffff")
    A = Batch("asphalt")
    for (x0, y0, x1, y1) in ((-56, -160, -44, 100),      # service road
                             (-100, 100, 400, 104),      # apron edge strip
                             (-20, 150, 500, 172),       # taxiway
                             (-300, 330, 900, 390),      # runway
                             (-54, 108, -14, 150),       # staff car park
                             (-100, 104, -56, 150)):     # tower forecourt
        A.quad([(x0, y0, 0.01), (x1, y0, 0.01), (x1, y1, 0.01), (x0, y1, 0.01)], am, uvs=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    A.build(plain)


def _markings(ctx, M, C, P):
    """paint on the ground (no ink): lead-in line, stop bars, stand number, red safety lines, GSE boxes, road lines"""
    plain = ctx["plain"]
    Y, R, W = M.c("#f6c31e"), M.c("#d8382c"), M.c("#f2f0ea")
    B = Batch("markings")
    z = 0.035

    def strip(p0, p1, w, mat, zz=z):
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0); d.z = 0; d.normalize(); n = Vector((-d.y, d.x, 0)) * (w / 2)
        B.quad([(p0 - n)[:2] + (zz,), (p1 - n)[:2] + (zz,), (p1 + n)[:2] + (zz,), (p0 + n)[:2] + (zz,)], mat)

    def dashed(p0, p1, w, mat, dash, gap, zz=z):
        p0, p1 = Vector(p0), Vector(p1)
        L = (p1 - p0).length; d = (p1 - p0) / L
        s = 0.0
        while s < L:
            e = min(L, s + dash)
            strip(p0 + d * s, p0 + d * e, w, mat, zz)
            s += dash + gap

    # lead-in line on the jet's centreline (the jet taxied in from the north), with a curve from the taxiway
    strip((0, NOSE_GEAR_Y, 0), (0, 92, 0), 0.3, Y)
    pts = [Vector((0, 92, 0))]
    for k in range(1, 13):
        a = math.radians(90 * k / 12)
        pts.append(Vector((12 - 12 * math.cos(a), 92 + 12 * math.sin(a), 0)))
    for a, b in zip(pts, pts[1:]):
        strip(a, b, 0.3, Y)
    strip((12, 104, 0), (300, 104, 0), 0.3, Y)
    # stop bars with aircraft-type labels (readable from the south cameras)
    for y, lab, w in ((NOSE_GEAR_Y, "767", 2.4), (NOSE_GEAR_Y + 3.0, "DC-9", 1.6), (NOSE_GEAR_Y - 2.5, "L-1011", 1.6)):
        strip((-w, y, 0), (w, y, 0), 0.45, Y)
        text_mesh(plain, lab, 0.75, Y, (w + 1.6, y, z), font=FONT_BOLD, name="stoplabel")
    # stand number box in front of the nose (seen in shot 18) and at the stand entry
    for (x, y, s) in ((-0.2, -31.6, 2.2), (0, 70, 3.2)):
        B.quad([(x - s * 0.95, y - s * 0.62, z - 0.005), (x + s * 0.95, y - s * 0.62, z - 0.005),
                (x + s * 0.95, y + s * 0.62, z - 0.005), (x - s * 0.95, y + s * 0.62, z - 0.005)], M.c("#2a2a32"))
        text_mesh(plain, "12", s, Y, (x, y, z + 0.004), font=FONT_BLACK, name="standno")
    # red equipment restraint line around the stand + hatched no-parking corners
    ex0, ex1, ey0, ey1 = -27.0, 27.0, -30.0, 31.0
    for a, b in (((ex0, ey0), (ex1, ey0)), ((ex1, ey0), (ex1, ey1)), ((ex1, ey1), (ex0, ey1)), ((ex0, ey1), (ex0, ey0))):
        strip(a + (0,), b + (0,), 0.25, R)
    for k in range(7):  # hatch in the nose corner (equipment keep-out in front of the nose)
        strip((ex1 - 4 - k * 1.4, ey0, 0), (ex1 - k * 1.4, ey0 + 4, 0), 0.22, R)
    # white GSE parking boxes east of the stand, with labels
    for i in range(4):
        x0, y0 = 31.0, -26.0 + i * 7.5
        for a, b in (((x0, y0), (x0 + 12, y0)), ((x0 + 12, y0), (x0 + 12, y0 + 6)), ((x0 + 12, y0 + 6), (x0, y0 + 6)), ((x0, y0 + 6), (x0, y0))):
            strip(a + (0,), b + (0,), 0.18, W)
        text_mesh(plain, "GSE", 0.9, W, (x0 + 10.0, y0 + 1.0, z), font=FONT_BOLD, name="gse")
    # service road: edge lines, dashed centre, stop line + zebra crossing at the bridge
    strip((-56, -160, 0), (-56, 100, 0), 0.2, W); strip((-44, -160, 0), (-44, 100, 0), 0.2, W)
    dashed((-50, -160, 0), (-50, 100, 0), 0.18, W, 3.0, 3.0)
    for k in range(8):
        strip((-55 + k * 1.4, -24, 0), (-55 + k * 1.4, -20, 0), 0.7, W)
    text_mesh(plain, "STOP", 1.4, W, (-47, -28, z), rot=(0, 0, math.pi / 2), font=FONT_BOLD, name="stop")
    # wingtip clearance dashes + the safety line along the terminal
    dashed((-40, -150, 0), (-40, 100, 0), 0.25, R, 2.0, 2.0)
    # fuel hydrant pits (yellow ring + dark lid) near the wings
    for (x, y) in ((12.5, 1.5), (-12.5, 1.5), (13.5, 5.5), (-13.5, 5.5)):
        B.disc((x, y, z), (0, 0, 1), 0.55, Y, seg=20)
        B.disc((x, y, z + 0.004), (0, 0, 1), 0.4, M.c("#3a3b42"), seg=20)
    # taxiway centreline + yellow apron edge line
    strip((-20, 161, 0), (500, 161, 0), 0.3, Y)
    strip((-100, 100.4, 0), (400, 100.4, 0), 0.2, Y)
    # car park stall lines
    for row in range(3):
        y0 = 112 + row * 12.5
        for k in range(15):
            x = -52 + k * 2.6
            strip((x, y0, 0), (x, y0 + 5.0, 0), 0.12, W)
    # runway: threshold bars + dashed centreline
    dashed((-300, 360, 0), (900, 360, 0), 0.9, W, 30, 20)
    for k in range(12):
        strip((-290, 334 + k * 4.6, 0), (-262, 334 + k * 4.6, 0), 1.8, W)
    B.build(plain)


# ---------------------------------------------------------------- terminal
def _terminal(ctx, M, C, P, rng):
    ink, plain = ctx["ink"], ctx["plain"]
    x0 = TERM_X
    ya, yb = TERM_Y
    fin = M.c("#efe7d4", ao=True)
    conc = M.c("#ddd3bd", ao=True)
    roofm = M.c("#a59c8e")
    glass = M.t("glass", "glass_bay.png", (8.0, 6.5), tint="#ffffff")
    gfl = M.t("gfloor", "ground_floor.png", (8.0, 4.5), tint="#ffffff")
    sign = M.t("sign", "sign_band.png", (64.0, 3.5), tint="#ffffff")
    B = Batch("terminal")
    # main volume (behind the facade): roof slab + back
    B.box((x0 - 26, ya, 0), (x0 - 1.0, yb, 14.0), conc, mats=dict(top=roofm))
    # ground floor: recessed glazing with doors
    B.quad([(x0 - 0.8, ya, 0.0), (x0 - 0.8, yb, 0.0), (x0 - 0.8, yb, 4.5), (x0 - 0.8, ya, 4.5)], gfl,
           uvs=[(ya / 8, 0), (yb / 8, 0), (yb / 8, 1), (ya / 8, 1)])
    # canopy slab over the ground floor (deep shadow line)
    B.box((x0 - 1.0, ya - 1, 4.5), (x0 + 4.5, yb + 1, 5.1), fin)
    # curtain wall (upper floors)
    B.quad([(x0 - 0.2, ya, 5.1), (x0 - 0.2, yb, 5.1), (x0 - 0.2, yb, 11.2), (x0 - 0.2, ya, 11.2)], glass,
           uvs=[(ya / 8, 0), (yb / 8, 0), (yb / 8, 1), (ya / 8, 1)])
    # signage band (orange fascia) + roof parapet
    B.box((x0 - 1.0, ya - 1, 11.2), (x0 + 0.9, yb + 1, 14.6), conc, mats=dict(px=sign))
    # re-UV the sign face explicitly
    for f in B.bm.faces:
        if f.material_index == B._mi(sign):
            for l in f.loops:
                co = l.vert.co
                l[B.uv].uv = (co.y / 64.0, (co.z - 11.2) / 3.4)
    B.box((x0 - 26, ya - 1, 14.6), (x0 + 0.9, yb + 1, 15.2), roofm)
    # concrete fins every 8 m (full height, proud of the glass)
    y = ya
    while y <= yb + 0.01:
        B.box((x0 - 0.2, y - 0.35, 0.0), (x0 + 1.6, y + 0.35, 14.0), fin)
        y += 8.0
    # rooftop: plant rooms, vents, antenna masts
    for k in range(9):
        yy = ya + 15 + k * 24 + rng.uniform(-4, 4)
        B.box((x0 - 20, yy, 15.2), (x0 - 10, yy + rng.uniform(6, 11), 15.2 + rng.uniform(1.8, 3.2)), M.c("#cfc6b4"))
        B.cyl((x0 - 6, yy - 3, 15.2), (x0 - 6, yy - 3, 17.0), 0.6, mat=C["lgrey"], seg=10)
    for yy in (-40.0, 30.0, 88.0):
        B.cyl((x0 - 14, yy, 15.2), (x0 - 14, yy, 24.0), 0.12, mat=C["dgrey"], seg=6)
        B.box((x0 - 14.6, yy - 0.05, 22.0), (x0 - 13.4, yy + 0.05, 22.2), C["dgrey"])
    # flags on the roof edge
    for yy, col in ((-6.0, "#d8382c"), (2.0, "#2f62b0"), (10.0, "#d8382c")):
        B.cyl((x0 + 0.2, yy, 15.2), (x0 + 0.2, yy, 22.0), 0.07, mat=C["lgrey"], seg=6)
        _flag(B, (x0 + 0.2, yy, 21.8), M.c(col), C["white"])
    T = B.build(ink, "terminal")
    # big lettering on top of the roof edge (readable from the apron)
    text_mesh(ink, "AÉROGARE", 3.0, M.c("#f2efe6"), (x0 + 0.95, 30.0, 16.8), rot=(math.pi / 2, 0, math.pi / 2),
              font=FONT_BLACK, extrude=0.25, name="roofsign")
    text_mesh(ink, "MONTRÉAL", 3.0, M.c("#f2efe6"), (x0 + 0.95, -40.0, 16.8), rot=(math.pi / 2, 0, math.pi / 2),
              font=FONT_BLACK, extrude=0.25, name="roofsign2")
    # gate number boards on the canopy edge
    for yy, n in ((-24.0, "12"), (50.0, "14"), (-88.0, "10")):
        G = Batch("gate" + n)
        G.quad([(x0 + 4.55, yy - 1.2, 5.3), (x0 + 4.55, yy + 1.2, 5.3), (x0 + 4.55, yy + 1.2, 7.7), (x0 + 4.55, yy - 1.2, 7.7)],
               M.t("gate" + n, f"gate_{n}.png", (1, 1), tint="#ffffff"), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        G.build(plain)


def _flag(B, top, mat, mat2, w=2.2, h=1.4):
    """a waving flag (strip mesh) hanging off the pole top, toward +Y; mat2 = middle stripe"""
    x, y, z = top
    n = 6
    for k in range(n):
        u0, u1 = k / n, (k + 1) / n
        def p(u, v):
            return (x + 0.25 * math.sin(u * 5.5), y + u * w, z - v * h - 0.15 * u)
        m = mat2 if n // 3 <= k < 2 * n // 3 else mat
        B.quad([p(u0, 1), p(u1, 1), p(u1, 0), p(u0, 0)], m)
        B.quad([p(u0, 0), p(u1, 0), p(u1, 1), p(u0, 1)], m)


# ---------------------------------------------------------------- jet bridges
def _bridge(B, M, C, start, end, z0, z1, rot_r=2.4):
    """apron-drive bridge from a rotunda at `start` to a cab at `end` (2D points), floors z0 -> z1"""
    tb = M.t("bridge", "jetbridge.png", (8.0, 2.4), tint="#ffffff")
    s, e = Vector(start + (0,)), Vector(end + (0,))
    d = e - s; L = d.length; d.normalize()
    yaw = math.atan2(d.y, d.x)
    # rotunda drum on a column
    B.cyl((s.x, s.y, 0), (s.x, s.y, z0), 0.7, mat=C["lgrey"], seg=12)
    B.cyl((s.x, s.y, z0 - 0.3), (s.x, s.y, z0 + 3.4), rot_r, mat=M.c("#d9d2c2"), seg=20)
    B.cyl((s.x, s.y, z0 + 3.4), (s.x, s.y, z0 + 3.8), rot_r + 0.2, mat=C["dgrey"], seg=20)
    # telescoping tunnels (3 sections, each a bit smaller), sloping
    secs = [(0.0, 0.42, 1.0), (0.38, 0.74, 0.93), (0.70, 0.93, 0.86)]
    for a, b, k in secs:
        pa = s + d * (rot_r + (L - rot_r - 3.2) * a); pb = s + d * (rot_r + (L - rot_r - 3.2) * b)
        za = z0 + (z1 - z0) * a; zb = z0 + (z1 - z0) * b
        wdt, hgt = 3.0 * k, 3.0 * k
        n = Vector((-d.y, d.x, 0)) * (wdt / 2)
        ca, cb = Vector((pa.x, pa.y, za)), Vector((pb.x, pb.y, zb))
        corners = lambda c: [c - n, c + n, c + n + Vector((0, 0, hgt)), c - n + Vector((0, 0, hgt))]
        A, Bc = corners(ca), corners(cb)
        seglen = (cb - ca).length
        for i in range(4):
            j = (i + 1) % 4
            uvs = [(0, 0), (seglen / 8.0, 0), (seglen / 8.0, 1), (0, 1)]
            mat = tb if i in (0, 2) else M.c("#c8c0ae")
            f = B.quad([A[i], Bc[i], Bc[j], A[j]], mat, uvs=uvs)
            c = (ca + cb) / 2 + Vector((0, 0, hgt / 2))
            if f and f.normal.dot(f.calc_center_median() - c) < 0:
                f.normal_flip()
        B.quad(A[::-1], M.c("#8d8679")); B.quad(Bc, M.c("#8d8679"))
    # drive column with wheel bogie at 80 %
    pc = s + d * (rot_r + (L - rot_r - 3.2) * 0.8)
    zc = z0 + (z1 - z0) * 0.8
    for side in (-1, 1):
        q = pc + Vector((-d.y, d.x, 0)) * 0.9 * side
        B.cyl((q.x, q.y, 0.9), (q.x, q.y, zc), 0.22, mat=C["dgrey"], seg=8)
    B.obox((pc.x, pc.y, 0.75), (2.6, 1.0, 0.5), C["yellow"], yaw=yaw)
    for side in (-1, 1):
        q = pc + Vector((-d.y, d.x, 0)) * 1.0 * side
        B.cyl((q.x - d.x * 0.0, q.y, 0.55) if False else (q.x, q.y, 0.55), (q.x + (-d.y) * 0.4 * side, q.y + d.x * 0.4 * side, 0.55), 0.55, mat=C["tyre"], seg=14, cap_mat=C["grey"])
    # cab: a box turned toward the door + black bellows + canopy
    cab = e - d * 1.6
    B.obox((cab.x, cab.y, z1 + 1.4), (3.2, 3.6, 2.9), M.c("#d9d2c2"), yaw=yaw)
    bel = e - d * 0.25
    B.obox((bel.x, bel.y, z1 + 1.3), (0.6, 3.2, 2.7), M.c("#2c2b33"), yaw=yaw)
    B.obox((cab.x, cab.y, z1 - 0.25), (3.0, 3.4, 0.3), C["dgrey"], yaw=yaw)
    B.obox((cab.x, cab.y, z1 + 3.0), (3.4, 3.8, 0.25), C["dgrey"], yaw=yaw)


def _jetbridges(ctx, M, C, P):
    ink = ctx["ink"]
    B = Batch("bridges")
    x0 = TERM_X
    # gate 12 (our jet's front door on the -X side, around y = -16): fixed walkway on pillars, rotunda, bridge
    zw = 4.6
    B.box((x0 + 0.9, -18.6, zw), (-36.0, -14.6, zw + 3.0), M.c("#d9d2c2"), mats=dict(py=M.t("bridge", "jetbridge.png", (8.0, 2.4), tint="#ffffff"),
                                                                                   ny=M.t("bridge", "jetbridge.png", (8.0, 2.4), tint="#ffffff")))
    for xx in (-60.0, -48.0):
        B.box((xx - 0.4, -17.0, 0), (xx + 0.4, -16.2, zw), C["lgrey"])
    _bridge(B, M, C, (-33.5, -16.6), (-2.9, -16.4), zw, 2.75)
    # gate 14 (the other airliner, nose-in): rotunda near the facade, bridge to its left door
    B.box((x0 + 0.9, 46.4, zw), (-64.0, 50.4, zw + 3.0), M.c("#d9d2c2"))
    _bridge(B, M, C, (-61.5, 48.4), (-51.5, 55.2), zw, 3.1, rot_r=2.2)
    # gate 10: retracted bridge, parked
    B.box((x0 + 0.9, -90.0, zw), (-64.0, -86.0, zw + 3.0), M.c("#d9d2c2"))
    _bridge(B, M, C, (-61.5, -88.0), (-40.0, -96.0), zw, 4.2, rot_r=2.2)
    B.build(ink)


# ---------------------------------------------------------------- tower, ops building, car park, hangar, fence
def _tower_and_north(ctx, M, C, P, rng):
    lib, ink, plain = ctx["lib"], ctx["ink"], ctx["plain"]
    B = Batch("north")
    tx, ty = -66.0, 128.0
    # ops building
    B.box((-84, 116, 0), (-56, 142, 8.0), M.c("#e9dcc0", ao=True))
    B.box((-84.2, 115.8, 3.2), (-55.8, 142.2, 5.0), M.c("#3d5f9c"))   # window band
    B.box((-84.4, 115.6, 8.0), (-55.6, 142.4, 8.6), M.c("#b25b34"))  # brown fascia
    # tower shaft (12-sided, white concrete) + balcony + cab + roof + mast
    B.cyl((tx, ty, 8.0), (tx, ty, 34.0), 3.0, 2.6, mat=M.c("#f1ece0", ao=True), seg=12, smooth=False)
    for zz in (14.0, 20.0, 26.0):
        B.cyl((tx, ty, zz), (tx, ty, zz + 0.5), 3.0 - (zz - 8) * 0.015 + 0.15, mat=M.c("#b25b34"), seg=12, smooth=False)
    B.cyl((tx, ty, 34.0), (tx, ty, 34.8), 5.4, mat=M.c("#e6ddcb"), seg=16, smooth=False)
    B.cyl((tx, ty, 34.8), (tx, ty, 39.6), 4.4, 5.3, mat=M.c("#2b4f86"), seg=10, smooth=False)
    for i in range(10):
        a = 2 * math.pi * (i + 0.5) / 10
        p0 = (tx + math.cos(a) * 4.45, ty + math.sin(a) * 4.45, 34.8); p1 = (tx + math.cos(a) * 5.35, ty + math.sin(a) * 5.35, 39.6)
        B.tube([p0, p1], 0.09, C["dgrey"], seg=5)
    B.cyl((tx, ty, 39.6), (tx, ty, 40.5), 5.8, 5.0, mat=M.c("#3a3e4a"), seg=16, smooth=False)
    B.cyl((tx, ty, 40.5), (tx, ty, 48.0), 0.18, mat=C["red"], seg=6)
    B.cyl((tx + 2, ty + 1, 40.5), (tx + 2, ty + 1, 44.0), 0.08, mat=C["lgrey"], seg=5)
    B.box((tx - 2.6, ty - 0.2, 40.5), (tx - 1.8, ty + 0.6, 41.6), C["lgrey"])
    # radar on a lattice-ish post
    rx, ry = -92.0, 150.0
    B.cyl((rx, ry, 0), (rx, ry, 14.0), 0.5, mat=C["lgrey"], seg=8)
    B.box((rx - 3.5, ry - 0.3, 14.2), (rx + 3.5, ry + 0.3, 15.6), C["white"])
    # hangar: walls, door, barrel roof
    hx0, hx1, hy0, hy1, hz = -46.0, 6.0, 186.0, 236.0, 13.0
    cream = M.t("corrc", "corr_cream.png", (4, 4), tint="#ffffff")
    B.box((hx0, hy0, 0), (hx1, hy1, hz), cream)
    door = M.t("hdoor", "hangar_door.png", (hx1 - hx0 - 4, hz - 1), tint="#ffffff")
    B.quad([(hx0 + 2, hy0 - 0.15, 0), (hx1 - 2, hy0 - 0.15, 0), (hx1 - 2, hy0 - 0.15, hz - 0.6), (hx0 + 2, hy0 - 0.15, hz - 0.6)], door,
           uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    roofm = M.t("corrb", "corr_blue.png", (4, 4), tint="#ffffff")
    n = 14
    xs = [hx0 - 0.6 + (hx1 - hx0 + 1.2) * k / n for k in range(n + 1)]
    zs = [hz + 9.0 * math.sin(math.pi * k / n) for k in range(n + 1)]
    for k in range(n):
        B.quad([(xs[k], hy0 - 0.8, zs[k]), (xs[k + 1], hy0 - 0.8, zs[k + 1]), (xs[k + 1], hy1 + 0.8, zs[k + 1]), (xs[k], hy1 + 0.8, zs[k])], roofm)
    gable = [(xs[k], zs[k]) for k in range(n + 1)]
    for yy, rev in ((hy0, False), (hy1, True)):
        pts = [(x, yy, z) for x, z in gable]
        pts = pts if not rev else pts[::-1]
        B.quad([pts[0], pts[-1], pts[len(pts) // 2]], cream) if False else None
        for k in range(n):
            q = [(xs[k], yy, hz), (xs[k + 1], yy, hz), (xs[k + 1], yy, zs[k + 1]), (xs[k], yy, zs[k])]
            B.quad(q if (yy == hy1) else q[::-1], M.c("#e9dfc6"))
    # a small office lean-to + sign on the hangar
    B.box((hx1, hy0 + 6, 0), (hx1 + 10, hy0 + 26, 5.0), M.c("#d8cbb0", ao=True))
    B.box((hx1 - 0.1, hy0 + 8, 1.0), (hx1 + 10.1, hy0 + 24, 2.6), M.c("#3d5f9c"))
    B.build(ink)
    # staff car park: 1980s cars in period colours
    colours = ["maroon", "cream", "mustard", "brown", "navy", "avocado", "orange", "skyblue", "white", "red", "beige", "green", "teal"]
    models = ["sedan", "sedan", "suv", "van", "truck", "hatchback-sports", "sedan", "delivery"]
    k = 0
    for row in range(3):
        y0 = 112 + row * 12.5
        for i in range(14):
            if rng.random() < 0.18:
                continue
            x = -52 + i * 2.6 + 1.3
            mdl = models[k % len(models)]
            facing = 0.0 if row % 2 == 0 else math.pi
            kit(lib, ink, "car-kit", mdl, (x + rng.uniform(-0.1, 0.1), y0 + 2.5, 0), facing + rng.uniform(-0.05, 0.05), 1.25,
                body_mat=car_paint(lib, colours[(k * 7 + row) % len(colours)]))
            k += 1
    # chain-link fence around the car park (posts + mesh + barbed top) and along the apron's north edge
    F = Batch("fence_posts")
    mesh = M.cutout("chain", "chainlink.png", (0.5, 0.5), "#b8c0c8")
    Fm = Batch("fence_mesh")
    runs = [((-56.5, 107.0), (-11.0, 107.0)), ((-11.0, 107.0), (-11.0, 152.0)), ((-56.5, 107.0), (-56.5, 116.0)),
            ((-11.0, 107.0), (60.0, 107.0))]
    for (a, b) in runs:
        a, b = Vector(a + (0,)), Vector(b + (0,))
        L = (b - a).length; d = (b - a) / L
        npost = max(1, int(L / 3.0))
        for k in range(npost + 1):
            p = a + d * (L * k / npost)
            F.cyl((p.x, p.y, 0), (p.x, p.y, 2.4), 0.05, mat=C["grey"], seg=6)
            F.tube([(p.x, p.y, 2.4), (p.x - 0.0, p.y, 2.4) if False else (p.x + d.y * 0.35, p.y - d.x * 0.35, 2.75)], 0.03, C["grey"], seg=4)
        F.tube([(a.x, a.y, 2.35), (b.x, b.y, 2.35)], 0.035, C["grey"], seg=5, caps=False)
        for h in (2.55, 2.68):
            o = Vector((d.y, -d.x, 0)) * ((h - 2.4) * 1.6)
            F.tube([(a.x + o.x, a.y + o.y, h), (b.x + o.x, b.y + o.y, h)], 0.012, C["dgrey"], seg=3, caps=False)
        Fm.quad([(a.x, a.y, 0.05), (b.x, b.y, 0.05), (b.x, b.y, 2.35), (a.x, a.y, 2.35)], mesh, uvs=[(0, 0), (L, 0), (L, 2.3), (0, 2.3)])
    F.build(ink); Fm.build(plain)
    # car park light poles + a gate booth
    P2 = Batch("north_props")
    for (x, y) in ((-46.0, 124.0), (-30.0, 124.0), (-18.0, 136.0)):
        P2.cyl((x, y, 0), (x, y, 9.0), 0.12, mat=C["grey"], seg=8)
        P2.box((x - 0.2, y - 1.2, 9.0), (x + 0.2, y + 1.2, 9.3), C["dgrey"])
    P2.box((-14.0, 104.5, 0), (-11.8, 106.7, 2.6), M.c("#e9dcc0"))
    P2.box((-14.2, 104.3, 2.6), (-11.6, 106.9, 2.85), C["red"])
    P2.box((-11.6, 105.4, 0.9), (-4.0, 105.6, 1.0), C["red"])
    # windsock on the grass east of the car park
    wx, wy = 34.0, 128.0
    P2.cyl((wx, wy, 0), (wx, wy, 7.5), 0.08, mat=C["lgrey"], seg=6)
    for k in range(5):
        a0, a1 = k / 5, (k + 1) / 5
        P2.cyl((wx + 0.2 + a0 * 3.2, wy + a0 * 1.2, 7.4 - a0 * 0.5), (wx + 0.2 + a1 * 3.2, wy + a1 * 1.2, 7.4 - a1 * 0.5),
               0.55 - a0 * 0.3, 0.55 - a1 * 0.3, mat=C["orange"] if k % 2 == 0 else C["white"], seg=10, caps=False)
    # taxiway signs (yellow/black boards)
    for (x, y, t) in ((22.0, 148.0, "A"), (60.0, 148.0, "B"), (-6.0, 98.0, "12")):
        P2.box((x - 1.4, y - 0.15, 0.35), (x + 1.4, y + 0.15, 1.45), C["black"])
        P2.box((x - 1.3, y - 0.2, 0.42), (x + 1.3, y - 0.14, 1.38), C["yellow"])
        for sx in (-1.0, 1.0):
            P2.box((x + sx - 0.05, y - 0.05, 0), (x + sx + 0.05, y + 0.05, 0.4), C["grey"])
        text_mesh(ink, t, 0.8, C["black"], (x, y - 0.22, 0.9), rot=(math.pi / 2, 0, 0), font=FONT_BLACK, name="twysign")
    # blue taxiway edge lights along the taxiway
    for k in range(40):
        for y in (149.5, 172.5):
            x = -18 + k * 12
            P2.cyl((x, y, 0), (x, y, 0.35), 0.03, mat=C["grey"], seg=4, caps=False)
            P2.dome((x, y, 0.35), 0.09, M.emit("blue_light", "#3f7bff", 1.2), seg=6, rings=2)
    P2.build(ink)
    _S["windsock"] = (wx, wy)


# ---------------------------------------------------------------- the fuel truck (detailed) + gauge + hoses
def _fuel_truck(ctx, M, C, P):
    ink, plain = ctx["ink"], ctx["plain"]
    x0, x1 = TRUCK_X; y0, y1 = TRUCK_Y
    xc = (x0 + x1) / 2
    red, white, chrome, dg, tyre = M.c("#d6452f", ao=True), M.c("#f4f1e8", ao=True), C["chrome"], C["dgrey"], C["tyre"]
    B = Batch("fueltruck")
    # chassis rails + bumper
    for xx in (xc - 0.55, xc + 0.35):
        B.box((xx, y0 + 0.4, 0.62), (xx + 0.2, y1 - 0.2, 0.86), C["black"])
    B.box((x0 + 0.05, y1 - 0.16, 0.55), (x1 - 0.05, y1 + 0.02, 0.85), chrome)
    # wheels: front axle + rear tandem
    for yy in (1.35, -2.25, -3.35):
        for side, xx in ((-1, x0 + 0.17), (1, x1 - 0.17)):
            B.cyl((xx - 0.17, yy, 0.52), (xx + 0.17, yy, 0.52), 0.52, mat=tyre, seg=18, cap_mat=tyre)
            B.cyl((xx + side * 0.18, yy, 0.52), (xx + side * 0.2, yy, 0.52), 0.28, mat=chrome, seg=12)
            B.cyl((xx + side * 0.2, yy, 0.52), (xx + side * 0.24, yy, 0.52), 0.12, mat=red, seg=8)
    # fenders over the wheels
    for yy in (1.35, -2.8):
        for xx in (x0 - 0.02, x1 - 0.32):
            B.box((xx, yy - (0.65 if yy > 0 else 1.25), 1.08), (xx + 0.34, yy + (0.65 if yy > 0 else 1.25), 1.16), C["black"])
    # cab-over (red) with windscreen, side windows, grille, lights, beacon, mirrors
    cy0, cy1 = 0.55, y1 - 0.15
    B.box((x0 + 0.05, cy0, 0.85), (x1 - 0.05, cy1, 3.05), red)
    B.box((x0 + 0.1, cy0 + 0.1, 3.05), (x1 - 0.1, cy1 - 0.1, 3.18), white)  # roof cap
    B.box((x0 + 0.15, cy1, 1.95), (x1 - 0.15, cy1 + 0.03, 2.9), M.c("#24345e"))  # windscreen
    B.box((x0 + 0.1, cy1 - 0.01, 1.92), (x1 - 0.1, cy1 + 0.02, 1.98), C["black"])
    B.box((xc - 0.03, cy1, 1.95), (xc + 0.03, cy1 + 0.05, 2.9), C["black"])
    B.box((x0 + 0.25, cy1, 1.05), (x1 - 0.25, cy1 + 0.04, 1.7), C["black"])  # grille
    for k in range(5):
        zz = 1.12 + k * 0.12
        B.box((x0 + 0.3, cy1 + 0.03, zz), (x1 - 0.3, cy1 + 0.07, zz + 0.04), chrome)
    for xx in (x0 + 0.35, x1 - 0.35):
        B.cyl((xx, cy1, 1.38), (xx, cy1 + 0.08, 1.38), 0.17, mat=chrome, seg=12)
        B.cyl((xx, cy1 + 0.07, 1.38), (xx, cy1 + 0.09, 1.38), 0.13, mat=M.emit("headlamp", "#fff3c4", 1.0), seg=12)
    for side, xx in ((-1, x0 + 0.03), (1, x1 - 0.03)):
        B.box((xx - 0.02 if side < 0 else xx - 0.01, cy0 + 0.3, 1.95), (xx + 0.01 if side < 0 else xx + 0.02, cy1 - 0.15, 2.8), M.c("#24345e"))
        B.box((xx - 0.02, cy0 + 0.25, 1.0), (xx + 0.02, cy0 + 0.27, 2.9), C["dred"])  # door seam
        B.tube([(xx, cy1 - 0.2, 2.6), (xx + side * 0.45, cy1 - 0.1, 2.6)], 0.03, C["black"], seg=4)
        B.box((xx + side * 0.42 - 0.06, cy1 - 0.16, 2.2), (xx + side * 0.42 + 0.06, cy1 - 0.06, 2.75), C["black"])
        B.box((xx - 0.2 if side < 0 else xx, cy0 + 0.6, 0.55), (xx + 0.0 if side < 0 else xx + 0.2, cy0 + 1.2, 0.65), C["grey"])  # step
    B.cyl((xc, cy0 + 0.6, 3.18), (xc, cy0 + 0.6, 3.3), 0.14, mat=C["dgrey"], seg=10)
    B.dome((xc, cy0 + 0.6, 3.3), 0.13, M.emit("beacon", "#ffae2a", 1.4), seg=10, rings=3, zscale=1.3)
    # tank: white elliptic cylinder with a red belt stripe + blue pinstripe, dished ends
    tz, ra, rb = 1.95, 1.12, 0.98
    ty0, ty1 = -3.65, 0.4
    B.cyl((xc, ty0, tz), (xc, ty1, tz), ra, mat=white, seg=28, ell=rb / ra, cap_mat=white)
    B.cyl((xc, ty0 - 0.01, tz), (xc, ty0 - 0.01, tz), 0.0) if False else None
    for yy in (ty0 + 0.6, ty1 - 0.6):
        B.cyl((xc, yy - 0.12, tz), (xc, yy + 0.12, tz), ra + 0.02, mat=C["lgrey"], seg=28, ell=rb / ra, caps=False)
    B.cyl((xc, ty0 - 0.02, tz - 0.05), (xc, ty1 + 0.02, tz - 0.05), ra + 0.012, mat=red, seg=28, ell=0.16, caps=False) if False else None
    for side in (-1, 1):  # side stripes: red belt + blue pinstripe as thin boxes hugging the tank sides
        xx = xc + side * (ra + 0.005)
        B.box((min(xx, xx + side * 0.02), ty0 + 0.25, tz - 0.38), (max(xx, xx + side * 0.02), ty1 - 0.25, tz - 0.16), red)
        B.box((min(xx, xx + side * 0.02), ty0 + 0.25, tz - 0.48), (max(xx, xx + side * 0.02), ty1 - 0.25, tz - 0.43), M.c("#2a54a8"))
    # decals on the +X side (camera side): AVIATION FUEL strip, hazard diamond, JET A-1, UN panel
    dec = M.t("placards", "placards.png", (1, 1), tint="#ffffff")
    xs = xc + ra + 0.03
    B.quad([(xs, ty1 - 0.5, tz + 0.05), (xs, ty0 + 0.5, tz + 0.05), (xs, ty0 + 0.5, tz + 0.55), (xs, ty1 - 0.5, tz + 0.55)], dec,
           uvs=[(0.25, 0.30), (0.75, 0.30), (0.75, 0.40), (0.25, 0.40)])
    for (yy, cell) in ((ty0 + 0.75, 0), (ty0 + 1.55, 2), (ty1 - 0.9, 3)):
        u0 = cell * 0.25
        B.quad([(xs + 0.005, yy + 0.3, tz - 0.05), (xs + 0.005, yy - 0.3, tz - 0.05), (xs + 0.005, yy - 0.3, tz - 0.65), (xs + 0.005, yy + 0.3, tz - 0.65)] if False else
               [(xs + 0.005, yy + 0.32, tz - 0.62), (xs + 0.005, yy - 0.32, tz - 0.62), (xs + 0.005, yy - 0.32, tz + 0.0), (xs + 0.005, yy + 0.32, tz + 0.0)],
               dec, uvs=[(u0, 0.5), (u0 + 0.25, 0.5), (u0 + 0.25, 1.0), (u0, 1.0)])
    # door emblem (both doors)
    for side in (-1, 1):
        xx = x1 + 0.01 if side > 0 else x0 - 0.01
        pts = [(xx, cy0 + 0.45, 1.15), (xx, cy0 + 1.25, 1.15), (xx, cy0 + 1.25, 1.85), (xx, cy0 + 0.45, 1.85)]
        if side > 0:
            pts = [pts[1], pts[0], pts[3], pts[2]]
        B.quad(pts, dec, uvs=[(0.0, 0.0), (0.25, 0.0), (0.25, 0.5), (0.0, 0.5)])
    # top: catwalk + yellow handrails + manholes
    B.box((xc - 0.35, ty0 + 0.2, tz + rb - 0.05), (xc + 0.35, ty1 - 0.2, tz + rb + 0.04), C["dgrey"])
    for yy in (ty0 + 0.9, (ty0 + ty1) / 2, ty1 - 0.9):
        B.cyl((xc, yy, tz + rb), (xc, yy, tz + rb + 0.18), 0.3, mat=C["lgrey"], seg=12)
    for side in (-1, 1):
        xx = xc + side * 0.6
        B.tube([(xx, ty0 + 0.3, tz + rb + 0.55), (xx, ty1 - 0.3, tz + rb + 0.55)], 0.03, C["yellow"], seg=5)
        for k in range(4):
            yy = ty0 + 0.3 + (ty1 - ty0 - 0.6) * k / 3
            B.tube([(xx, yy, tz + rb - 0.05), (xx, yy, tz + rb + 0.55)], 0.025, C["yellow"], seg=5)
    # amber side marker lights
    for k in range(4):
        yy = ty0 + 0.4 + k * 1.1
        B.box((x1 - 0.02, yy - 0.06, 1.0), (x1 + 0.03, yy + 0.06, 1.08), M.emit("amber", "#ffb43a", 1.2))
    # side lockers between the axles (red, with latches)
    for side, (xa, xb) in ((-1, (x0 + 0.02, x0 + 0.5)), (1, (x1 - 0.5, x1 - 0.02))):
        B.box((xa, -1.6, 0.62), (xb, 0.35, 1.05), red)
        for yy in (-1.2, -0.3):
            B.box((xa - 0.01 if side < 0 else xb - 0.01, yy, 0.8), (xa + 0.01 if side < 0 else xb + 0.01, yy + 0.18, 0.86), chrome)
    # rear deck: diamond-plate platform, ladder up the tank, hose reel, filter vessel
    B.box((x0, y0, 0.86), (x1, ty0 + 0.05, 1.0), M.c("#9aa1ab"))
    B.box((x0, y0, 0.55), (x1, y0 + 0.12, 0.86), M.c("#2b2b31"))  # rear bumper
    for xx in (x0 + 0.2, x1 - 0.3):
        B.box((xx, y0 - 0.02, 0.62), (xx + 0.1, y0 + 0.02, 0.76), M.emit("taillight", "#ff3b2e", 1.0))
    for xx in (xc - 0.35, xc + 0.35):
        B.tube([(xx, ty0 - 0.05, 1.0), (xx, ty0 - 0.05, tz + rb + 0.1)], 0.025, C["grey"], seg=5)
    for k in range(6):
        zz = 1.15 + k * 0.28
        B.tube([(xc - 0.35, ty0 - 0.05, zz), (xc + 0.35, ty0 - 0.05, zz)], 0.02, C["grey"], seg=4)
    rx0, rx1, ry, rz = xc - 0.25, x1 - 0.12, -4.35, 1.62
    for xx in (rx0, rx1 - 0.06):
        B.cyl((xx, ry, rz), (xx + 0.06, ry, rz), 0.6, mat=C["red"], seg=20, cap_mat=C["red"])
    B.cyl((rx0 + 0.06, ry, rz), (rx1 - 0.06, ry, rz), 0.48, mat=M.c("#2a2a30"), seg=20)
    for k in range(5):
        xx = rx0 + 0.12 + k * (rx1 - rx0 - 0.24) / 4
        B.cyl((xx - 0.035, ry, rz), (xx + 0.035, ry, rz), 0.5, mat=M.c("#1e1e24"), seg=20, caps=False)
    for xx in (rx0 + 0.03, rx1 - 0.03):
        B.box((xx - 0.05, ry - 0.08, 1.0), (xx + 0.05, ry + 0.08, rz), C["dgrey"])
    B.cyl((x0 + 0.65, -3.95, 1.0), (x0 + 0.65, -3.95, 2.05), 0.22, mat=C["lgrey"], seg=12)
    B.dome((x0 + 0.65, -3.95, 2.05), 0.22, C["lgrey"], seg=12, rings=3, zscale=0.5)
    # side railings of the deck (no rear rail: the shot-4 insert camera looks in from behind the deck)
    for xx in (x0 + 0.04, x1 - 0.04):
        B.tube([(xx, y0 + 0.15, 1.0), (xx, y0 + 0.15, 1.95), (xx, ty0 - 0.1, 1.95)], 0.025, C["yellow"], seg=5)
    # meter cabinet with the tank-level gauge (faces the insert camera)
    _gauge_cabinet(B, M, C)
    T = B.build(ink, "fueltruck")
    _S["truck"] = T
    # the gauge needle: its own object pivoting on the dial normal
    nb = Batch("needle")
    w0, w1, L, tail = 0.0085, 0.0025, 0.100, 0.032
    red_n = M.c("#c81e1e")
    # a slim tapered blade (front + back faces) with a counterweight tail, and a black hub cap on top
    nb.quad([(-w0, 0, -tail), (w0, 0, -tail), (w1, 0, L), (-w1, 0, L)], red_n)
    nb.quad([(-w1, 0.001, L), (w1, 0.001, L), (w0, 0.001, -tail), (-w0, 0.001, -tail)], red_n)
    nb.cyl((0, -0.010, 0), (0, 0.002, 0), 0.017, mat=C["black"], seg=14)
    nb.cyl((0, -0.012, 0), (0, -0.010, 0), 0.008, mat=C["chrome"], seg=10)
    needle = nb.build(plain, "gauge_needle")
    # local frame: X = image right (viewer's right), -Y = dial normal (toward the viewer), Z = up ("12 o'clock").
    # Rotation about local Y by +a turns the needle from 12 o'clock toward the viewer's right (= toward F).
    n = GAUGE_N
    xa = Vector((-n.y, n.x, 0)).normalized()
    Rm = Matrix((xa, -n, Vector((0, 0, 1)))).transposed().to_4x4()
    _S["needle"] = needle
    _S["needle_base"] = Matrix.Translation(GAUGE + n * 0.034) @ Rm  # just in front of the dial face (n * 0.0305)
    _set_needle(1.0)
    # hoses: built as placeholders, re-fitted to the wing on the first frame (animate)
    _S["hose_mat"] = M.c("#232228")
    _S["hose_col"] = plain if False else ink
    _S["hoses"] = []


def _gauge_cabinet(B, M, C):
    """cabinet on the left of the rear deck; its front (normal GAUGE_N) carries the painted panel + dial"""
    n = GAUGE_N
    t = Vector((-n.y, n.x, 0))  # panel 'right' as seen from the camera is -t... keep geometry symmetric
    up = Vector((0, 0, 1))
    w, h, dpt = 0.40, 0.72, 0.26
    c = GAUGE - up * 0.02
    front = c
    back = c - n * dpt
    zb, zt = 1.0, c.z + h / 2
    # box body (4 sides + top), front face textured
    def P(a, s, z):
        return a + t * s + Vector((0, 0, z - a.z))
    pm = M.t("panel", "panel.png", (1, 1), tint="#ffffff")
    body = M.c("#e9e4d6")
    f0, f1, f2, f3 = P(front, -w / 2, zb), P(front, w / 2, zb), P(front, w / 2, zt), P(front, -w / 2, zt)
    b0, b1, b2, b3 = P(back, -w / 2, zb), P(back, w / 2, zb), P(back, w / 2, zt), P(back, -w / 2, zt)
    # the texture's top 0.72 m portion (v from 0.0 to 1.0 over zb..zt); the gauge sits at its centre
    zf = (GAUGE.z - zb) / (zt - zb)
    f = B.quad([f1, f0, f3, f2], pm, uvs=[(1, 0), (0, 0), (0, 1), (1, 1)])  # f1 = viewer's right -> u = 1
    if f and f.normal.dot(n) < 0:
        f.normal_flip()
    for q in ([b0, b1, b2, b3], [f0, b0, b3, f3], [b1, f1, f2, b2], [f3, b3, b2, f2]):
        f = B.quad(q, body)
        if f:
            cc = (front + back) / 2; cc.z = (zb + zt) / 2
            if f.normal.dot(f.calc_center_median() - cc) < 0:
                f.normal_flip()
    # rain hood over the panel
    hood = [P(front + n * 0.08, -w / 2 - 0.03, zt + 0.02), P(front + n * 0.08, w / 2 + 0.03, zt + 0.02),
            P(back, w / 2 + 0.03, zt + 0.06), P(back, -w / 2 - 0.03, zt + 0.06)]
    f = B.quad(hood, M.c("#d6452f"))
    if f and f.normal.z < 0:
        f.normal_flip()
    # dial: chrome bezel ring (short cylinder) + painted face + glass
    dial = M.t("gauge", "gauge.png", (1, 1), tint="#ffffff")
    B.cyl(GAUGE - n * 0.005, GAUGE + n * 0.03, 0.145, mat=C["chrome"], seg=28, cap_mat=C["chrome"])
    f = B.disc(GAUGE + n * 0.0305, n, 0.128, dial, seg=36, uv_unit=True)
    # valve handle + pipe below the dial
    B.tube([GAUGE - up * 0.42 + n * 0.02, GAUGE - up * 0.42 + n * 0.12], 0.025, C["grey"], seg=6)
    B.cyl(GAUGE - up * 0.42 + n * 0.12, GAUGE - up * 0.42 + n * 0.16, 0.08, mat=C["red"], seg=12)
    B.tube([GAUGE - up * 0.25 + t * 0.12 + n * 0.01, GAUGE - up * 0.25 + t * 0.12 + n * 0.06, GAUGE - up * 0.6 + t * 0.12 + n * 0.06], 0.02, C["chrome"], seg=6)
    # a little data plate + two indicator lamps
    B.quad([GAUGE + n * 0.004 + t * 0.12 + up * 0.2, GAUGE + n * 0.004 - t * 0.12 + up * 0.2,
            GAUGE + n * 0.004 - t * 0.12 + up * 0.27, GAUGE + n * 0.004 + t * 0.12 + up * 0.27], M.c("#c9ced6")) if False else None
    for s, col in ((-0.13, "#ff3b2e"), (0.13, "#4be06a")):
        B.cyl(GAUGE + t * s - up * 0.2, GAUGE + t * s - up * 0.2 + n * 0.03, 0.022, mat=M.emit("lamp" + col, col, 1.3), seg=10)


def _set_needle(level):
    """level 1 = full (F, +135 deg), 0.5 = half (straight up), 0 = empty (E, -135 deg)"""
    ang = math.radians(-135 + 270 * level)
    nd = _S.get("needle")
    if nd is None:
        return
    # rotate about the dial normal (local -Y); positive angle = clockwise as seen from the front
    nd.matrix_world = _S["needle_base"] @ Matrix.Rotation(ang, 4, "Y")


# ---------------------------------------------------------------- ground support equipment
def _gse(ctx, M, C, P, rng):
    lib, ink, plain = ctx["lib"], ctx["ink"], ctx["plain"]
    B = Batch("gse")
    bag_cols = ["#d8382c", "#2f62b0", "#3f8a4a", "#f4b72c", "#7b3fa0", "#ef7a28", "#2f8a84", "#7a4a2c", "#e05a9a", "#25305e", "#c9b48a"]

    def wheel(x, y, z, r, w, axis="x"):
        if axis == "x":
            B.cyl((x - w / 2, y, z), (x + w / 2, y, z), r, mat=C["tyre"], seg=14)
            B.cyl((x - w / 2 - 0.01, y, z), (x + w / 2 + 0.01, y, z), r * 0.5, mat=C["lgrey"], seg=10)
        else:
            B.cyl((x, y - w / 2, z), (x, y + w / 2, z), r, mat=C["tyre"], seg=14)
            B.cyl((x, y - w / 2 - 0.01, z), (x, y + w / 2 + 0.01, z), r * 0.5, mat=C["lgrey"], seg=10)

    def suitcase(c, yaw, size, col):
        m = M.c(col)
        B.obox(c, size, m, yaw=yaw)
        sx, sy, sz = size
        # handle on top + a contrasting strap
        B.obox((c[0], c[1], c[2] + sz / 2 + 0.03), (min(sx, sy) * 0.15 + 0.02, max(sx, sy) * 0.35, 0.05), C["black"], yaw=yaw if sx < sy else yaw + math.pi / 2)
        B.obox(c, (sx + 0.01, 0.06, sz + 0.01) if sx > sy else (0.06, sy + 0.01, sz + 0.01), M.c("#f4f0e6") if col not in ("#f4b72c", "#c9b48a") else C["navy"], yaw=yaw)

    def tug(x, y, yaw, col="#f4b72c"):
        T = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z")
        B.push(T)
        body = M.c(col, ao=True)
        B.box((-0.65, -1.3, 0.3), (0.65, 1.3, 0.95), body)
        B.box((-0.6, 0.6, 0.95), (0.6, 1.3, 1.25), body)  # engine hood (front = +y)
        B.box((-0.7, 1.3, 0.3), (0.7, 1.45, 0.6), C["black"])
        B.box((-0.25, -0.6, 0.95), (0.25, -0.1, 1.35), C["black"])  # seat
        B.box((-0.25, -0.75, 1.35), (0.25, -0.6, 1.8), C["black"])
        B.tube([(0, 0.2, 0.95), (0, 0.05, 1.45)], 0.03, C["dgrey"], seg=4)
        B.cyl((0, 0.05, 1.45), (0, 0.0, 1.5), 0.18, mat=C["black"], seg=12)
        for sx in (-0.6, 0.6):
            for sy in (-1.15, 0.45):
                B.tube([(sx, sy, 0.95), (sx, sy, 2.1)], 0.035, C["dgrey"], seg=5)
        B.box((-0.7, -1.25, 2.1), (0.7, 0.55, 2.2), body)  # canopy
        B.cyl((0, -0.3, 2.2), (0, -0.3, 2.28), 0.1, mat=C["dgrey"], seg=8)
        B.dome((0, -0.3, 2.28), 0.1, M.emit("beacon", "#ffae2a", 1.4), seg=8, rings=2, zscale=1.3)
        for sx in (-0.62, 0.62):
            for sy in (-0.85, 0.85):
                wheel(sx, sy, 0.32, 0.32, 0.25)
        B.box((-0.1, -1.6, 0.35), (0.1, -1.3, 0.45), C["dgrey"])  # hitch
        B.pop()

    def cart(x, y, yaw, bags=True, col="#3f6fb0"):
        T = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z")
        B.push(T)
        fr = M.c(col, ao=True)
        B.box((-0.75, -1.35, 0.45), (0.75, 1.35, 0.55), fr)  # bed
        for sx in (-0.72, 0.72):
            B.box((sx - 0.03, -1.35, 0.55), (sx + 0.03, 1.35, 0.75), fr)  # side rails
        for sx in (-0.72, 0.72):
            for sy in (-1.3, 1.3):
                B.tube([(sx, sy, 0.55), (sx, sy, 1.75)], 0.03, C["grey"], seg=4)
        B.box((-0.8, -1.4, 1.75), (0.8, 1.4, 1.85), M.c("#dfe3ea"))  # roof
        B.box((-0.8, 1.32, 0.75), (0.8, 1.4, 1.75), M.c("#dfe3ea"))  # front shield
        for sx in (-0.55, 0.55):
            for sy in (-0.95, 0.95):
                wheel(sx, sy, 0.22, 0.22, 0.16)
        B.tube([(0, 1.35, 0.4), (0, 2.2, 0.35)], 0.04, C["dgrey"], seg=4)  # tow bar
        if bags:
            yy = -1.1
            while yy < 1.05:
                sz = (rng.uniform(0.55, 0.75), rng.uniform(0.32, 0.45), rng.uniform(0.22, 0.3))
                if rng.random() < 0.4:
                    sz = (rng.uniform(0.4, 0.5), rng.uniform(0.25, 0.3), rng.uniform(0.55, 0.7))
                xx = rng.uniform(-0.3, 0.3)
                B.obox((xx, yy + sz[1] / 2, 0.55 + sz[2] / 2), sz, M.c(rng.choice(bag_cols)), yaw=rng.uniform(-0.15, 0.15))
                if sz[2] < 0.35 and rng.random() < 0.7:  # a second bag on top
                    s2 = (sz[0] * 0.8, sz[1] * 0.9, rng.uniform(0.2, 0.28))
                    B.obox((xx + rng.uniform(-0.1, 0.1), yy + sz[1] / 2, 0.55 + sz[2] + s2[2] / 2), s2, M.c(rng.choice(bag_cols)), yaw=rng.uniform(-0.3, 0.3))
                yy += sz[1] + 0.06
        B.pop()

    # baggage train at the aft bulk-cargo door (left side = +X, aft): tug + 3 carts, plus the belt loader
    bx, by = 9.0, 13.0
    tug(bx, by + 4.6, math.pi)
    for k in range(3):
        cart(bx, by - k * 3.6, math.pi, bags=k < 3)
    # belt loader against the aft door (inclined conveyor rising toward the fuselage)
    lx0, lx1, ly = 8.2, 3.2, 17.0
    B.box((lx1 + 0.8, ly - 0.75, 0.35), (lx0, ly + 0.75, 0.8), M.c("#f4b72c", ao=True))
    for xx in (lx1 + 1.3, lx0 - 0.6):
        for yy in (ly - 0.8, ly + 0.8):
            wheel(xx, yy, 0.32, 0.32, 0.22, axis="y")
    B.box((lx0 - 1.2, ly - 0.5, 0.8), (lx0 - 0.2, ly + 0.5, 1.25), C["black"])  # seat
    p0, p1 = Vector((lx0 + 0.6, ly, 0.75)), Vector((lx1 - 0.2, ly, 2.25))
    d = p1 - p0; Lb = d.length
    pitch = math.atan2(d.z, -d.x)
    mid = (p0 + p1) / 2
    B.push(Matrix.Translation(mid) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Rotation(-pitch, 4, "Y"))
    B.box((-Lb / 2, -0.5, -0.12), (Lb / 2, 0.5, 0.0), M.c("#f4b72c"))
    B.box((-Lb / 2, -0.42, 0.0), (Lb / 2, 0.42, 0.04), M.c("#2a2a30"))
    for sy in (-0.52, 0.52):
        B.box((-Lb / 2, sy - 0.03, 0.0), (Lb / 2, sy + 0.03, 0.22), C["grey"])
    for k in range(3):
        xx = -Lb / 2 + 1.0 + k * 1.6
        B.obox((xx, 0, 0.18), (0.5, 0.35, 0.28), M.c(bag_cols[(k * 3) % len(bag_cols)]), yaw=0.1 * k)
    B.pop()
    B.tube([(lx0 - 2.5, ly, 0.8), (lx0 - 2.5, ly, 1.45)], 0.08, C["grey"], seg=6)  # lift ram
    # ground power unit near the nose (+X side) with its cable
    gx, gy = 4.6, -21.5
    B.box((gx - 0.65, gy - 1.1, 0.35), (gx + 0.65, gy + 1.1, 1.45), M.c("#f4b72c", ao=True))
    B.box((gx - 0.66, gy - 0.8, 0.6), (gx + 0.66, gy + 0.3, 1.2), M.c("#d9a020"))
    for k in range(6):
        B.box((gx + 0.66, gy - 0.75 + k * 0.17, 0.65), (gx + 0.68, gy - 0.67 + k * 0.17, 1.15), C["dgrey"])
    B.box((gx - 0.7, gy - 1.15, 1.45), (gx + 0.7, gy + 1.15, 1.55), C["dgrey"])
    for sx in (-0.5, 0.5):
        for sy in (-0.75, 0.75):
            wheel(gx + sx, gy + sy, 0.3, 0.3, 0.2)
    B.tube([(gx, gy - 1.1, 0.35), (gx, gy - 1.9, 0.3)], 0.04, C["dgrey"], seg=4)
    text_mesh(ink, "400 Hz", 0.18, C["black"], (gx + 0.69, gy + 0.65, 1.3), rot=(math.pi / 2, 0, math.pi / 2), font=FONT_BOLD, name="gpu_txt")
    _S["gpu_plug"] = Vector((gx - 0.66, gy + 0.6, 0.9))
    # chocks: nose gear + main gears (yellow wedges)
    ch = M.c("#f4c21e")
    for (x, y) in ((0.0, NOSE_GEAR_Y - 0.62), (0.0, NOSE_GEAR_Y + 0.62),
                   (MAIN_GEAR[0], MAIN_GEAR[1] - 1.42), (MAIN_GEAR[0], MAIN_GEAR[1] + 1.42),
                   (-MAIN_GEAR[0], MAIN_GEAR[1] - 1.42), (-MAIN_GEAR[0], MAIN_GEAR[1] + 1.42)):
        s = -1 if y < (NOSE_GEAR_Y if abs(x) < 1 else MAIN_GEAR[1]) else 1
        B.push(Matrix.Translation((x, y, 0)))
        prof = [(-0.12 * s, 0.0), (0.12 * s, 0.0), (-0.12 * s, 0.2)] if s > 0 else [(0.12, 0.0), (-0.12, 0.2), (-0.12, 0.0)]
        prof = [(0.0, -0.12), (0.0, 0.12), (0.2, -0.12)] if s < 0 else [(0.0, 0.12), (0.0, -0.12), (0.2, 0.12)]
        B.prism([(v, u) for u, v in prof], -0.35, 0.35, ch, axis="x")
        B.pop()
    B.build(ink)
    # traffic cones (Kenney) at the wingtips, engines, nose and tail
    for (x, y) in ((24.6, 11.0), (-24.6, 11.0), (8.0, -8.6), (-8.0, -8.6), (2.6, -25.6), (0.0, 27.5), (17.8, -6.4),
                   (13.2, -6.8), (6.2, 21.0), (-12.0, 21.0)):
        kit(lib, ink, "car-kit", "cone", (x, y, 0), rng.uniform(0, 6), 1.25)
    # GSE parked in the white boxes east of the stand: spare tug, empty carts, a container dolly, a van
    T2 = Batch("gse_parked")
    Bk = B
    B = T2
    tug(36.0, -23.0, math.pi / 2, col="#ef7a28")
    for k in range(2):
        cart(41.0 + k * 3.2, -12.5, math.pi / 2, bags=k == 0, col="#5a7f3a")
    B.build(ink)
    B = Bk
    kit(lib, ink, "car-kit", "van", (37.5, 4.0, 0), math.pi * 0.5, 1.35, body_mat=car_paint(lib, "yellow"))
    kit(lib, ink, "car-kit", "truck", (41.0, -1.5, 0), math.pi * 0.5, 1.35, body_mat=car_paint(lib, "orange"))
    # vehicles near the terminal / service road: stairs truck, catering truck, follow-me car, tugs + carts
    T3 = Batch("gse_term")
    B = T3
    tug(-60.0, 18.0, 0.0)
    for k in range(4):
        cart(-60.0, 13.6 - k * 3.6, 0.0, bags=k % 2 == 0, col="#3f6fb0")
    tug(-61.0, -60.0, math.pi)
    for k in range(3):
        cart(-61.0, -55.4 + k * 3.6, math.pi, bags=True, col="#c8642a")
    # stairs truck (white with a red stripe)
    sx, sy = -58.0, -40.0
    B.box((sx - 1.1, sy - 3.0, 0.5), (sx + 1.1, sy + 3.0, 1.1), M.c("#efeae0", ao=True))
    B.box((sx - 1.1, sy + 1.4, 1.1), (sx + 1.1, sy + 3.0, 2.6), M.c("#efeae0", ao=True))
    B.box((sx - 1.12, sy + 1.6, 1.9), (sx + 1.12, sy + 2.9, 2.5), M.c("#24345e"))
    B.box((sx - 1.12, sy - 3.0, 0.8), (sx + 1.12, sy + 3.0, 0.95), C["red"])
    for k in range(10):
        B.box((sx - 0.7, sy - 2.6 + k * 0.38, 1.1 + k * 0.33), (sx + 0.7, sy - 2.2 + k * 0.38, 1.25 + k * 0.33), C["grey"])
    for s in (-0.75, 0.75):
        B.tube([(sx + s, sy - 2.6, 2.0), (sx + s, sy + 1.2, 4.7)], 0.04, C["lgrey"], seg=5)
    for yy in (sy - 2.0, sy + 2.0):
        wheel(sx - 1.0, yy, 0.45, 0.45, 0.3); wheel(sx + 1.0, yy, 0.45, 0.45, 0.3)
    # catering truck at the other airliner (box on a raised scissor lift)
    cx, cy = -44.0, 63.5
    B.box((cx - 1.2, cy - 1.0, 0.5), (cx + 1.2, cy + 1.0, 2.6), M.c("#efeae0", ao=True))
    B.box((cx - 1.21, cy - 0.9, 1.6), (cx + 1.21, cy + 0.6, 2.4), M.c("#24345e"))
    B.box((cx - 1.2, cy - 6.0, 0.5), (cx + 1.2, cy - 1.0, 0.9), C["dgrey"])
    for k in range(2):
        B.tube([(cx - 1.0, cy - 5.6, 0.9 + k * 1.1), (cx - 1.0, cy - 1.4, 2.0 + k * 1.1)], 0.06, C["grey"], seg=4)
        B.tube([(cx - 1.0, cy - 1.4, 0.9 + k * 1.1), (cx - 1.0, cy - 5.6, 2.0 + k * 1.1)], 0.06, C["grey"], seg=4)
    B.box((cx - 1.3, cy - 6.2, 3.1), (cx + 1.3, cy - 0.9, 5.6), M.c("#2f62b0", ao=True))
    B.box((cx - 1.32, cy - 5.6, 4.4), (cx + 1.32, cy - 1.6, 4.8), M.c("#f4f0e6"))
    for yy in (cy - 5.0, cy - 0.2):
        wheel(cx - 1.1, yy, 0.45, 0.45, 0.3); wheel(cx + 1.1, yy, 0.45, 0.45, 0.3)
    B.build(ink)
    B = Bk
    kit(lib, ink, "car-kit", "sedan", (-49.0, 30.0, 0), 0.0, 1.3, body_mat=car_paint(lib, "yellow"))  # follow-me car
    kit(lib, ink, "car-kit", "van", (-62.5, 34.0, 0), 0.0, 1.35, body_mat=car_paint(lib, "white"))
    kit(lib, ink, "car-kit", "delivery", (-63.0, -12.0, 0), math.pi, 1.35, body_mat=car_paint(lib, "red"))
    kit(lib, ink, "car-kit", "truck", (-62.0, 72.0, 0), 0.0, 1.35, body_mat=car_paint(lib, "skyblue"))
    # a few loose cones along the service road
    for k in range(6):
        kit(lib, ink, "car-kit", "cone", (-43.2, -10.0 + k * 3.0, 0), rng.uniform(0, 6), 1.2)


# ---------------------------------------------------------------- light masts
def _light_masts(ctx, M, C, P):
    ink = ctx["ink"]
    B = Batch("masts")
    for (x, y) in ((-34.0, -58.0), (-36.0, 30.0), (-36.0, 90.0), (40.0, 45.0), (52.0, -40.0), (12.0, 70.0)):
        B.cyl((x, y, 0), (x, y, 26.0), 0.42, 0.22, mat=M.c("#b8bdc6"), seg=10, smooth=False)
        B.cyl((x, y, 0), (x, y, 1.2), 0.8, 0.7, mat=M.c("#c9c1ae"), seg=10, smooth=False)  # plinth
        B.box((x - 2.2, y - 0.9, 26.0), (x + 2.2, y + 0.9, 26.3), C["dgrey"])
        B.box((x - 2.2, y - 0.9, 27.5), (x + 2.2, y + 0.9, 27.7), C["dgrey"])
        for i in range(5):
            xx = x - 1.8 + i * 0.9
            for yy in (y - 0.5, y + 0.5):
                B.box((xx - 0.35, yy - 0.3, 26.3), (xx + 0.35, yy + 0.3, 27.4), M.c("#e9e7e0"))
                B.box((xx - 0.3, yy - 0.31, 26.4), (xx + 0.3, yy - 0.29 if yy < y else yy + 0.31, 27.3), M.c("#fff8d8")) if False else None
        # ladder cage hint: a thin rail up the side
        B.tube([(x + 0.5, y, 1.2), (x + 0.3, y, 26.0)], 0.04, C["dgrey"], seg=4, caps=False)
    B.build(ink)


# ---------------------------------------------------------------- another airliner at gate 14 (simple)
def _other_jet(ctx, M, C, P):
    ink = ctx["ink"]
    B = Batch("jet2")
    yc, zc, r = 58.0, 3.0, 2.0
    xn, xt = -56.0, -18.0
    liv = M.t("livery2", "livery2.png", (1, 1), tint="#ffffff")
    white = M.c("#f4f2ec")
    # fuselage (UV: u along the body, v around: livery strip on both sides)
    seg = 20
    rings = []
    xs = [xn + 3.5 + (xt - 4.0 - xn - 3.5) * k / 6 for k in range(7)]
    for x in xs:
        rings.append([B._v((x, yc + math.cos(2 * math.pi * i / seg) * r, zc + math.sin(2 * math.pi * i / seg) * r)) for i in range(seg)])
    for k in range(len(rings) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            u0 = (xs[k] - xn) / (xt - xn); u1 = (xs[k + 1] - xn) / (xt - xn)
            a0 = math.sin(2 * math.pi * i / seg); a1 = math.sin(2 * math.pi * j / seg)
            v0, v1 = 0.5 + a0 * 0.45, 0.5 + a1 * 0.45
            f = B._face([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]], liv, uvs=[(1 - u0, v0), (1 - u0, v1), (1 - u1, v1), (1 - u1, v0)], smooth=True)
            if f and f.normal.dot(f.calc_center_median() - Vector((f.calc_center_median().x, yc, zc))) < 0:
                f.normal_flip()
    # nose + tail cones
    B.cyl((xs[0], yc, zc), (xn, yc, zc - 0.5), r, 0.15, mat=white, seg=seg, caps=False)
    B.cyl((xs[-1], yc, zc), (xt, yc, zc + 1.3), r, 0.25, mat=white, seg=seg, caps=False)
    B.disc((xn - 0.01, yc, zc - 0.5), (-1, 0, 0), 0.15, white) if False else None
    # cockpit windows (dark band near the nose)
    B.obox((xn + 2.6, yc, zc + 1.2), (0.9, 2.6, 0.45), M.c("#22304e"))
    # wings, stabilisers, fin
    wing = M.c("#d0d4db")
    for s in (-1, 1):
        B.quad([(-40.0, yc + s * 1.8, zc - 1.2), (-33.0, yc + s * 1.8, zc - 1.2), (-27.0, yc + s * 17.0, zc - 0.2), (-24.5, yc + s * 17.0, zc - 0.2)][::1], wing)
        B.quad([(-40.0, yc + s * 1.8, zc - 1.2), (-24.5, yc + s * 17.0, zc - 0.2), (-27.0, yc + s * 17.0, zc - 0.2), (-33.0, yc + s * 1.8, zc - 1.2)][::-1], wing)
        B.quad([(-23.0, yc + s * 1.0, zc + 0.6), (-19.5, yc + s * 1.0, zc + 0.8), (-17.0, yc + s * 6.5, zc + 1.2), (-15.6, yc + s * 6.5, zc + 1.2)], wing)
        B.quad([(-15.6, yc + s * 6.5, zc + 1.2), (-17.0, yc + s * 6.5, zc + 1.2), (-19.5, yc + s * 1.0, zc + 0.8), (-23.0, yc + s * 1.0, zc + 0.6)], wing)
        # engine under the wing
        ex, ey = -36.5, yc + s * 6.5
        B.cyl((ex - 1.8, ey, zc - 2.0), (ex + 1.6, ey, zc - 2.0), 0.95, 0.75, mat=M.c("#e9ebef"), seg=16, cap_mat=M.c("#2b2f38"))
        B.box((ex - 0.6, ey - 0.12, zc - 1.2), (ex + 1.2, ey + 0.12, zc - 0.9), wing)
    fin = M.c("#1f8c6c")
    B.prism([(-24.5, zc + 1.6), (-18.0, zc + 1.6), (-16.4, zc + 9.0), (-19.0, zc + 9.0)][::-1], yc - 0.18, yc + 0.18, fin, axis="y")
    # gear
    for (x, dy) in ((xn + 4.0, 0.0), (-34.0, -2.6), (-34.0, 2.6)):
        B.cyl((x, yc + dy, 0.0), (x, yc + dy, zc - 1.0), 0.12, mat=C["grey"], seg=6)
        B.cyl((x - 0.0, yc + dy - 0.35, 0.5), (x, yc + dy + 0.35, 0.5), 0.5, mat=C["tyre"], seg=12)
    B.build(ink)
    # its stand: pushback tug in front of the nose
    T = Batch("jet2_tug")
    T.box((xn - 6.5, yc - 1.3, 0.3), (xn - 2.2, yc + 1.3, 1.3), M.c("#f2f0ea", ao=True))
    T.box((xn - 6.3, yc - 1.32, 0.7), (xn - 2.4, yc + 1.32, 0.95), M.c("#2f62b0"))
    T.box((xn - 5.8, yc - 0.6, 1.3), (xn - 4.6, yc + 0.6, 2.1), M.c("#24345e"))
    T.build(ink)


# ---------------------------------------------------------------- far landscape: tree lines, city, hills
def _far(ctx, M, C, P, rng):
    lib, ink, plain = ctx["lib"], ctx["ink"], ctx["plain"]
    trees = ["tree_default", "tree_oak", "tree_fat", "tree_detailed", "tree_tall", "tree_pineRoundA", "tree_simple"]
    rec = {"leafsGreen": "#4f9a3a", "leafsDark": "#2f7a3e", "woodBark": "#6e4a2c", "woodBarkDark": "#553823"}
    # tree belt north (beyond the runway) and west (behind the terminal), plus clumps east
    for k in range(70):
        x = rng.uniform(-500, 700); y = rng.uniform(440, 620)
        kit(lib, ink, "nature-kit", rng.choice(trees), (x, y, 0), rng.uniform(0, 6), rng.uniform(9, 14), recolor=rec)
    for k in range(40):
        x = rng.uniform(-420, -150); y = rng.uniform(-200, 400)
        kit(lib, ink, "nature-kit", rng.choice(trees), (x, y, 0), rng.uniform(0, 6), rng.uniform(8, 13), recolor=rec)
    for (cx, cy, n) in ((90.0, 140.0, 6), (150.0, 210.0, 8), (-150.0, 190.0, 7), (110.0, -180.0, 5)):
        for k in range(n):
            kit(lib, ink, "nature-kit", rng.choice(trees), (cx + rng.uniform(-14, 14), cy + rng.uniform(-10, 10), 0), rng.uniform(0, 6), rng.uniform(6, 9), recolor=rec)
    # distant city skyline (pale, aerial perspective) + a hill (no ink)
    haze = [M.c("#9fb4dc"), M.c("#a9bde2"), M.c("#b4c6e6")]
    for k in range(16):
        mdl = rng.choice(["building-skyscraper-a", "building-skyscraper-b", "building-skyscraper-c", "building-skyscraper-d", "building-skyscraper-e", "low-detail-building-wide-a", "low-detail-building-b"])
        x = -900 + k * 55 + rng.uniform(-15, 15); y = 1500 + rng.uniform(-60, 60)
        kit(lib, plain, "city-kit-commercial", mdl, (x, y, 0), rng.uniform(0, 6), rng.uniform(26, 40), mat_all=haze[k % 3])
    B = Batch("hill")
    seg, rr = 24, 1
    cxh, cyh = -1500.0, 2600.0
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        B.quad([(cxh + math.cos(a0) * 700, cyh + math.sin(a0) * 300, -1), (cxh + math.cos(a1) * 700, cyh + math.sin(a1) * 300, -1),
                (cxh + math.cos(a1) * 250, cyh + math.sin(a1) * 120, 160), (cxh + math.cos(a0) * 250, cyh + math.sin(a0) * 120, 160)], M.c("#93add6"))
    B.build(plain)


def _clouds(ctx, M):
    plain = ctx["plain"]
    rng = random.Random(9)
    # cloud cards far away, facing the camera region (south-east), at 3 depths
    for k in range(14):
        az = math.radians(rng.uniform(70, 175))   # direction from the apron toward the cloud
        dist = rng.uniform(900, 2200)
        el = math.radians(rng.uniform(3.5, 16))
        c = Vector((math.cos(az) * dist, math.sin(az) * dist - 40, math.tan(el) * dist))
        w = rng.uniform(260, 520) * dist / 1500
        mat = M.card(f"cloud{k % 4}", f"cloud{k % 4}.png")
        B = Batch("cloud")
        n = Vector((-math.cos(az), -math.sin(az), 0))
        t = Vector((-n.y, n.x, 0))
        B.quad([c - t * w / 2 - Vector((0, 0, w / 4)), c + t * w / 2 - Vector((0, 0, w / 4)), c + t * w / 2 + Vector((0, 0, w / 4)), c - t * w / 2 + Vector((0, 0, w / 4))],
               mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        o = B.build(plain, f"cloud{k}")
        o.visible_shadow = False


# ================================================================ animate
def animate(ctx, layer, info):
    if not _S.get("_init"):
        _S["_init"] = True
        _ink_width_setup()
        _fit_hoses(ctx)
    shot, f = ctx["shot"], info["f"]
    # ink width: px per metre from the current field of view
    k = _S.get("ink_k")
    if k is not None:
        k.outputs[0].default_value = math.tan(math.radians(layer["cam"]["fov"]) / 2) / 1920.0
    # fuel gauge: full; in shot 4 it drops to half between picture frames 484 and 498 and settles with a wobble
    level = 1.0
    if shot == 4:
        u = min(1.0, max(0.0, (f - 484) / 14.0))
        s = u * u * (3 - 2 * u)
        level = 1.0 - 0.5 * s
        if f > 498:
            level += 0.035 * math.exp(-(f - 498) / 5.0) * math.cos((f - 498) * 0.9)
        elif f < 484:
            level += 0.006 * math.sin(f * 0.7)  # a faint tremble while full
    _set_needle(level)


def _ink_width_setup():
    """screen-constant ink: a geometry-nodes modifier on the shared Line Art object sets every stroke point's
    radius to  W_px(d) * d * tan(fov/2) / 1920  (d = distance to the camera); W from 3.4 px near to 2.3 px far"""
    ink = bpy.data.objects.get("Ink")
    if ink is None or ink.modifiers.get("ApronInkWidth"):
        return
    ng = bpy.data.node_groups.new("ApronInkWidth", "GeometryNodeTree")
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
    mod = ink.modifiers.new("ApronInkWidth", "NODES"); mod.node_group = ng
    _S["ink_k"] = kv


def _ray_up(origin, maxd=12.0, ignore=()):
    """first hit straight up from origin (ignoring our own objects); returns the hit point or None"""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    o = Vector(origin)
    for _ in range(6):
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(dg, o, Vector((0, 0, 1)), distance=maxd)
        if not hit:
            return None
        if obj is not None and (obj.name in ignore or obj.name.startswith(("body", "card", "cut", "soft", "blob"))):
            o = loc + Vector((0, 0, 0.01)); continue
        return loc
    return None


def _fit_hoses(ctx):
    """fuel hoses from the truck's reel to the wing's underside, GPU cable to the nose; only while refuelling
    (shots 2-4). The attachment points are found on the real jet by ray casts."""
    shot = ctx["shot"]
    if shot not in (2, 3, 4):
        return
    mat = _S["hose_mat"]
    col = ctx["ink"]
    B = Batch("hoses")
    ign = {"fueltruck", "apron_ground", "markings", "grass", "asphalt", "gse"}
    for k, (wx, wy) in enumerate(((12.6, 3.4), (13.4, 4.6))):
        top = _ray_up((wx, wy, 0.3), ignore=ign)
        z = top.z - 0.05 if top is not None and top.z < 6.0 else 2.6
        start = Vector((TRUCK_X[0] + 0.9 + k * 0.5, -4.35 + 0.0, 1.05))
        pts = [start, start + Vector((-0.1, 0.25, -0.6)), Vector((14.2 - k * 0.3, -3.2, 0.06)),
               Vector((13.9 - k * 0.2, -0.5, 0.06)), Vector((wx + 0.4, wy - 1.2, 0.06)), Vector((wx + 0.15, wy - 0.4, 0.35)),
               Vector((wx, wy, z * 0.55)), Vector((wx, wy, z - 0.25))]
        B.tube(pts, 0.045, mat, seg=8)
        # coupling at the wing: chrome nozzle + red handle
        B.cyl((wx, wy, z - 0.32), (wx, wy, z), 0.075, mat=bpy.data.materials.get("ap_d3d7de") or mat, seg=10)
        B.box((wx - 0.12, wy - 0.03, z - 0.25), (wx + 0.12, wy + 0.03, z - 0.18), bpy.data.materials.get("ap_d8432c") or mat)
    # static bonding cable from the truck to the main gear (thin, on the ground)
    B.tube([(TRUCK_X[0] + 0.1, -1.0, 0.7), (TRUCK_X[0] - 0.2, -1.0, 0.04), (8.0, 2.2, 0.04), (MAIN_GEAR[0] + 0.5, MAIN_GEAR[1] - 0.6, 0.3)], 0.012, bpy.data.materials.get("ap_4b4f5b") or mat, seg=4)
    o = B.build(col, "hoses")
    o.visible_shadow = True
