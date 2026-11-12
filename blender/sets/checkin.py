# Check-in hall (shot 21, day interior): counter, baggage scale with glowing display, belt, red suitcase with the jet-piece
# tag, queue stanchions, departures board, windows onto an apron with a parked jet, plants, benches, trolleys, signs.
# Textures: D:\gimli3d\blender\tex\checkin\ (make_tex.py + gen.py, Pillow). Airline-neutral, invented flight codes.
import math
import os

import bmesh
import bpy
import mathutils

INK_RADIUS = {"default": 0.022}
TEX = r"D:\gimli3d\blender\tex\checkin"

BLUE, NAVY, WHITE, YEL, RED, TEAL, ORANGE, PURPLE, GREEN = (
    "#1b57d6", "#14306e", "#f4f6fb", "#ffc61a", "#e23a2e", "#1fb5a8", "#ff8a2a", "#7a4fd1", "#2fae4a")

_S = {}  # animation state


def T(n):
    return os.path.join(TEX, n)


# ------------------------------------------------------------------ helpers
def _emis(name, file=None, color="#ffffff", strength=1.0, alpha=False):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); L = nt.links
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = strength
    tex = None
    if file:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.name = "Tex"
        tex.image = bpy.data.images.load(T(file), check_existing=True); tex.extension = "CLIP"
        L.new(tex.outputs[0], em.inputs[0])
    else:
        h = color.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
        em.inputs[0].default_value = (*c, 1)
    if alpha and tex:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        L.new(tex.outputs[1], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
        L.new(mix.outputs[0], out.inputs[0])
    else:
        L.new(em.outputs[0], out.inputs[0])
    return m


def _quad(col, name, c, w, h, mat, facing="-y"):
    x, y, z = c
    if facing == "-y":
        v = [(x - w / 2, y, z - h / 2), (x + w / 2, y, z - h / 2), (x + w / 2, y, z + h / 2), (x - w / 2, y, z + h / 2)]
    elif facing == "+y":
        v = [(x + w / 2, y, z - h / 2), (x - w / 2, y, z - h / 2), (x - w / 2, y, z + h / 2), (x + w / 2, y, z + h / 2)]
    else:  # -z (ceiling light facing down)
        v = [(x - w / 2, y - h / 2, z), (x - w / 2, y + h / 2, z), (x + w / 2, y + h / 2, z), (x + w / 2, y - h / 2, z)]
    me = bpy.data.meshes.new(name); me.from_pydata(v, [], [(0, 1, 2, 3)])
    me.uv_layers.new(); uv = me.uv_layers.active.data
    for k, p in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv[k].uv = p
    o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(mat)
    return o


def _cyl(col, name, loc, r, h, mat, rot=(0, 0, 0), verts=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o); o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def _sph(col, name, loc, r, mat, scale=(1, 1, 1), sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o); o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def _prism(col, name, pts, axis, lo, hi, mat):
    """extruded convex polygon; axis 'z': pts = (x, y), extruded z lo..hi; axis 'y': pts = (x, z), extruded y lo..hi"""
    n = len(pts)
    mk = (lambda p, t: (p[0], p[1], t)) if axis == "z" else (lambda p, t: (p[0], t, p[1]))
    v = [mk(p, lo) for p in pts] + [mk(p, hi) for p in pts]
    f = [list(range(n)), list(range(2 * n - 1, n - 1, -1))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    me = bpy.data.meshes.new(name); me.from_pydata(v, [], f)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(mat)
    return o


def _kid(o, root):
    o.parent = root
    return o


def _root(col, name, loc, rot_z=0.0):
    r = bpy.data.objects.new(name, None); r.location = loc; r.rotation_euler = (0, 0, rot_z); col.objects.link(r)
    return r


# ------------------------------------------------------------------ props
def suitcase(lib, col, name, loc, rot_z, size, color, band=None, upright=True):
    sx, sy, sz = size
    r = _root(col, name, loc, rot_z)
    body = lib.toon("sc_" + color, color); dark = lib.toon("sc_dark", "#2a2630"); bandm = lib.toon("sc_b" + (band or ""), band or "#ffffff")
    _kid(lib.box(col, name + "_b", (-sx / 2, -sy / 2, 0.05), (sx / 2, sy / 2, sz), body, bevel=min(sx, sy, sz) * 0.16), r)
    if band:
        _kid(lib.box(col, name + "_band", (-sx / 2 - .006, -sy * .09, 0.05), (sx / 2 + .006, sy * .09, sz + .004), bandm, bevel=0.005), r)
        _kid(lib.box(col, name + "_band2", (-sx * .07, -sy / 2 - .006, 0.05), (sx * .07, sy / 2 + .006, sz + .004), bandm, bevel=0.005), r)
    if upright:  # telescopic handle + wheels
        _kid(lib.box(col, name + "_h", (-sx * .28, -.02, sz), (sx * .28, .02, sz + .1), dark, bevel=0.01), r)
        for s in (-1, 1):
            _kid(_cyl(col, name + "_w", (s * sx * .36, 0, 0.04), 0.04, 0.05, dark, rot=(0, math.pi / 2, 0), verts=10), r)
    else:  # top handle
        _kid(lib.box(col, name + "_h", (-sx * .14, -.03, sz), (sx * .14, .03, sz + .035), dark, bevel=0.01), r)
        for s in (-1, 1):
            _kid(lib.box(col, name + "_f", (s * sx * .38 - .03, -sy * .4, 0), (s * sx * .38 + .03, -sy * .4 + .06, .05), dark), r)
    return r


def plant(lib, col, loc, s=1.0, pot=ORANGE):
    x, y, z = loc
    _cyl(col, "pot", (x, y, z + .22 * s), .24 * s, .44 * s, lib.toon("pot" + pot, pot))
    _cyl(col, "soil", (x, y, z + .45 * s), .21 * s, .03 * s, lib.toon("soil", "#4a3020"))
    g1, g2 = lib.toon("leaf1", "#2fae4a"), lib.toon("leaf2", "#7ad23a")
    for i, (dx, dy, dz, r, m) in enumerate([(0, 0, .95, .42, g1), (.22, .1, 1.25, .3, g2), (-.2, -.1, 1.3, .32, g1), (0, .18, 1.55, .26, g2), (.1, -.2, .75, .3, g2)]):
        _sph(col, "leaf", (x + dx * s, y + dy * s, z + dz * s), r * s, m, scale=(1, 1, 1.15))


def bench(lib, col, loc, n, colors, rot_z=0.0):
    r = _root(col, "bench", loc, rot_z); steel = lib.toon("steel", "#aab4c6")
    w = .62
    _kid(lib.box(col, "beam", (0, -.05, .32), (w * n, .05, .38), steel), r)
    for i in range(n):
        c = lib.toon("seat" + colors[i % len(colors)], colors[i % len(colors)])
        _kid(lib.box(col, "seat", (i * w + .03, -.27, .42), ((i + 1) * w - .03, .24, .52), c, bevel=.03), r)
        _kid(lib.box(col, "back", (i * w + .03, .24, .52), ((i + 1) * w - .03, .31, .98), c, bevel=.03), r)
    for x in (.1, w * n - .1):
        _kid(lib.box(col, "leg", (x - .025, -.1, 0), (x + .025, .0, .42), steel), r)


def trolley(lib, col, loc, rot_z, bags):
    r = _root(col, "trolley", loc, rot_z); st = lib.toon("steel", "#aab4c6"); blk = lib.toon("sc_dark", "#2a2630")
    _kid(lib.box(col, "deck", (-.45, -.3, .13), (.45, .3, .17), st, bevel=.01), r)
    for x in (-.43, .43):
        _kid(lib.box(col, "post", (x - .015, .28, .17), (x + .015, .32, 1.0), st), r)
    _kid(lib.box(col, "handle", (-.45, .26, .98), (.45, .34, 1.02), lib.toon("trolleyhandle", YEL), bevel=.01), r)
    for x in (-.4, .4):
        for y in (-.25, .25):
            _kid(_cyl(col, "tw", (x, y, .07), .07, .05, blk, rot=(math.pi / 2, 0, 0), verts=10), r)
    for i, (dx, dz, sz, c, b) in enumerate(bags):
        z0 = .17 if dz == 0 else dz
        suitcase(lib, col, "tb", (loc[0] + dx, loc[1], loc[2] + z0), rot_z, sz, c, b, upright=False)


def stanchion_line(lib, col, p0, p1, n):
    steel = lib.toon("chrome", "#d9dfeb"); belt = lib.toon("beltblue", "#1b57d6")
    p0, p1 = mathutils.Vector(p0), mathutils.Vector(p1); pts = [p0.lerp(p1, i / (n - 1)) for i in range(n)]
    for i, p in enumerate(pts):
        _cyl(col, "base", (p.x, p.y, .02), .17, .04, steel)
        _cyl(col, "post", (p.x, p.y, .5), .035, 1.0, steel)
        _sph(col, "cap", (p.x, p.y, 1.02), .06, lib.toon("capred", RED), sub=1)
        if i < n - 1:
            q = pts[i + 1]; mid = (p + q) / 2; ln = (q - p).length; ang = math.atan2(q.y - p.y, q.x - p.x)
            o = lib.box(col, "belt", (-ln / 2, -.012, -.035), (ln / 2, .012, .035), belt)
            o.location = (mid.x, mid.y, .88); o.rotation_euler = (0, 0, ang)


def tower_light(lib, col):
    pass


# ------------------------------------------------------------------ the jet outside
def parked_jet(lib, ink, plain, c):
    cx, cy, cz = c
    L, R = 52.0, 3.0
    white, navy = lib.toon("jetwhite", "#f4f6fb"), lib.toon("jetnavy", NAVY)
    livery = lib.toon("jetlivery", "#ffffff", image=T("livery.png"))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    NL, NR = 44, 24; rings = []
    for i in range(NL + 1):
        u = i / NL
        r = R * (math.sin(u / .1 * math.pi / 2) ** .55 if u < .1 else 1.0 if u < .76 else 1 - .8 * ((u - .76) / .24) ** 1.4)
        lift = 0.0 if u < .76 else 1.1 * ((u - .76) / .24) ** 2
        rings.append([bm.verts.new((cx - L / 2 + u * L, cy - r * math.cos(2 * math.pi * j / NR), cz + lift + r * math.sin(2 * math.pi * j / NR))) for j in range(NR)])
    for i in range(NL):
        for j in range(NR):
            j2 = (j + 1) % NR
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i, j2), (i + 1, j2), (i + 1, j))):
                lp[uvl].uv = (ii / NL, .5 + .5 * math.sin(2 * math.pi * jj / NR))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("fuse"); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new("fuselage", me); ink.objects.link(o); me.materials.append(livery)
    # wings (swept back toward +x as they go toward the terminal, i.e. -y)
    for sgn, nm in ((-1, "wingN"), (1, "wingF")):
        pts = [(cx - 2, cy + sgn * 2.2), (cx + 7, cy + sgn * 2.2), (cx + 15, cy + sgn * 17), (cx + 12.5, cy + sgn * 17)]
        _prism(ink, nm, pts, "z", cz - 1.4, cz - 1.0, white)
        tip = [(cx + 12.5, cy + sgn * 17), (cx + 15, cy + sgn * 17), (cx + 16.6, cy + sgn * 18.2)]
        _prism(ink, nm + "t", tip, "z", cz - 1.4, cz + .6, lib.toon("jetred", RED))
    # engines under the near wing
    eng = lib.toon("engine", "#d8deea"); dark = lib.toon("engdark", "#1d2236")
    for ey in (cy - 8.5, cy + 8.5):
        _cyl(ink, "engine", (cx + 4.4, ey, cz - 2.7), 1.25, 5.2, eng, rot=(0, math.pi / 2, 0), verts=24)
        _cyl(plain, "intake", (cx + 1.76, ey, cz - 2.7), 1.0, .05, dark, rot=(0, math.pi / 2, 0), verts=24)
        _kid(lib.box(ink, "pylon", (cx + 3.6, ey - .25, cz - 1.5), (cx + 6.6, ey + .25, cz - 1.0), white), _root(ink, "e", (0, 0, 0)))
    # tail fin + stabilisers
    fin = [(cx + 18, cz + 2.4), (cx + 25.5, cz + 2.4), (cx + 23, cz + 11), (cx + 20.5, cz + 11)]
    _prism(ink, "fin", [(p[0], p[1] + 0.0) for p in fin], "y", cy - .25, cy + .25, lib.toon("jettail", BLUE))
    _quad(plain, "tailmark", (cx + 22.2, cy - .27, cz + 6.2), 3.3, 3.3, _emis("tailmark", "tail.png", strength=0.9, alpha=True), "-y")
    for sgn in (-1, 1):
        _prism(ink, "stab", [(cx + 22.5, cy + sgn * 1), (cx + 26.5, cy + sgn * 1), (cx + 28, cy + sgn * 8), (cx + 26, cy + sgn * 8)], "z", cz + 2.0, cz + 2.25, white)
    # landing gear
    for gx, gy in ((cx - 18, cy - .9), (cx + 4, cy - 1.6), (cx + 4, cy + 1.6)):
        _cyl(ink, "strut", (gx, gy, cz - 2.2), .16, 1.8, lib.toon("steel", "#aab4c6"))
        _cyl(ink, "wheel", (gx, gy, 0.5), .5, .45, dark, rot=(math.pi / 2, 0, 0), verts=14)


