// The six places of the film, each a group switched on per shot (all share the origin, ground y = 0):
// sky (cloud sea), apron (Montreal 1983), cockpit, cabin, gimli (old air base turned race track + the analogy
// field), checkin. Interior shells do not cast shadows, so the sun lights the inside like a cartoon set.
import * as THREE from "three";
import { V, lam, quad, boxGeo, Batch } from "./build";
import { ctex, rep, grassHD, cloudHD, CLOUD_DAY, CLOUD_GOLD, jit } from "./paint";
import { NOINK } from "./ink";
import { SetName, APRON, COCKPIT, CABIN, GIMLI, CHECKIN, W, FPS, clamp01 } from "./story";

// ---------------- textures ----------------
const asphalt = () => ctex("asphalt", 1024, 1024, (g, r) => {
  g.fillStyle = "#8d8f96"; g.fillRect(0, 0, 1024, 1024);
  for (let i = 0; i < 1400; i++) { g.fillStyle = jit(r, "#7f8189", 0.12, 4, 0.2); g.globalAlpha = 0.5; g.fillRect(r() * 1024, r() * 1024, 2 + r() * 5, 2 + r() * 5); }
  g.globalAlpha = 0.25; g.fillStyle = "#6f717a";
  for (let i = 0; i < 18; i++) { g.beginPath(); g.ellipse(r() * 1024, r() * 1024, 40 + r() * 120, 20 + r() * 60, r() * 3, 0, 7); g.fill(); }
  g.globalAlpha = 1; g.strokeStyle = "rgba(60,60,70,0.35)"; g.lineWidth = 3;
  g.beginPath(); g.moveTo(0, 512); g.lineTo(1024, 512); g.moveTo(512, 0); g.lineTo(512, 1024); g.stroke();
});
const concrete = () => ctex("concrete", 1024, 1024, (g, r) => {
  g.fillStyle = "#b9b6ad"; g.fillRect(0, 0, 1024, 1024);
  for (let x = 0; x < 4; x++) for (let y = 0; y < 4; y++) { g.fillStyle = jit(r, "#b5b2a8", 0.06, 3, 0.2); g.fillRect(x * 256 + 3, y * 256 + 3, 250, 250); }
  for (let i = 0; i < 70; i++) { g.strokeStyle = "rgba(70,68,64,0.35)"; g.lineWidth = 1.5; g.beginPath(); let x = r() * 1024, y = r() * 1024; g.moveTo(x, y); for (let k = 0; k < 5; k++) { x += (r() - 0.5) * 60; y += (r() - 0.5) * 60; g.lineTo(x, y); } g.stroke(); }
  g.globalAlpha = 0.18; g.fillStyle = "#5b6b3a";
  for (let i = 0; i < 40; i++) g.fillRect(r() * 1024, r() * 1024, 2 + r() * 30, 2);
  g.globalAlpha = 1;
});
const facadeGlass = () => ctex("terminalGlass", 1024, 512, (g) => {
  g.fillStyle = "#d8d3c6"; g.fillRect(0, 0, 1024, 512);
  for (let x = 0; x < 16; x++) for (let y = 0; y < 3; y++) {
    const gr = g.createLinearGradient(0, 60 + y * 150, 0, 170 + y * 150); gr.addColorStop(0, "#5f86b6"); gr.addColorStop(1, "#2f4f7a");
    g.fillStyle = gr; g.fillRect(x * 64 + 6, 50 + y * 150, 52, 110);
  }
  g.fillStyle = "#b9b2a2"; for (let y = 0; y < 4; y++) g.fillRect(0, 36 + y * 150, 1024, 12);
});
const screenTex = (on: boolean) => ctex("efis" + on, 1024, 256, (g) => {
  g.fillStyle = "#15171d"; g.fillRect(0, 0, 1024, 256);
  for (let i = 0; i < 6; i++) {
    const x = 20 + i * 168;
    g.fillStyle = "#0b0c10"; g.fillRect(x, 30, 150, 190);
    if (!on) continue;
    if (i === 0 || i === 5) { // attitude: sky over ground
      g.fillStyle = "#2f7fd8"; g.fillRect(x + 8, 38, 134, 90); g.fillStyle = "#9a6a3c"; g.fillRect(x + 8, 128, 134, 84);
      g.strokeStyle = "#fff"; g.lineWidth = 3; g.beginPath(); g.moveTo(x + 40, 128); g.lineTo(x + 110, 128); g.stroke();
      g.fillStyle = "#ffd23a"; g.fillRect(x + 62, 124, 26, 8);
    } else if (i === 1 || i === 4) { // map: magenta line + arcs
      g.strokeStyle = "#e8e8f0"; g.lineWidth = 2; g.beginPath(); g.arc(x + 75, 210, 120, Math.PI * 1.15, Math.PI * 1.85); g.stroke();
      g.strokeStyle = "#ff4fd8"; g.lineWidth = 4; g.beginPath(); g.moveTo(x + 75, 205); g.lineTo(x + 100, 60); g.stroke();
      g.fillStyle = "#4fe0ff"; g.beginPath(); g.arc(x + 100, 60, 7, 0, 7); g.fill();
    } else { // engine gauges: green arcs
      for (const cy of [80, 165]) for (const cx of [x + 45, x + 105]) {
        g.strokeStyle = "#5c6370"; g.lineWidth = 6; g.beginPath(); g.arc(cx, cy, 26, Math.PI * 0.9, Math.PI * 2.1); g.stroke();
        g.strokeStyle = "#62e07a"; g.beginPath(); g.arc(cx, cy, 26, Math.PI * 0.9, Math.PI * 1.6); g.stroke();
      }
    }
  }
});
const panelTex = () => ctex("cockpitPanel", 512, 512, (g, r) => {
  g.fillStyle = "#4c535f"; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 160; i++) {
    const x = 10 + r() * 490, y = 10 + r() * 490;
    g.fillStyle = r() < 0.5 ? "#2c3038" : "#e9e6dc"; g.fillRect(x, y, 6 + r() * 6, 4 + r() * 4);
  }
  g.strokeStyle = "rgba(20,22,28,0.6)"; g.lineWidth = 3; for (let y = 64; y < 512; y += 96) { g.beginPath(); g.moveTo(0, y); g.lineTo(512, y); g.stroke(); }
});
const cabinWall = () => ctex("cabinWall", 1024, 256, (g) => {
  g.fillStyle = "#ece6da"; g.fillRect(0, 0, 1024, 256);
  for (let k = 0; k < 8; k++) {
    const x = 40 + k * 128;
    g.fillStyle = "#d8d0c0"; g.beginPath(); g.roundRect(x - 6, 74, 60, 92, 26); g.fill();
    const gr = g.createLinearGradient(0, 84, 0, 156); gr.addColorStop(0, "#ffd9a0"); gr.addColorStop(1, "#ff9f6a");
    g.fillStyle = gr; g.beginPath(); g.roundRect(x, 84, 48, 72, 20); g.fill();
  }
  g.fillStyle = "#c9c0ae"; g.fillRect(0, 200, 1024, 8);
});
const seatFabric = () => ctex("seatFabric", 256, 256, (g, r) => {
  g.fillStyle = "#3d5c9a"; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 300; i++) { g.fillStyle = jit(r, "#355290", 0.15, 4, 0.1); g.fillRect(r() * 256, r() * 256, 3, 3); }
  g.fillStyle = "#e9e3d6"; g.fillRect(40, 10, 176, 46); // headrest cloth
});
const boardTex = () => ctex("departures", 1024, 256, (g) => {
  g.fillStyle = "#1c1f27"; g.fillRect(0, 0, 1024, 256);
  for (let row = 0; row < 6; row++) for (let c = 0; c < 26; c++) {
    g.fillStyle = (row + c) % 7 === 0 ? "#ffcf4a" : "#f2efe6";
    if (c === 8 || c === 9 || c === 17) continue;
    g.fillRect(24 + c * 38, 22 + row * 38, 30, 26);
  }
});
/** the check-in scale display: 0 = blank, 1 = 23 kg, 2 = 50 lb, 3 = "?" (pictograms drawn as glyphs, no captions) */
const scaleTex = (k: number) => ctex("scaleDisp" + k, 512, 256, (g) => {
  g.fillStyle = "#14261a"; g.fillRect(0, 0, 512, 256);
  g.fillStyle = "#7dff9a"; g.font = "bold 150px monospace"; g.textAlign = "center"; g.textBaseline = "middle";
  const txt = ["", "23 kg", "50 lb", "?"][k];
  g.fillText(txt, 256, 136);
});

