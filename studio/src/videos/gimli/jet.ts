// A procedural wide-body twinjet in the proportions of a 767-200 (48.5 m long, 47.6 m span, 5 m fuselage), in a
// generic early-80s livery (white top, grey belly, red cheatline and tail; no real logo). Origin = fuselage centreline
// at mid-length, nose toward +z, right wing toward -x. pose() applies story.ts JetPose: gear, nose-gear collapse,
// ram-air turbine, fan spin, slip/roll/pitch.
import * as THREE from "three";
import { V, lam, quad, boxGeo } from "./build";
import { ctex } from "./paint";
import { JetPose } from "./story";

const Z0 = -24.3, Z1 = 24.2, N_Z = 64, N_A = 32;
/** fuselage section at z: radius and centre height (nose droop, tail upsweep keeping the crown line straight) */
const section = (z: number): [number, number] => {
  if (z > 15.5) { const u = (z - 15.5) / (Z1 - 15.5); const r = 2.5 * Math.sqrt(Math.max(0, 1 - u ** 2.2)); return [Math.max(r, 0.02), -0.55 * u * u]; }
  if (z < -11) { const u = (-11 - z) / (-11 - Z0); const r = 2.5 - 2.15 * u ** 1.25; return [r, (2.5 - r) * 0.82]; }
  return [2.5, 0];
};
/** z of the n-th sample: denser at the nose */
const zAt = (i: number) => { const u = i / N_Z; return Z0 + (Z1 - Z0) * (u < 0.75 ? u / 0.75 * 0.78 : 0.78 + ((u - 0.75) / 0.25) * 0.22); };

