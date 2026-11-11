// "The Jet That Couldn't Count" (Gimli Glider, 23 July 1983): timeline, sets, jet pose and cameras.
// Every shot happens on one SET (a group in world.ts switched on per shot; all sets share the origin, ground y = 0).
// Frames are timed to shorts/gimli/voice/words.json (scratch voice, 68.8 s). Camera grammar copied from the bridge
// short: smootherstep glides of 18-40 f, cuts on big reframes, every hold creeps in, 7-frame flip kicks on impacts.
export const FPS = 30;
export const TOTAL = 2064;
export const D0 = 0;
export type V3 = [number, number, number];

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (x: number) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
export const easeOut = (u: number) => 1 - (1 - clamp01(u)) ** 3;
export const easeIn = (u: number) => clamp01(u) ** 2;
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const T = (f: number) => f / FPS;

// ---------------- sets and shots ----------------
export type SetName = "sky" | "apron" | "cockpit" | "cabin" | "gimli" | "checkin";
export type Light = "day" | "golden";
export type ShotDef = { id: number; a: number; b: number; set: SetName; light: Light; sunAz?: number; sunEl?: number };
export const SHOTS: ShotDef[] = [
  { id: 1, a: 0, b: 138, set: "sky", light: "golden" },        // hook: ran out of fuel at 41,000 ft
  { id: 2, a: 138, b: 243, set: "apron", light: "day" },       // Canada going metric; new Boeing thinks in kg
  { id: 3, a: 243, b: 350, set: "apron", light: "day" },       // gauges broken, dipstick, sum by hand
  { id: 4, a: 350, b: 520, set: "apron", light: "day" },       // 22,300 kg ... pounds. Less than half
  { id: 5, a: 520, b: 650, set: "cockpit", light: "golden" },  // over Ontario: alarm, another, engines quiet
  { id: 6, a: 650, b: 700, set: "cockpit", light: "golden" },  // screens go dark
  { id: 7, a: 700, b: 770, set: "cabin", light: "golden" },    // 69 people in a very large glider
  { id: 8, a: 770, b: 842, set: "cockpit", light: "golden" },  // luckily: captain flew gliders for fun
  { id: 9, a: 842, b: 905, set: "sky", light: "golden" },      // unluckily: every big airport too far
  { id: 10, a: 905, b: 987, set: "cockpit", light: "golden" }, // co-pilot remembers an old air force base
  { id: 11, a: 987, b: 1019, set: "gimli", light: "golden" },  // "Gimli."
  { id: 12, a: 1019, b: 1140, set: "gimli", light: "day" },    // analogy: rock vs paper plane (field)
  { id: 13, a: 1140, b: 1250, set: "sky", light: "golden" },   // 1 m down, 12 m forward. Just enough
  { id: 14, a: 1250, b: 1375, set: "gimli", light: "golden" }, // base closed, race track, a race today
  { id: 15, a: 1375, b: 1489, set: "gimli", light: "golden" }, // too high, too fast: sideways slip
  { id: 16, a: 1489, b: 1604, set: "gimli", light: "golden" }, // nose wheel never locked, nose as a brake
  { id: 17, a: 1604, b: 1700, set: "gimli", light: "golden" }, // racers with extinguishers. Nobody died
  { id: 18, a: 1700, b: 1745, set: "apron", light: "day" },    // investigators blamed the airline
  { id: 19, a: 1745, b: 1828, set: "cockpit", light: "day" },  // simulator: they crashed
  { id: 20, a: 1828, b: 1930, set: "apron", light: "day" },    // 25 more years, then luggage tags
  { id: 21, a: 1930, b: TOTAL, set: "checkin", light: "day" }, // 23 kg. Or 50 lb. Please check which
];
/** crossfades (frames) at place/time changes; a white 4-frame flash after the hook */
export const XFADE: Record<number, number> = { 5: 8, 7: 6, 12: 8, 13: 8, 18: 8, 21: 8 };
export const FLASH_AT = 138;

export const shotAt = (f: number) => SHOTS.find((s) => f >= s.a && f < s.b) ?? SHOTS[SHOTS.length - 1];
export const layersAt = (f: number): { id: number; alpha: number }[] => {
  for (const s of SHOTS) {
    const x = XFADE[s.id];
    if (x && f >= s.a - x / 2 && f < s.a + x / 2) return [{ id: s.id - 1, alpha: 1 }, { id: s.id, alpha: (f - (s.a - x / 2) + 1) / (x + 1) }];
  }
  return [{ id: shotAt(f).id, alpha: 1 }];
};

