// Gimli cast (infrastructure from the bridge short). Our cast as lit flat sprites in the 3D world. Each frame every character asks for a drawing (a key + a draw call);
// the pool keeps one canvas per distinct drawing, so soldiers marching in step share canvases (7 head shapes x 4
// outfits). Characters are yaw-only billboards shaded by cardShade() (scene tint, bright floor, side gradient toward
// the sun, painted crescent in the drawing); standing ones get a soft multiply contact blob. Effects are unlit cards.
// Cards, effects and blobs live on the NOINK layer so the world ink pass never outlines their quads.
import * as THREE from "three";
import { Pen, bodyFront, bodySide, KID, SKINS, INK, fxBurst, fxPuff, fxStars, fxShadow, fxContact, Outfit, Expr, FrontOpts, SideOpts } from "./toon";
import { FPS, SHOTS, V3, smooth, clamp01, W, jetAt, STOP_Z, TD, APRON, COCKPIT, CABIN, GIMLI, CHECKIN } from "./story";
import { LIGHTS } from "./lights";
import { NOINK } from "./ink";
import { cardShade, blobMaterial, CARD_K } from "./cardshade";

// ---------------- canvas pool ----------------
type Entry = { cv: HTMLCanvasElement; tex: THREE.CanvasTexture; w: number; h: number };
export type Req = { key: string; w: number; h: number; k: number; draw: (p: Pen) => void; tex?: THREE.CanvasTexture };
const makeEntry = (w: number, h: number): Entry => {
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return { cv, tex, w, h };
};
export class Pool {
  private live = new Map<string, Entry>();
  private free: Entry[] = [];
  private reqs: Req[] = [];
  req(key: string, w: number, h: number, k: number, draw: (p: Pen) => void) {
    const r: Req = { key: `${w}x${h}|${key}`, w, h, k, draw };
    this.reqs.push(r);
    return r;
  }
  flush() {
    const want = new Map<string, Req[]>();
    for (const r of this.reqs) { const l = want.get(r.key); if (l) l.push(r); else want.set(r.key, [r]); }
    for (const [key, e] of this.live) if (!want.has(key)) { this.live.delete(key); this.free.push(e); }
    for (const [key, rs] of want) {
      let e = this.live.get(key);
      if (!e) {
        const r = rs[0], i = this.free.findIndex((x) => x.w === r.w && x.h === r.h);
        e = i >= 0 ? this.free.splice(i, 1)[0] : makeEntry(r.w, r.h);
        const g = e.cv.getContext("2d")!;
        g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, e.w, e.h); g.setTransform(r.k, 0, 0, r.k, 0, 0);
        r.draw(new Pen(g));
        e.tex.needsUpdate = true;
        this.live.set(key, e);
      }
      for (const r of rs) r.tex = e.tex;
    }
    this.reqs = [];
  }
}

// ---------------- sprite meshes ----------------
const blank = (() => { const c = document.createElement("canvas"); c.width = c.height = 2; return new THREE.CanvasTexture(c); })();
export const SU = 0.00216; // metres per design unit: 1000 units = 2.16 m
export const SU_SWING = 2.3 / 1830; // swing canvas: rope of 1830 units = 2.3 m
const BODY = (() => { const g = new THREE.PlaneGeometry(600 * SU, 1000 * SU); g.translate(0, (975 - 500) * SU, 0); return g; })();
const CARD = new THREE.PlaneGeometry(1, 1);
/** world roots that hold actors (to find the scene's sun when world.ts does not pass it) */
const ROOTS = new Set<THREE.Object3D>();

/** lit flat character: cardShade() material, receives shadows (dims to the bright floor only), casts its silhouette
 *  when world.ts says so (golden). Drawn after the contact blobs (renderOrder 1). */