const fuselageGeo = () => {
  const pos: number[] = [], uv: number[] = [], idx: number[] = [];
  for (let i = 0; i <= N_Z; i++) {
    const z = zAt(i), [r, yc] = section(z);
    for (let k = 0; k <= N_A; k++) {
      const th = (k / N_A) * Math.PI * 2; // 0 = crown, +pi/2 = +x side (left wing side)
      pos.push(r * Math.sin(th), yc + r * Math.cos(th) * 1.04, z);
      uv.push((z - Z0) / (Z1 - Z0), k / N_A);
    }
  }
  for (let i = 0; i < N_Z; i++) for (let k = 0; k < N_A; k++) {
    const a = i * (N_A + 1) + k, b = a + 1, c = a + N_A + 1, d = c + 1;
    idx.push(a, c, b, b, c, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
};

/** livery: canvas x = along the body (tail -> nose), canvas y = around (crown at 0, +x side at 1/4, belly at 1/2) */
const LW = 2048, LH = 512;
const zx = (z: number) => ((z - Z0) / (Z1 - Z0)) * LW;
const liveryTex = () => ctex("jetLivery", LW, LH, (g) => {
  g.fillStyle = "#f3f1ec"; g.fillRect(0, 0, LW, LH);
  // grey belly
  g.fillStyle = "#c7cad1"; g.fillRect(0, LH * 0.34, LW, LH * 0.32);
  for (const side of [0.25, 0.75]) {
    const y = LH * side;
    // red cheatline under the windows + thin pinstripe
    g.fillStyle = "#c8323a"; g.fillRect(zx(-17), y + (side < 0.5 ? 10 : -26), zx(21.5) - zx(-17), 16);
    g.fillStyle = "#7a2028"; g.fillRect(zx(-17), y + (side < 0.5 ? 30 : -34), zx(21.5) - zx(-17), 3);
    // cabin windows
    g.fillStyle = "#26304a";
    for (let z = -13.5; z < 14.5; z += 0.52) {
      if (Math.abs(z - 9.5) < 0.6 || Math.abs(z + 11) < 0.6 || Math.abs(z - 1.5) < 0.5) continue; // doors
      const x = zx(z); g.beginPath(); g.roundRect(x - 3.2, y - (side < 0.5 ? 2 : 6), 6.4, 8, 3); g.fill();
    }
    // doors (outlines)
    g.strokeStyle = "rgba(60,60,70,0.55)"; g.lineWidth = 2;
    for (const z of [9.5, -11, 1.5]) g.strokeRect(zx(z) - 9, y - (side < 0.5 ? 24 : 14), 18, 38);
    // cockpit windows
    g.fillStyle = "#1c2438";
    const cy = LH * (side < 0.5 ? 0.165 : 0.835);
    g.beginPath(); g.moveTo(zx(18.6), cy - 18); g.lineTo(zx(20.5), cy - 22); g.lineTo(zx(20.9), cy + 6); g.lineTo(zx(18.6), cy + 10); g.closePath(); g.fill();
    g.beginPath(); g.moveTo(zx(17.2), cy - 16); g.lineTo(zx(18.3), cy - 18); g.lineTo(zx(18.3), cy + 10); g.lineTo(zx(17.2), cy + 9); g.closePath(); g.fill();
  }
  // windscreen panes across the crown front
  g.fillStyle = "#1c2438";
  g.fillRect(zx(20.6), 0, zx(21.4) - zx(20.6), LH * 0.11); g.fillRect(zx(20.6), LH * 0.89, zx(21.4) - zx(20.6), LH * 0.11);
  // panel seams (faint)
  g.strokeStyle = "rgba(90,90,100,0.18)"; g.lineWidth = 1.5;
  for (let z = -20; z < 18; z += 2.6) { g.beginPath(); g.moveTo(zx(z), 0); g.lineTo(zx(z), LH); g.stroke(); }
  // nose cone: radome darker
  g.fillStyle = "#3a3f4a"; g.fillRect(zx(23.1), 0, LW - zx(23.1), LH);
});
const fanTex = () => ctex("jetFan", 256, 256, (g) => {
  g.fillStyle = "#2b2f38"; g.beginPath(); g.arc(128, 128, 126, 0, Math.PI * 2); g.fill();
  g.strokeStyle = "#8d939d"; g.lineWidth = 9;
  for (let k = 0; k < 22; k++) { const a = (k / 22) * Math.PI * 2; g.beginPath(); g.moveTo(128 + Math.cos(a) * 30, 128 + Math.sin(a) * 30); g.lineTo(128 + Math.cos(a + 0.35) * 120, 128 + Math.sin(a + 0.35) * 120); g.stroke(); }
  g.fillStyle = "#c9ccd3"; g.beginPath(); g.arc(128, 128, 30, 0, Math.PI * 2); g.fill();
  g.fillStyle = "#3a3f4a"; g.beginPath(); g.moveTo(128, 104); g.lineTo(136, 128); g.lineTo(128, 130); g.fill(); // spinner swirl
});

/** a tapered slab (wing / tailplane / fin) from its top outline (root LE, root TE, tip TE, tip LE) and thicknesses */
const slab = (rl: THREE.Vector3, rt: THREE.Vector3, tt: THREE.Vector3, tl: THREE.Vector3, thR: number, thT: number, up = V(0, 1, 0)) => {
  const off = (p: THREE.Vector3, th: number) => p.clone().addScaledVector(up, -th);
  const b = [off(rl, thR), off(rt, thR * 0.4), off(tt, thT * 0.4), off(tl, thT)];
  const t = [rl, rt.clone().addScaledVector(up, -thR * 0.3), tt.clone().addScaledVector(up, -thT * 0.3), tl];
  const c = new THREE.Vector3(); [...t, ...b].forEach((p) => c.add(p)); c.multiplyScalar(1 / 8);
  const face = (a: THREE.Vector3, bb: THREE.Vector3, cc: THREE.Vector3, d: THREE.Vector3) => {
    const n = new THREE.Vector3().subVectors(bb, a).cross(new THREE.Vector3().subVectors(d, a));
    const m = a.clone().add(bb).add(cc).add(d).multiplyScalar(0.25).sub(c);
    return n.dot(m) >= 0 ? quad(a, bb, cc, d) : quad(a, d, cc, bb);
  };
  return [face(t[0], t[1], t[2], t[3]), face(b[0], b[1], b[2], b[3]), face(t[0], t[3], b[3], b[0]), face(t[1], t[2], b[2], b[1]), face(t[2], t[3], b[3], b[2])];
};

const M = () => ({
  body: lam("jetBody", () => ({ map: liveryTex() })),
  wing: lam("jetWing", () => ({ color: "#d3d6dc" })),
  red: lam("jetRed", () => ({ color: "#c8323a" })),
  nac: lam("jetNacelle", () => ({ color: "#dcdee3" })),
  lip: lam("jetLip", () => ({ color: "#aab0b9" })),
  fan: new THREE.MeshBasicMaterial({ map: fanTex() }),
  strut: lam("jetStrut", () => ({ color: "#a2a7b0" })),
  tyre: lam("jetTyre", () => ({ color: "#2c2b31" })),
  hub: lam("jetHub", () => ({ color: "#c3c6cc" })),
  dark: lam("jetDark", () => ({ color: "#3a3f4a" })),
});

const mesh = (g: THREE.BufferGeometry | THREE.BufferGeometry[], m: THREE.Material, parent: THREE.Object3D) => {
  const list = Array.isArray(g) ? g : [g];
  for (const x of list) { const o = new THREE.Mesh(x, m); o.castShadow = true; o.receiveShadow = true; parent.add(o); }
};
const cyl = (r0: number, r1: number, len: number, seg = 20) => { const g = new THREE.CylinderGeometry(r1, r0, len, seg, 1, true); g.rotateX(Math.PI / 2); return g; }; // along z, r0 at -z

export class Jet {
  root = new THREE.Group();
  private body = new THREE.Group();
  private mains: THREE.Group[] = [];
  private noseGear = new THREE.Group();
  private rat = new THREE.Group();
  private fans: THREE.Mesh[] = [];
  private ratBlades = new THREE.Group();

  constructor() {
    const m = M(), B = this.body;
    this.root.add(B);
    mesh(fuselageGeo(), m.body, B);
    // wings (low, swept 31 deg, dihedral 6 deg) + tailplanes + fin
    for (const s of [1, -1]) {
      mesh(slab(V(2.3 * s, -1.55, 6.2), V(2.3 * s, -1.55, -4.6), V(23.8 * s, 0.65, -11.6), V(23.8 * s, 0.65, -9.4), 0.75, 0.2), m.wing, B);
      mesh(slab(V(1.2 * s, 1.3, -17.5), V(0.9 * s, 1.35, -22.3), V(9.3 * s, 2.2, -24.6), V(9.3 * s, 2.2, -22.9), 0.32, 0.1), m.wing, B);
      // engine: nacelle, inlet lip, fan face, exhaust cone, pylon
      const ex = 7.9 * s, ey = -3.15, ez = 6.6;
      mesh(cyl(1.05, 1.32, 4.6, 24).translate(ex, ey, ez - 2.3), m.nac, B);
      mesh(new THREE.TorusGeometry(1.32, 0.12, 8, 28).translate(ex, ey, ez), m.lip, B);
      const fan = new THREE.Mesh(new THREE.CircleGeometry(1.25, 32), m.fan); fan.position.set(ex, ey, ez - 0.35); B.add(fan); this.fans.push(fan);
      mesh(new THREE.ConeGeometry(0.62, 1.4, 16).rotateX(-Math.PI / 2).translate(ex, ey, ez - 5.2), m.dark, B);
      mesh(boxGeo(V(ex - 0.18, ey + 0.9, ez - 4.4), V(ex + 0.18, -1.2, ez - 0.6)), m.wing, B);
      // main gear: strut + 4-wheel bogie (gear down: wheels touch y = -3.3)
      const g = new THREE.Group(); g.position.set(4.6 * s, -1.7, -3.2);
      mesh(cyl(0.16, 0.16, 1, 10).rotateX(Math.PI / 2).scale(1, 1.25, 1).translate(0, -0.62, 0), m.strut, g);
      mesh(boxGeo(V(-0.12, -1.38, -0.9), V(0.12, -1.18, 0.9)), m.strut, g);
      for (const [dx, dz] of [[-0.42, -0.72], [0.42, -0.72], [-0.42, 0.72], [0.42, 0.72]]) {
        mesh(new THREE.CylinderGeometry(0.58, 0.58, 0.36, 18).rotateZ(Math.PI / 2).translate(dx, -1.02, dz), m.tyre, g);
        mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.38, 12).rotateZ(Math.PI / 2).translate(dx, -1.02, dz), m.hub, g);
      }
      B.add(g); this.mains.push(g);
    }
    mesh(slab(V(0, 2.0, -12.5), V(0, 2.25, -21.6), V(0, 10.6, -24.6), V(0, 10.6, -21.3), 0.4, 0.15, V(1, 0, 0)).map((x) => x.translate(0.2, 0, 0)), m.red, B);
    // wing-to-body fairing under the belly
    mesh(new THREE.SphereGeometry(1, 20, 12).scale(2.6, 1.0, 7.5).translate(0, -2.05, 0.6), m.body, B);
    // nose gear
    const ng = this.noseGear; ng.position.set(0, -1.9, 18.6);
    mesh(cyl(0.11, 0.11, 1, 10).rotateX(Math.PI / 2).scale(1, 0.9, 1).translate(0, -0.45, 0), m.strut, ng);
    for (const dx of [-0.25, 0.25]) mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.26, 16).rotateZ(Math.PI / 2).translate(dx, -0.98, 0), m.tyre, ng);
    B.add(ng);
    // ram-air turbine: a little propeller that drops out of the right wing root fairing
    this.rat.position.set(-1.6, -2.6, 1.2);
    mesh(boxGeo(V(-0.05, -0.75, -0.05), V(0.05, 0, 0.05)), m.strut, this.rat);
    for (let k = 0; k < 2; k++) mesh(boxGeo(V(-0.04, -0.03, -0.42), V(0.04, 0.03, 0.42)).rotateX(0).rotateY(0).translate(0, 0, 0), m.dark, this.ratBlades);
    this.ratBlades.children[1].rotation.y = Math.PI / 2;
    this.ratBlades.position.set(0, -0.8, 0.12); this.ratBlades.rotation.x = Math.PI / 2;
    this.rat.add(this.ratBlades); B.add(this.rat);
  }

  pose(p: JetPose, t: number) {
    const R = this.root;
    R.visible = p.visible && (p.scrap ?? 0) < 0.5;
    if (!R.visible) return;
    R.position.set(...p.pos);
    R.rotation.order = "YXZ";
    // nose collapse: pitch down about the main-gear contact so the nose rests on the runway
    const collapse = 0.052 * p.nose;
    R.rotation.set(-(p.pitch - collapse), p.yaw, p.roll);
    R.position.y -= collapse * 3.2;
    const sc = 1 - 0.3 * (p.scrap ?? 0); R.scale.setScalar(sc);
    for (const g of this.mains) { g.visible = p.gear > 0.02; g.scale.set(1, Math.max(0.05, p.gear), 1); }
    const ng = Math.min(p.gear, 1 - p.nose);
    this.noseGear.visible = ng > 0.05; this.noseGear.scale.set(1, Math.max(0.05, ng), 1);
    this.rat.visible = p.rat > 0.02; this.rat.scale.setScalar(Math.max(0.05, p.rat));
    this.ratBlades.rotation.z = t * 40;
    // fans: fast spin reads as a still blur; slow spin shows the blades turning
    for (const [i, f] of this.fans.entries()) f.rotation.z = (i ? -1 : 1) * (p.spin * t * 9 + (1 - p.spin) * t * 0.6);
  }
}