// ---------------- word times (frames) used by the picture ----------------
export const W = {
  fuelOut: 54, mistake: 115, kilograms: 210, stick: 305, kg: 391, pounds: 466, half: 490,
  alarm1: 552, alarm2: 584, quiet: 614, dark: 672, glider: 744, captain: 790, fun: 813, far: 877,
  remembered: 928, gimli: 989, rock: 1050, paper: 1104, twelve: 1182, enough: 1218, race: 1295, today: 1327,
  sideways: 1418, locked: 1504, scraped: 1535, brake: 1575, racers: 1604, died: 1666, blamed: 1715, simulator: 1767,
  crashed: 1796, years: 1853, cut: 1885, tags: 1904, weight: 1935, kg23: 1952, lb50: 1994, check: 2030,
};

// ---------------- the jet ----------------
/** jet pose in its set: origin = fuselage centreline at mid-length, nose toward +z before yaw.
 *  gear 0 up .. 1 down; nose = nose-gear collapse 0..1 (the nose drops onto the runway); rat 0..1; spin = engine fan
 *  speed 0..1 (fans stop when the fuel runs out). pitch + = nose up, roll + = right wing down (rotation about +z). */
export type JetPose = { visible: boolean; pos: V3; yaw: number; pitch: number; roll: number; gear: number; nose: number; rat: number; spin: number; scrap?: number };
export const PARKED_Y = 3.3; // fuselage centreline over the ground with the gear down
const HIDE: JetPose = { visible: false, pos: [0, 0, 0], yaw: 0, pitch: 0, roll: 0, gear: 1, nose: 0, rat: 0, spin: 0 };
const parked = (spin = 0): JetPose => ({ visible: true, pos: [0, PARKED_Y, 0], yaw: 0, pitch: 0, roll: 0, gear: 1, nose: 0, rat: 0, spin });

// Gimli landing path along +z on the runway: touchdown z = -260 at TD, stops at z = STOP_Z at STOP_F.
export const TD = 1497, STOP_F = 1592, STOP_Z = 120;
const landZ = (f: number) => {
  if (f <= TD) return -260 - (TD - f) * 4.2;                       // ~126 m/s ... cartoon-slowed approach
  const u = clamp01((f - TD) / (STOP_F - TD));
  return -260 + (STOP_Z + 260) * easeOut(u);                       // braking to a stop
};
/** glide altitude over the runway end before touchdown (slip sheds height) */
const landY = (f: number) => (f >= TD ? PARKED_Y : PARKED_Y + Math.pow((TD - f) / 120, 1.6) * 60);
export const jetAt = (id: number, f: number): JetPose => {
  const t = T(f);
  switch (id) {
    case 1: return { visible: true, pos: [0, 0, 0], yaw: 0, pitch: 0.02, roll: 0.03 * Math.sin(t * 0.8), gear: 0, nose: 0, rat: 0, spin: f < W.fuelOut + 10 ? 1 : Math.max(0, 1 - (f - W.fuelOut - 10) / 40) };
    case 9: case 13: {
      const sink = id === 13 ? (f - 1140) * 0.06 : 0;
      return { visible: true, pos: [0, -sink, 0], yaw: 0, pitch: -0.045, roll: 0, gear: 0, nose: 0, rat: 1, spin: 0 };
    }
    case 2: case 3: case 4: return parked(0.15);
    case 18: return parked(0);
    case 20: { const scrap = clamp01((f - W.cut) / 14); return { ...parked(0), scrap }; }
    case 11: return { visible: true, pos: [30, 75, -300 + (f - 987) * 2], yaw: 0, pitch: -0.07, roll: 0, gear: 0, nose: 0, rat: 1, spin: 0 }; // far up the approach
    case 14: return HIDE;
    case 15: {
      const slip = smooth((f - (W.sideways - 30)) / 40);
      return { visible: true, pos: [0, landY(f), landZ(f)], yaw: 0.28 * slip, pitch: 0.03, roll: -0.42 * slip, gear: 1, nose: 0, rat: 1, spin: 0 };
    }
    case 16: case 17: {
      const slip = id === 16 ? 1 - smooth((f - 1489) / 8) : 0;
      const nose = id === 17 ? 1 : smooth((f - W.locked - 20) / 10);
      return { visible: true, pos: [0, landY(f), landZ(f)], yaw: 0.28 * slip, pitch: f < TD ? 0.05 : 0, roll: -0.42 * slip, gear: 1, nose, rat: 1, spin: 0 };
    }
    default: return HIDE;
  }
};

