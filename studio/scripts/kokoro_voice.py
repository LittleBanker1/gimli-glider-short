# Narration with Kokoro-82M (local neural TTS): one take per script line, word timings from the model's phoneme
# durations, lines joined with fixed pauses, resampled to 48 kHz.
# Usage: python scripts/kokoro_voice.py <SCRIPT.md> <outDir> [voice] [speed]
#   -> outDir/voice.wav (48 kHz mono 16-bit), outDir/words.json [{w, s, e}]
import json
import os
import re
import sys
import wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "audio"))
from sigshim import resample_poly  # noqa: E402
from kokoro_onnx import Kokoro  # noqa: E402

script, out = sys.argv[1], sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "af_heart"
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
GAP, GAP_HOOK, LEAD_IN, TAIL = 0.32, 0.5, 0.12, 0.6
PUNCT = set(".,!?;:…—\"'()- ")

lines = []
for ln in open(script, encoding="utf-8"):
    m = re.match(r"^\d+\. (.*)$", ln.strip())
    if m:
        lines.append(re.sub(r"\s*\*\([^)]*\)\*", "", m.group(1)).replace(" — ", ", ").strip())

k = Kokoro(os.path.join(ROOT, "tts_models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "tts_models", "voices-v1.0.bin"))


def groups(timings):
    """phoneme timings -> [(start, end)] per spoken phoneme-word (punctuation-only groups dropped)"""
    out, cur = [], []
    for t in timings + [None]:
        if t is None or t.phoneme == " ":
            if cur and any(c.phoneme not in PUNCT for c in cur):
                sp = [c for c in cur if c.phoneme not in PUNCT]
                out.append((sp[0].start, sp[-1].end))
            cur = []
        else:
            cur.append(t)
    return out


def nwords(word):
    ph = k.tokenizer.phonemize(word, "en-us")
    return max(1, sum(1 for g in ph.split(" ") if any(ch not in PUNCT for ch in g)))


audio, words, t0 = [np.zeros(int(LEAD_IN * 24000), np.float32)], [], LEAD_IN
for i, line in enumerate(lines):
    a, sr, tm = k.create_timed(line, voice, speed=speed)
    g = groups(tm)
    toks = line.split()
    counts = [nwords(w) for w in toks]
    if sum(counts) != len(g):  # fall back to a proportional map when espeak splits words differently
        print(f"line {i + 1}: {sum(counts)} text-phoneme words vs {len(g)} spoken groups -> proportional map")
        idx = np.linspace(0, len(g), len(toks) + 1)
        spans = [(g[int(idx[j])][0], g[max(int(idx[j]), int(np.ceil(idx[j + 1])) - 1)][1]) for j in range(len(toks))]
    else:
        spans, p = [], 0
        for c in counts:
            spans.append((g[p][0], g[p + c - 1][1])); p += c
    for w, (s, e) in zip(toks, spans):
        words.append({"w": re.sub(r"[^\w'\-]", "", w), "s": round(t0 + s, 3), "e": round(t0 + e, 3)})
    audio.append(a.astype(np.float32))
    t0 += len(a) / sr
    gap = GAP_HOOK if i == 0 else GAP
    if i < len(lines) - 1:
        audio.append(np.zeros(int(gap * sr), np.float32)); t0 += gap
audio.append(np.zeros(int(TAIL * 24000), np.float32))
y = np.concatenate(audio)
y = resample_poly(y, 2, 1)  # 24 kHz -> 48 kHz
y = y / (np.abs(y).max() + 1e-9) * 0.89
os.makedirs(out, exist_ok=True)
with wave.open(os.path.join(out, "voice.wav"), "wb") as wv:
    wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(48000)
    wv.writeframes((y * 32767).astype("<i2").tobytes())
json.dump(words, open(os.path.join(out, "words.json"), "w", encoding="utf-8"), indent=0)
print(f"{voice} x{speed}: {len(lines)} lines, {len(words)} words, {len(y) / 48000:.2f} s")