export class Actor {
  mesh: THREE.Mesh; mat: THREE.MeshLambertMaterial; dmat: THREE.MeshDepthMaterial; r: Req | null = null;
  constructor(parent: THREE.Object3D, geo: THREE.BufferGeometry = BODY) {
    this.mat = cardShade(new THREE.MeshLambertMaterial({ map: blank, alphaTest: 0.5, side: THREE.DoubleSide }));
    this.mat.alphaToCoverage = false; // A2C + MSAA left 1 px sky-depth seams on blurred far cards (POST)
    this.dmat = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: blank, alphaTest: 0.5, side: THREE.DoubleSide });
    this.mesh = new THREE.Mesh(geo, this.mat);
    this.mesh.customDepthMaterial = this.dmat;
    // rim width is in output pixels: tell the card shader the render height (1920 = 1080 x 1920 frame)
    this.mesh.onBeforeRender = (r) => { const rt = r.getRenderTarget(); CARD_K.uPx.value = (rt ? rt.height : r.domElement.height) / 1920; };
    this.mesh.castShadow = false; this.mesh.receiveShadow = true; this.mesh.visible = false;
    this.mesh.rotation.order = "YXZ"; this.mesh.renderOrder = 1; this.mesh.layers.set(NOINK);
    parent.add(this.mesh);
    ROOTS.add(parent);
  }
  bind() { const t = this.r?.tex; if (t) { this.mat.map = t; this.dmat.map = t; } }
}
/** unlit effect card: hard cut-out (ink drawings), soft see-through (dust, mist) or a multiply ground blob */
export class Fx {
  mesh: THREE.Mesh; mat: THREE.MeshBasicMaterial; soft: THREE.MeshBasicMaterial; blob: THREE.MeshBasicMaterial; r: Req | null = null;
  constructor(parent: THREE.Object3D) {
    this.mat = new THREE.MeshBasicMaterial({ map: blank, alphaTest: 0.5, side: THREE.DoubleSide });
    this.mat.alphaToCoverage = false; // A2C + MSAA left 1 px sky-depth seams on blurred far cards (POST)
    this.soft = new THREE.MeshBasicMaterial({ map: blank, transparent: true, depthWrite: false, side: THREE.DoubleSide });
    this.blob = blobMaterial(blank);
    this.mesh = new THREE.Mesh(CARD, this.mat);
    this.mesh.visible = false; this.mesh.layers.set(NOINK);
    parent.add(this.mesh);
  }
  use(soft: boolean) { this.mesh.material = soft ? this.soft : this.mat; }
  bind() {
    const t = this.r?.tex;
    if (!t) return;
    if (this.r!.key.includes("|blob|")) {
      // no mipmaps: at grazing views the mip chain averages the blob with its white surround and it fades out
      if (t.generateMipmaps) { t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.needsUpdate = true; }
      this.blob.map = t; this.mesh.material = this.blob; this.mesh.renderOrder = 0.5;
    }
    else { this.mat.map = t; this.soft.map = t; this.mesh.renderOrder = 0; }
  }
}

// ---------------- placements ----------------
export type Place = {
  key: string; draw: (p: Pen) => void; x: number; y: number; z: number;
  scale?: number; mirror?: boolean; yaw?: number; geo?: "body" | "swing"; roll?: number; size?: [number, number, number];
};
export type FxPlace = { key: string; cw: number; ch: number; draw: (p: Pen) => void; x: number; y: number; z: number; w: number; h: number; flat?: boolean; rot?: number; soft?: boolean };
/** sun = world direction TOWARD the sun (optional: when absent the scene's shadow-casting light is used) */
export type CamInfo = { pos: THREE.Vector3; right: THREE.Vector3; sun?: THREE.Vector3 };

const hh = (i: number, s = 0) => { const v = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return v - Math.floor(v); };
const q = (v: number, n = 120) => Math.round(v * n) / n;
/** head-shape seed: 7 shapes, so marching soldiers in step still share canvases */
const seedOf = (i: number) => ((i * 5 + 3) % 7) + 1;
/** drawing resolution by distance: [canvas w, h, scale from the 600 x 1000 design]; sized for the 1440 x 2560 final */
const tier = (d: number): [number, number, number] =>
  d < 3.2 ? [1800, 3000, 3.0] : d < 6.5 ? [1080, 1800, 1.8] : d < 16 ? [480, 800, 0.8] : [240, 400, 0.4];

// ---------------- light ----------------
const SUN = new THREE.Vector3(0.5, 0.75, -0.4).normalize();
const tmp = new THREE.Vector3();
let LNAME: "day" | "golden" = "day";
const sunOf = (root: THREE.Object3D) => {
  let s: THREE.DirectionalLight | null = null;
  root.traverse((o) => { if (!s && o instanceof THREE.DirectionalLight && o.castShadow) s = o; });
  return s as THREE.DirectionalLight | null;
};
/** the sun of the world that is calling: the attached root whose sun target sits on this camera's view axis */
const findSun = (cam: CamInfo, out: THREE.Vector3) => {
  if (cam.sun) return out.copy(cam.sun).normalize();
  let best: THREE.DirectionalLight | null = null, err = Infinity;
  for (const r of ROOTS) {
    if (!r.parent) continue;
    const s = sunOf(r);
    if (!s) continue;
    const d = tmp.copy(s.target.position).sub(cam.pos), e = Math.abs(d.dot(cam.right)) / (d.length() || 1);
    if (e < err) { err = e; best = s; }
  }
  return best ? out.copy(best.position).sub(best.target.position).normalize() : out;
};
/** canvas angle the sun comes FROM on an upright card facing the camera, in 45-degree steps (small texture cache) */
const light2D = (cam: CamInfo, mirror: boolean) => {
  const sx = SUN.dot(cam.right) * (mirror ? -1 : 1), sy = -SUN.y;
  return Math.round(Math.atan2(sy, sx) / (Math.PI / 4)) * (Math.PI / 4);
};