// ---------------- helpers ----------------
const ground = (w: number, d: number, y = 0) => { const g = new THREE.PlaneGeometry(w, d); g.rotateX(-Math.PI / 2); g.translate(0, y, 0); return g; };
const tiled = (key: string, t: () => THREE.Texture, rx: number, ry: number) => lam(key, () => ({ map: rep(t(), rx, ry) }));
const solid = (key: string, col: string) => lam(key, () => ({ color: col }));
const mesh = (g: THREE.BufferGeometry, m: THREE.Material, parent: THREE.Object3D, cast = true) => {
  const o = new THREE.Mesh(g, m); o.castShadow = cast; o.receiveShadow = true; parent.add(o); return o;
};
const wheel = (b: Batch, x: number, y: number, z: number, r: number, w: number) => {
  b.add(new THREE.CylinderGeometry(r, r, w, 16).rotateZ(Math.PI / 2), solid("tyre", "#2c2b31"), new THREE.Matrix4().makeTranslation(x, y, z));
  b.add(new THREE.CylinderGeometry(r * 0.5, r * 0.5, w + 0.02, 10).rotateZ(Math.PI / 2), solid("hub", "#c3c6cc"), new THREE.Matrix4().makeTranslation(x, y, z));
};
/** simple vehicle: body box (+ cab), wheels; yaw about y; returned as a group so it can be placed */
const vehicle = (o: { len: number; w: number; h: number; col: string; cab?: string; stripe?: string; tank?: string; wheelR?: number; race?: boolean }) => {
  const grp = new THREE.Group(), b = new Batch(), L = o.len, Wd = o.w, wr = o.wheelR ?? 0.42;
  if (o.tank) {
    b.add(boxGeo(V(-Wd / 2, wr, -L / 2), V(Wd / 2, wr + 0.35, L / 2 - 2.2)), solid("chassis", "#3a3d45"));
    b.add(new THREE.CylinderGeometry(Wd * 0.48, Wd * 0.48, L - 2.6, 20).rotateX(Math.PI / 2).translate(0, wr + 0.35 + Wd * 0.48, -1.1), solid("tank" + o.tank, o.tank));
    b.add(boxGeo(V(-Wd / 2, wr, L / 2 - 2.1), V(Wd / 2, wr + 1.9, L / 2)), solid("cab" + o.cab, o.cab ?? o.col));
    b.add(boxGeo(V(-Wd / 2 - 0.01, wr + 1.15, L / 2 - 1.2), V(Wd / 2 + 0.01, wr + 1.75, L / 2 + 0.01)), solid("glass", "#33476a"));
  } else if (o.race) {
    b.add(boxGeo(V(-Wd / 2, wr * 0.6, -L / 2), V(Wd / 2, wr * 0.6 + 0.45, L / 2)), solid("race" + o.col, o.col));
    b.add(boxGeo(V(-Wd * 0.32, wr * 0.6 + 0.45, -L * 0.18), V(Wd * 0.32, wr * 0.6 + 0.85, L * 0.12)), solid("glass", "#33476a"));
    if (o.stripe) b.add(boxGeo(V(-0.18, wr * 0.6 + 0.451, -L / 2), V(0.18, wr * 0.6 + 0.46, L / 2)), solid("stripe" + o.stripe, o.stripe));
  } else {
    b.add(boxGeo(V(-Wd / 2, wr, -L / 2), V(Wd / 2, wr + o.h, L / 2)), solid("veh" + o.col, o.col));
    if (o.stripe) b.add(boxGeo(V(-Wd / 2 - 0.01, wr + o.h * 0.45, -L / 2 - 0.01), V(Wd / 2 + 0.01, wr + o.h * 0.58, L / 2 + 0.01)), solid("stripe" + o.stripe, o.stripe));
    b.add(boxGeo(V(-Wd / 2 - 0.01, wr + o.h * 0.62, L / 2 - 1.0), V(Wd / 2 + 0.01, wr + o.h * 0.88, L / 2 + 0.01)), solid("glass", "#33476a"));
  }
  for (const s of [-1, 1]) for (const z of [-L / 2 + 1.0, L / 2 - 1.0]) wheel(b, s * (Wd / 2 - 0.05), wr, z, wr, 0.3);
  b.build(grp);
  return grp;
};
const place = (parent: THREE.Object3D, o: THREE.Object3D, x: number, z: number, yaw = 0, y = 0) => { o.position.set(x, y, z); o.rotation.y = yaw; parent.add(o); return o; };
const cloudCard = (parent: THREE.Object3D, tex: THREE.Texture, x: number, y: number, z: number, w: number, flat: boolean) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w / 2), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, color: new THREE.Color(1.08, 1.08, 1.08) }));
  if (flat) m.rotation.x = -Math.PI / 2;
  m.position.set(x, y, z); m.layers.set(NOINK); m.renderOrder = -0.2; parent.add(m);
  return m;
};

