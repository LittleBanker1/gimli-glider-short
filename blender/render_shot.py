# Render one shot of the film in Blender from the exported data.
#   blender -b --factory-startup -P render_shot.py -- --shot 3 [--frames 260,300 | --range 243 350] [--scale 50]
#          [--out D:\gimli3d\render] [--export D:\gimli3d\export] [--samples 16] [--no-cards] [--tag test]
# Frames are FINAL frames (the voice take, 0..2056) as in export/frames.jsonl. Every layer of a frame whose shot id is
# --shot is rendered (crossfade frames appear in two shots; assemble.py blends them).
# Output: <out>/<tag or shot_XX>/<frame:05d>.png
# A set module sets/<name>.py must define build(ctx) and may define animate(ctx, layer, frame_info);
# ctx = dict(ink=<collection for outlined geometry>, plain=<collection for non-outlined>, shot, light, set, lib, layout).
# The jet module jet.py defines build(ctx) -> handle and pose(handle, jet_dict, t).
import argparse
import importlib
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import layout  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--shot", type=int, required=True)
ap.add_argument("--frames", default="")
ap.add_argument("--range", nargs=2, type=int)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--samples", type=int, default=16)
ap.add_argument("--out", default=r"D:\gimli3d\render")
ap.add_argument("--export", default=r"D:\gimli3d\export")
ap.add_argument("--tag", default="")
ap.add_argument("--no-cards", action="store_true")
ap.add_argument("--save-blend", default="")
a = ap.parse_args(argv)

INTERIOR = {"cockpit", "cabin", "checkin"}
want = set(int(x) for x in a.frames.split(",") if x) if a.frames else None
jobs = []
with open(os.path.join(a.export, "frames.jsonl"), encoding="utf-8") as fh:
    for line in fh:
        d = json.loads(line)
        fn = d["fn"]
        if want is not None and fn not in want:
            continue
        if a.range and not (a.range[0] <= fn <= a.range[1]):
            continue
        for lay in d["layers"]:
            if lay["id"] == a.shot:
                jobs.append((fn, d["f"], lay))
if not jobs:
    raise SystemExit(f"no frames of shot {a.shot} in the selection")
meta = json.load(open(os.path.join(a.export, "meta.json")))

bpy.ops.wm.read_factory_settings(use_empty=True)
first = jobs[0][2]
setname = first["set"]
light = first["light"]
if setname in INTERIOR:
    light = "interior_golden" if light == "golden" else "interior"
lib.render_settings(a.scale, a.samples)
lib.toon_group(); lib.card_group(); lib.set_light(light)
lib.world_sky(light)
sun = lib.sun_lamp(light, first["sun"])
ink = lib.new_col("INK"); plain = lib.new_col("PLAIN"); cards_col = lib.new_col("CARDS")
ctx = dict(ink=ink, plain=plain, shot=a.shot, light=light, set=setname, lib=lib, layout=layout)
setmod = importlib.import_module(f"sets.{setname}")
setmod.build(ctx)
jetmod = jet = None
if any(j[2]["jet"]["visible"] for j in jobs):
    jetmod = importlib.import_module("jet")
    jet = jetmod.build(ctx)
ink_radius = getattr(setmod, "INK_RADIUS", 0.03)
if isinstance(ink_radius, dict):
    ink_radius = ink_radius.get(a.shot, ink_radius.get("default", 0.03))
lib.line_art(ink, radius=ink_radius)
tmpl = bpy.data.collections.get("_templates")
if tmpl:  # imported Kenney originals stay out of the render
    tmpl.hide_render = True
    if tmpl.name in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.unlink(tmpl)

camd = bpy.data.cameras.new("Cam"); camd.sensor_fit = "VERTICAL"
cam = bpy.data.objects.new("Cam", camd); bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
pool = lib.CardPool(cards_col, os.path.join(a.export, "cards"), meta["body"])

outdir = os.path.join(a.out, a.tag or f"shot_{a.shot:02d}")
os.makedirs(outdir, exist_ok=True)
sc = bpy.context.scene
t0 = time.time()
for k, (fn, fpic, lay) in enumerate(jobs):
    sc.frame_current = fn
    camd.angle_y = lay["cam"]["fov"] * 3.14159265 / 180
    camd.clip_start, camd.clip_end = lay["cam"]["near"], 4000
    cam.matrix_world = lib.cam_matrix(lay["cam"]["m"])
    if jet is not None:
        jetmod.pose(jet, lay["jet"], fpic / 30.0)
    if hasattr(setmod, "animate"):
        setmod.animate(ctx, lay, dict(fn=fn, f=fpic, t=fpic / 30.0))
    if not a.no_cards:
        pool.pose(lay)
    sc.render.filepath = os.path.join(outdir, f"{fn:05d}.png")
    bpy.ops.render.render(write_still=True)
    if k % 20 == 0:
        print(f"[shot {a.shot}] frame {fn} ({k + 1}/{len(jobs)}) {time.time() - t0:.0f} s", flush=True)
if a.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
print(f"[shot {a.shot}] done {len(jobs)} frames in {time.time() - t0:.0f} s -> {outdir}", flush=True)