/** front / side view and mirroring for someone at (x, z) walking along (dx, dz); fs = foreshortening of the walk */
const viewOf = (cam: CamInfo, x: number, z: number, dx: number, dz: number) => {
  const tx = cam.pos.x - x, tz = cam.pos.z - z, tl = Math.hypot(tx, tz) || 1;
  const c = (tx * dx + tz * dz) / tl;
  return { side: c < 0.57, mirror: dx * cam.right.x + dz * cam.right.z < 0, fs: Math.round(Math.sqrt(Math.max(0, 1 - c * c)) * 20) / 20 };
};

// ---------------- life: blinks and reaction timing ----------------
/** reference expression and action changes land 0-3 f before the word onset */
const LEAD = 2 / FPS;
/** eyelid 0 open .. 1 shut. Reference: gaps 0.5-2.3 s, 4-frame blink half / shut / shut / half, plus a blink across
 *  every expression swap (the shut frames hide the swap) */
const LID = [0.5, 1, 1, 0.5];
const SWAPS: Record<number, number[]> = {};
const lidAt = (t: number, i: number, swaps: number[] = []) => {
  const f = Math.round(t * FPS);
  for (const ts of swaps) { const k = f - Math.round((ts - LEAD) * FPS) + 1; if (k >= 0 && k < 4) return LID[k]; }
  let s = Math.round(-60 * hh(i, 9));
  for (let n = 0; s <= f && n < 400; n++) {
    const k = f - s;
    if (k >= 0 && k < 4) return LID[k];
    s += Math.round(15 + 54 * hh(i * 31 + n, 13)); // next blink 0.5-2.3 s later
  }
  return 0;
};
const fkey = (o: object) => JSON.stringify(o, (_k, v) => (typeof v === "number" ? q(v) : v));

type Who = { i: number; o: Outfit; okey: string };
/** one character drawing in the 600 x 1000 design space, sized by distance, lit from the scene's sun */
const person = (cam: CamInfo, who: Who, x: number, y: number, z: number, view: { side: boolean; mirror: boolean }, fo: FrontOpts, so: SideOpts, scale = 1): Place & { tierKey: string } => {
  const d = cam.pos.distanceTo(tmp.set(x, y + 1.2, z)) / scale;
  const [w, h, k] = tier(d);
  const mirror = view.side && view.mirror, light = light2D(cam, mirror), seed = seedOf(who.i);
  const f2: FrontOpts = { ...fo, light, seed }, s2: SideOpts = { ...so, light, seed };
  const key = view.side ? `S|${who.okey}|${fkey(s2)}` : `F|${who.okey}|${fkey(f2)}`;
  return {
    key, x, y, z, scale, mirror, tierKey: `${w}`,
    draw: (p) => (view.side ? bodySide(p, who.o, s2) : bodyFront(p, who.o, f2)),
    size: [w, h, k],
  };
};

/** ground shadow under a standing / sitting card (review rounds 2-4), multiply, blue-violet: a TIGHT contact pool right under
 *  the feet (~.5 on screen at the core) so nobody floats, plus by day (cards cast no real shadow) a lighter soft tail
 *  stretched AWAY from the sun, length ~1.6 m / tan(sun elevation), capped. Golden: world.ts casts real card shadows. */
const CONTACT: Record<"day" | "golden", [number, number, number]> = { day: [0.2, 0.21, 0.33], golden: [0.24, 0.2, 0.33] };
const TAIL: [number, number, number] = [0.42, 0.44, 0.62];
const toSrgb = (v: number) => { const c = clamp01(v); return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055; };
const hexOf = (c: [number, number, number], k: number) => "#" + c.map((v) => Math.round(255 * toSrgb(1 - (1 - v) * k)).toString(16).padStart(2, "0")).join("");
const blob = (out: Stage, x: number, y: number, z: number, sc = 1, k = 1) => {
  const hl = Math.hypot(SUN.x, SUN.z) || 1, ox = -SUN.x / hl, oz = -SUN.z / hl, rot = Math.atan2(-ox, -oz);
  if (LNAME === "day") {
    const el = Math.asin(Math.min(0.99, Math.max(0.1, SUN.y)));
    const len = Math.min(2.4, Math.max(0.5, 1.6 / Math.tan(el))) * sc, h = len + 0.55 * sc, c = 0.3 * h; // feet at v = .2 of the card
    const tc = hexOf(TAIL, k);
    out.fx.push({ key: `blob|shadow|${tc}`, cw: 128, ch: 256, draw: (p) => fxShadow(p, tc), x: x + ox * c, y: y + 0.018, z: z + oz * c,
      w: 0.72 * sc, h, flat: true, rot });
  }
  const cc = hexOf(CONTACT[LNAME], k);
  out.fx.push({ key: `blob|contact|${cc}`, cw: 128, ch: 128, draw: (p) => fxContact(p, cc), x: x + ox * 0.03 * sc, y: y + 0.022, z: z + oz * 0.03 * sc,
    w: 0.52 * sc, h: 0.4 * sc, flat: true, rot });
};

// ---------------- crowd by shot ----------------
export type Stage = { places: Place[]; fx: FxPlace[] };