# ------------------------------------------------------------------ build
def build(ctx):
    lib, ink, plain = ctx["lib"], ctx["ink"], ctx["plain"]
    toon = lib.toon
    white, blue, navy = toon("c_white", WHITE), toon("c_blue", BLUE), toon("c_navy", NAVY)
    yel, red, teal = toon("c_yel", YEL), toon("c_red", RED), toon("c_teal", TEAL)
    steel, dark = toon("steel", "#aab4c6"), toon("sc_dark", "#2a2630")
    ctx["_noshadow"] = []

    # ---------- floor, ceiling, walls
    lib.plane(ink, "floor", 26, 16, toon("floor", "#ffffff", image=T("floor.png")), loc=(0, -.5, 0), uv_scale=3.0)
    fl = lib.box(ink, "ceiling", (-13, -8, 4.7), (13, 7, 4.85), toon("ceil", "#dfe6f3")); fl.visible_shadow = False
    # blue guide stripe on the floor to the counter
    lib.box(plain, "stripe", (-.15, -7.5, .002), (.15, -.5, .006), toon("floor_stripe", "#ffb81a"))
    # back wall with window bays
    pil = toon("pillar", WHITE)
    lib.box(ink, "wall_low", (-13, 5.9, 0), (13, 6.3, .95), toon("wall_low", BLUE))
    lib.box(ink, "wall_trim", (-13, 5.85, .95), (13, 6.3, 1.02), yel)
    hd = lib.box(ink, "wall_head", (-13, 5.9, 3.6), (13, 6.3, 4.85), toon("wall_head", "#e8eefb")); hd.visible_shadow = False
    lib.box(ink, "wall_headband", (-13, 5.8, 3.5), (13, 6.3, 3.62), blue)
    for k in range(-5, 6):
        x = k * 2.6
        lib.box(ink, "mullion", (x - .12, 5.8, .95), (x + .12, 6.2, 3.6), pil, bevel=.02)
        lib.box(ink, "transom", (x + .12, 5.95, 2.2), (x + 2.48, 6.05, 2.26), toon("transom", "#cfd8ea"))
    lib.box(ink, "wall_L", (-13.4, -8, 0), (-13, 7, 4.85), toon("wall_L", TEAL)).visible_shadow = False
    lib.box(ink, "wall_R", (13, -8, 0), (13.4, 7, 4.85), toon("wall_R", "#ff8a2a")).visible_shadow = False
    # window glare streaks
    gl = _emis("glare", "glass.png", strength=1.0, alpha=True)
    for k in range(-5, 5):
        _quad(plain, "glare", (k * 2.6 + 1.3, 5.9, 2.25), 2.3, 2.6, gl, "-y")
    # ceiling light panels + cove
    lm = _emis("ceillight", color="#fffbe8", strength=1.6)
    for ix in range(-4, 5):
        for iy in (-3, 0, 3):
            _quad(plain, "light", (ix * 3.0, iy * 1.6, 4.69), 2.0, .5, lm, "-z")
    # ---------- outside: apron, jet, buildings
    lib.plane(ink, "apron", 600, 600, toon("apron", "#8d97b3", image=lib.texture_path("Asphalt033"), repeat=(1, 1)), loc=(0, 300, -.12), uv_scale=8.0)
    lib.box(plain, "taxi_line", (-200, 14.0, -.115), (200, 14.25, -.11), toon("yel_line", YEL))
    lib.box(plain, "taxi_line2", (-200, 40.0, -.115), (200, 40.25, -.11), toon("yel_line", YEL))
    parked_jet(lib, ink, plain, (0, 24, 3.4))
    # background buildings / tower
    for i, (bx, by, w, h, c) in enumerate([(-70, 110, 30, 14, "#e8523a"), (-20, 130, 26, 20, "#ffffff"), (40, 120, 34, 12, "#1fb5a8"), (95, 140, 30, 24, "#ffc61a"), (-110, 150, 28, 10, "#7a4fd1")]):
        lib.box(ink, "bld", (bx - w / 2, by, -.1), (bx + w / 2, by + 20, h), toon("bld%d" % i, c), bevel=.3)
    lib.box(ink, "tower", (14, 90, -.1), (19, 95, 32), toon("tower", "#f1f3f8"))
    lib.box(ink, "tower_cab", (11, 87, 32), (22, 98, 37), toon("tower_cab", "#3b86e8"), bevel=.4)
    lib.box(ink, "tower_roof", (10, 86, 37), (23, 99, 38.2), red)

    # ---------- counter (gap for the belt at x 0.4..1.4)
    cwhite, cblue = toon("cnt_top", "#ffffff"), toon("cnt_blue", BLUE)
    for x0, x1, tag in ((-12.0, 0.4, "L"), (1.4, 12.0, "R")):
        lib.box(ink, "cnt" + tag, (x0, -.42, .1), (x1, .38, 1.0), cblue, bevel=.02)
        lib.box(ink, "cnt_kick" + tag, (x0, -.38, 0), (x1, .34, .1), navy)
        lib.box(ink, "cnt_top" + tag, (x0, -.5, 1.0), (x1, .44, 1.08), cwhite, bevel=.015)
        lib.box(ink, "cnt_stripe" + tag, (x0, -.435, .62), (x1, -.40, .72), yel)
        lib.box(ink, "cnt_stripe2" + tag, (x0, -.435, .45), (x1, -.40, .5), red)
    for x in (0.4, 1.4):  # end caps
        lib.box(ink, "cap", (x - .06 if x == 1.4 else x - .02, -.5, 0), (x + .02 if x == 1.4 else x + .06, .44, 1.08), toon("cnt_cap", RED))
    # counter-top gear: monitors, printers, bag-tag stacks, desk numbers
    for i, x in enumerate((-9.2, -6.6, -4.0, -2.0, 2.6, 4.8, 7.4, 9.6)):
        lib.box(ink, "mon", (x - .22, .06, 1.08), (x + .22, .12, 1.5), dark, bevel=.01)
        lib.box(ink, "mon_foot", (x - .08, .04, 1.08), (x + .08, .2, 1.12), dark)
        lib.box(ink, "printer", (x + .35, .0, 1.08), (x + .7, .3, 1.2), toon("printer", "#e9edf6"), bevel=.02)
        lib.box(ink, "kbd", (x - .2, -.2, 1.08), (x + .2, -.05, 1.1), toon("kbd", "#3a3f55"), bevel=.005)
        n = [13, 14, 15][i % 3]
        _quad(plain, "deskno", (x, -.505, .9), .42, .24, _emis("deskno%d" % n, "desk_%d.png" % n, strength=0.9), "-y")
    # ---------- logo panel + signs hanging above the counter
    lg = _emis("counter_logo", "counter_logo.png", strength=1.0)
    lib.box(ink, "logo_back", (-1.85, 1.74, 2.0), (1.85, 1.86, 3.65), navy, bevel=.03)
    _quad(plain, "logo", (0, 1.72, 2.82), 3.6, 1.8, lg, "-y")
    for x in (-1.5, 1.5):
        lib.box(ink, "rod", (x - .02, 1.78, 3.65), (x + .02, 1.82, 4.7), steel)
    lib.box(ink, "banner_back", (-6.1, 1.9, 3.5), (-2.9, 2.02, 4.15), navy, bevel=.03)
    _quad(plain, "banner", (-4.5, 1.88, 3.82), 3.0, .75, _emis("sign_checkin", "sign_checkin.png", strength=1.0), "-y")
    lib.box(ink, "banner2_back", (2.9, 1.9, 3.5), (6.1, 2.02, 4.15), navy, bevel=.03)
    _quad(plain, "banner2", (4.5, 1.88, 3.82), 3.0, .75, _emis("sign_gates", "sign_gates.png", strength=1.0), "-y")
    for x in (-5.5, -3.5, 3.5, 5.5):
        lib.box(ink, "rod", (x - .02, 1.95, 4.15), (x + .02, 1.99, 4.7), steel)
    # departures board hanging further back
    lib.box(ink, "board_back", (-1.9, 3.22, 3.1), (1.9, 3.38, 4.4), dark, bevel=.04)
    _quad(plain, "board", (0, 3.2, 3.75), 3.7, 1.25, _emis("board", "board.png", strength=1.05), "-y")
    for x in (-1.5, 1.5):
        lib.box(ink, "rod", (x - .02, 3.28, 4.4), (x + .02, 3.32, 4.7), steel)
    lib.box(ink, "board2_back", (5.3, 3.22, 3.1), (9.1, 3.38, 4.4), dark, bevel=.04)
    _quad(plain, "board2", (7.2, 3.2, 3.75), 3.7, 1.25, _emis("board", "board.png", strength=1.05), "-y")
    lib.box(ink, "board3_back", (-9.1, 3.22, 3.1), (-5.3, 3.38, 4.4), dark, bevel=.04)
    _quad(plain, "board3", (-7.2, 3.2, 3.75), 3.7, 1.25, _emis("board", "board.png", strength=1.05), "-y")

    # ---------- scale, display post, belt
    sx, sy = 0.9, -0.85
    lib.box(ink, "scale_base", (sx - .55, sy - .55, 0), (sx + .55, sy + .55, .06), toon("scale_edge", YEL), bevel=.015)
    lib.box(ink, "scale_plate", (sx - .5, sy - .5, .06), (sx + .5, sy + .5, .13), toon("scale_plate", "#4a5068", image=lib.texture_path("Metal027"), repeat=(1, 1)), bevel=.012)
    lib.box(ink, "scale_trim", (sx - .5, sy - .5, .125), (sx + .5, sy - .46, .145), toon("scale_hazard", ORANGE))
    _cyl(ink, "post", (sx - .37, -.52, .62), .04, 1.05, steel)
    lib.box(ink, "disp_frame", (sx - .75, -.64, 1.07), (sx + .05, -.44, 1.55), toon("disp_frame", "#232838"), bevel=.025)
    lib.box(ink, "disp_cap", (sx - .75, -.64, 1.52), (sx + .05, -.44, 1.55), red, bevel=.012)
    dm = _emis("disp_mat", "disp_blank.png", strength=1.9)
    _quad(plain, "display", (sx - .35, -.652, 1.3), .74, .347, dm, "-y")
    _S["node"] = dm.node_tree.nodes["Tex"]
    _S["imgs"] = [bpy.data.images.load(T(n), check_existing=True) for n in ("disp_blank.png", "disp_23kg.png", "disp_50lb.png")]
    # belt (through the counter gap, out through rubber flaps)
    bmat = toon("belt", "#ffffff", image=T("belt.png"))
    o = lib.box(ink, "belt", (sx - .45, -.3, .0), (sx + .45, 3.6, .15), bmat); lib.box_uv(o, .5)
    for s in (-1, 1):
        lib.box(ink, "rail", (sx + s * .47 - .03, -.3, .0), (sx + s * .47 + .03, 3.6, .4), steel, bevel=.01)
    lib.box(ink, "flap_frame", (sx - .75, 3.55, 0), (sx + .75, 3.8, 1.2), dark)
    lib.box(ink, "flap_arch", (sx - .85, 3.5, 1.15), (sx + .85, 3.85, 1.4), yel)
    for i in range(9):
        lib.box(ink, "flap", (sx - .45 + i * .1, 3.5, .15), (sx - .37 + i * .1, 3.53, 1.1), toon("flap", "#15131c"))
    # red suitcase on the scale, with the jet-piece tag
    suitcase(lib, ink, "red_suitcase", (sx, sy, .13), math.radians(7), (.72, .42, .42), RED, "#ffd21a", upright=False)
    lib.box(ink, "strap", (sx - .27, sy - .22, .5), (sx - .23, sy - .205, .56), dark)
    tg = toon("tag", "#ffffff", image=T("tag.png"))
    t = _quad(ink, "tag", (sx - .25, sy - .27, .35), .13, .26, tg, "-y"); t.rotation_euler = (0, 0, 0)
    lib.box(ink, "tag_cord", (sx - .256, sy - .245, .46), (sx - .244, sy - .235, .53), dark)

    # ---------- queue stanchions, flanking the camera lane
    stanchion_line(lib, ink, (-3.0, -6.2, 0), (-3.0, -2.2, 0), 5)
    stanchion_line(lib, ink, (-3.0, -2.2, 0), (-5.0, -2.2, 0), 3)
    stanchion_line(lib, ink, (3.1, -6.2, 0), (3.1, -2.4, 0), 5)
    stanchion_line(lib, ink, (3.1, -2.4, 0), (5.2, -2.4, 0), 3)
    stanchion_line(lib, ink, (-8.5, -3.0, 0), (-6.2, -3.0, 0), 4)

    # ---------- luggage on the floor, trolleys
    cols = [(RED, "#ffd21a"), ("#1fb5a8", "#ffffff"), ("#7a4fd1", "#ffc61a"), ("#ff8a2a", "#14306e"), ("#2fae4a", "#ffffff"), ("#1b57d6", "#ffc61a")]
    spots = [(-2.3, -2.9, .5, .3, .7, 0), (-2.0, -2.5, .42, .26, .56, 1), (2.4, -1.9, .5, .3, .66, 2), (2.8, -1.5, .4, .25, .52, 3),
             (-4.2, -1.1, .55, .32, .74, 4), (-3.6, -.9, .42, .26, .5, 5), (3.9, -.9, .52, .3, .7, 1), (5.0, -1.3, .42, .26, .56, 0),
             (-6.5, -1.6, .5, .3, .66, 2), (6.8, -2.2, .5, .3, .66, 4)]
    for i, (x, y, a, b, c, k) in enumerate(spots):
        suitcase(lib, ink, "lug%d" % i, (x, y, 0), math.radians(i * 37 % 90 - 30), (a, b, c), cols[k][0], cols[k][1])
    trolley(lib, ink, (-5.2, -3.6, 0), math.radians(20), [(0, 0, (.7, .42, .3), "#1b57d6", "#ffc61a"), (0, .47, (.5, .32, .4), RED, "#ffffff")])
    trolley(lib, ink, (4.6, -4.0, 0), math.radians(-15), [(0, 0, (.7, .42, .34), "#2fae4a", "#ffffff"), (0, .47, (.55, .34, .3), "#ff8a2a", "#14306e")])
    trolley(lib, ink, (7.4, -.4, 0), math.radians(5), [(0, 0, (.72, .4, .3), PURPLE, YEL)])

    # ---------- seating, plants, columns with pictograms, lightboxes, clock
    bench(lib, ink, (-9.5, 4.9, 0), 4, [BLUE, YEL, RED, TEAL])
    bench(lib, ink, (-6.0, 4.9, 0), 4, [TEAL, ORANGE, BLUE, PURPLE])
    bench(lib, ink, (5.0, 4.9, 0), 4, [RED, BLUE, YEL, GREEN])
    bench(lib, ink, (8.2, 4.9, 0), 3, [PURPLE, TEAL, ORANGE])
    for x, y, s, p in ((-2.8, 1.0, 1.0, ORANGE), (3.1, 1.1, 1.1, TEAL), (-1.8, 5.2, 1.3, YEL), (2.4, 5.2, 1.2, RED), (-7.6, .8, 1.0, BLUE), (7.2, .9, 1.0, ORANGE), (-10.8, 4.3, 1.3, TEAL), (11.0, 4.5, 1.3, YEL)):
        plant(lib, ink, (x, y, 0), s, p)
    icons = ["sign_plane.png", "sign_bag.png", "sign_arrow.png", "sign_info.png"]
    for i, x in enumerate((-8.0, -3.8, 3.9, 8.2)):
        _cyl(ink, "column", (x, 3.7, 2.35), .34, 4.7, toon("col_white", WHITE))
        _cyl(ink, "column_band", (x, 3.7, .35), .36, .7, blue)
        _cyl(ink, "column_band2", (x, 3.7, 1.25), .355, .12, yel)
        lib.box(ink, "sign_box", (x - .42, 3.7 - .46, 2.0), (x + .42, 3.7 - .38, 2.84), navy, bevel=.03)
        _quad(plain, "sign", (x, 3.7 - .462, 2.42), .74, .74, _emis("icon" + icons[i], icons[i], strength=1.0), "-y")
    for i, x in enumerate((-11.5, -10.0)):
        pass
    for x, ptex in ((-7.4, "poster_beach.png"), (-5.4, "poster_mountain.png"), (5.4, "poster_beach.png"), (7.4, "poster_mountain.png")):
        lib.box(ink, "lightbox", (x - .75, 5.5, .0), (x + .75, 5.7, 2.35), navy, bevel=.03)
        _quad(plain, "poster", (x, 5.49, 1.2), 1.4, 2.1, _emis(ptex, ptex, strength=.95), "-y")
    lib.box(ink, "clock_back", (-.4, 5.7, 3.25), (.4, 5.85, 3.45), navy)
    _quad(plain, "clock", (0, 5.68, 3.6), .75, .75, _emis("clock", "clock.png", strength=1.0, alpha=True), "-y")

    ctx["_ok"] = True


def animate(ctx, layer, info):
    f = info["f"]
    k = 0 if f < 1950 else 1 if f < 1992 else 2 if f < 2030 else (1 if ((f - 2030) // 10) % 2 == 0 else 2)
    node = _S.get("node")
    if node is not None:
        node.image = _S["imgs"][k]