export class Sets {
  groups = {} as Record<SetName, THREE.Group>;
  private seaDay: THREE.Mesh[] = []; private seaGold: THREE.Mesh[] = [];
  private screens!: THREE.MeshBasicMaterial; private screenOn: THREE.Texture; private screenOff: THREE.Texture;
  private alarms: THREE.MeshBasicMaterial[] = [];
  private display!: THREE.MeshBasicMaterial;
  private bagTag!: THREE.Object3D;
  private racers: { o: THREE.Object3D; x: number; z: number }[] = [];

  constructor(root: THREE.Object3D) {
    for (const n of ["sky", "apron", "cockpit", "cabin", "gimli", "checkin"] as SetName[]) { const g = new THREE.Group(); g.visible = false; root.add(g); this.groups[n] = g; }
    this.screenOn = screenTex(true); this.screenOff = screenTex(false);
    this.buildSky(); this.buildApron(); this.buildCockpit(); this.buildCabin(); this.buildGimli(); this.buildCheckin();
  }

  // ---- sky: a cloud sea 150 m below, scrolling past (the jet stays at the origin) ----
  private buildSky() {
    const S = this.groups.sky;
    const td = [0, 1, 2, 3].map((k) => cloudHD(k, CLOUD_DAY)), tg = [0, 1, 2, 3].map((k) => cloudHD(k, CLOUD_GOLD));
    let i = 0;
    for (let gx = -6; gx <= 6; gx++) for (let gz = -8; gz <= 8; gz++) {
      const x = gx * 140 + Math.sin(i * 12.9) * 50, z = gz * 140 + Math.cos(i * 7.3) * 50, y = -150 - (i % 5) * 8, w = 260 + (i % 4) * 60;
      this.seaDay.push(cloudCard(S, td[i % 4], x, y, z, w, true));
      this.seaGold.push(cloudCard(S, tg[i % 4], x, y, z, w, true));
      i++;
    }
    // a soft floor under the sea so gaps never show the void
    const floor = mesh(ground(4000, 4000, -175), new THREE.MeshBasicMaterial({ color: "#e9d4c8" }), S, false); floor.layers.set(NOINK);
    floor.userData.floor = true;
  }

