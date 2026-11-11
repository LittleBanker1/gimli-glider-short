# words_raw.json (SAPI starts) + voice.wav -> words.json [{w, s, e}] with e = last voiced sample before the next word.
import json, sys, wave
import numpy as np
d = sys.argv[1]
raw0 = json.load(open(f"{d}/words_raw.json", encoding="utf-8-sig"))
SCALE = float(sys.argv[2]) if len(sys.argv) > 2 else 1 / 3   # SAPI reports AudioPosition as if the stream were 16 kHz
raw = []
for r in raw0:                     # number expansion fires several events with the same text: keep the earliest
    t = float(r["s"]) * SCALE
    if raw and raw[-1]["w"] == r["w"] and t - raw[-1]["s"] < 1.5: raw[-1]["s"] = min(raw[-1]["s"], t); continue
    raw.append({"w": r["w"], "s": t})
with wave.open(f"{d}/voice.wav") as w:
    sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hop = sr // 100
env = np.sqrt(np.convolve(x * x, np.ones(hop) / hop, "same"))[::hop]   # 10 ms RMS
thr = max(env.max() * 0.03, 1e-4)
dur = len(x) / sr
out = []
for i, r in enumerate(raw):
    s = float(r["s"]); nxt = float(raw[i + 1]["s"]) if i + 1 < len(raw) else dur
    a, b = int(s * 100), max(int(nxt * 100), int(s * 100) + 1)
    voiced = np.nonzero(env[a:b] > thr)[0]
    e = (a + voiced[-1] + 1) / 100 if len(voiced) else min(nxt, s + 0.25)
    out.append({"w": r["w"], "s": round(s, 3), "e": round(max(e, s + 0.05), 3)})
json.dump(out, open(f"{d}/words.json", "w", encoding="utf-8"), indent=0)
print(f"{len(out)} words, {dur:.2f} s audio, last word ends {out[-1]['e']:.2f} s")
