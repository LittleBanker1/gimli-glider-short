# Sky set (shots 1, 9, 13; golden): the jet flies at the origin toward -Y, high above a sunset cloud sea.
#  - world: a painted sunset for camera rays (deep violet top -> magenta/rose -> orange/gold horizon band), a big sun
#    disc + glow in the camera direction, high cirrus streaks lit from below; a flat ambient for lighting (as lib).
#  - cloud sea ~150 m below: stylised cumulus (metaballs -> mesh, flat bases, lumpy noise, cavity + height attributes),
#    three-tone toon (lit #ffd2a8, mid #f2a08f, shade #a98fc4) driven by the sun + its shadows, backlit silver lining,
#    aerial perspective toward the horizon colour, thin plum inverted-hull outlines (Line Art on hundreds of clouds
#    would be far too slow). Depth bands near / mid / far / very far, towering cumulus near the horizon.
#  - wisps at the jet's level for parallax (kept out of every camera -> jet and camera -> fx-card sight line).
#  - a dark dusk ground ~1 km under the cloud sea (fields, forests, lakes that mirror the sunset) seen through the gaps.
#  - animate(): everything earth-fixed rides on one rig empty that scrolls toward +Y at 70 m/s; in shot 13 the air also
#    rises so that, relative to the sinking jet, it passes 12 m forward for every metre down.
# The cloud field is generated around each shot's cameras (read from export/frames.jsonl) and culled to what the
# camera can see during the shot, so every shot gets a dense sea for a modest polygon budget.
import json
import math
import os
import random
import sys
import time

import bmesh
import bpy
from mathutils import Vector
from mathutils import noise as mnoise

INK_RADIUS = {1: 0.04, 9: 0.09, 13: 0.045, "default": 0.05}

SPEED = 70.0       # m/s, the cloud sea scrolls toward +Y (the jet flies toward -Y)
GLIDE = 12.0       # shot 13: 12 m forward for every metre down
SEA = -150.0       # mean cloud-top height
GROUND = -1150.0   # the dusk ground under the cloud sea
CLIP = 16000.0     # far clip for the sky shots (render_shot.py sets 4000 m, too short for the horizon)
T0 = {1: 0.0, 9: 842.374 / 30.0, 13: 1136.253 / 30.0}  # picture time of each shot's first frame
GLIDE_SHOTS = {13}
LINE_PX = 2.4      # cloud outline width in pixels at 1080x1920
ASPECT = 1080 / 1920

PAL = {
    "golden": dict(lit="#ffd2a8", mid="#f2a08f", shade="#a98fc4", deep="#76609f", ink="#341d4c", glow="#fff1d2",
                   haze_sun="#ffb47a", haze_off="#e5879a", ground_haze="#6a4682"),
    "day": dict(lit="#fbf8f1", mid="#e1e5f3", shade="#c3cbe9", deep="#97a3d4", ink="#26305e", glow="#ffffff",
                haze_sun="#d8e7fb", haze_off="#bed3f6", ground_haze="#7f9ccc"),
}
# camera-visible sky by elevation (degrees, hex); compressed so the narrow vertical frame spans the whole sunset
SKY = {
    "golden": [(-6, "#e2898a"), (-0.4, "#ffb47c"), (0, "#ffcc88"), (1.2, "#ffad74"), (3, "#f98a6c"), (5.5, "#e1657a"),
               (8, "#b24c8a"), (11, "#7f3c8f"), (15, "#532f88"), (21, "#382572"), (32, "#221950")],
    "day": [(-6, "#b9d2f4"), (0, "#d4e5fb"), (3, "#a4c6f4"), (8, "#6f9eee"), (15, "#4d80e2"), (32, "#3361cf")],
}

_S = {}  # per-run state shared by build() and animate()


# ---------------------------------------------------------------- small node helpers
def _lin(lib, h):
    return (*lib.hex_rgb(h), 1.0)


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _smooth(nt, x, e0, e1):
    n = nt.nodes.new("ShaderNodeMapRange"); n.interpolation_type = "SMOOTHSTEP"; n.clamp = True
    nt.links.new(x, n.inputs["Value"])
    n.inputs["From Min"].default_value = e0; n.inputs["From Max"].default_value = e1
    return n.outputs["Result"]


