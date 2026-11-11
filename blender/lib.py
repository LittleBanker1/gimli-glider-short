# Shared Blender library for "The Jet That Couldn't Count" (Blender 5.3, EEVEE). Every set builder, the jet and the
# shot renderer use these helpers so the whole film shares ONE look:
#   - coordinates: the film's data is three.js (y up). to_b() converts a point to Blender (z up): (x, y, z) -> (x, -z, y).
#     Set builders work directly in Blender coordinates; layout.py already holds the converted anchor points.
#   - materials: soft-toon "ToonSurf" node group on every world surface (albedo x ramp between ShadowTint and LitTint
#     driven by the scene's sun + shadows), emission output, view transform Standard (what you paint is what you get).
#     The tints live in ONE node group, so set_light() re-tints the whole world per shot (day / golden / interior).
#   - ink: Grease Pencil Line Art over the "INK" collection (sets + jet; never cards or sky).
#   - sky: camera rays see a painted elevation gradient; lighting sees a flat ambient colour.
#   - cards: the 2D characters / effects as textured planes posed per frame from the exported data.
# Paths: assets on D:\gimli3d (kenney\<kit>\Models\GLB format\*.glb, textures\<Id>\<Id>_1K-JPG_Color.jpg).
import math
import os
import bpy
import mathutils

ROOT = r"D:\gimli3d"
KENNEY = os.path.join(ROOT, "kenney")
TEX = os.path.join(ROOT, "textures")
C3 = mathutils.Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
C4 = C3.to_4x4()
C4i = C4.inverted()


def to_b(p):
    """three.js point (x, y, z) -> Blender Vector"""
    return mathutils.Vector((p[0], -p[2], p[1]))


def mat_from_three(el):
    """three.js Matrix4.elements (column-major list of 16) -> mathutils Matrix (still in three space)"""
    return mathutils.Matrix([[el[c * 4 + r] for c in range(4)] for r in range(4)])


def obj_matrix(el):
    """world matrix for an object whose mesh was authored in Blender space from three-space data (cards, jet)"""
    return C4 @ mat_from_three(el) @ C4i


def cam_matrix(el):
    """three camera matrixWorld -> Blender camera matrix_world (both look down local -Z with +Y up)"""
    return C4 @ mat_from_three(el)


# ---------------------------------------------------------------- light presets (display-referred, Standard view)
# LitTint / ShadowTint multiply the albedo (LOOK_STUDY 4.1). sky = 5 elevation stops (deg, hex) seen by the camera.
LIGHTS = {
    "day": dict(lit=(1.0, 0.98, 0.94), shadow=(0.55, 0.50, 0.62), sun_energy=4.0, sun_col=(1.0, 0.97, 0.9),
                ambient=("#8fa6dc", 0.35), sky=[(0, "#a9c8f2"), (5, "#79a8ef"), (12, "#4f86e8"), (25, "#3366d6"), (45, "#2a55c4")],
                card=(1.0, 0.99, 0.97), card_shade=(0.92, 0.90, 0.96), ink="#1a1420"),
    "golden": dict(lit=(1.15, 0.85, 0.62), shadow=(0.32, 0.30, 0.62), sun_energy=4.0, sun_col=(1.0, 0.78, 0.55),
                   ambient=("#5a4a8c", 0.4), sky=[(0, "#ffb060"), (3, "#f08a6a"), (8, "#a8608a"), (16, "#5e3f86"), (35, "#33285e")],
                   card=(1.0, 0.9, 0.82), card_shade=(0.86, 0.82, 0.95), ink="#1a1420"),
    "interior": dict(lit=(1.0, 0.97, 0.92), shadow=(0.62, 0.60, 0.72), sun_energy=3.0, sun_col=(1.0, 0.95, 0.88),
                     ambient=("#b9b4c8", 0.5), sky=[(0, "#a9c8f2"), (5, "#79a8ef"), (12, "#4f86e8"), (25, "#3366d6"), (45, "#2a55c4")],
                     card=(1.0, 0.99, 0.97), card_shade=(0.92, 0.90, 0.96), ink="#1a1420"),
    "interior_golden": dict(lit=(1.12, 0.88, 0.68), shadow=(0.40, 0.36, 0.62), sun_energy=3.5, sun_col=(1.0, 0.8, 0.58),
                            ambient=("#6a5a8c", 0.45), sky=[(0, "#ffb060"), (3, "#f08a6a"), (8, "#a8608a"), (16, "#5e3f86"), (35, "#33285e")],
                            card=(1.0, 0.93, 0.86), card_shade=(0.88, 0.84, 0.95), ink="#1a1420"),
}