// ---------------- camera ----------------
export type Cam = { pos: V3; look: V3; fov: number; roll: number };
type Shot = Partial<Cam> & { pos: V3; look: V3 };
type Key = { f: number; dur?: number; cut?: boolean; s: (f: number) => Shot };
export const glide = (u: number) => { const x = clamp01(u); return x * x * x * (x * (6 * x - 15) + 10); };
const mix = (a: Cam, b: Cam, k: number): Cam => ({
  pos: a.pos.map((v, i) => v + (b.pos[i] - v) * k) as V3, look: a.look.map((v, i) => v + (b.look[i] - v) * k) as V3,
  fov: a.fov + (b.fov - a.fov) * k, roll: a.roll + (b.roll - a.roll) * k,
});
const full = (c: Shot): Cam => ({ fov: 40, roll: 0, ...c });
const run = (keys: Key[], f: number) => {
  let cur = full(keys[0].s(f));
  for (let i = 1; i < keys.length; i++) {
    const k = keys[i];
    if (f < k.f) break;
    cur = k.cut ? full(k.s(f)) : mix(cur, full(k.s(f)), glide((f - k.f) / (k.dur ?? 24)));
  }
  return cur;
};
const pushK = (f: number, f0: number, rate: number, punch = 0, n = 35) => {
  const x = Math.max(0, f - f0);
  let s = rate * x;
  if (punch > rate) for (let i = 0; i < Math.min(x, n); i++) s += (punch - rate) * Math.max(0, Math.min(1, (i + 0.5) / 8, (n - i - 0.5) / 8));
  return Math.exp(-s);
};
const dolly = (pos: V3, look: V3, k: number, rest: Partial<Cam> = {}): Shot =>
  ({ pos: [look[0] + (pos[0] - look[0]) * k, look[1] + (pos[1] - look[1]) * k, look[2] + (pos[2] - look[2]) * k], look, ...rest });
const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const jetP = (id: number, f: number) => jetAt(id, f).pos;

// ---- set layout contracts (sets.ts / cast.ts build to these) ----
/** apron: jet parked at the origin, nose +z; fuel truck under the right wing (screen-left from the front) */
export const APRON = { truck: [13.5, 0, 2.5] as V3, captain: [9.0, 0, -0.6] as V3, fueler: [11.6, 0, 1.6] as V3, terminal: [-70, 0, 10] as V3 };
/** cockpit interior: floor y = 0, nose +z; captain sits left (+x), first officer right (-x); eyes at y ~ 1.25 */
export const COCKPIT = { capt: [0.55, 0, -0.1] as V3, fo: [-0.55, 0, -0.1] as V3, panelZ: 0.95, windowZ: 1.35, eyeY: 1.25 };
/** cabin interior: aisles at x = +-1.05, rows every 0.86 m from z = -10 toward +z, floor y = 0 */
export const CABIN = { rows: 14, row0: -10, pitch: 0.86, seats: [-2.05, -1.55, -0.5, 0, 0.5, 1.55, 2.05] };
/** gimli: runway along z (x -30..30), race paddock east of the runway end, the analogy field to the far west */
export const GIMLI = { field: [-150, 0, -460] as V3, paddock: [55, 0, 260] as V3, rail0: 100, rail1: 420 };
/** check-in: counter along x at z = 0, scale in front of it, traveller on the public side (+z) */
export const CHECKIN = { scale: [0.9, 0, 0.85] as V3, agent: [0, 0, -0.9] as V3, traveller: [-0.5, 0, 1.35] as V3 };

const nosePt = (id: number, f: number): V3 => { const j = jetAt(id, f); return [j.pos[0] + Math.sin(j.yaw) * 22, j.pos[1] - 1.2, j.pos[2] + Math.cos(j.yaw) * 22]; };

