// Export the film's per-frame data + card textures for the Blender pipeline.
// usage: node scripts/export_frames.mjs <outDir> [from] [to]
//   outDir/frames.jsonl  one JSON object per frame (see src/export/export.ts)
//   outDir/cards/<name>.png  every character / effect card texture
//   outDir/meta.json  { total, body: [w, h, yOffset] }
import { build } from "esbuild";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const out = path.resolve(process.argv[2] || "D:/gimli3d/export");
const web = path.join(out, "web");
fs.mkdirSync(path.join(out, "cards"), { recursive: true });
fs.mkdirSync(web, { recursive: true });
await build({ entryPoints: ["src/export/export.ts"], bundle: true, format: "iife", platform: "browser", outfile: path.join(web, "bundle.js"), logLevel: "warning", loader: { ".ts": "ts", ".tsx": "tsx" } });
fs.writeFileSync(path.join(web, "index.html"), '<!doctype html><meta charset="utf-8"><body><script src="bundle.js"></script></body>');

const server = http.createServer((q, r) => {
  const p = path.join(web, decodeURIComponent(q.url.split("?")[0]).replace(/^\/+/, "") || "index.html");
  if (!fs.existsSync(p)) { r.writeHead(404); r.end(); return; }
  r.writeHead(200, { "content-type": p.endsWith(".js") ? "text/javascript" : "text/html" });
  fs.createReadStream(p).pipe(r);
}).listen(8766, "127.0.0.1");

const chrome = spawn("C:/Program Files/Google/Chrome/Application/chrome.exe", ["--headless=new", "--remote-debugging-port=9333", `--user-data-dir=${path.join(out, "chrome-prof")}`, "--disable-gpu", "--no-first-run", "http://127.0.0.1:8766/index.html"], { stdio: "ignore" });
let ws = null;
for (let i = 0; i < 60 && !ws; i++) {
  await new Promise((r) => setTimeout(r, 500));
  try {
    const list = await (await fetch("http://127.0.0.1:9333/json")).json();
    const page = list.find((t) => t.type === "page" && t.url.includes("8766"));
    if (page) ws = new WebSocket(page.webSocketDebuggerUrl);
  } catch { /* not up yet */ }
}
if (!ws) throw new Error("chrome devtools not reachable");
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let seq = 0;
const pending = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const evaluate = (expression) => new Promise((resolve, reject) => {
  const id = ++seq;
  pending.set(id, (m) => (m.result?.exceptionDetails ? reject(new Error(JSON.stringify(m.result.exceptionDetails).slice(0, 2000))) : resolve(m.result?.result?.value)));
  ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { expression, returnByValue: true, awaitPromise: true } }));
});
for (let i = 0; i < 40; i++) { if (await evaluate("typeof window.exportFrame")  === "function") break; await new Promise((r) => setTimeout(r, 250)); }
const total = await evaluate("window.NEW_TOTAL");
const body = await evaluate("window.BODY");
fs.writeFileSync(path.join(out, "meta.json"), JSON.stringify({ total, body }));
const from = Number(process.argv[3] ?? 0), to = Math.min(total - 1, Number(process.argv[4] ?? total - 1));
const fd = fs.openSync(path.join(out, from === 0 && to === total - 1 ? "frames.jsonl" : `frames_${from}_${to}.jsonl`), "w");
let nCards = 0, t0 = Date.now();
for (let n = from; n <= to; n++) {
  const s = await evaluate(`window.exportFrame(${n})`);
  const d = JSON.parse(s);
  for (const c of d.cards) {
    fs.writeFileSync(path.join(out, "cards", `${c.name}.png`), Buffer.from(c.png.split(",")[1], "base64"));
    nCards++;
  }
  d.cards = d.cards.map((c) => ({ name: c.name, key: c.key }));
  fs.writeSync(fd, JSON.stringify(d) + "\n");
  if (n % 100 === 0) console.log(`frame ${n}/${to}  cards so far ${nCards}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}
fs.closeSync(fd);
console.log(`done: ${to - from + 1} frames, ${nCards} card textures -> ${out}`);
ws.close(); chrome.kill(); server.close();
process.exit(0);
