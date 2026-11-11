# Assemble the final film from the per-shot Blender renders: crossfades (two layers), the white flash, then encode
# with the soundtrack.  python assemble.py <render_dir> <export_dir> <mix.wav> <out.mp4> [--frames-dir D:\gimli3d\final]
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

render, export, wav, out = sys.argv[1:5]
fdir = sys.argv[sys.argv.index("--frames-dir") + 1] if "--frames-dir" in sys.argv else os.path.join(os.path.dirname(out), "final_frames")
os.makedirs(fdir, exist_ok=True)
missing = []
size = None
with open(os.path.join(export, "frames.jsonl"), encoding="utf-8") as fh:
    for line in fh:
        d = json.loads(line)
        fn = d["fn"]
        img = None
        for lay in d["layers"]:
            p = os.path.join(render, f"shot_{lay['id']:02d}", f"{fn:05d}.png")
            if not os.path.exists(p):
                missing.append((fn, lay["id"])); continue
            a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
            size = size or a.shape
            img = a if img is None else img * (1 - lay["alpha"]) + a * lay["alpha"]
        if img is None:
            img = np.zeros(size or (1920, 1080, 3), np.float32)
        if d["flash"]:
            img = img * (1 - d["flash"]) + 255 * d["flash"]
        Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(fdir, f"{fn:05d}.png"))
print(f"{len(missing)} missing layer renders" + (f", first: {missing[:5]}" if missing else ""))
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(fdir, "%05d.png"), "-i", wav,
                       "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
                       "-vf", "scale=1080:1920:flags=lanczos", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out])
print("wrote", out)