def hex_rgb(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)  # linear for node colours


def srgb_lin(c):
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


# ---------------------------------------------------------------- ToonSurf node group
def toon_group():
    g = bpy.data.node_groups.get("ToonSurf")
    if g:
        return g
    g = bpy.data.node_groups.new("ToonSurf", "ShaderNodeTree")
    g.interface.new_socket("Albedo", in_out="INPUT", socket_type="NodeSocketColor").default_value = (0.8, 0.8, 0.8, 1)
    g.interface.new_socket("AO", in_out="INPUT", socket_type="NodeSocketFloat").default_value = 1.0
    g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    n, l = g.nodes, g.links
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    diff = n.new("ShaderNodeBsdfDiffuse"); diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = n.new("ShaderNodeShaderToRGB")
    bw = n.new("ShaderNodeRGBToBW")
    ramp = n.new("ShaderNodeValToRGB"); ramp.name = "Ramp"
    ramp.color_ramp.interpolation = "EASE"
    e0, e1 = ramp.color_ramp.elements
    e0.position, e1.position = 0.22, 0.38
    e0.color, e1.color = (0, 0, 0, 1), (1, 1, 1, 1)
    lit = n.new("ShaderNodeRGB"); lit.name = "LitTint"
    sh = n.new("ShaderNodeRGB"); sh.name = "ShadowTint"
    tint = n.new("ShaderNodeMix"); tint.data_type = "RGBA"
    alb = n.new("ShaderNodeMix"); alb.data_type = "RGBA"; alb.blend_type = "MULTIPLY"; alb.inputs[0].default_value = 1
    ao = n.new("ShaderNodeMix"); ao.data_type = "RGBA"; ao.blend_type = "MULTIPLY"
    em = n.new("ShaderNodeEmission")
    l.new(diff.outputs[0], s2r.inputs[0]); l.new(s2r.outputs[0], bw.inputs[0]); l.new(bw.outputs[0], ramp.inputs[0])
    l.new(ramp.outputs[0], tint.inputs[0]); l.new(sh.outputs[0], tint.inputs[6]); l.new(lit.outputs[0], tint.inputs[7])
    l.new(tint.outputs[2], alb.inputs[6]); l.new(gi.outputs["Albedo"], alb.inputs[7])
    # AO input: 1 = none; the colour is multiplied by (0.75 + 0.25 AO) so cavities darken gently
    aom = n.new("ShaderNodeMapRange"); aom.inputs[3].default_value = 0.75; aom.inputs[4].default_value = 1.0
    l.new(gi.outputs["AO"], aom.inputs[0])
    l.new(alb.outputs[2], ao.inputs[6]); ao.inputs[0].default_value = 1
    gray = n.new("ShaderNodeCombineColor")
    for i in range(3):
        l.new(aom.outputs[0], gray.inputs[i])
    l.new(gray.outputs[0], ao.inputs[7])
    l.new(ao.outputs[2], em.inputs[0]); l.new(em.outputs[0], go.inputs["Shader"])
    set_light("day")
    return g


def set_light(name):
    g = bpy.data.node_groups.get("ToonSurf") or toon_group()
    L = LIGHTS[name]
    g.nodes["LitTint"].outputs[0].default_value = (*L["lit"], 1)
    g.nodes["ShadowTint"].outputs[0].default_value = (*L["shadow"], 1)
    cg = bpy.data.node_groups.get("CardLit")
    if cg:
        cg.nodes["CardTint"].outputs[0].default_value = (*srgb_lin(L["card"]), 1)