const CAMS: Record<number, Key[]> = {
  // 1: chase beside the jet over the cloud sea, push in; at "mistake" slide forward to the dead engine
  1: [
    { f: 0, s: (f) => dolly([-46, 9, 52], [0, 0, 2], pushK(f, 0, 0.0022), { fov: 42 }) },
    { f: 66, dur: 34, s: (f) => dolly([-22, 1.5, 24], [-7.8, -2.4, 6], pushK(f, 66, 0.003), { fov: 38, roll: 0.05 }) },
  ],
  // 2: apron establishing, high 3/4 front; push on "kilograms"
  2: [
    { f: 138, s: (f) => dolly([42, 18, 52], [0, 4, 2], pushK(f, 138, 0.0018, 0.005, 30), { fov: 44 }) },
    { f: 196, dur: 26, s: (f) => dolly([22, 5.5, 34], [2, 4.2, 10], pushK(f, 196, 0.0025), { fov: 40, roll: -0.04 }) },
  ],
  // 3: under the right wing: fueler + captain with the dipstick
  3: [
    { f: 243, s: (f) => dolly([18.5, 2.4, 9.5], [10.3, 1.7, 0.4], pushK(f, 243, 0.0022), { fov: 40 }) },
    { f: 300, cut: true, s: (f) => dolly([11.4, 1.9, 2.9], [9.0, 1.75, -0.6], pushK(f, 300, 0.003), { fov: 36, roll: 0.04 }) },
  ],
  // 4: the fueler's clipboard sums (kg ... pounds), then the gauge on the truck at "less than half"
  4: [
    { f: 350, s: (f) => dolly([13.6, 1.95, 4.9], [11.6, 1.6, 1.6], pushK(f, 350, 0.0025), { fov: 36 }) },
    { f: 458, dur: 18, s: (f) => dolly([12.9, 1.75, 3.6], [11.6, 1.45, 1.6], pushK(f, 458, 0.002, 0.006, 30), { fov: 34, roll: -0.04 }) },
    { f: 486, cut: true, s: (f) => dolly([16.4, 1.6, 5.4], [13.5, 1.45, 4.1], pushK(f, 486, 0.003), { fov: 34 }) },
  ],
  // 5: cockpit from behind the seats into the sunset, push; jolt on the second alarm, lean in on "quiet"
  // (the camera sits over the glareshield looking back: the cards always face the lens, so we see the pilots' faces)
  5: [
    { f: 516, s: (f) => dolly([-1.3, 1.42, 2.4], [0.05, 1.18, -0.45], pushK(f, 516, 0.002), { fov: 44 }) },
    { f: 600, dur: 26, s: (f) => dolly([-1.05, 1.38, 2.05], [0.05, 1.18, -0.45], pushK(f, 600, 0.0025, 0.006, 30), { fov: 40, roll: 0.04 }) },
  ],
  // 6: the instrument panel close-up, screens go dark
  6: [{ f: 650, s: (f) => dolly([0.15, 1.28, 0.25], [0.05, 1.0, COCKPIT.panelZ], pushK(f, 650, 0.003), { fov: 40 }) }],
  // 7: down the aisle at passengers' eye level
  7: [
    { f: 696, s: (f) => dolly([1.05, 1.75, 5.6], [0.5, 1.0, -6], pushK(f, 696, 0.0025), { fov: 46 }) },
    { f: 735, dur: 22, s: (f) => dolly([1.0, 1.6, 3.6], [0.2, 1.05, -3], pushK(f, 735, 0.003), { fov: 42, roll: -0.04 }) },
  ],
  // 8: the captain from the windscreen side, cracking a grin on "fun"
  8: [
    { f: 770, s: (f) => dolly([0.2, 1.3, 0.8], [0.55, 1.22, -0.1], pushK(f, 770, 0.0025, 0.006, 30), { fov: 40, roll: -0.03 }) },
  ],
  // 9: high and far behind the jet: nothing but cloud to the horizon
  9: [
    { f: 842, s: (f) => dolly([30, 70, -160], [0, -10, 120], pushK(f, 842, 0.0018), { fov: 40 }) },
  ],
  // 10: the first officer remembers; push in on "remembered", he points out the window
  10: [
    { f: 905, s: (f) => dolly([-0.1, 1.32, 0.85], [-0.55, 1.22, -0.1], pushK(f, 905, 0.002), { fov: 40, roll: 0.03 }) },
    { f: 925, dur: 22, s: (f) => dolly([-0.25, 1.28, 0.6], [-0.55, 1.22, -0.1], pushK(f, 925, 0.0025, 0.006, 28), { fov: 38, roll: -0.02 }) },
  ],
  // 11: GIMLI: the old base from the air, the jet tiny on the approach
  11: [{ f: 983, s: (f) => { const p = jetP(11, f); return dolly(add(p, [16, 9, -62]), [0, 0, 160], pushK(f, 983, 0.002), { fov: 46, roll: -0.04 }); } }],
  // 12: the field: a kid drops a rock (straight down), then throws a paper plane (slides away)
  12: [
    { f: 1015, s: (f) => dolly(add(GIMLI.field, [0.6, 1.55, 5.2]), add(GIMLI.field, [0.6, 1.1, 0]), pushK(f, 1015, 0.0022), { fov: 40 }) },
    { f: 1092, dur: 30, s: (f) => dolly(add(GIMLI.field, [1.8, 1.5, 6.0]), add(GIMLI.field, [0.5, 1.2, -3]), pushK(f, 1092, 0.002), { fov: 44, roll: 0.03 }) },
  ],
  // 13: side-on glide: the jet slides down its 1:12 line, camera rides with it
  13: [
    { f: 1136, s: (f) => { const p = jetP(13, f); return dolly(add(p, [80, 6, -45]), add(p, [0, -3, -28]), pushK(f, 1136, 0.0015), { fov: 42 }); } },
    { f: 1210, dur: 26, s: (f) => { const p = jetP(13, f); return dolly(add(p, [62, 4, -30]), add(p, [0, -2, -4]), pushK(f, 1210, 0.002, 0.005, 25), { fov: 40, roll: -0.03 }); } },
  ],
  // 14: down at the race: cars on the old runway, campers, a flag; push on "today there was a race"
  14: [
    { f: 1250, s: (f) => dolly(add(GIMLI.paddock, [-30, 2.2, 22]), add(GIMLI.paddock, [-52, 1.2, -6]), pushK(f, 1250, 0.002), { fov: 44 }) },
    { f: 1318, cut: true, s: (f) => dolly([24, 0.9, 318], [4, 0.8, 300], pushK(f, 1318, 0.0025, 0.006, 30), { fov: 40, roll: 0.04 }) },
  ],
  // 15: from the crowd, the jet comes in sideways and fast
  15: [
    { f: 1375, s: (f) => { const p = jetP(15, f); return { pos: [34, 1.7, 230], look: [p[0] * 0.5, p[1] * 0.85 + 2, p[2]], fov: 40, roll: 0 }; } },
    { f: 1414, cut: true, s: (f) => { const p = jetP(15, f); return { pos: [46, 3.2, -120], look: [p[0], p[1], p[2] + 10], fov: 34, roll: 0.05 }; } },
  ],
  // 16: low beside the runway: touchdown, the nose drops at "never locked", scrapes past in sparks
  16: [
    { f: 1489, s: (f) => { const p = jetP(16, f); return { pos: [44, 2.2, -150], look: [p[0], p[1] - 0.5, p[2] + 10], fov: 36, roll: -0.03 }; } },
    { f: 1526, cut: true, s: (f) => { const n = nosePt(16, f); return { pos: [16, 1.2, n[2] + 30], look: [n[0], 1.2, n[2]], fov: 34, roll: 0.04 }; } },
  ],
  // 17: racers spray the nose; then wide: everyone on the grass
  17: [
    { f: 1604, s: (f) => dolly([9, 2.0, STOP_Z + 40], [0, 1.4, STOP_Z + 23], pushK(f, 1604, 0.0025), { fov: 40 }) },
    { f: 1660, cut: true, s: (f) => dolly([-52, 9, STOP_Z - 24], [0, 2, STOP_Z + 8], pushK(f, 1660, 0.0018), { fov: 44 }) },
  ],
  // 18: investigators with a magnifying glass at the nose
  18: [{ f: 1696, s: (f) => dolly([4.2, 1.6, 33.5], [0.3, 1.4, 27.2], pushK(f, 1696, 0.0025, 0.006, 25), { fov: 44 }) }],
  // 19: the simulator: same cockpit, red light, crash
  19: [
    { f: 1745, s: (f) => dolly([-1.3, 1.42, 2.4], [0.05, 1.18, -0.45], pushK(f, 1745, 0.0025), { fov: 44 }) },
    { f: 1790, cut: true, s: (f) => dolly([0.25, 1.3, 0.75], [0.55, 1.2, -0.1], pushK(f, 1790, 0.002), { fov: 40, roll: 0.05 }) },
  ],
  // 20: the old jet on the apron, crane up; it bursts into luggage tags
  20: [
    { f: 1828, s: (f) => dolly([30, 6, 42], [0, 4, 0], pushK(f, 1828, 0.0022), { fov: 42 }) },
    { f: 1870, dur: 30, s: (f) => dolly([36, 14, 46], [0, 6, 0], pushK(f, 1870, 0.0015), { fov: 46, roll: -0.03 }) },
  ],
  // 21: check-in: the scale's display, the traveller's face
  21: [
    { f: 1926, s: (f) => dolly([-1.6, 1.6, 3.6], [0.4, 1.1, 0.4], pushK(f, 1926, 0.002), { fov: 42 }) },
    { f: 1946, dur: 22, s: (f) => dolly([1.9, 1.55, 3.7], [0.45, 1.2, 0.9], pushK(f, 1946, 0.0025, 0.006, 25), { fov: 46 }) },
    { f: 2020, cut: true, s: (f) => dolly([0.4, 1.62, 2.9], [-0.5, 1.62, 1.35], pushK(f, 2020, 0.0025, 0.006, 30), { fov: 36, roll: 0.04 }) },
  ],
};

