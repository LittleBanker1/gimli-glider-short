# Soundtrack for "The Jet That Couldn't Count" (Gimli short): original synthesized score + SFX placed on the picture's
# frames (src/videos/gimli/story.ts), ducked under the voice, mastered to -14 LUFS / -1 dBTP.
# Usage: python audio/gimli_mix.py shorts/gimli   -> shorts/gimli/audio/{mix.wav, stem_*.wav}
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dsp import SR, ns, tt, rng, lp, hp, bp, st, dbg, place, colored, fades, read_wav, write_wav, integrated, true_peak, pan, phase  # noqa: E402
import sfx_gen as G  # noqa: E402
import instruments as I  # noqa: E402
from mix import limiter, duck_db, speech_spans  # noqa: E402

FPS = 30
# picture frames (story.ts) -> seconds of the voice take, through the warp written by scripts/make_warp.py
_WARP = json.load(open(os.path.join(sys.argv[1], "voice", "warp.json")))
DUR = _WARP["new_total"] / FPS
fr = lambda f: float(np.interp(f, _WARP["old"], _WARP["new"])) / FPS
CUTS = [138, 520, 700, 770, 842, 905, 987, 1019, 1140, 1250, 1318, 1375, 1414, 1489, 1526, 1604, 1660, 1700, 1745, 1790, 1828, 1930, 2020]
W = dict(fuelOut=54, alarm1=552, alarm2=584, quiet=614, dark=672, glider=744, captain=790, fun=813, far=877, gimli=989,
         rock=1050, paper=1104, today=1327, sideways=1418, locked=1504, td=1497, nose=1526, stop=1592, racers=1604, died=1666,
         simulator=1767, crashed=1796, cut=1885, kg23=1952, lb50=1994, check=2030)


# ---------------------------------------------------------------- SFX
def beep(f, dur, vel=0.4):
    t = tt(dur)
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return fades(y * vel, 0.004, 0.02)


def chime(r):  # master-caution: two falling tones
    return np.concatenate([beep(1046, 0.16, 0.35), np.zeros(ns(0.03)), beep(784, 0.22, 0.35)])


def spool_down(dur, r, f0=420, f1=40):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.35))
    whine = np.sin(phase(f)) * np.exp(-t / (dur * 0.5)) * 0.25
    roar = lp(colored(len(t), r, 1.0), 900) * np.exp(-t / (dur * 0.3)) * 0.6
    return fades(whine + roar, 0.01, 0.2)


def cruise(dur, r):
    n = ns(dur)
    return fades(lp(hp(colored(n, r, 1.2), 60), 1200) * 0.35, 0.3, 0.3)


def thud(r, f0=70, dur=0.5, vel=1.0):
    t = tt(dur)
    y = np.sin(phase(f0 * (1 + 1.5 * np.exp(-t / 0.03)))) * np.exp(-t / 0.12)
    y += lp(r.standard_normal(len(t)), 1800) * np.exp(-t / 0.03) * 0.5
    return fades(y * vel, 0.001, 0.05)


def screech(r, dur=0.9):
    t = tt(dur)
    f = 2400 + 300 * np.sin(2 * np.pi * 9 * t)
    y = np.sin(phase(f)) * 0.25 + bp(r.standard_normal(len(t)), 1800, 4200) * 0.35
    return fades(y * np.exp(-t / 0.5), 0.005, 0.15)


def scrape(r, dur):
    n = ns(dur)
    t = np.arange(n) / SR
    nz = bp(colored(n, r, 0.3), 500, 6000)
    am = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 13 * t + r.uniform(0, 6)))
    env = np.minimum(1, t / 0.05) * np.clip((dur - t) / 0.6, 0, 1)
    rumble = lp(colored(n, r, 1.5), 250) * 0.8
    return fades((nz * am * 0.55 + rumble) * env, 0.005, 0.2)


def hiss(r, dur):
    n = ns(dur)
    return fades(hp(colored(n, r, 0.0), 2500) * 0.3, 0.02, 0.15)


def car_pass(r, dur=1.6, f0=150):
    t = tt(dur)
    k = (t - dur / 2) / 0.25
    f = f0 * (1 + 0.18 * np.tanh(-k))  # doppler: higher coming, lower going
    saw = sum(np.sin(phase(f * h)) / h for h in range(1, 9))
    env = 1 / (1 + k * k)
    y = lp(saw, 2500) * env * 0.6 + bp(colored(len(t), r, 0.6), 300, 3000) * env * 0.25
    return pan(fades(y, 0.02, 0.1), 0.0), np.tanh(-k)  # stereo pan follows below


def crash(r):
    y = thud(r, 55, 0.9, 1.0)
    y = y + np.pad(G.wood_crack(r), (0, max(0, len(y) - len(G.wood_crack(r)))))[: len(y)] * 0.6
    n = len(y)
    y += hp(r.standard_normal(n), 1500) * np.exp(-np.arange(n) / SR / 0.25) * 0.5
    return fades(y, 0.001, 0.1)