// =====================================================================================================
// Gimli roles
// =====================================================================================================
const NAVY = "#1f2a44";
export const CAPTAIN: Outfit = { jacket: NAVY, pants: NAVY, boots: INK, hat: "cap", cap: NAVY, buttons: "#e8c45a", moustache: "#6a5a4a", skin: SKINS[0] };
export const FO: Outfit = { jacket: NAVY, pants: NAVY, boots: INK, hat: "hair", hair: "#3a2a20", buttons: "#e8c45a", skin: SKINS[2] };
export const SIMPILOT: Outfit = { jacket: "#2f3f5f", pants: "#2f3f5f", boots: INK, hat: "hair", hair: "#b0844a", buttons: "#d9dde0", skin: SKINS[1] };
export const FUELER: Outfit = { jacket: "#e8892c", pants: "#e8892c", boots: "#4a3426", hat: "cap", cap: "#2f5f6a", skin: SKINS[3] };
export const INVESTIGATOR = (v: number): Outfit => ({ jacket: ["#5a5d66", "#6b5a48", "#4a5a6b"][v % 3], pants: "#3b3f52", boots: INK, hat: "hair", hair: ["#2a201a", "#8a8a8a", "#5a3b2a"][v % 3], moustache: v === 1 ? "#8a8a8a" : undefined, skin: SKINS[v % 4] });
export const AGENT: Outfit = { jacket: "#3f6fb5", pants: "#2c3a5c", boots: INK, hat: "hair", hair: "#5a3b2a", dress: "#3f6fb5", skin: SKINS[1] };
export const TRAVELLER: Outfit = { jacket: "#2f9a55", pants: "#3b5b9a", boots: "#f4f1ea", hat: "cap", cap: "#f2c230", skin: SKINS[0] };
const PAX_COATS = ["#c26a3a", "#5d7a3a", "#3f6fb5", "#8c3b4a", "#d9a441", "#7b5ac9", "#2f5f6a", "#b5653f"];
const HAIRS = ["#3a2a20", "#e0b66a", "#7a4a2a", "#2a201a", "#a85a32", "#8a8a8a"];
export const PAX = (v: number): Outfit => ({ jacket: PAX_COATS[v % 8], pants: "#3b3f52", boots: "#4a3426", hat: "hair", hair: HAIRS[v % 6], skin: SKINS[v % 4], dress: v % 3 === 1 ? ["#d9a441", "#c25a7a", "#5a8fc2"][v % 3] : undefined, moustache: v % 7 === 2 ? "#4a3426" : undefined });
export const RACER = (v: number): Outfit => ({ jacket: ["#f4f1e6", "#d6452f", "#2f6fd6", "#f2c230"][v % 4], pants: ["#f4f1e6", "#d6452f", "#2f6fd6", "#1c1f27"][v % 4], boots: INK, hat: "hair", hair: HAIRS[(v + 2) % 6], skin: SKINS[(v + 1) % 4] });

const WHO = (i: number, o: Outfit, okey: string): Who => ({ i, o, okey });
/** expression that switches at word frames: [[frame, expr], ...] (lands LEAD before the word) */
const exprAt = (t: number, seq: [number, Expr][]) => { let e = seq[0][1]; for (const [f, x] of seq) if (t >= f / FPS - LEAD) e = x; return e; };
const front = (cam: CamInfo, who: Who, x: number, y: number, z: number, fo: FrontOpts, scale = 1) => person(cam, who, x, y, z, { side: false, mirror: false }, fo, {}, scale);