// impact kicks: sign flips every frame, decays over 7 f
const KICKS: [number, number][] = [[T(W.quiet), 0.4], [T(W.dark), 0.35], [T(TD), 0.9], [T(W.locked + 22), 1.4], [T(W.crashed), 1.2], [T(W.cut), 0.7]];
export const kickAt = (t: number) => {
  let a = 0;
  for (const [t0, g] of KICKS) {
    const n = Math.floor((t - t0) * FPS + 1e-6);
    if (n >= 0 && n < 7) a += g * (n % 2 ? -1 : 1) * (1 - n / 7) ** 1.5;
  }
  return a;
};
export const camAt = (id: number, f: number): Cam => {
  const c = run(CAMS[id], f), a = kickAt(T(f));
  if (!a) return c;
  const d: V3 = [c.look[0] - c.pos[0], c.look[1] - c.pos[1], c.look[2] - c.pos[2]];
  const L = Math.hypot(...d), h = Math.hypot(d[0], d[2]) || 1;
  const m = (3 / 640) * Math.tan((c.fov * Math.PI) / 360) * L * a;
  return { ...c, look: [c.look[0] - (d[2] / h) * m, c.look[1] + 0.6 * m, c.look[2] + (d[0] / h) * m], roll: c.roll + a * 0.004 };
};