def _mix(nt, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"; n.clamp_factor = True
    for sock, v in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return n.outputs[2]


def _add_col(nt, a, b, fac=1.0):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"; n.blend_type = "ADD"
    n.inputs[0].default_value = fac if isinstance(fac, (int, float)) else 1.0
    if not isinstance(fac, (int, float)):
        nt.links.new(fac, n.inputs[0])
    for sock, v in ((n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, tuple):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return n.outputs[2]


def _vec(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeVectorMath"); n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, Vector)):
            n.inputs[i].default_value = tuple(v)
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[1] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs[0]


def _xyz(nt, v):
    n = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(v, n.inputs[0])
    return n.outputs


def _haze_col(nt, lib, pal, view, sun):
    """aerial-perspective colour: golden toward the sun's azimuth, rose away from it"""
    sh = Vector((sun.x, sun.y, 0)).normalized()
    vx = _xyz(nt, view)
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(vx[0], comb.inputs[0]); nt.links.new(vx[1], comb.inputs[1])
    hv = _vec(nt, "NORMALIZE", comb.outputs[0])
    k = _smooth(nt, _vec(nt, "DOT_PRODUCT", hv, sh), 0.55, 0.995)
    return _mix(nt, k, _lin(lib, pal["haze_off"]), _lin(lib, pal["haze_sun"]))


# ---------------------------------------------------------------- materials
def _cloud_material(lib, pal, sun, sunk):
    m = bpy.data.materials.new("SkyCloud"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse"); diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB"); bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(diff.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs[0], bw.inputs[0])
    lv = _math(nt, "MULTIPLY", bw.outputs[0], 1.0 / sunk)            # ~ N.L x sun visibility
    hgt = nt.nodes.new("ShaderNodeAttribute"); hgt.attribute_name = "hgt"
    cav = nt.nodes.new("ShaderNodeAttribute"); cav.attribute_name = "cav"
    # three tones; the shade tone darkens toward the flat base (cumulus have darker bellies)
    shade = _mix(nt, _smooth(nt, hgt.outputs["Fac"], 0.0, 0.6), _lin(lib, pal["deep"]), _lin(lib, pal["shade"]))
    f_mid = _smooth(nt, lv, 0.035, 0.085)
    f_lit = _smooth(nt, lv, 0.2, 0.32)
    col = _mix(nt, f_mid, shade, _lin(lib, pal["mid"]))
    col = _mix(nt, f_lit, col, _lin(lib, pal["lit"]))
    # pink sky-fill on up-facing shaded tops
    nz = _xyz(nt, geo.outputs["Normal"])[2]
    up = _math(nt, "MULTIPLY", _smooth(nt, nz, 0.45, 0.95), 0.45)
    up = _math(nt, "MULTIPLY", up, _math(nt, "SUBTRACT", 1.0, f_mid))
    col = _mix(nt, up, col, _lin(lib, pal["mid"]))
    # crevices between the puffs
    col = _mix(nt, _math(nt, "MULTIPLY", cav.outputs["Fac"], 0.75), col, _lin(lib, pal["deep"]))
    # silver lining where we look toward the sun past a silhouette
    view = _vec(nt, "SCALE", geo.outputs["Incoming"]); view.node.inputs["Scale"].default_value = -1.0
    fwd = _smooth(nt, _vec(nt, "DOT_PRODUCT", view, tuple(sun)), 0.45, 0.97)
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    rim = _math(nt, "MULTIPLY", _smooth(nt, lw.outputs["Facing"], 0.55, 0.88), fwd)
    col = _mix(nt, _math(nt, "MULTIPLY", rim, 0.95), col, _lin(lib, pal["glow"]))
    # aerial perspective: far clouds melt into the horizon band (only beyond ~700 m, never a full wash)
    cam = nt.nodes.new("ShaderNodeCameraData")
    d = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", cam.outputs["View Distance"], 700.0), 0.0)
    fog = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, _math(nt, "EXPONENT", _math(nt, "MULTIPLY", d, -1 / 5200.0))), 0.86)
    hz = _haze_col(nt, lib, pal, view, sun)
    col = _mix(nt, fog, col, hz)
    nt.links.new(col, em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
    return m


def _ink_material(lib, pal, sun):
    m = bpy.data.materials.new("SkyCloudInk"); m.use_nodes = True
    m.use_backface_culling = True
    if hasattr(m, "use_backface_culling_shadow"):
        m.use_backface_culling_shadow = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry"); cam = nt.nodes.new("ShaderNodeCameraData")
    view = _vec(nt, "SCALE", geo.outputs["Incoming"]); view.node.inputs["Scale"].default_value = -1.0
    d = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", cam.outputs["View Distance"], 350.0), 0.0)
    fog = _math(nt, "SUBTRACT", 1.0, _math(nt, "EXPONENT", _math(nt, "MULTIPLY", d, -1 / 2600.0)))
    hz = _haze_col(nt, lib, pal, view, sun)
    col = _mix(nt, _math(nt, "MULTIPLY", fog, 0.92), _lin(lib, pal["ink"]), hz)
    nt.links.new(col, em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
    return m


def _ground_material(lib, pal, sun):
    """dusk prairie/forest/lakes in object space (so it scrolls with the rig); emission only"""
    m = bpy.data.materials.new("SkyGround"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord"); geo = nt.nodes.new("ShaderNodeNewGeometry")
    cam = nt.nodes.new("ShaderNodeCameraData")
    wn = nt.nodes.new("ShaderNodeTexNoise"); wn.inputs["Scale"].default_value = 1 / 700.0; wn.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], wn.inputs["Vector"])
    cen = _vec(nt, "SUBTRACT", wn.outputs["Color"], (0.5, 0.5, 0.5))
    sc_ = _vec(nt, "SCALE", cen); sc_.node.inputs["Scale"].default_value = 900.0
    co = _vec(nt, "ADD", tc.outputs["Object"], sc_)
    # field patchwork: Voronoi cells with random colours + light edges (roads / hedges)
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 1 / 300.0
    vor.inputs["Randomness"].default_value = 0.85
    nt.links.new(co, vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = "CONSTANT"
    fields = ["#2a2950", "#3b3466", "#2e3a5c", "#47396a", "#353058", "#3f4a6c"]
    cr.elements[0].color = _lin(lib, fields[0]); cr.elements[1].position = 0.99; cr.elements[1].color = _lin(lib, fields[-1])
    for i, h in enumerate(fields[1:-1]):
        e = cr.elements.new((i + 1) / len(fields)); e.color = _lin(lib, h)
    bwv = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(vor.outputs["Color"], bwv.inputs[0]); nt.links.new(bwv.outputs[0], ramp.inputs[0])
    col = ramp.outputs[0]
    edge = nt.nodes.new("ShaderNodeTexVoronoi"); edge.feature = "DISTANCE_TO_EDGE"
    edge.inputs["Scale"].default_value = 1 / 300.0; edge.inputs["Randomness"].default_value = 0.85
    nt.links.new(co, edge.inputs["Vector"])
    road = _math(nt, "SUBTRACT", 1.0, _smooth(nt, edge.outputs["Distance"], 0.008, 0.02))
    col = _mix(nt, _math(nt, "MULTIPLY", road, 0.55), col, _lin(lib, "#7a6596"))
    # forests: big dark blotches
    fn = nt.nodes.new("ShaderNodeTexNoise"); fn.inputs["Scale"].default_value = 1 / 2600.0
    fn.inputs["Detail"].default_value = 5; fn.inputs["Roughness"].default_value = 0.6
    nt.links.new(co, fn.inputs["Vector"])
    forest = _smooth(nt, fn.outputs["Fac"], 0.48, 0.53)
    col = _mix(nt, forest, col, _lin(lib, "#1f2346"))
    # lakes mirror the sunset, with a dark shore line
    ln = nt.nodes.new("ShaderNodeTexNoise"); ln.inputs["Scale"].default_value = 1 / 1900.0
    ln.inputs["Detail"].default_value = 4; ln.inputs["Roughness"].default_value = 0.55
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = (5310.0, -2270.0, 0.0)
    nt.links.new(co, mp.inputs[0]); nt.links.new(mp.outputs[0], ln.inputs["Vector"])
    shore = _smooth(nt, ln.outputs["Fac"], 0.625, 0.632)
    lake = _smooth(nt, ln.outputs["Fac"], 0.64, 0.646)
    view = _vec(nt, "SCALE", geo.outputs["Incoming"]); view.node.inputs["Scale"].default_value = -1.0
    lake_col = _haze_col(nt, lib, dict(pal, haze_off="#d77a92", haze_sun="#ffc98c"), view, sun)
    col = _mix(nt, shore, col, _lin(lib, "#1a1534"))
    col = _mix(nt, lake, col, lake_col)
    # distance haze (keeps real darks near, melts far ground into dusk)
    fog = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, _math(nt, "EXPONENT", _math(nt, "MULTIPLY", cam.outputs["View Distance"], -1 / 9000.0))), 0.75)
    col = _mix(nt, fog, col, _lin(lib, pal["ground_haze"]))
    nt.links.new(col, em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
    return m


# ---------------------------------------------------------------- world: the painted sunset
def _world(lib, light, pal, disc, sun, streak_deg):
    w = bpy.context.scene.world or bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    dirv = _vec(nt, "NORMALIZE", tc.outputs["Generated"])
    dz = _xyz(nt, dirv)[2]
    el = _math(nt, "MULTIPLY", _math(nt, "ARCSINE", dz), 180 / math.pi)       # elevation in degrees
    stops = SKY["golden" if "golden" in light else "day"]
    lo, hi = stops[0][0], stops[-1][0]
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = "B_SPLINE"
    cr.elements[0].position = 0.0; cr.elements[0].color = _lin(lib, stops[0][1])
    cr.elements[1].position = 1.0; cr.elements[1].color = _lin(lib, stops[-1][1])
    for e, h in stops[1:-1]:
        cr.elements.new((e - lo) / (hi - lo)).color = _lin(lib, h)
    nt.links.new(_math(nt, "MULTIPLY", _math(nt, "SUBTRACT", el, lo), 1 / (hi - lo)), ramp.inputs[0])
    col = ramp.outputs[0]
    # angle to the sun disc (degrees)
    th = _math(nt, "MULTIPLY", _math(nt, "ARCCOSINE", _math(nt, "MINIMUM", _vec(nt, "DOT_PRODUCT", dirv, tuple(disc)), 1.0)), 180 / math.pi)
    elp = _math(nt, "MAXIMUM", el, 0.0)
    golden = "golden" in light
    if golden:
        # high cirrus streaks on a plane 2.5 km above, lit pink/gold from below (perspective-correct)
        zc = _math(nt, "MAXIMUM", dz, 0.02)
        proj = _vec(nt, "SCALE", dirv); nt.links.new(_math(nt, "DIVIDE", 2500.0, zc), proj.node.inputs["Scale"])
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(streak_deg))
        mp.inputs["Scale"].default_value = (1 / 2600.0, 1 / 520.0, 1.0)
        nt.links.new(proj, mp.inputs[0])
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0
        nz.inputs["Detail"].default_value = 4.0; nz.inputs["Roughness"].default_value = 0.55
        nz.inputs["Distortion"].default_value = 0.35
        nt.links.new(mp.outputs[0], nz.inputs["Vector"])
        fade = _math(nt, "MULTIPLY", _smooth(nt, el, 1.2, 3.5), _math(nt, "SUBTRACT", 1.0, _smooth(nt, el, 13.0, 24.0)))
        fade = _math(nt, "MULTIPLY", fade, _smooth(nt, th, 3.2, 6.0))     # keep the disc itself clean
        body = _math(nt, "MULTIPLY", _smooth(nt, nz.outputs["Fac"], 0.55, 0.6), fade)
        core = _smooth(nt, nz.outputs["Fac"], 0.6, 0.66)
        near = _math(nt, "MINIMUM", _math(nt, "ADD", _math(nt, "EXPONENT", _math(nt, "MULTIPLY", th, -1 / 9.0)),
                                           _math(nt, "MULTIPLY", _math(nt, "EXPONENT", _math(nt, "MULTIPLY", elp, -1 / 4.0)), 0.5)), 1.0)
        c_edge = _mix(nt, near, _lin(lib, "#8e4f8e"), _lin(lib, "#e0757e"))
        c_core = _mix(nt, near, _lin(lib, "#d9709a"), _lin(lib, "#ffc890"))
        ccol = _mix(nt, core, c_edge, c_core)
        col = _mix(nt, _math(nt, "MULTIPLY", body, 0.9), col, ccol)
        # sun glow: wide horizon warmth, halo, hot core
        g3 = _math(nt, "MULTIPLY", _math(nt, "EXPONENT", _math(nt, "MULTIPLY", th, -1 / 16.0)),
                   _math(nt, "EXPONENT", _math(nt, "MULTIPLY", elp, -1 / 5.0)))
        col = _add_col(nt, col, _lin(lib, "#c4552a"), _math(nt, "MULTIPLY", g3, 0.55))
        g2 = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", th, -1 / 5.0))
        col = _add_col(nt, col, _lin(lib, "#ff9a40"), _math(nt, "MULTIPLY", g2, 0.5))
        g1 = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", th, -1 / 1.4))
        col = _add_col(nt, col, _lin(lib, "#fff0c0"), _math(nt, "MULTIPLY", g1, 0.9))
        R = 2.9
        disc_f = _math(nt, "SUBTRACT", 1.0, _smooth(nt, th, R - 0.1, R + 0.1))
        ring = _math(nt, "SUBTRACT", 1.0, _smooth(nt, th, R - 0.55, R - 0.35))   # slightly warmer rim inside the edge
        dcol = _mix(nt, _math(nt, "SUBTRACT", 1.0, ring), _lin(lib, "#fff9e6"), _lin(lib, "#ffe2a0"))
        col = _mix(nt, disc_f, col, dcol)
    else:
        g = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", th, -1 / 3.0))
        col = _add_col(nt, col, _lin(lib, "#fff6e0"), g)
        col = _mix(nt, _math(nt, "SUBTRACT", 1.0, _smooth(nt, th, 1.6, 1.8)), col, _lin(lib, "#fffdf6"))
    bg_cam = nt.nodes.new("ShaderNodeBackground"); nt.links.new(col, bg_cam.inputs[0])
    amb_hex, amb_k = lib.LIGHTS.get(light, lib.LIGHTS["golden"])["ambient"]
    bg_amb = nt.nodes.new("ShaderNodeBackground"); bg_amb.inputs[0].default_value = _lin(lib, amb_hex); bg_amb.inputs[1].default_value = amb_k
    lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(bg_amb.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])