// ---------------- effect drawings ----------------
const HAND = "bold 46px \"Comic Sans MS\", \"Segoe Print\", cursive";
const HAND_BIG = "bold 62px \"Comic Sans MS\", \"Segoe Print\", cursive";
const fxClipboard = (p: Pen, k: number) => {
  const g = p.g;
  p.poly([[20, 40], [380, 40], [380, 500], [20, 500]], "#a8744a", 9);
  p.poly([[44, 70], [356, 70], [356, 476], [44, 476]], "#fbf8f0", 5);
  p.poly([[150, 18], [250, 18], [262, 62], [138, 62]], "#9aa0a8", 7);
  g.strokeStyle = "rgba(90,110,160,0.5)"; g.lineWidth = 3;
  for (let y = 120; y < 470; y += 44) { g.beginPath(); g.moveTo(60, y); g.lineTo(340, y); g.stroke(); }
  g.fillStyle = "#1f2a44"; g.textAlign = "left"; g.textBaseline = "alphabetic";
  g.font = HAND;
  g.fillText("7682 L", 70, 158); g.fillText("x 1.77", 70, 202);
  g.strokeStyle = "#1f2a44"; g.lineWidth = 5; g.beginPath(); g.moveTo(66, 222); g.lineTo(300, 222); g.stroke();
  if (k >= 1) {
    g.font = HAND_BIG; g.fillText("22300", 70, 300);
    g.fillStyle = k === 1 ? "#1f9a55" : "#c8323a"; g.fillText(k === 1 ? "kg" : "lb", 272, 300);
    if (k === 2) { g.strokeStyle = "#c8323a"; g.lineWidth = 7; g.beginPath(); g.ellipse(300, 282, 52, 40, 0, 0, Math.PI * 2); g.stroke(); }
  }
};
const fxStick = (p: Pen) => { p.poly([[14, 10], [30, 10], [30, 590], [14, 590]], "#d9d3c4", 5); for (let y = 60; y < 580; y += 60) p.line([[12, y], [32, y]], INK, 3, false); p.poly([[14, 420], [30, 420], [30, 590], [14, 590]], "#7fb0d8", 4); };
const fxRock = (p: Pen) => p.poly([[40, 120], [30, 70], [70, 30], [140, 26], [176, 70], [168, 128], [110, 146]], "#8f8a86", 9);
const fxPaperPlane = (p: Pen) => { p.poly([[10, 80], [290, 60], [120, 120]], "#ffffff", 7); p.poly([[10, 80], [290, 60], [130, 30]], "#e9eef6", 7); p.line([[10, 80], [290, 60]], INK, 4); };
const fxBubble = (p: Pen) => {
  p.ell(260, 170, 230, 150, "#ffffff", 8);
  p.ell(70, 340, 30, 22, "#ffffff", 7); p.ell(30, 385, 16, 12, "#ffffff", 6);
  // sailplane: long thin wings, slim body, T-tail
  p.poly([[60, 160], [460, 150], [462, 162], [62, 174]], "#f2efe6", 6);
  p.poly([[200, 172], [380, 160], [420, 166], [390, 176], [210, 182]], "#f2efe6", 6);
  p.poly([[380, 160], [400, 110], [414, 112], [404, 164]], "#c8323a", 5);
  p.poly([[370, 112], [440, 108], [440, 116], [372, 118]], "#f2efe6", 5);
};
const fxDash = (p: Pen) => p.poly([[10, 18], [190, 18], [190, 42], [10, 42]], "#ffffff", 5);
const fxTag = (p: Pen, v: number) => { p.poly([[8, 30], [30, 8], [52, 30], [52, 112], [8, 112]], "#f3f1ec", 5); p.poly([[8, 70], [52, 70], [52, 84], [8, 84]], v % 2 ? "#c8323a" : "#26304a", 0); p.ell(30, 32, 6, 6, INK, 0); };
const fxMagnifier = (p: Pen) => { p.line([[100, 180], [100, 290]], "#5a3b2a", 22); p.ell(100, 100, 80, 80, "rgba(200,230,255,0.55)", 12); };
const fxGlow = (p: Pen, col: string) => {
  const g = p.g, gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, col); gr.addColorStop(1, "rgba(0,0,0,0)"); g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
};
const fxSpray = (p: Pen, u: number) => {
  for (let i = 0; i < 9; i++) { const d = 30 + i * 30 + 20 * u, r = 14 + i * 5; p.ell(40 + d, 150 + Math.sin(i * 2.1 + u * 9) * (6 + i * 3), r, r * 0.8, "#f4f6fb", 4); }
};
const fxCity = (p: Pen) => { for (let i = 0; i < 18; i++) { const h = 30 + ((i * 37) % 70); p.poly([[i * 22, 160], [i * 22, 160 - h], [i * 22 + 18, 160 - h], [i * 22 + 18, 160]], "#b9b4c8", 0); } };