// ---------------- lens ----------------
export type Dof = { f: number; dur?: number; cInf: number; focus?: (f: number) => V3 };
export const DOF: Dof[] = [
  { f: 0, cInf: 0 },
  { f: 138, cInf: 0 },
  { f: 243, cInf: 10 },
  { f: 300, cInf: 13 },
  { f: 350, cInf: 13 },
  { f: 486, cInf: 12 },
  { f: 520, cInf: 6 },
  { f: 650, cInf: 12 },
  { f: 700, cInf: 9 },
  { f: 770, cInf: 13 },
  { f: 842, cInf: 0 },
  { f: 905, cInf: 13 },
  { f: 987, cInf: 0 },
  { f: 1019, cInf: 10 },
  { f: 1140, cInf: 0 },
  { f: 1250, cInf: 9 },
  { f: 1375, cInf: 0 },
  { f: 1604, cInf: 10 },
  { f: 1660, cInf: 0 },
  { f: 1700, cInf: 12 },
  { f: 1745, cInf: 6 },
  { f: 1790, cInf: 13 },
  { f: 1828, cInf: 0 },
  { f: 1930, cInf: 10 },
  { f: 2020, cInf: 14 },
];
export const dofAt = (f: number) => {
  let i = 0; while (i + 1 < DOF.length && f >= DOF[i + 1].f) i++;
  const d = DOF[i], p = DOF[Math.max(0, i - 1)];
  const k = d.dur ? Math.min(1, (f - d.f) / d.dur) : 1;
  return { cInf: p.cInf + (d.cInf - p.cInf) * k, focus: d.focus };
};