def poof(r):
    n = ns(0.8)
    t = np.arange(n) / SR
    return fades(lp(colored(n, r, 1.0), 1500) * np.exp(-t / 0.18) * 0.9, 0.003, 0.1)


def build_sfx(r):
    b = np.zeros((2, ns(DUR) + SR))
    for c in CUTS:
        place(b, G.whoosh(0.7, r, 0.32, 300, 1800, 0.9, 0.2, 0.1), fr(c) - 0.32, dbg(-14))
    place(b, cruise(fr(W["fuelOut"]) + 0.4, r), 0, dbg(-12))
    place(b, spool_down(2.4, r), fr(W["fuelOut"]), dbg(-8))
    place(b, I.cymbal(0.4, r, 1.6), fr(138) - 0.05, dbg(-16))
    for f in (W["alarm1"], W["alarm2"]):
        for k in range(3):
            place(b, chime(r), fr(f) + k * 0.55, dbg(-10))
    place(b, spool_down(1.6, r, 300, 30), fr(W["quiet"]), dbg(-10))
    place(b, thud(r, 90, 0.25, 0.6), fr(W["dark"]), dbg(-12))
    place(b, G.babble(2.3, r, 160, 1.0), fr(700), dbg(-22))
    place(b, G.whoa(r), fr(W["glider"]), dbg(-16))
    for a, d in ((842, 63), (1140, 110), (987, 32)):
        place(b, G.breeze(fr(d), r, 1.2), fr(a), dbg(-16))
    place(b, G.breeze(fr(121), r, 0.6), fr(1019), dbg(-22))
    place(b, G.bird_chirps(fr(121), r, 0.4), fr(1019), dbg(-24))
    place(b, thud(r, 120, 0.25, 0.7), fr(W["rock"]) + 0.46, dbg(-10))
    place(b, G.whoosh(0.5, r, 0.1, 800, 3000, 0.7, 0.2, 0.2), fr(W["paper"]) + 0.1, dbg(-16))
    # race: crowd bed + cars passing the low camera (frame 1318 + 11 i)
    place(b, G.babble(fr(125), r, 190, 1.0), fr(1250), dbg(-24))
    place(b, G.applause(1.6, r, 20), fr(W["today"]), dbg(-20))
    for i in range(5):
        s, pk = car_pass(r, 1.6, 140 + i * 15)
        place(b, s, fr(1318 + i * 11) - 0.8, dbg(-12))
    # the approach: rising air roar, crowd gasp, touchdown, nose scrape
    n = ns(fr(1497 - 1375))
    roar = lp(colored(n, r, 1.0), 1400) * np.linspace(0.1, 1, n) ** 2
    place(b, fades(roar, 0.2, 0.05), fr(1375), dbg(-10))
    place(b, G.whoa(r), fr(W["sideways"]) + 0.2, dbg(-14))
    place(b, screech(r, 0.9), fr(W["td"]), dbg(-10))
    place(b, thud(r, 60, 0.6, 1.0), fr(W["td"]), dbg(-6))
    place(b, thud(r, 50, 0.7, 1.0), fr(W["nose"]), dbg(-4))
    place(b, scrape(r, fr(W["stop"] - W["nose"])), fr(W["nose"]), dbg(-8))
    place(b, hiss(r, 2.0), fr(W["racers"] + 15), dbg(-12))
    place(b, G.applause(1.8, r, 30), fr(W["died"]), dbg(-16))
    for k in range(3):
        place(b, chime(r), fr(W["simulator"]) + k * 0.5, dbg(-12))
    place(b, crash(r), fr(W["crashed"]), dbg(-5))
    place(b, poof(r), fr(W["cut"]), dbg(-8))
    place(b, G.rattle(1.2, r, 40), fr(W["cut"]) + 0.2, dbg(-18))
    place(b, beep(2093, 0.12, 0.5), fr(W["kg23"]), dbg(-14))
    place(b, beep(2093, 0.12, 0.5), fr(W["lb50"]), dbg(-14))
    for k in range(2):
        place(b, beep(523, 0.18, 0.5), fr(W["check"]) + k * 0.25, dbg(-14))
    return b[:, : ns(DUR)]


# ---------------------------------------------------------------- music: pizzicato + vibes + pad, 104 bpm, F major
BPM = 104
BEAT = 60 / BPM
F, Dm, Bb, C, Am, Gm = [53, 57, 60], [50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 48, 52], [43, 46, 50]
m2f = I.m2f