# ---------------------------------------------------------------- cloud templates (metaballs -> mesh)
def _bumps(B, rng, n, r0, r1):
    big = [b for b in B if b[3] >= 0.12]
    for _ in range(n):
        x, y, z, r = rng.choice(big)
        a = rng.uniform(0, 2 * math.pi); u = rng.uniform(0.15, 1.0)
        dv = Vector((math.cos(a) * math.sqrt(1 - u * u), math.sin(a) * math.sqrt(1 - u * u), u))
        B.append((x + dv.x * r * 0.62, y + dv.y * r * 0.62, z + dv.z * r * 0.62, rng.uniform(r0, r1)))


def _balls(kind, rng):
    B = []
    if kind in ("clump", "puff"):
        tall = kind == "puff"
        a, b = 0.5, rng.uniform(0.26, 0.36) * (1.25 if tall else 1.0)
        h = rng.uniform(0.75, 1.0) if tall else rng.uniform(0.3, 0.48)
        nb = rng.randint(8, 12)
        for k in range(nb):
            t = 2 * math.pi * k / nb + rng.uniform(-0.25, 0.25); rr = rng.uniform(0.45, 0.88)
            B.append((math.cos(t) * a * rr, math.sin(t) * b * rr, 0.06, rng.uniform(0.12, 0.19)))
        for _ in range(rng.randint(3, 5)):
            B.append((rng.uniform(-0.22, 0.22), rng.uniform(-0.07, 0.07), h * 0.42, rng.uniform(0.17, 0.25)))
        for _ in range(rng.randint(3, 6)):
            x = rng.uniform(-0.3, 0.3)
            B.append((x, rng.uniform(-0.08, 0.08), h * (0.95 - abs(x)) * rng.uniform(0.75, 1.0), rng.uniform(0.11, 0.17)))
        if tall:
            for _ in range(3):
                B.append((rng.uniform(-0.12, 0.12), rng.uniform(-0.06, 0.06), h * rng.uniform(0.6, 0.95), rng.uniform(0.16, 0.22)))
        _bumps(B, rng, rng.randint(12, 18), 0.045, 0.08)
    elif kind == "tower":
        h = rng.uniform(1.5, 2.0)
        for k in range(12):
            t = 2 * math.pi * k / 12 + rng.uniform(-0.2, 0.2); rr = rng.uniform(0.5, 0.9)
            B.append((math.cos(t) * 0.5 * rr, math.sin(t) * 0.4 * rr, 0.08, rng.uniform(0.15, 0.22)))
        lev = 7
        for i in range(1, lev + 1):
            z = h * i / (lev + 1)
            w = 0.34 * (1.0 - 0.45 * i / lev) + 0.08 * math.sin(i * 1.7)
            for _ in range(3):
                a = rng.uniform(0, 2 * math.pi)
                B.append((math.cos(a) * w * 0.55 + 0.05 * i * 0.15, math.sin(a) * w * 0.4, z, rng.uniform(0.17, 0.25)))
        for _ in range(6):  # cauliflower crown
            a = rng.uniform(0, 2 * math.pi)
            B.append((math.cos(a) * 0.17, math.sin(a) * 0.13, h * rng.uniform(0.86, 1.0), rng.uniform(0.13, 0.19)))
        _bumps(B, rng, 30, 0.05, 0.09)
    elif kind == "bank":
        for _ in range(26):
            B.append((rng.uniform(-0.45, 0.45), rng.uniform(-0.32, 0.32), 0.05, rng.uniform(0.1, 0.16)))
        for _ in range(9):
            B.append((rng.uniform(-0.38, 0.38), rng.uniform(-0.22, 0.22), rng.uniform(0.09, 0.15), rng.uniform(0.1, 0.15)))
        _bumps(B, rng, 18, 0.04, 0.07)
    elif kind == "wisp":
        n = 11
        for i in range(n):
            u = i / (n - 1); x = (u - 0.5) * 0.92
            r = 0.05 + 0.08 * math.sin(math.pi * u) ** 0.8
            B.append((x, 0.05 * math.sin(u * 7.0 + rng.uniform(0, 3)), 0.03 * math.sin(u * 5.0), r * rng.uniform(0.85, 1.15)))
        for _ in range(6):
            x = rng.uniform(-0.3, 0.3)
            B.append((x, rng.uniform(-0.04, 0.04), 0.04, rng.uniform(0.05, 0.09)))
    return B