// ---------------- per-shot staging ----------------
const sitY = 0.42; // seated card base over the cabin / cockpit floor (cushion top ~0.5 m)
const pilots = (id: number, t: number, cam: CamInfo, out: Stage) => {
  const f = t * FPS;
  const sim = id === 19;
  const cE: Expr = sim ? exprAt(t, [[1745, "smile"], [W.simulator, "nervous"], [W.crashed, "shock"], [W.crashed + 18, "dazed"]])
    : id === 5 ? exprAt(t, [[520, "neutral"], [W.alarm1, "stern"], [W.alarm2, "nervous"], [W.quiet, "shock"]])
    : id === 8 ? exprAt(t, [[770, "nervous"], [W.captain, "smile"], [W.fun, "grin"]])
    : id === 10 ? "stern" : "nervous";
  const oE: Expr = sim ? exprAt(t, [[1745, "neutral"], [W.simulator, "nervous"], [W.crashed, "shock"], [W.crashed + 18, "dazed"]])
    : id === 5 ? exprAt(t, [[520, "smile"], [W.alarm1, "nervous"], [W.quiet, "shock"]])
    : id === 10 ? exprAt(t, [[905, "nervous"], [W.remembered, "smile"], [W.gimli - 20, "grin"]])
    : "nervous";
  const [cx, , cz] = COCKPIT.capt, [ox, , oz] = COCKPIT.fo;
  out.places.push(front(cam, WHO(1, sim ? SIMPILOT : CAPTAIN, sim ? "sim" : "capt"), cx, sitY, cz - 0.15, { mode: "sit", expr: cE, blink: lidAt(t, 1) }));
  const wave = id === 10 && f > W.remembered + 20 ? q(0.6 + 0.2 * Math.sin(t * 3), 30) : undefined;
  out.places.push(front(cam, WHO(2, FO, "fo"), ox, sitY, oz - 0.15, { mode: "sit", expr: oE, blink: lidAt(t, 2), wave }));
  // amber/red glow on the faces when the cautions light
  const glowOn = (id === 5 && f >= W.alarm1) || id === 6 || (sim && f >= W.simulator);
  if (glowOn && Math.floor(f / 8) % 2 === 0) for (const x of [cx, ox])
    out.fx.push({ key: `glow|${sim ? "r" : "a"}`, cw: 256, ch: 256, draw: (p) => fxGlow(p, sim ? "rgba(255,60,48,0.55)" : "rgba(255,181,46,0.5)"), x, y: 1.25, z: 0.3, w: 0.9, h: 0.9, soft: true });
  if (id === 8 && f >= W.captain + 6) {
    const u = q(smooth((f - W.captain - 6) / 10), 20);
    out.fx.push({ key: "bubble", cw: 500, ch: 420, draw: fxBubble, x: cx - 0.28, y: 1.6, z: cz - 0.05, w: 0.62 * u, h: 0.52 * u });
  }
  if (sim && f >= W.crashed && f < W.crashed + 14) {
    const u = q((f - W.crashed) / 14, 30);
    out.fx.push({ key: `burst${u}`, cw: 500, ch: 500, draw: (p) => fxBurst(p, u, "#ffd23a", 12, 50, 240), x: 0, y: 1.45, z: 0.9, w: 2.2, h: 2.2 });
  }
  if (sim && f >= W.crashed + 18) {
    const u = q((t * 0.9) % 1, 30);
    out.fx.push({ key: `stars${u}`, cw: 420, ch: 210, draw: (p) => fxStars(p, u), x: cx, y: 1.78, z: cz - 0.1, w: 0.5, h: 0.25 });
  }
};

const passengers = (t: number, cam: CamInfo, out: Stage) => {
  let i = 0;
  for (let r = 0; r < CABIN.rows; r++) for (const x of CABIN.seats) {
    i++;
    if ((i * 7) % 11 === 3) continue; // a few empty seats
    const z = CABIN.row0 + r * CABIN.pitch + 0.2;
    const ex: Expr[] = ["nervous", "shock", "neutral", "nervous", "smile"];
    const expr = exprAt(t, [[700, ex[i % 5]], [W.glider, (["shock", "nervous", "shock", "dazed"] as Expr[])[i % 4]]]);
    out.places.push(front(cam, WHO(100 + i, PAX(i), `p${i % 24}`), x, sitY, z, { mode: "sit", expr, blink: lidAt(t, 100 + i) }, i % 9 === 4 ? 0.72 : 1));
  }
};

const apronCrew = (id: number, t: number, cam: CamInfo, out: Stage) => {
  const f = t * FPS;
  const [cx, , cz] = APRON.captain, [fx_, , fz] = APRON.fueler;
  const capE: Expr = id === 4 ? exprAt(t, [[350, "smile"], [W.pounds, "smile_closed"]]) : "neutral";
  const fueE: Expr = id === 4 ? exprAt(t, [[350, "smile"], [W.kg, "grin"], [W.pounds, "smile"]]) : "smile";
  out.places.push(front(cam, WHO(1, CAPTAIN, "capt"), cx, 0, cz, { mode: "stand", expr: capE, blink: lidAt(t, 1) }));
  blob(out, cx, 0, cz);
  out.places.push(front(cam, WHO(3, FUELER, "fuel"), fx_, 0, fz, { mode: "stand", expr: fueE, blink: lidAt(t, 3) }));
  blob(out, fx_, 0, fz);
  // the dipstick in the captain's hand, the clipboard in the fueler's
  out.fx.push({ key: "stick", cw: 44, ch: 600, draw: fxStick, x: cx + 0.32, y: 1.3, z: cz + 0.15, w: 0.05, h: 1.4, rot: -0.12 });
  const k = id < 4 || f < W.kg - 2 ? 0 : f < W.pounds - 2 ? 1 : 2;
  out.fx.push({ key: `clip${k}`, cw: 400, ch: 520, draw: (p) => fxClipboard(p, k), x: fx_ + 0.12, y: 1.0, z: fz + 0.42, w: 0.36, h: 0.47, rot: 0.08 });
};

