# Run a command while holding the machine-wide GPU lock (one Blender/Chrome render at a time on this PC).
#   python D:\gimli3d\blender\lockrun.py <command> [args...]
# Every agent MUST launch Blender through this wrapper: parallel renders exhausted the GPU before.
import msvcrt
import os
import subprocess
import sys
import time

LOCK = r"D:\gimli3d\gpu.lock"
fh = open(LOCK, "a+")
t0 = time.time()
while True:
    try:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        break
    except OSError:
        time.sleep(2)
waited = time.time() - t0
if waited > 3:
    print(f"[lockrun] waited {waited:.0f} s for the GPU", flush=True)
try:
    rc = subprocess.call(sys.argv[1:])
finally:
    fh.seek(0)
    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    fh.close()
sys.exit(rc)
