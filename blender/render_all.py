# Full v3 build: re-export cards, render every shot in chunks (resumable), re-render white/blank frames, assemble.
#   python -I D:\gimli3d\blender\render_all.py [--skip-export] [--scale 100] [--chunk 30] [--shots 1,2,...]
# Every Blender / Chrome run goes through lockrun.py (one GPU).  Re-running skips frames that already exist.
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

ROOT = r"D:\gimli3d"
PY = sys.executable
LOCK = os.path.join(ROOT, "blender", "lockrun.py")
BLENDER = r"D:\tools\blender-5.3.0-windows-x64\blender.exe"
EXPORT = os.path.join(ROOT, "export")
RENDER = os.path.join(ROOT, "render")
WAV = os.path.join(ROOT, "studio", "shorts", "gimli", "audio", "mix.wav")
OUT = os.path.join(ROOT, "out", "gimli_v4.mp4")

ap = argparse.ArgumentParser()
ap.add_argument("--skip-export", action="store_true")
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--chunk", type=int, default=30)
ap.add_argument("--shots", default="")
a = ap.parse_args()


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(os.path.join(RENDER, "render_all.log"), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


os.makedirs(RENDER, exist_ok=True)
if not a.skip_export:
    log("export start")
    subprocess.check_call([PY, "-I", LOCK, "node", "scripts/export_frames.mjs", "D:/gimli3d/export"],
                          cwd=os.path.join(ROOT, "studio"), shell=False)
    log("export done")

frames = {}  # shot -> sorted final frame numbers
with open(os.path.join(EXPORT, "frames.jsonl"), encoding="utf-8") as fh:
    for line in fh:
        d = json.loads(line)
        for lay in d["layers"]:
            frames.setdefault(lay["id"], []).append(d["fn"])
shots = [int(s) for s in a.shots.split(",") if s] or sorted(frames)


def path(shot, fn):
    return os.path.join(RENDER, f"shot_{shot:02d}", f"{fn:05d}.png")


def bad(p):
    if not os.path.exists(p):
        return True
    try:
        im = np.asarray(Image.open(p).convert("L").resize((90, 160)), dtype=np.float32)
    except Exception:
        return True
    return im.mean() > 250 or im.std() < 2  # white / blank frame from a GPU context loss


def render(shot, fns):
    cmd = [PY, "-I", LOCK, BLENDER, "-b", "--factory-startup", "-P", os.path.join(ROOT, "blender", "render_shot.py"),
           "--", "--shot", str(shot), "--frames", ",".join(map(str, fns)), "--scale", str(a.scale)]
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=os.path.join(ROOT, "blender"), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    log(f"shot {shot}: {len(fns)} frames {fns[0]}-{fns[-1]} rc={rc} {time.time() - t0:.0f}s")
    return rc


for attempt in range(3):
    todo_total = 0
    for shot in shots:
        todo = [fn for fn in frames[shot] if bad(path(shot, fn))]
        todo_total += len(todo)
        for i in range(0, len(todo), a.chunk):
            render(shot, todo[i:i + a.chunk])
    if not todo_total:
        break
    log(f"pass {attempt + 1}: {todo_total} frames rendered; checking again")

left = [(s, fn) for s in shots for fn in frames[s] if bad(path(s, fn))]
log(f"bad/missing frames after rendering: {len(left)} {left[:10]}")
if a.shots:
    sys.exit(0)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.check_call([PY, "-I", os.path.join(ROOT, "blender", "assemble.py"), RENDER, EXPORT, WAV, OUT,
                       "--frames-dir", os.path.join(ROOT, "final_frames")])
log(f"assembled {OUT}")
