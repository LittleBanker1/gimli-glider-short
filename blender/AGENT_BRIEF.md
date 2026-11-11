# Brief for every agent working on the Blender rebuild of "The Jet That Couldn't Count"

## The goal
A 68.6 s vertical (1080x1920, 30 fps) animated short about the Gimli Glider (Air Canada 767, 1983). The user wants it to
LOOK LIKE the YouTube channel **Ricks Clips**: 2D bean-head cartoon characters (white heads, dark ink outlines) standing in
**rich, colourful, detailed 3D worlds** with strong contrast, cobalt-blue skies, warm sun / violet shadows, black ink
outlines on the 3D world, dense props, foreground objects, sharp backgrounds. Our first version looked "cheap, dull,
empty". Copy the STYLE only, never their stories, characters or shots.

Read before you start (all mandatory):
- `C:\Users\plamb\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\scratch-workspaces\1075869b-3b4c-4777-beb3-a01a908a47fd\d9dcb754-77d8-4770-a5fa-52e3259a2e7f\scratch-2026-11-10-8476a0\shorts-studio\shorts\gimli\LOOK_STUDY.md`
  (measured reference look, gap list, Blender recipe, asset list per set). Call that project folder STUDIO.
- Reference frames: `STUDIO\references\ricks\*.jpg` (76 frames, 337x600; LOOK at the ones relevant to your task) and the
  contact sheets `STUDIO\out\cmp\look_sheet*.jpg`. Our old (bad) frames: `STUDIO\out\cmp\ours\*.jpg`.
- The script/story: `STUDIO\shorts\gimli\SCRIPT.md`. The old three.js versions of the sets (for what each set must contain
  and which props the story needs): `STUDIO\src\videos\gimli\sets.ts`, `jet.ts`, `story.ts` (cameras), `cast.ts` (who stands where).