def section(b, r, t0, t1, chords, mode, vel=1.0):
    """fill t0..t1 with a 4-beats-per-chord pattern; mode: play (plucks+vibes), tense (pad + tick), warm (pad + vibes)"""
    t, k = t0, 0
    while t < t1 - 0.05:
        ch = chords[k % len(chords)]
        bar = min(4 * BEAT, t1 - t)
        if mode in ("play", "tense", "warm"):
            place(b, I.pad([m2f(n) for n in ch], bar, 0.18 if mode != "tense" else 0.12, r, 0.3, 0.6, 700), t, dbg(-6) * vel)
        if mode == "play":
            for j, bt in enumerate([0, 1, 2, 2.5, 3]):
                if t + bt * BEAT < t1:
                    place(b, st(I.pluck(m2f(ch[0] - 12 if j % 2 == 0 else ch[j % 3]), 0.7, r, 0.7)), t + bt * BEAT, dbg(-4) * vel)
            for j, bt in enumerate([0.5, 1.5, 3.5]):
                if t + bt * BEAT < t1:
                    place(b, st(I.vibes(m2f(ch[(j + k) % 3] + 12), 0.45, r, 1.0)), t + bt * BEAT, dbg(-10) * vel)
        if mode == "tense":
            for bt in range(8):
                if t + bt * BEAT / 2 < t1:
                    place(b, st(I.brush(0.25, r, 0.12)), t + bt * BEAT / 2, dbg(-14) * vel)
            place(b, st(I.pluck(m2f(ch[0] - 24), 0.8, r, 1.2, 0.3)), t, dbg(-2) * vel)
        if mode == "warm":
            for j, bt in enumerate([0, 2]):
                if t + bt * BEAT < t1:
                    place(b, st(I.vibes(m2f(ch[j] + 12), 0.5, r, 1.6)), t + bt * BEAT, dbg(-8) * vel)
        t += bar
        k += 1


def build_music(r):
    b = np.zeros((2, ns(DUR) + 4 * SR))
    section(b, r, 0, fr(138), [F, Dm, Bb, C], "play")
    section(b, r, fr(138), fr(520), [F, Am, Bb, C], "play")
    section(b, r, fr(520), fr(770), [Dm, Bb, Dm, Gm], "tense")
    section(b, r, fr(770), fr(1019), [F, C, Dm, Bb], "play", 0.9)
    section(b, r, fr(1019), fr(1250), [Bb, F, Gm, C], "warm")
    section(b, r, fr(1250), fr(1375), [F, Dm, Bb, C], "play")
    section(b, r, fr(1375), fr(1604), [Dm, Dm, Bb, C], "tense", 1.2)
    for tr, vr in I.snare_roll(0, fr(1526 - 1440), 0.2, 0.9, r):  # roll builds to the nose hitting the runway
        place(b, st(I.snare(vr, r, 0.2, buzz=True)), fr(1440) + tr, dbg(-12))
    section(b, r, fr(1604), fr(1745), [F, Bb, F, C], "warm")
    section(b, r, fr(1745), fr(1828), [Dm, Bb], "tense", 0.8)
    section(b, r, fr(1828), DUR, [F, Am, Bb, C], "play")
    place(b, st(I.glock(m2f(77), 0.7, r, 2.0)), fr(2040), dbg(-6))  # end button on "which"
    return b[:, : ns(DUR)]


def main():
    d = sys.argv[1]
    os.makedirs(os.path.join(d, "audio"), exist_ok=True)
    r = rng(1983)
    v, sr = read_wav(os.path.join(d, "voice", "voice.wav"))
    v = st(v)[:, : ns(DUR)]
    v = np.pad(v, ((0, 0), (0, ns(DUR) - v.shape[1])))
    words = json.load(open(os.path.join(d, "voice", "words.json"), encoding="utf-8"))
    vI = integrated(v)
    m = build_music(r)
    s = build_sfx(r)
    m *= dbg(vI - 8 - integrated(m))               # music bed 8 LU under the voice before ducking (~13 LU under after)
    s *= dbg(vI - 7 - integrated(s))               # effects ~7 LU under the voice
    dk = duck_db(speech_spans(words), depth=-7.0)[: m.shape[1]]
    dk = np.pad(dk, (0, m.shape[1] - len(dk)), mode="edge")
    m *= dbg(dk)[None, :]
    mix0 = v + m + s
    G = -14.0 - integrated(mix0)
    for _ in range(4):  # master gain to -14 LUFS through the -1 dBTP look-ahead limiter
        y, _g3 = limiter(mix0 * dbg(G), -1.0)
        L = integrated(y)
        if abs(L + 14.0) < 0.05:
            break
        G += -14.0 - L
    g = dbg(G)
    print(f"voice {vI:.1f} LUFS; mix {integrated(y):.2f} LUFS, TP {true_peak(y):.2f} dBTP, {y.shape[1] / SR:.2f} s")
    write_wav(os.path.join(d, "audio", "mix.wav"), y)
    for n, x in (("voice", v * g), ("music", m * g), ("sfx", s * g)):
        write_wav(os.path.join(d, "audio", f"stem_{n}.wav"), x)


if __name__ == "__main__":
    main()