  // ---- apron: Montreal, 1983 ----
  private buildApron() {
    const A = this.groups.apron, b = new Batch();
    b.add(ground(400, 400), tiled("asphaltT", asphalt, 40, 40));
    b.add(ground(3000, 3000, -0.05), lam("grassHDg", () => ({ map: rep(grassHD(), 300, 300) })));
    // painted lead-in line and stop bar
    b.add(ground(0.3, 120, 0.01).translate(0, 0, -20), solid("paintY", "#f2c230"));
    b.add(ground(8, 0.4, 0.01).translate(0, 0, 25.5), solid("paintY", "#f2c230"));
    // terminal: long building with a glass band, flat roof, control tower
    const [tx, , tz] = APRON.terminal;
    b.add(boxGeo(V(tx - 14, 0, tz - 110), V(tx, 14, tz + 110)), lam("terminalF", () => ({ map: rep(facadeGlass(), 6, 1) })));
    b.add(boxGeo(V(tx - 14.6, 14, tz - 110.6), V(tx + 0.6, 15.2, tz + 110.6)), solid("termRoof", "#9c968a"));
    b.add(new THREE.CylinderGeometry(3.2, 3.6, 42, 20).translate(tx - 40, 21, tz + 60), solid("tower", "#e4dccb"));
    b.add(new THREE.CylinderGeometry(6, 5, 5, 16).translate(tx - 40, 44.5, tz + 60), solid("glassT", "#40618f"));
    b.add(new THREE.CylinderGeometry(6.6, 6.6, 1.0, 16).translate(tx - 40, 47.5, tz + 60), solid("termRoof", "#9c968a"));
    // a jet bridge stub toward the left front door
    b.add(boxGeo(V(tx, 4.2, 14), V(-6, 7.0, 17)), solid("bridgeJ", "#cfcac0"));
    b.add(boxGeo(V(-8, 0, 14.5), V(-7, 4.2, 16.5)), solid("strut", "#8f939b"));
    // hangar far away + light poles
    b.add(boxGeo(V(60, 0, -180), V(160, 22, -120)), solid("hangar", "#c9c4b6"));
    for (const [x, z] of [[-30, -40], [-30, 60], [40, 70], [45, -60]]) {
      b.add(new THREE.CylinderGeometry(0.25, 0.3, 20, 8).translate(x, 10, z), solid("pole", "#9aa0a8"));
      b.add(boxGeo(V(x - 1.6, 19.5, z - 0.5), V(x + 1.6, 20.5, z + 0.5)), solid("lamp", "#e8e6dd"));
    }
    // baggage carts
    for (let k = 0; k < 3; k++) b.add(boxGeo(V(-12 - k * 3.2, 0.35, -16), V(-9.6 - k * 3.2, 1.4, -14.4)), solid("cart", "#6d7f9b"));
    b.build(A);
    // the fuel truck beside the right wing, facing aft
    place(A, vehicle({ len: 9, w: 2.5, h: 2.4, col: "#f0ede4", cab: "#d6452f", tank: "#eeeae0" }), APRON.truck[0] + 2.2, APRON.truck[2] - 2, Math.PI);
    // its fuel gauge (a round dial on the tank side, facing +x / camera): shot 4 insert
    const dial = new THREE.Mesh(new THREE.CircleGeometry(0.42, 32), new THREE.MeshBasicMaterial({ map: ctex("gaugeFace", 256, 256, (g) => {
      g.fillStyle = "#f4f1e6"; g.beginPath(); g.arc(128, 128, 124, 0, 7); g.fill();
      g.strokeStyle = "#222"; g.lineWidth = 8; g.stroke();
      g.lineWidth = 6; for (let k = 0; k <= 4; k++) { const a = Math.PI * (0.8 + 1.4 * k / 4); g.beginPath(); g.moveTo(128 + Math.cos(a) * 92, 128 + Math.sin(a) * 92); g.lineTo(128 + Math.cos(a) * 112, 128 + Math.sin(a) * 112); g.stroke(); }
      g.fillStyle = "#d6452f"; g.beginPath(); g.arc(128, 128, 92, Math.PI * 0.8, Math.PI * 1.05); g.lineTo(128, 128); g.fill();
    }) }));
    dial.position.set(APRON.truck[0] + 2.2 - 1.27, 1.95, APRON.truck[2] - 0.6); dial.rotation.y = -Math.PI / 2; A.add(dial);
    dial.name = "dial"; dial.layers.set(NOINK);
    const needle = new THREE.Mesh(new THREE.PlaneGeometry(0.05, 0.36).translate(0, 0.17, 0), new THREE.MeshBasicMaterial({ color: "#1d1d22" }));
    needle.position.set(dial.position.x - 0.01, dial.position.y, dial.position.z); needle.rotation.y = -Math.PI / 2; needle.name = "needle"; needle.layers.set(NOINK);
    A.add(needle);
    // stairs truck at the rear door
    place(A, vehicle({ len: 6, w: 2.3, h: 1.4, col: "#e8e2d2", stripe: "#d6452f" }), -9, -14, 0.2);
  }