- This folder `D:\gimli3d\blender\`: `lib.py` (shared helpers: toon materials, Kenney import, sky, sun, ink, cards),
  `layout.py` (where everything must be, Blender coordinates), `render_shot.py` (the renderer), this brief.

## Hard rules
- **Blender**: `D:\tools\blender-5.3.0-windows-x64\blender.exe` (5.3, EEVEE). Python for helper scripts:
  `C:\Users\plamb\AppData\Local\Programs\Python\Python312\python.exe -I` (numpy + Pillow; `scipy.signal` is BLOCKED by
  Windows Application Control, don't import it).
- **Every Blender (or Chrome) run goes through the GPU lock** — several agents share one GPU and parallel renders crashed it:
  `python -I D:\gimli3d\blender\lockrun.py D:\tools\blender-5.3.0-windows-x64\blender.exe -b --factory-startup -P D:\gimli3d\blender\render_shot.py -- --shot 3 --frames 280,330 --scale 50 --tag <yourname>_try1`
  Output: `D:\gimli3d\render\<tag>\<frame:05d>.png`. Keep each locked run short (a handful of frames); never hold the lock
  while thinking. Use `--scale 50` for tests, `--no-cards` to see the set alone.
- **Only edit the files you own** (named in your task). Do NOT edit `lib.py`, `render_shot.py`, `layout.py`, `assemble.py`,
  other agents' files, or anything under STUDIO except what your task names. If you need a helper, write it inside your
  own module. If something shared is broken, say so in your final report.
- **Assets** (all CC0, already downloaded; do not download anything else):
  - Kenney kits `D:\gimli3d\kenney\<kit>\Models\GLB format\*.glb` for kits `car-kit` (50), `city-kit-commercial` (41),
    `city-kit-industrial` (37), `furniture-kit` (140), `nature-kit` (329), `racing-kit` (112). List the folders to choose.
    `lib.kenney(col, kit, model, loc, rot_z, scale, recolor={material: hex})` imports + converts to toon, re-uses meshes.
  - Textures `D:\gimli3d\textures\<Id>\<Id>_1K-JPG_Color.jpg` for Asphalt033, Concrete049, Grass004, Tiles141, Carpet016,
    Leather037, Metal027, Fabric086 (`lib.texture_path(id)`). Use them stylised (tint, `lib.toon(name, color, image, repeat)`),
    never photoreal. You may also paint your own textures with Pillow into `D:\gimli3d\blender\tex\<yourname>\`.
  - Build anything else (jet, cockpit, counters, signs...) yourself from primitives/bmesh with bevels.
- **Look**: all surfaces use `lib.toon(...)` (soft toon ramp, tints per light set by the renderer). Saturated, clean
  albedos; strong value contrast; no grey mush; detailed silhouettes (bevels, trims, panel lines, props). Outlined geometry
  goes in `ctx["ink"]`; things that must NOT get ink lines (glass, emissive screens, sky/cloud cards, particles) in
  `ctx["plain"]`. Set `INK_RADIUS` (metres, world space; a dict `{shot: r, "default": r}` is allowed) so lines are ~3-4 px
  near and >= 2 px far at 1080x1920.
- **Coordinates**: Blender z up. Layout anchors in `layout.py` are the contract — cameras and characters are already fixed
  there by the exported film data (`D:\gimli3d\export\frames.jsonl`, one JSON per final frame: layers[].cam.m = three.js
  camera matrix; use render_shot.py, don't parse it unless you need to). Keep the camera's line of sight clear: render
  your shots and check nothing blocks a face or the subject.
- **Performance**: a 100 % frame must render in <= 6 s. Use linked duplicates / instancing, modest poly counts, few lights.
- **Copyright**: reference frames are private study material; never copy their characters, text or shots.

## Module contract
`sets/<name>.py`:
```python
INK_RADIUS = 0.03           # or {shot: radius, "default": radius}
def build(ctx): ...         # ctx: ink, plain (bpy collections), shot, light, set, lib, layout
def animate(ctx, layer, info): ...   # optional, called before every frame; info = dict(fn=final frame, f=picture frame, t=f/30)
```
`jet.py`: `build(ctx) -> handle`, `pose(handle, jet, t)`; `jet` = dict(visible, pos, yaw, pitch, roll, gear 0..1,
nose 0..1 (nose-gear collapse), rat 0..1, spin 0..1, scrap 0..1 (optional), m = 16 floats (three.js world matrix of the
jet root incl. the nose-down pitch)). Root object's `matrix_world = lib.obj_matrix(jet["m"])`.

Story cue frames (PICTURE frames, i.e. `info["f"]`): fuel-gauge needle drops from full to half 484-498 (shot 4);
amber master-caution lights blink (8-frame period) from 552 (captain side) and 584 (both), shots 5-6; EFIS screens go
black at 672 (shot 6) and stay black in shots 8 and 10; simulator (shot 19, daylight) red warning lights blink from 1767,
crash at 1796; check-in scale display: blank until 1950, "23 kg" 1950-1992, "50 lb" 1992-2030, then alternating every
10 frames; race cars (shot 14) pass y = -300 at picture frame 1318 + 11 i moving toward -Y at 30 m/s in lanes
x = 4 + (i % 3) * 5 (+1.5 for i > 2), i = 0..4; sky cloud sea scrolls toward +Y at 70 m/s (the jet flies toward -Y).

Shot table (FINAL frames for --frames/--range, set, light):
```
 1: 0-159 sky golden        2: 160-263 apron day      3: 264-390 apron day      4: 391-554 apron day
 5: 548-664 cockpit golden  6: 665-719 cockpit golden 7: 714-793 cabin golden   8: 794-863 cockpit golden
 9: 864-923 sky golden     10: 924-1007 cockpit golden 11: 1008-1041 gimli golden 12: 1034-1166 gimli day (field)
13: 1159-1262 sky golden   14: 1263-1374 gimli golden 15: 1375-1490 gimli golden 16: 1491-1616 gimli golden
17: 1617-1721 gimli golden 18: 1713-1764 apron day    19: 1765-1838 cockpit day  20: 1839-1939 apron day
21: 1932-2056 checkin day
```

## How to check your work
Render 3-6 frames spread over each of your shots at --scale 50, then build a side-by-side sheet (Pillow: your frames top,
3-6 relevant `references\ricks` frames bottom, same height) and LOOK at it. Compare: colour richness, contrast, detail
density, ink, depth, foreground. Iterate until yours could sit next to the reference. Keep your final test renders and
sheet in `D:\gimli3d\render\<yourname>_final\`.

## Final report (your last message, <= 250 words)
What you built, which shots you checked, the paths of your final sheet, render time per frame, known weaknesses.