def _template(name, kind, rng, res, lib, mats):
    B = _balls(kind, rng)
    mb = bpy.data.metaballs.new(name)
    mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    for x, y, z, r in B:
        e = mb.elements.new(); e.co = (x, y, z); e.radius = r; e.stiffness = 2.0
    ob = bpy.data.objects.new(name, mb); bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.metaballs.remove(mb)
    me.name = name
    bm = bmesh.new(); bm.from_mesh(me)
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
    w = max(xs) - min(xs)
    cx, cy, z0 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)
    for v in bm.verts:
        v.co = Vector(((v.co.x - cx) / w, (v.co.y - cy) / w, (v.co.z - z0) / w))
    top = (max(zs) - z0) / w
    if kind != "wisp":  # flat cumulus base
        cut = 0.07 * top if kind != "tower" else 0.035 * top
        for v in bm.verts:
            if v.co.z < cut:
                v.co.z = cut
    else:
        for v in bm.verts:
            v.co.z *= 0.55
    bm.normal_update()
    seed = Vector((rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(0, 100)))
    for v in bm.verts:  # lumpy surface
        n = mnoise.fractal(v.co * 9.0 + seed, 0.6, 2.1, 3)
        v.co += v.normal * (0.011 * n * (0.3 if v.co.z <= 0.08 * top else 1.0))
    bm.normal_update()
    zs = [v.co.z for v in bm.verts]; zmin, zmax = min(zs), max(zs)
    cav = []
    for v in bm.verts:
        if not v.link_edges:
            cav.append(0.0); continue
        avg = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
        el = sum(e.calc_length() for e in v.link_edges) / len(v.link_edges)
        cav.append((avg - v.co).dot(v.normal) / max(el, 1e-6))
    bm.verts.ensure_lookup_table()
    for _ in range(2):  # blur
        cav = [(c + sum(cav[e.other_vert(v).index] for e in v.link_edges)) / (1 + len(v.link_edges)) for v, c in zip(bm.verts, cav)]
    bm.to_mesh(me); bm.free()
    a = me.attributes.new("cav", "FLOAT", "POINT")
    a.data.foreach_set("value", [min(1.0, max(0.0, (c - 0.015) / 0.09)) for c in cav])
    h = me.attributes.new("hgt", "FLOAT", "POINT")
    h.data.foreach_set("value", [(v.co.z - zmin) / max(zmax - zmin, 1e-6) for v in me.vertices])
    me.shade_smooth()
    for m in mats:
        me.materials.append(m)
    return dict(me=me, top=zmax, kind=kind, depth=max(v.co.y for v in me.vertices) - min(v.co.y for v in me.vertices))