const fieldKid = (t: number, cam: CamInfo, out: Stage) => {
  const f = t * FPS, [x0, , z0] = GIMLI.field;
  const expr = exprAt(t, [[1019, "smile"], [W.rock, "neutral"], [W.paper, "grin"]]);
  out.places.push(front(cam, WHO(9, KID, "kid"), x0, 0, z0, { mode: "stand", expr, blink: lidAt(t, 9), wave: f > W.paper - 6 && f < W.paper + 14 ? 1 : undefined }, 0.72));
  blob(out, x0, 0, z0, 0.72);
  // the rock: held out, let go on "rock", drops straight down (g = 9.8 m/s^2)
  const tr = Math.max(0, (f - W.rock) / FPS), ry = Math.max(0.08, 1.05 - 4.9 * tr * tr);
  if (f < W.paper - 10) out.fx.push({ key: "rock", cw: 200, ch: 160, draw: fxRock, x: x0 + 0.42, y: ry, z: z0 + 0.15, w: 0.16, h: 0.13 });
  // the paper plane: thrown on "plane", slides forward 12 m for every metre down
  if (f >= W.paper + 6) {
    const tp = (f - W.paper - 6) / FPS, d = 3.2 * tp;
    out.fx.push({ key: "plane", cw: 300, ch: 150, draw: fxPaperPlane, x: x0 + 0.4 + d * 0.62, y: 1.25 - d / 12, z: z0 - d * 0.78, w: 0.34, h: 0.17, rot: -0.05 });
  } else if (f >= W.rock + 20) out.fx.push({ key: "plane", cw: 300, ch: 150, draw: fxPaperPlane, x: x0 + 0.38, y: 1.18, z: z0 + 0.12, w: 0.3, h: 0.15, rot: 0.2 });
};

const glideLine = (t: number, out: Stage) => {
  const f = t * FPS, n = Math.min(26, Math.floor((f - 1140) / 4));
  const j = jetAt(13, f).pos;
  for (let k = 1; k < n; k++) {
    const d = k * 9; // dashes behind the jet along its 1:12 path
    out.fx.push({ key: "dash", cw: 200, ch: 60, draw: fxDash, x: 0, y: j[1] + d / 12 - 1.8, z: j[2] - 24 - d, w: 4, h: 1.2, rot: Math.atan(1 / 12) });
  }
};

const raceCrowd = (id: number, t: number, cam: CamInfo, out: Stage) => {
  const f = t * FPS, [px, , pz] = GIMLI.paddock;
  const shocked = id >= 15;
  for (let i = 0; i < 22; i++) {
    const x = i < 12 ? px - 20 + (i % 6) * 3.1 + Math.sin(i) * 0.6 : 33 + (i % 5) * 1.6, z = i < 12 ? pz - 8 + Math.floor(i / 6) * 3 : 205 + (i - 12) * 2.8;
    const kid = i % 7 === 3;
    const expr: Expr = shocked ? (["shock", "nervous", "shock"] as Expr[])[i % 3] : exprAt(t, [[1250, (["smile", "grin", "smile_closed"] as Expr[])[i % 3]], [W.today, i % 2 ? "laugh" : "grin"]]);
    const look = id >= 15 ? viewOf(cam, x, z, 0, -1) : { side: false, mirror: false };
    const fo: FrontOpts = { mode: "stand", expr, blink: lidAt(t, 40 + i), wave: !shocked && i % 4 === 1 && f > W.today ? q(Math.sin(t * 9 + i), 30) : undefined };
    out.places.push(person(cam, WHO(40 + i, kid ? KID : PAX(i + 30), kid ? "kid" : `p${(i + 30) % 24}`), x, 0, z, look, fo, { mode: "stand", expr }, kid ? 0.72 : 1));
    blob(out, x, 0, z, kid ? 0.72 : 1);
  }
  for (const [i, x, z] of [[0, -15.8, 238], [1, -9.8, 260], [2, 17.4, 298]] as const) {
    const expr: Expr = shocked ? "shock" : "grin";
    out.places.push(front(cam, WHO(60 + i, RACER(i), `r${i}`), x, 0, z, { mode: "stand", expr, blink: lidAt(t, 60 + i) }));
    blob(out, x, 0, z);
  }
};

const rescue = (t: number, cam: CamInfo, out: Stage) => {
  const f = t * FPS, nz = STOP_Z + 24.5;
  if (f < W.died - 6) {
    for (const [i, x] of [[0, -2.2], [1, 0.6], [2, 2.8]] as const) {
      const run = clamp01((f - W.racers) / 20);
      const zz = nz + 2.4 + i * 0.3 + (1 - run) * 6;
      const view = viewOf(cam, x, zz, 0, -1);
      out.places.push(person(cam, WHO(60 + i, RACER(i), `r${i}`), x, 0, zz, view, { mode: "stand", expr: "stern", blink: lidAt(t, 60 + i) }, { mode: "march", phase: q((t * 2) % 1, 30), stride: view.fs * 0.8, expr: "stern" }));
      blob(out, x, 0, zz);
      if (run >= 1) {
        const u = q((t * 3 + i * 0.3) % 1, 20);
        out.fx.push({ key: `spray${u}`, cw: 400, ch: 300, draw: (p) => fxSpray(p, u), x: x * 0.6, y: 1.0, z: nz + 1.0, w: 1.8, h: 1.35, rot: Math.PI });
      }
    }
  } else {
    for (let i = 0; i < 18; i++) {
      const x = -16 - (i % 6) * 1.7 - Math.sin(i * 3) * 0.5, z = STOP_Z - 14 + Math.floor(i / 6) * 2.4;
      const expr = (["relief", "relief_open", "smile", "grin"] as Expr[])[i % 4];
      out.places.push(front(cam, WHO(140 + i, i % 5 === 0 ? CAPTAIN : PAX(i + 50), i % 5 === 0 ? "capt" : `p${(i + 50) % 24}`), x, 0, z, { mode: "stand", expr, blink: lidAt(t, 140 + i), wave: i % 3 ? q(Math.sin(t * 8 + i), 30) : undefined }));
      blob(out, x, 0, z);
    }
  }
};