def toon(name, color=None, image=None, repeat=(1, 1), ao=False, hue_shift=None):
    """toon material: flat colour (hex or linear rgb tuple) or an image (path) as albedo; repeat = UV tiling"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = toon_group()
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image, check_existing=True)
        if repeat != (1, 1):
            uv = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (repeat[0], repeat[1], 1)
            nt.links.new(uv.outputs["UV"], mp.inputs[0]); nt.links.new(mp.outputs[0], tex.inputs[0])
        src = tex.outputs[0]
        if color is not None:  # tint the texture
            mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
            nt.links.new(src, mul.inputs[6]); mul.inputs[7].default_value = (*(hex_rgb(color) if isinstance(color, str) else color), 1)
            src = mul.outputs[2]
        nt.links.new(src, grp.inputs["Albedo"])
    else:
        c = hex_rgb(color) if isinstance(color, str) else (color or (0.8, 0.8, 0.8))
        grp.inputs["Albedo"].default_value = (*c[:3], 1)
    if ao:
        aon = nt.nodes.new("ShaderNodeAmbientOcclusion"); aon.inputs["Distance"].default_value = 0.4
        nt.links.new(aon.outputs["AO"], grp.inputs["AO"])
    nt.links.new(grp.outputs[0], out.inputs[0])
    return m


def texture_path(asset_id, kind="Color"):
    return os.path.join(TEX, asset_id, f"{asset_id}_1K-JPG_{kind}.jpg")


# ---------------------------------------------------------------- objects
def new_col(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def box(col, name, mn, mx, mat, bevel=0.0):
    """axis box from min to max corner (Blender coords)"""
    mn, mx = mathutils.Vector(mn), mathutils.Vector(mx)
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = mathutils.Vector(((v.co.x + 0.5) * (mx.x - mn.x) + mn.x, (v.co.y + 0.5) * (mx.y - mn.y) + mn.y, (v.co.z + 0.5) * (mx.z - mn.z) + mn.z))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    me.materials.append(mat)
    if bevel > 0:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = 2; b.limit_method = "ANGLE"
    box_uv(o)
    return o


def box_uv(o, size=1.0):
    """cube-project UVs in metres (texture repeats every `size` m)"""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new()
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u, v = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            uv[li].uv = (u / size, v / size)


def plane(col, name, size_x, size_y, mat, loc=(0, 0, 0), uv_scale=1.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = (size_x, size_y, 1); bpy.ops.object.transform_apply(scale=True)
    link(o, col)
    o.data.materials.append(mat)
    box_uv(o, uv_scale)
    return o


_glb_cache = {}


def kenney(col, kit, model, loc=(0, 0, 0), rot_z=0.0, scale=1.0, recolor=None, name=None):
    """import a Kenney GLB (kit e.g. 'car-kit', model e.g. 'sedan') at a Blender location, materials -> toon.
    Re-uses the imported mesh data for repeated models (linked duplicates). recolor = {material_name: hex}."""
    key = (kit, model)
    if key not in _glb_cache:
        path = os.path.join(KENNEY, kit, "Models", "GLB format", model + ".glb")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        roots = [o for o in new if o.parent is None]
        for o in new:
            for s in getattr(o, "material_slots", []):
                if s.material and not s.material.name.startswith("T_"):
                    s.material = to_toon(s.material, recolor)
        tmpl = bpy.data.collections.get("_templates") or bpy.data.collections.new("_templates")
        for o in new:
            link(o, tmpl)
        _glb_cache[key] = roots
    roots = _glb_cache[key]
    made = []
    for r in roots:
        dup = _dup_tree(r, col)
        dup.location = loc; dup.rotation_euler = (0, 0, rot_z); dup.scale = (scale, scale, scale)
        if name:
            dup.name = name
        made.append(dup)
    return made[0] if len(made) == 1 else made


def _dup_tree(o, col, parent=None):
    d = o.copy()
    if parent is not None:
        d.parent = parent
    col.objects.link(d)
    for ch in o.children:
        _dup_tree(ch, col, d)
    return d


def to_toon(m, recolor=None):
    """convert an imported Principled material to toon, keeping its base colour or base-colour texture"""
    name = "T_" + m.name
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    col, img = (0.8, 0.8, 0.8), None
    if m.use_nodes:
        p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if p:
            bc = p.inputs["Base Color"]
            if bc.is_linked and bc.links[0].from_node.type == "TEX_IMAGE":
                img = bc.links[0].from_node.image
            else:
                col = tuple(bc.default_value)[:3]
    if recolor and m.name in recolor:
        col, img = hex_rgb(recolor[m.name]), None
    t = bpy.data.materials.new(name); t.use_nodes = True
    nt = t.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = toon_group()
    if img:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Closest"
        nt.links.new(tex.outputs[0], grp.inputs["Albedo"])
    else:
        grp.inputs["Albedo"].default_value = (*col, 1)
    nt.links.new(grp.outputs[0], out.inputs[0])
    return t


# ---------------------------------------------------------------- sky, sun, render settings
def world_sky(light):
    L = LIGHTS[light]
    w = bpy.data.worlds.get("Sky") or bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    asin = nt.nodes.new("ShaderNodeMath"); asin.operation = "ARCSINE"
    deg = nt.nodes.new("ShaderNodeMath"); deg.operation = "DIVIDE"; deg.inputs[1].default_value = math.radians(60)  # 0..60 deg -> 0..1
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    stops = L["sky"]
    cr.elements[0].position = 0; cr.elements[0].color = (*hex_rgb(stops[0][1]), 1)
    cr.elements[1].position = min(1, stops[-1][0] / 60); cr.elements[1].color = (*hex_rgb(stops[-1][1]), 1)
    for e, h in stops[1:-1]:
        el = cr.elements.new(e / 60); el.color = (*hex_rgb(h), 1)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_amb = nt.nodes.new("ShaderNodeBackground"); bg_amb.inputs[0].default_value = (*hex_rgb(L["ambient"][0]), 1); bg_amb.inputs[1].default_value = L["ambient"][1]
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    l = nt.links
    l.new(tc.outputs["Generated"], sep.inputs[0])  # world 'Generated' = view direction
    l.new(sep.outputs["Z"], asin.inputs[0]); l.new(asin.outputs[0], deg.inputs[0]); l.new(deg.outputs[0], ramp.inputs[0])
    l.new(ramp.outputs[0], bg_cam.inputs[0])
    l.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); l.new(bg_amb.outputs[0], mix.inputs[1]); l.new(bg_cam.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs[0])
    return w


def sun_lamp(light, dir_three, angle_deg=2.0):
    """sun lamp shining FROM dir_three (three.js unit vector toward the sun)"""
    L = LIGHTS[light]
    s = bpy.data.lights.get("Sun") or bpy.data.lights.new("Sun", "SUN")
    s.energy = L["sun_energy"]; s.color = L["sun_col"]; s.angle = math.radians(angle_deg)
    o = bpy.data.objects.get("Sun") or bpy.data.objects.new("Sun", s)
    if o.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(o)
    d = to_b(dir_three).normalized()
    o.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return o


def render_settings(scale_pct=100, samples=16):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, scale_pct
    sc.render.fps = 30
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.film_transparent = False
    ee = sc.eevee
    if hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = samples
    if hasattr(ee, "use_shadows"):
        ee.use_shadows = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"


def line_art(col, radius=0.03, crease_deg=140, color="#1a1420"):
    """Grease Pencil Line Art over collection `col` (world ink). radius in metres (world space)."""
    bpy.ops.object.grease_pencil_add(type="LINEART_COLLECTION")
    o = bpy.context.object
    o.name = "Ink"
    m = o.modifiers[0]
    m.source_type = "COLLECTION"; m.source_collection = col
    m.radius = radius
    m.crease_threshold = math.radians(crease_deg)
    m.use_intersection = True; m.use_material = False
    mat = o.data.materials[0] if o.data.materials else None
    if mat and getattr(mat, "grease_pencil", None):
        mat.grease_pencil.color = (*hex_rgb(color), 1)
    return o


# ---------------------------------------------------------------- 2D cards (characters + effects)
def card_group():
    g = bpy.data.node_groups.get("CardLit")
    if g:
        return g
    g = bpy.data.node_groups.new("CardLit", "ShaderNodeTree")
    g.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    n, l = g.nodes, g.links
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    tint = n.new("ShaderNodeRGB"); tint.name = "CardTint"; tint.outputs[0].default_value = (1, 1, 1, 1)
    mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
    em = n.new("ShaderNodeEmission"); tr = n.new("ShaderNodeBsdfTransparent")
    cut = n.new("ShaderNodeMath"); cut.operation = "GREATER_THAN"; cut.inputs[1].default_value = 0.5
    mix = n.new("ShaderNodeMixShader")
    l.new(gi.outputs["Color"], mul.inputs[6]); l.new(tint.outputs[0], mul.inputs[7]); l.new(mul.outputs[2], em.inputs[0])
    l.new(gi.outputs["Alpha"], cut.inputs[0]); l.new(cut.outputs[0], mix.inputs[0])
    l.new(tr.outputs[0], mix.inputs[1]); l.new(em.outputs[0], mix.inputs[2]); l.new(mix.outputs[0], go.inputs["Shader"])
    return g


class CardPool:
    """planes reused every frame, one sub-pool per kind: body (lit character), cut (hard-alpha effect),
    soft (see-through effect), blob (multiply ground shadow drawn as a dark decal). pose(layer) places one layer."""

    def __init__(self, col, cards_dir, body):
        self.col, self.dir = col, cards_dir
        self.bw, self.bh, self.by = body
        self.items = {"body": [], "cut": [], "soft": [], "blob": []}
        card_group()

    def _mesh(self, kind):
        me = bpy.data.meshes.new("cardmesh")
        if kind == "body":  # three local: x +-w/2, y from by-bh/2 to by+bh/2, facing +z  -> Blender (x, -z, y)
            y0, y1, w = self.by - self.bh / 2, self.by + self.bh / 2, self.bw / 2
            verts = [(-w, 0, y0), (w, 0, y0), (w, 0, y1), (-w, 0, y1)]
        else:  # unit effect card, centred
            verts = [(-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 0, 0.5), (-0.5, 0, 0.5)]
        me.from_pydata(verts, [], [(0, 1, 2, 3)])
        me.uv_layers.new(); uv = me.uv_layers.active.data
        for k, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
            uv[k].uv = (u, v)
        return me

    def _material(self, kind):
        m = bpy.data.materials.new(f"card_{kind}")
        m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear(); L = nt.links
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.name = "Tex"; tex.extension = "CLIP"
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        L.new(tr.outputs[0], mix.inputs[1]); L.new(mix.outputs[0], out.inputs[0])
        if kind == "body":
            grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = card_group()
            L.new(tex.outputs["Color"], grp.inputs["Color"]); L.new(tex.outputs["Alpha"], grp.inputs["Alpha"])
            L.new(grp.outputs[0], out.inputs[0]); nt.nodes.remove(mix); nt.nodes.remove(tr)
        elif kind == "blob":
            bw = nt.nodes.new("ShaderNodeRGBToBW"); inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
            em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (0.05, 0.04, 0.12, 1)
            L.new(tex.outputs["Color"], bw.inputs[0]); L.new(bw.outputs[0], inv.inputs[1]); L.new(inv.outputs[0], mix.inputs[0])
            L.new(em.outputs[0], mix.inputs[2])
        else:
            em = nt.nodes.new("ShaderNodeEmission"); L.new(tex.outputs["Color"], em.inputs[0]); L.new(em.outputs[0], mix.inputs[2])
            if kind == "cut":
                cut = nt.nodes.new("ShaderNodeMath"); cut.operation = "GREATER_THAN"; cut.inputs[1].default_value = 0.5
                L.new(tex.outputs["Alpha"], cut.inputs[0]); L.new(cut.outputs[0], mix.inputs[0])
            else:
                L.new(tex.outputs["Alpha"], mix.inputs[0])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED" if kind in ("body", "cut") else "BLENDED"
        m.use_backface_culling = False
        return m

    def _make(self, kind):
        me = self._mesh(kind)
        m = self._material(kind)
        me.materials.append(m)
        o = bpy.data.objects.new(f"{kind}{len(self.items[kind])}", me); self.col.objects.link(o)
        o.visible_shadow = kind == "body"
        it = (o, m.node_tree.nodes["Tex"])
        self.items[kind].append(it)
        return it

    def pose(self, layer):
        free = {k: list(v) for k, v in self.items.items()}
        for v in self.items.values():
            for o, _ in v:
                o.hide_render = True; o.hide_viewport = True
        jobs = [(p, "body") for p in layer.get("places", [])] + [(p, p.get("mode", "cut")) for p in layer.get("fx", [])]
        for p, kind in jobs:
            o, tex = free[kind].pop(0) if free[kind] else self._make(kind)
            tex.image = bpy.data.images.load(os.path.join(self.dir, p["t"] + ".png"), check_existing=True)
            o.matrix_world = obj_matrix(p["m"])
            o.hide_render = False; o.hide_viewport = False
        return len(jobs)