def _templates(lib, mats):
    rng = random.Random(1983)
    T = {"clump": [], "puff": [], "tower": [], "bank": [], "wisp": []}
    spec = [("clump", 6, 0.016, 0.034), ("puff", 2, 0.016, 0.034), ("tower", 2, 0.03, 0.05), ("bank", 3, 0.02, 0.036),
            ("wisp", 3, 0.014, 0.03)]
    for kind, n, rhi, rlo in spec:
        for i in range(n):
            st = rng.getstate()
            hi = _template(f"cl{kind}{i}h", kind, rng, rhi, lib, mats)
            rng.setstate(st)
            lo = _template(f"cl{kind}{i}l", kind, rng, rlo, lib, mats)
            T[kind].append((hi, lo))
    return T


# ---------------------------------------------------------------- cameras of the shot (for culling and line widths)
def _export_dir():
    a = sys.argv
    if "--export" in a and a.index("--export") + 1 < len(a):
        return a[a.index("--export") + 1]
    return r"D:\gimli3d\export"


def _shot_frames(lib, shot):
    out = []
    try:
        with open(os.path.join(_export_dir(), "frames.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                if '"sky"' not in line:
                    continue
                d = json.loads(line)
                for lay in d["layers"]:
                    if lay["id"] != shot:
                        continue
                    m = lib.cam_matrix(lay["cam"]["m"])
                    jet = lay.get("jet", {})
                    jp = lib.obj_matrix(jet["m"]).translation.copy() if jet.get("m") else Vector((0, 0, 0))
                    fx = []
                    for p in lay.get("fx", []):
                        mm = lib.obj_matrix(p["m"]); sc = mm.to_scale()
                        fx.append((mm.translation.copy(), 0.55 * max(sc)))
                    out.append(dict(f=d["f"], inv=m.inverted(), pos=m.translation.copy(), fwd=(m.to_3x3() @ Vector((0, 0, -1))).normalized(),
                                    fov=math.radians(lay["cam"]["fov"]), jet=jp, jet_on=bool(jet.get("visible", True)), fx=fx))
    except (OSError, ValueError, KeyError) as e:
        print("[sky] could not read the shot cameras:", e)
    out.sort(key=lambda c: c["f"])
    return out


def _in_view(c, p, r):
    q = c["inv"] @ p
    depth = -q.z
    if depth < -r or depth - r > CLIP:
        return False
    ty = math.tan(c["fov"] / 2); tx = ty * ASPECT
    if abs(q.x) - tx * depth > r * math.sqrt(1 + tx * tx):
        return False
    if abs(q.y) - ty * depth > r * math.sqrt(1 + ty * ty):
        return False
    return True


def _blocks(c, p, ext):
    """True if an ellipsoid (centre p, half extents ext) hides the jet or an fx card from camera c"""
    targets = ([(c["jet"], 30.0)] if c["jet_on"] else []) + c["fx"]
    for tgt, tr in targets:
        lo = min(c["pos"].z, tgt.z) - tr - ext.z
        hi = max(c["pos"].z, tgt.z) + tr + ext.z
        if p.z < lo or p.z > hi:
            continue
        for k in range(1, 24):
            u = k / 24
            q = c["pos"].lerp(tgt, u)
            rad = tr * u + 2.0
            dx, dy, dz = (q.x - p.x) / (ext.x + rad), (q.y - p.y) / (ext.y + rad), (q.z - p.z) / (ext.z + rad)
            if dx * dx + dy * dy + dz * dz < 1.0:
                return True
    return False


# ---------------------------------------------------------------- build
def build(ctx):
    t_start = time.time()
    lib, shot, light = ctx["lib"], ctx["shot"], ctx["light"]
    pal = PAL["golden" if "golden" in light else "day"]
    _S.clear()
    sun_o = bpy.data.objects.get("Sun")
    sun = (sun_o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized() if sun_o else Vector((0, -0.99, 0.12)).normalized()
    sunk = 4.0
    if sun_o:
        c = sun_o.data.color
        sunk = max(0.5, sun_o.data.energy * (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]))
    cams = _shot_frames(lib, shot)
    t0 = T0.get(shot, cams[0]["f"] / 30.0 if cams else 0.0)
    rise = 0.0
    if shot in GLIDE_SHOTS and len(cams) > 1:
        dt = (cams[-1]["f"] - cams[0]["f"]) / 30.0
        rise = SPEED / GLIDE + (cams[-1]["jet"].z - cams[0]["jet"].z) / max(dt, 1e-3)
    _S.update(t0=t0, rise=rise, cams=cams)

    def off(f):
        k = f / 30.0 - t0
        return Vector((0.0, SPEED * k, rise * k))

    samples = cams[::3] + cams[-1:] if cams else []
    if cams:
        ref = sum((c["pos"] for c in cams), Vector()) / len(cams)
        vdir = sum((c["fwd"] for c in cams), Vector()); vdir.z = 0; vdir.normalize()
        fov = cams[0]["fov"]
        f_mid = (cams[0]["f"] + cams[-1]["f"]) / 2
    else:  # no export data: assume a camera behind the jet looking ahead
        ref, vdir, fov, f_mid = Vector((0, 120, 30)), Vector((0, -1, 0)), math.radians(40), t0 * 30
    view_az = math.degrees(math.atan2(vdir.y, vdir.x))

    # the sun sits just beside the camera direction (so it reads in frame) and low over the horizon; aim the lamp the same way
    az_s = math.radians(view_az + 9.0); el_s = math.radians(8.0)
    sun = Vector((math.cos(az_s) * math.cos(el_s), math.sin(az_s) * math.cos(el_s), math.sin(el_s)))
    if sun_o:
        sun_o.rotation_euler = (-sun).to_track_quat("-Z", "Y").to_euler()
    disc = sun.copy()
    if cams:
        pitch = math.degrees(math.asin(max(-1, min(1, cams[0]["fwd"].z))))
        top_el = pitch + math.degrees(fov) / 2 - 3.6
        if math.degrees(el_s) > top_el:
            e = math.radians(max(1.6, top_el))
            disc = Vector((math.cos(az_s) * math.cos(e), math.sin(az_s) * math.cos(e), math.sin(e)))
    _world(lib, light, pal, disc, sun, view_az + 62.0)
    print("[sky] sun az", math.degrees(math.atan2(sun.y, sun.x)), "el", math.degrees(math.asin(sun.z)), "cam fwd az", [round(math.degrees(math.atan2(c["fwd"].y, c["fwd"].x))) for c in cams[::20]], flush=True)
    for c in (cams[:1] + cams[-1:]):
        q = c["inv"].to_3x3() @ disc
        if q.z < 0:
            ty = math.tan(c["fov"] / 2)
            print(f"[sky] disc ndc f{c['f']}: x {q.x / -q.z / (ty * ASPECT):.2f} y {q.y / -q.z / ty:.2f}", flush=True)

    cmat = _cloud_material(lib, pal, sun, sunk)
    imat = _ink_material(lib, pal, sun)
    T = _templates(lib, [cmat, imat])

    plain = ctx["plain"]
    rig = bpy.data.objects.new("SkyRig", None); plain.objects.link(rig)
    _S["rig"] = rig

    rng = random.Random(7 + shot)
    clouds = []  # dict(t=template(hi, lo), lod, p (base centre), s (scale), yaw, shadow)

    def add(kind, p, w, dfac, hfac, yaw, band, var=None, shadow=True):
        hi, lo = (var if var is not None else rng.choice(T[kind]))
        tp = hi
        ext = Vector((w * 0.5, w * 0.5 * max(dfac, 1.0), w * hfac * tp["top"] * 0.5))
        clouds.append(dict(t=(hi, lo), p=p, s=Vector((w, w * dfac, w * hfac)), yaw=yaw, band=band, ext=ext, shadow=shadow))

    # -- cloud sea: jittered grid cells in distance bands around the shot's cameras
    bands = [(120, 1450, 85, "near", -0.12), (1450, 3300, 190, "mid", -0.28), (3300, 7200, 430, "far", -0.55),
             (7200, 15000, 1000, "vfar", -9.0)]
    o_mid = off(f_mid)
    for r0, r1, cell, band, thr in bands:
        n0x, n1x = math.floor((ref.x - r1) / cell), math.ceil((ref.x + r1) / cell)
        n0y, n1y = math.floor((ref.y - r1 - o_mid.y) / cell), math.ceil((ref.y + r1 - o_mid.y) / cell)
        for gx in range(n0x, n1x + 1):
            for gy in range(n0y, n1y + 1):
                cr = random.Random(f"{band}:{gx}:{gy}")
                x = (gx + cr.uniform(0.1, 0.9)) * cell
                y = (gy + cr.uniform(0.1, 0.9)) * cell
                pm = Vector((x, y, 0)) + o_mid
                d = math.hypot(pm.x - ref.x, pm.y - ref.y)
                if not (r0 <= d < r1):
                    continue
                # only the half-plane in front of the camera can ever be seen
                if (pm.x - ref.x) * vdir.x + (pm.y - ref.y) * vdir.y < -400:
                    continue
                cov = mnoise.noise(Vector((x / 1500, y / 1500, 0.37))) + 0.55 * mnoise.noise(Vector((x / 520, y / 520, 3.1)))
                if cov < thr:
                    continue
                if band in ("near", "mid"):
                    kind = "puff" if cr.random() < 0.08 else "clump"
                    w = cell * cr.uniform(1.05, 1.75)
                    hfac = cr.uniform(0.8, 1.25) if kind == "clump" else cr.uniform(0.9, 1.2)
                    top_z = SEA + cr.uniform(-14, 16) + (25 if kind == "puff" else 0)
                else:
                    kind = "bank" if (band == "vfar" or cr.random() < 0.5) else "clump"
                    w = cell * cr.uniform(1.0, 1.55)
                    hfac = cr.uniform(0.9, 1.4) if kind == "bank" else cr.uniform(0.45, 0.7)
                    top_z = SEA + cr.uniform(-5, 22) + (20 if band == "vfar" else 0)
                var = cr.choice(T[kind])
                top = var[0]["top"] * w * hfac
                p = Vector((x, y, top_z - top))
                add(kind, p, w, cr.uniform(0.75, 1.15), hfac, cr.uniform(0, 2 * math.pi), band, var=var, shadow=band != "vfar")

    # -- towering cumulus near the horizon, beside (never over) the sun
    disc_h = Vector((disc.x, disc.y, 0)).normalized()
    sun_az = math.degrees(math.atan2(disc_h.y, disc_h.x))
    half_h = math.degrees(math.atan(math.tan(fov / 2) * ASPECT))
    tower_spots = [(-0.75, 5200, 820), (0.82, 6400, 980), (-0.35, 9800, 1300), (0.45, 3900, 520), (1.25, 8200, 1150)]
    made = 0
    for k, (side, dist, w) in enumerate(tower_spots):
        az = view_az + side * half_h
        if abs((az - sun_az + 180) % 360 - 180) < 6.5:
            az += 7.0 * (1 if side >= 0 else -1)
        p = Vector((ref.x + math.cos(math.radians(az)) * dist, ref.y + math.sin(math.radians(az)) * dist, SEA - 30)) - o_mid
        var = T["tower"][k % len(T["tower"])]
        hfac = rng.uniform(0.75, 1.0)
        add("tower", p, w, rng.uniform(0.8, 1.0), hfac, rng.uniform(0, 6.28), "tower", var=var)
        made += 1

    # -- wisps at the jet's level (parallax), never between the camera and the jet / fx cards
    for k in range(70):
        ang = rng.uniform(-1.0, 1.0) * math.radians(half_h * 2.2) + math.radians(view_az)
        dist = rng.uniform(140, 1300)
        x = ref.x + math.cos(ang) * dist; y = ref.y + math.sin(ang) * dist
        z = rng.uniform(-95, 45)
        w = rng.uniform(40, 120) * (0.6 + dist / 900)
        p = Vector((x, y, z)) - o_mid
        add("wisp", p, w, rng.uniform(0.5, 0.9), rng.uniform(0.9, 1.4), math.radians(rng.uniform(-35, 35)) + math.radians(view_az + 90),
            "wisp", shadow=False)

    # -- cull: keep what any sampled camera sees; drop anything that hides the jet or an fx card; line widths
    rig_objs = 0
    keep = []
    for cl in clouds:
        ctr0 = cl["p"] + Vector((0, 0, cl["ext"].z))
        r = cl["ext"].length
        seen, block, dmin = False, False, 1e9
        for c in samples:
            ctr = ctr0 + off(c["f"])
            if _in_view(c, ctr, r):
                seen = True
                dmin = min(dmin, (ctr - c["pos"]).length)
            if cl["band"] in ("wisp", "tower", "near") and _blocks(c, ctr, cl["ext"]):
                block = True; break
            if cl["band"] == "wisp" and (ctr - c["pos"]).length < 2.2 * cl["ext"].x + 25:
                block = True; break
        if not samples:
            seen, dmin = True, (cl["p"] - ref).length
        if seen and not block:
            cl["dmin"] = max(dmin, 1.0)
            keep.append(cl)
    for i, cl in enumerate(keep):
        hi, lo = cl["t"]
        tp = hi if cl["band"] in ("near", "mid", "wisp", "tower") or cl["dmin"] < 3000 else lo
        o = bpy.data.objects.new(f"cloud{i}", tp["me"]); plain.objects.link(o)
        o.parent = rig
        o.location = cl["p"]; o.rotation_euler = (0, 0, cl["yaw"]); o.scale = cl["s"]
        o.visible_shadow = cl["shadow"]
        px = cl["dmin"] * 2 * math.tan(fov / 2) / 1920
        thick = LINE_PX * px * (0.85 if cl["band"] in ("far", "vfar") else 1.0)
        if cl["band"] == "vfar" or cl["dmin"] > 11000:
            thick = 0
        if thick > 0:
            m = o.modifiers.new("ink", "SOLIDIFY")
            m.thickness = thick / cl["s"].x; m.offset = 1.0; m.use_flip_normals = True; m.use_rim = False
            m.material_offset = 1; m.use_even_offset = False
        rig_objs += 1

    # -- dusk ground far below, seen through the gaps
    gm = _ground_material(lib, pal, sun)
    me = bpy.data.meshes.new("skyground")
    R = 34000.0
    me.from_pydata([(-R, -R, 0), (R, -R, 0), (R, R, 0), (-R, R, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(gm)
    g = bpy.data.objects.new("SkyGround", me); plain.objects.link(g)
    g.parent = rig; g.location = (ref.x, ref.y, GROUND); g.visible_shadow = False
    _S["ground"] = g

    tris = sum(len(o.data.polygons) for o in plain.objects if o.type == "MESH")
    print(f"[sky] shot {shot}: {len(clouds)} candidates -> {rig_objs} clouds ({tris} base faces), "
          f"rise {rise:.2f} m/s, disc el {math.degrees(math.asin(disc.z)):.1f} deg, built in {time.time() - t_start:.1f} s", flush=True)


def animate(ctx, layer, info):
    rig = _S.get("rig")
    if rig is None:
        return
    k = info["t"] - _S["t0"]
    rig.location = (0.0, SPEED * k, _S["rise"] * k)
    cam = bpy.context.scene.camera
    if cam is not None and cam.data.clip_end < CLIP:
        cam.data.clip_end = CLIP