  // ---- cockpit ----
  private buildCockpit() {
    const C = this.groups.cockpit, shell = new Batch(), b = new Batch();
    const wall = solid("cpWall", "#b9b4a8"), dark = solid("cpDark", "#3e434d"), panel = lam("cpPanel", () => ({ map: panelTex() }));
    shell.add(boxGeo(V(-1.7, -0.1, -2.2), V(1.7, 0, 1.6)), solid("cpFloor", "#5a5d66"));
    for (const s of [-1, 1]) {
      // side wall with a window opening (two boxes around the hole)
      shell.add(boxGeo(V(s * 1.7 - 0.05, 0, -2.2), V(s * 1.7 + 0.05, 1.05, 1.3)), wall);
      shell.add(boxGeo(V(s * 1.7 - 0.05, 1.6, -2.2), V(s * 1.7 + 0.05, 2.1, 1.3)), wall);
      shell.add(boxGeo(V(s * 1.7 - 0.05, 1.05, -2.2), V(s * 1.7 + 0.05, 1.6, 0.0)), wall);
    }
    shell.add(boxGeo(V(-1.7, 2.1, -2.2), V(1.7, 2.2, 1.0)), wall);
    shell.add(boxGeo(V(-1.7, 0, -2.3), V(1.7, 2.2, -2.2)), wall);
    // overhead panel sloping down to the windscreen
    shell.add(quad(V(1.5, 2.05, 0.2), V(-1.5, 2.05, 0.2), V(-1.3, 1.82, 1.25), V(1.3, 1.82, 1.25)), panel);
    // windscreen frame: sill, top, posts (the panes are open so the sky shows)
    b.add(boxGeo(V(-1.45, 1.12, 1.0), V(1.45, 1.2, 1.55)), dark);
    b.add(boxGeo(V(-1.35, 1.76, 1.2), V(1.35, 1.84, 1.36)), dark);
    for (const x of [-1.38, -0.62, 0, 0.62, 1.38]) b.add(boxGeo(V(x - 0.045, 1.2, 1.25), V(x + 0.045, 1.8, 1.45)).rotateX(-0.28).translate(0, 0.33, 0.36), dark);
    // glareshield + instrument panel + screens
    b.add(boxGeo(V(-1.4, 1.02, 0.78), V(1.4, 1.12, 1.15)), dark);
    b.add(boxGeo(V(-1.4, 0.45, 0.98), V(1.4, 1.02, 1.08)), panel);
    this.screens = new THREE.MeshBasicMaterial({ map: this.screenOn });
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(2.5, 0.62), this.screens); scr.position.set(0, 0.74, COCKPIT.panelZ + 0.02); scr.rotation.y = Math.PI; scr.layers.set(NOINK); C.add(scr);
    // center pedestal + throttles
    b.add(boxGeo(V(-0.22, 0, 0.0), V(0.22, 0.72, 0.95)), panel);
    for (const x of [-0.08, 0.08]) b.add(boxGeo(V(x - 0.025, 0.72, 0.35), V(x + 0.025, 0.92, 0.42)), solid("lever", "#d9d6cc"));
    // seats + yokes
    for (const [x] of [COCKPIT.capt, COCKPIT.fo]) {
      b.add(boxGeo(V(x - 0.3, 0.42, -0.55), V(x + 0.3, 0.55, 0.0)), solid("seat", "#4a5266"));
      b.add(boxGeo(V(x - 0.28, 0.55, -0.6), V(x + 0.28, 1.35, -0.45)), solid("seat", "#4a5266"));
      b.add(boxGeo(V(x - 0.16, 1.35, -0.6), V(x + 0.16, 1.55, -0.47)), solid("seat", "#4a5266"));
      b.add(boxGeo(V(x - 0.03, 0.3, 0.55), V(x + 0.03, 0.85, 0.62)), dark);
      b.add(new THREE.TorusGeometry(0.14, 0.022, 6, 16, Math.PI).rotateX(Math.PI).translate(x, 0.9, 0.58), dark);
    }
    // amber master-caution lights on the glareshield (one per pilot) + two red over the screens
    for (const [x, y, z] of [[0.62, 1.125, 0.9], [-0.62, 1.125, 0.9], [0.25, 1.0, 0.97], [-0.25, 1.0, 0.97]] as const) {
      const m = new THREE.MeshBasicMaterial({ color: "#3a2a12" }); this.alarms.push(m);
      const o = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.05, 0.06), m); o.position.set(x, y, z); o.layers.set(NOINK); C.add(o);
    }
    shell.build(C, false); b.build(C, true);
    // clouds outside, below the nose
    const tg = [0, 1, 2, 3].map((k) => cloudHD(k, CLOUD_GOLD));
    for (let i = 0; i < 26; i++) cloudCard(C, tg[i % 4], (i % 7 - 3) * 160 + Math.sin(i) * 40, -60 - (i % 3) * 10, 220 + Math.floor(i / 7) * 180, 260, true);
  }

  // ---- cabin ----
  private buildCabin() {
    const C = this.groups.cabin, shell = new Batch(), b = new Batch();
    const z0 = CABIN.row0 - 4, z1 = CABIN.row0 + CABIN.rows * CABIN.pitch + 4;
    shell.add(boxGeo(V(-2.5, -0.1, z0), V(2.5, 0, z1)), solid("cabFloor", "#6b5e66"));
    shell.add(boxGeo(V(-0.95, 0.001, z0), V(-1.15, 0.006, z1)), solid("aisle", "#8a3f4c"));
    shell.add(boxGeo(V(0.95, 0.001, z0), V(1.15, 0.006, z1)), solid("aisle", "#8a3f4c"));
    for (const s of [-1, 1]) {
      const wm = lam("cabWallT", () => ({ map: rep(cabinWall(), (z1 - z0) / 8, 1) }));
      shell.add(s > 0 ? quad(V(2.45, 0, z0), V(2.45, 0, z1), V(2.45, 2.0, z1), V(2.45, 2.0, z0), 1, 1) : quad(V(-2.45, 0, z1), V(-2.45, 0, z0), V(-2.45, 2.0, z0), V(-2.45, 2.0, z1), 1, 1), wm);
      // overhead bins
      b.add(boxGeo(V(s > 0 ? 1.55 : -2.45, 1.78, z0), V(s > 0 ? 2.45 : -1.55, 2.22, z1)), solid("bins", "#e3dccd"));
    }
    shell.add(boxGeo(V(-2.5, 2.3, z0), V(2.5, 2.35, z1)), solid("cabCeil", "#efe9dd"));
    b.add(boxGeo(V(-0.85, 1.85, z0), V(0.85, 2.25, z1)), solid("bins", "#e3dccd"));
    shell.add(boxGeo(V(-2.5, 0, z1), V(2.5, 2.35, z1 + 0.1)), solid("bulkhead", "#cfc6b5"));
    shell.add(boxGeo(V(-2.5, 0, z0 - 0.1), V(2.5, 2.35, z0)), solid("bulkhead", "#cfc6b5"));
    const fab = lam("seatFab", () => ({ map: seatFabric() }));
    for (let r = 0; r < CABIN.rows; r++) {
      const z = CABIN.row0 + r * CABIN.pitch;
      for (const x of CABIN.seats) {
        b.add(boxGeo(V(x - 0.23, 0.38, z), V(x + 0.23, 0.5, z + 0.48)), fab);
        b.add(boxGeo(V(x - 0.23, 0.45, z - 0.12), V(x + 0.23, 1.18, z)), fab);
      }
    }
    shell.build(C, false); b.build(C, false);
  }

  // ---- gimli: the old air base on its race day ----
  private buildGimli() {
    const G = this.groups.gimli, b = new Batch();
    b.add(ground(6000, 6000, -0.03), lam("grassHDg2", () => ({ map: rep(grassHD(), 600, 600) })));
    b.add(ground(60, 3000, 0).translate(0, 0, 0), tiled("concreteT", concrete, 6, 300));
    // faded centreline dashes and threshold bars
    for (let z = -1400; z < 1400; z += 60) b.add(ground(0.9, 30, 0.01).translate(0, 0, z), solid("paintW", "#e9e6dc"));
    for (let k = -6; k <= 6; k++) b.add(ground(1.8, 30, 0.01).translate(k * 4, 0, -1380), solid("paintW", "#e9e6dc"));
    // the drag-strip guardrail down the middle of the runway (the jet's main gear ends up straddling it)
    for (let z = GIMLI.rail0; z < GIMLI.rail1; z += 4) {
      b.add(boxGeo(V(-0.08, 0, z), V(0.08, 0.75, z + 0.16)), solid("railPost", "#8f939b"));
    }
    b.add(boxGeo(V(-0.06, 0.45, GIMLI.rail0), V(0.06, 0.72, GIMLI.rail1)), solid("rail", "#c9ccd2"));
    // tyre stacks and cones marking the road course on the runway
    for (let k = 0; k < 14; k++) {
      const z = 170 + k * 18, x = k % 2 ? 22 : -22;
      for (let n = 0; n < 3; n++) b.add(new THREE.TorusGeometry(0.42, 0.18, 8, 16).rotateX(Math.PI / 2).translate(x, 0.18 + n * 0.34, z), solid("tyre", "#2c2b31"));
    }
    for (let k = 0; k < 40; k++) b.add(new THREE.ConeGeometry(0.22, 0.6, 10).translate((k % 2 ? 1 : -1) * (12 + (k % 3)), 0.3, 150 + k * 7), solid("cone", "#f07a2a"));
    // old hangars and a water tower west of the runway
    for (const [z, w] of [[-60, 50], [20, 40], [90, 46]] as const) {
      b.add(boxGeo(V(-270, 0, z), V(-270 + w, 9, z + 34)), solid("hangarG", "#b8b2a2"));
      b.add(new THREE.CylinderGeometry(17, 17, w, 20, 1, false, 0, Math.PI).rotateZ(Math.PI / 2).translate(-270 + w / 2, 9, z + 17), solid("hangarRoof", "#8c939c"));
    }
    b.add(new THREE.CylinderGeometry(0.6, 0.6, 26, 8).translate(-240, 13, 160), solid("pole", "#9aa0a8"));
    b.add(new THREE.SphereGeometry(5, 16, 10).translate(-240, 28, 160), solid("wtower", "#d9d3c4"));
    // lake on the eastern horizon
    b.add(ground(4000, 6000, 0.02).translate(2600, 0, 0), solid("lake", "#6c8fc4"));
    // paddock: campers, tents, a little grandstand
    const [px, , pz] = GIMLI.paddock;
    for (let k = 0; k < 6; k++) b.add(boxGeo(V(px + 26 + k * 4.2, 0, pz - 40 + (k % 2) * 3), V(px + 29 + k * 4.2, 0.9, pz - 34 + (k % 2) * 3)), solid("bench", "#b28a5c"));
    for (let k = 0; k < 5; k++) {
      const x = px + 8 + k * 9, z = pz + 30;
      b.add(new THREE.ConeGeometry(2.6, 2.6, 4).rotateY(Math.PI / 4).translate(x, 1.3, z), solid("tent" + (k % 3), ["#e2453c", "#3f6fb5", "#f2c230"][k % 3]));
    }
    // flag poles
    for (const z of [pz - 20, pz + 10]) {
      b.add(new THREE.CylinderGeometry(0.06, 0.06, 7, 6).translate(px - 30, 3.5, z), solid("pole", "#9aa0a8"));
      b.add(new THREE.PlaneGeometry(1.6, 1.0).translate(px - 30 + 0.8, 6.4, z), solid("chequer", "#f4f1e6"));
    }
    // analogy field: a fence and two trees
    const [fx, , fz] = GIMLI.field;
    for (let k = -8; k <= 8; k++) b.add(boxGeo(V(fx + k * 2.5 - 0.06, 0, fz - 9), V(fx + k * 2.5 + 0.06, 1.1, fz - 8.88)), solid("fence", "#b48a5a"));
    b.add(boxGeo(V(fx - 20, 0.8, fz - 9), V(fx + 20, 0.9, fz - 8.9)), solid("fence", "#b48a5a"));
    for (const [x, z] of [[fx - 9, fz - 16], [fx + 12, fz - 20], [fx + 30, fz - 30]]) {
      b.add(new THREE.CylinderGeometry(0.35, 0.45, 4, 8).translate(x, 2, z), solid("bark", "#8f5d3b"));
      b.add(new THREE.SphereGeometry(3.2, 16, 12).translate(x, 5.8, z), solid("leaf", "#4f9a3f"));
    }
    b.build(G);
    // campers and parked cars along the paddock
    const cols = ["#f0ede4", "#efe3c4", "#e8e2d2"], stripes = ["#c8323a", "#3f6fb5", "#d98a2a"];
    for (let k = 0; k < 8; k++) place(G, vehicle({ len: 7.5, w: 2.4, h: 2.6, col: cols[k % 3], stripe: stripes[k % 3] }), px + 18 + (k % 4) * 9, pz - 18 + Math.floor(k / 4) * 14, 0.3 * (k % 2) - 0.15);
    // race cars on the course
    const rc: [number, number, string, string][] = [[-18, 240, "#d6452f", "#f4f1e6"], [-12, 262, "#2f6fd6", "#f2c230"], [15, 300, "#f2c230", "#1c1f27"], [8, 330, "#2f9a55", "#f4f1e6"], [-20, 360, "#f4f1e6", "#d6452f"]];
    for (const [x, z, c, s] of rc) this.racers.push({ o: place(G, vehicle({ len: 4.2, w: 1.8, h: 0.6, col: c, stripe: s, race: true, wheelR: 0.33 }), x, z, 0), x, z });
  }

  // ---- check-in hall ----
  private buildCheckin() {
    const K = this.groups.checkin, shell = new Batch(), b = new Batch();
    shell.add(boxGeo(V(-8, -0.1, -6), V(8, 0, 8)), lam("hallFloor", () => ({ map: rep(ctex("tiles", 256, 256, (g) => { g.fillStyle = "#d9d3c6"; g.fillRect(0, 0, 256, 256); g.fillStyle = "#c9c2b2"; g.fillRect(0, 0, 128, 128); g.fillRect(128, 128, 128, 128); }), 14, 14) })));
    shell.add(boxGeo(V(-8, 0, -6.1), V(8, 4.5, -6)), solid("hallWall", "#e9e2d2"));
    const board = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 1.05), new THREE.MeshBasicMaterial({ map: boardTex() })); board.position.set(-0.5, 3.0, -5.95); board.layers.set(NOINK); K.add(board);
    // counter, belt, scale with display, suitcase
    b.add(boxGeo(V(-2.6, 0, -0.35), V(0.4, 1.05, 0.35)), solid("counter", "#3f6fb5"));
    b.add(boxGeo(V(-2.65, 1.05, -0.4), V(0.45, 1.1, 0.4)), solid("counterTop", "#e9e2d2"));
    b.add(boxGeo(V(-2.6, 0, -2.4), V(3.0, 0.5, -1.6)), solid("belt", "#3a3d45"));
    const [sx, , sz] = CHECKIN.scale;
    b.add(boxGeo(V(sx - 0.45, 0, sz - 0.5), V(sx + 0.45, 0.16, sz + 0.5)), solid("scale", "#9aa0a8"));
    b.add(boxGeo(V(sx - 0.05, 0.16, sz - 0.45), V(sx + 0.05, 1.15, sz - 0.35)), solid("scalePost", "#5a5d66"));
    b.add(boxGeo(V(sx - 0.34, 1.12, sz - 0.48), V(sx + 0.34, 1.48, sz - 0.34)), solid("scaleHead", "#3a3d45"));
    b.add(boxGeo(V(sx - 0.32, 0.16, sz - 0.2), V(sx + 0.32, 0.86, sz + 0.24)), solid("suitcase", "#c8323a"));
    b.add(boxGeo(V(sx - 0.1, 0.86, sz - 0.03), V(sx + 0.1, 0.92, sz + 0.03)), solid("handle", "#2c2b31"));
    shell.build(K, false); b.build(K, true);
    this.display = new THREE.MeshBasicMaterial({ map: scaleTex(0) });
    const d = new THREE.Mesh(new THREE.PlaneGeometry(0.6, 0.3), this.display); d.position.set(sx, 1.3, sz - 0.335); d.layers.set(NOINK); K.add(d);
    // the luggage tag (a sliver of jet skin) hanging off the handle
    const tag = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 0.2), new THREE.MeshBasicMaterial({ map: ctex("tagSkin", 64, 128, (g) => { g.fillStyle = "#f3f1ec"; g.fillRect(0, 0, 64, 128); g.fillStyle = "#c8323a"; g.fillRect(0, 70, 64, 18); g.fillStyle = "#26304a"; g.beginPath(); g.roundRect(22, 30, 20, 26, 8); g.fill(); }), side: THREE.DoubleSide }));
    tag.position.set(sx + 0.12, 0.78, sz + 0.25); tag.layers.set(NOINK); K.add(tag); this.bagTag = tag;
  }

  /** switch the set on and pose its moving parts for shot id at frame f */
  update(set: SetName, id: number, f: number, golden: boolean) {
    const t = f / FPS;
    for (const [n, g] of Object.entries(this.groups)) g.visible = n === set;
    if (set === "sky") {
      const v = 70; // m/s past the camera (cartoon-slow so the sea reads)
      const span = 17 * 140;
      for (const [list, on] of [[this.seaDay, !golden], [this.seaGold, golden]] as const) for (const m of list) {
        m.visible = on;
        const base = m.userData.z0 ?? (m.userData.z0 = m.position.z);
        m.position.z = ((((base - v * t) % span) + span * 1.5) % span) - span / 2;
      }
    }
    if (set === "cockpit") {
      const dark = (id === 6 && f >= W.dark) || id === 8 || id === 10;
      this.screens.map = dark ? this.screenOff : this.screenOn;
      const a1 = (id === 5 && f >= W.alarm1) || id === 6, a2 = (id === 5 && f >= W.alarm2) || id === 6;
      const blink = Math.floor(f / 8) % 2 === 0;
      const sim = id === 19 && f >= W.simulator;
      this.alarms.forEach((m, i) => m.color.set((i < 2 ? (i === 0 ? a1 : a2) : a2 || sim) && (blink || i < 2) ? (i < 2 ? "#ffb52e" : "#ff3b30") : (i < 2 ? "#3a2a12" : "#3a1414")));
      if (sim) for (const m of this.alarms) m.color.set(blink ? "#ff3b30" : "#5a1414");
    }
    if (set === "apron") {
      const needle = this.groups.apron.getObjectByName("needle");
      if (needle) needle.rotation.z = -(Math.PI * 0.6) + (id === 4 ? -Math.PI * 0.55 * clamp01((f - W.half + 6) / 14) : 0) + Math.PI * 0.9;
    }
    if (set === "gimli") {
      // race day: the cars lap the course along the runway (only while the race runs, shot 14)
      for (const [i, r] of this.racers.entries()) {
        // each car passes z = 300 (the low camera of shot 14) at frame 1318 + 11 i, at 30 m/s, in lanes x 4..16
        const z = id === 14 ? 300 + 30 * (f - (1318 + i * 11)) / FPS : r.z;
        r.o.position.set(id === 14 ? 4 + (i % 3) * 5 + (i > 2 ? 1.5 : 0) : r.x, 0, z);
      }
    }
    if (set === "checkin") {
      this.display.map = scaleTex(f < W.kg23 - 2 ? 0 : f < W.lb50 - 2 ? 1 : f < W.check ? 2 : (Math.floor(f / 10) % 2 ? 1 : 2));
      this.bagTag.rotation.z = 0.15 * Math.sin(t * 2.2);
    }
  }
}