const sparks = (t: number, out: Stage) => {
  const f = t * FPS;
  const j = jetAt(16, f);
  if (j.nose < 0.5 || f > 1592) return;
  for (let k = 0; k < 3; k++) {
    const u = q(((f * 0.37 + k * 0.33) % 1), 20);
    out.fx.push({ key: `spark${u}`, cw: 500, ch: 500, draw: (p) => fxBurst(p, u, "#ffd56a", 9, 30, 220), x: (k - 1) * 0.6, y: 0.4, z: j.pos[2] + 18.5 - k * 0.8, w: 2.2, h: 2.2 });
  }
};

const investigators = (t: number, cam: CamInfo, out: Stage) => {
  const pts: [number, number][] = [[-1.2, 27.4], [0.6, 26.8], [1.9, 28.0]];
  pts.forEach(([x, z], i) => {
    const expr = exprAt(t, [[1700, "stern"], [W.blamed, i === 1 ? "stern" : "nervous"]]);
    out.places.push(front(cam, WHO(80 + i, INVESTIGATOR(i), `inv${i}`), x, 0, z, { mode: "stand", expr, blink: lidAt(t, 80 + i) }));
    blob(out, x, 0, z);
  });
  out.fx.push({ key: "magnifier", cw: 200, ch: 300, draw: fxMagnifier, x: 0.25, y: 1.25, z: 26.4, w: 0.36, h: 0.54, rot: 0.3 });
};

const tags = (t: number, out: Stage) => {
  const f = t * FPS;
  if (f < W.cut) return;
  const u = (f - W.cut) / FPS;
  if (u < 0.5) { const k = q(u / 0.5, 20); out.fx.push({ key: `puff${k}`, cw: 300, ch: 300, draw: (p) => fxPuff(p, k), x: 0, y: 5, z: 0, w: 60, h: 60 }); }
  for (let i = 0; i < 70; i++) {
    const a = i * 2.39996, sp = 6 + (i % 7) * 2.2, x = Math.cos(a) * sp * u, z = Math.sin(a) * sp * u * 0.7;
    const y = Math.max(0.05, 4 + (8 + (i % 5) * 2) * u - 4.9 * u * u);
    const v = i % 2;
    out.fx.push({ key: `tag${v}`, cw: 60, ch: 120, draw: (p) => fxTag(p, v), x, y, z, w: 1.3, h: 2.6, rot: Math.sin(i + u * 6) * 0.8 });
  }
};

const checkin = (t: number, cam: CamInfo, out: Stage) => {
  const [ax, , az] = CHECKIN.agent, [tx, , tz] = CHECKIN.traveller;
  out.places.push(front(cam, WHO(90, AGENT, "agent"), ax, 0, az, { mode: "stand", expr: exprAt(t, [[1930, "smile"], [W.check, "smile_closed"]]), blink: lidAt(t, 90) }));
  const te = exprAt(t, [[1930, "smile"], [W.kg23, "smile_closed"], [W.lb50, "nervous"], [W.check, "dazed"]]);
  out.places.push(front(cam, WHO(91, TRAVELLER, "trav"), tx, 0, tz, { mode: "stand", expr: te, blink: lidAt(t, 91) }));
  blob(out, tx, 0, tz);
};

/** everything with a face (and the one-off effects) in shot `id` at time t */
export const stage = (id: number, t: number, cam: CamInfo): Stage => {
  const out: Stage = { places: [], fx: [] };
  const s = SHOTS[id - 1];
  LNAME = s.light;
  findSun(cam, SUN);
  switch (id) {
    case 2: case 3: case 4: apronCrew(id, t, cam, out); break;
    case 5: case 6: case 8: case 10: case 19: pilots(id, t, cam, out); break;
    case 7: passengers(t, cam, out); break;
    case 9: out.fx.push({ key: "city", cw: 400, ch: 170, draw: fxCity, x: 60, y: -40, z: 1400, w: 120, h: 50, soft: true }); break;
    case 12: fieldKid(t, cam, out); break;
    case 13: glideLine(t, out); break;
    case 14: case 15: raceCrowd(id, t, cam, out); break;
    case 16: raceCrowd(id, t, cam, out); sparks(t, out); break;
    case 17: rescue(t, cam, out); break;
    case 18: investigators(t, cam, out); break;
    case 20: tags(t, out); break;
    case 21: checkin(t, cam, out); break;
  }
  return out;
};
export { FPS };
