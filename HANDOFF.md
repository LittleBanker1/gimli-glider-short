# HANDOFF — "The Jet That Couldn't Count" (Gimli Glider animated short)

Last updated: 2026-11-11. Read this first in a new chat, then `D:\gimli3d\blender\AGENT_BRIEF.md`.
The user speaks Bulgarian; answer in Bulgarian.

## What the project is
A 68.6 s vertical (1080x1920, 30 fps) animated YouTube Short about the Gimli Glider (Air Canada Flight 143, 23 July 1983),
made with Claude. Started from the free skill github.com/mromidev/claude-animated-shorts (reviewed: no malicious code; it
redistributes ~1,250 frames of another channel — never put those in our videos). Style target chosen by the user:
YouTube channel **Ricks Clips** (@RicksClips3000): white-headed 2D bean characters in rich, saturated, ink-outlined 3D worlds.

## Where everything is
- **Project code (copy)**: `D:\gimli3d\studio\` = the Remotion/three.js project "shorts-studio" without node_modules
  (run `npm install` there if it is used as the working project). Original lived in a temporary session folder that is
  deleted with the old chat. Key files:
  - `shorts\gimli\SCRIPT.md` — approved English script (20 lines, sourced facts), `LOOK_STUDY.md` — measured style study
    (reference vs ours, gap list, Blender recipe, asset list, character-drawing fixes).
  - `shorts\gimli\voice\` — current voice: Kokoro-82M `af_heart` x1.4 (voice.wav, words.json, warp.json); `voice_sapi\` old.
  - `shorts\gimli\audio\mix.wav` — final soundtrack (-14 LUFS), made by `audio\gimli_mix.py shorts/gimli`.
  - `src\videos\gimli\` — story.ts (21 shots, cameras, jet poses, cue frames W), cast.ts (characters/effects staging),
    toon.ts (character drawing), sets.ts/jet.ts/world.ts (old three.js look), warp.ts (voice take -> picture frames).
  - `src\export\export.ts` + `scripts\export_frames.mjs` — exporter for Blender (per-frame cameras, jet, cards + PNGs).
  - `scripts\kokoro_voice.py`, `scripts\make_warp.py` — voice + re-timing. `audio\sigshim.py` — numpy replacement for
    scipy.signal (blocked by Windows Application Control on this PC; never change that setting).
  - `references\ricks\` — 76 reference screenshots (private study only).
  - `out\gimli\gimli_v1.mp4` (robot voice), `gimli_v2.mp4` (Kokoro voice) — the three.js versions the user found "cheap".
- **Blender rebuild**: `D:\gimli3d\` — Blender 5.3 portable `D:\tools\blender-5.3.0-windows-x64\blender.exe`;
  assets (CC0, user-approved downloads): `kenney\` (6 kits, 709 GLB), `textures\` (8 ambientCG 1K);
  `export\` (frames.jsonl for all 2057 final frames + cards\*.png, made with the CURRENT toon.ts);
  `blender\` — lib.py (toon material, sky, sun, Line Art ink, Kenney import, card planes), layout.py (set anchors in
  Blender coords), render_shot.py (renders one shot), assemble.py (crossfades + flash + ffmpeg with mix.wav), lockrun.py
  (GPU mutex — EVERY Blender/Chrome run must go through it), AGENT_BRIEF.md (full brief for builder agents),
  workflow_lookmatch.js (the multi-agent workflow script), sets\*.py + jet.py (STILL STUBS).
- Machine: Windows 11, AMD RX 9060 XT, 16 GB RAM; C: ~80 GB free, D: ~500 GB free. Python 3.12 at
  `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (use -I), ffmpeg via winget, Node 24, Chrome installed.

## GitHub
Public repo: https://github.com/LittleBanker1/gimli-glider-short (branch main; repo root = D:\gimli3d, see .gitignore for
what is left out). GitHub CLI (portable, logged in as LittleBanker1): D:\tools\gh\bin\gh.exe. In a new chat on
another machine: `git clone https://github.com/LittleBanker1/gimli-glider-short`, then re-download the Kenney kits and
ambientCG textures (names in this file and in blender/AGENT_BRIEF.md), `npm install` in studio/, and re-run the exporter.

## Status (2026-11-11)
1. DONE: script, Kokoro voice, sound mix, three.js v2 video, look study, all downloads, Blender pipeline verified end to end
   (test render of shot 3 with stub set: cameras/cards/ink correct, ~2 s per frame at 50 %).
2. NOT DONE — next step: run the multi-agent workflow (8 builders: jet, sky, apron, cockpit, cabin, gimli, checkin,
   characters; each -> independent review -> fix -> final review). It was launched twice and stopped (first by a session
   end, then by the user) before any file changed. Relaunch with the Workflow tool: `scriptPath` =
   `D:\gimli3d\blender\workflow_lookmatch.js`. STUDIO now = `D:\gimli3d\studio` (repointed 2026-11-11 in the script and
   AGENT_BRIEF.md; node_modules, tts_models and out\cmp were copied there from the old temp folder; tsc shows only the
   12 known errors in Gimli.tsx/Bridge.tsx). The full workflow (run wf_613e9c15-97e) burned a whole 5-hour window and
   ~20 % of the weekly limit in ~25 min (8 Opus agents at once) and was STOPPED by the user's choice; it left partial
   sky/apron/cockpit/gimli sets and textures in blender\tex\. REPLACED by `blender\workflow_build_lite.js` (builders
   only, Sonnet, two at a time, token-frugal rules; order characters, jet, apron, gimli, sky, cockpit, cabin, checkin),
   launched 2026-11-11 as run wf_cf7023fe-1e1. Resume in the same chat with `resumeFromRunId` if it stops.
   Reviews/fix rounds are dropped; do a cheap review later only if the budget allows.
   RESULT (all 8 done, ~50 min, ~6 % weekly): self-scores characters 6.5, jet 6.5 (shots 16-17 untested), apron 7,
   gimli 6, sky 7, cockpit 5 (pale, no sunset through windows, thin ink), cabin 5.5, checkin 7. Small sheets of each in
   render\review\. Seen by the main agent: jet nose looks like a flat grey disc head-on (shots 16-18).
   v3 build: `python -I blender\render_all.py` (re-export + chunked resumable render of all shots + white-frame re-render
   + assemble to out\gimli_v3.mp4; log render\render_all.log). Started 2026-11-11 evening.
   DONE 2026-11-12 00:37: out\gimli_v3.mp4 (68.57 s, 1080x1920, 30 fps, -14.1 LUFS, 0 missing/white renders; sky shots
   ~30 s/frame, the rest 1-3 s; whole render ~3 h). QA in out\qa_v3\ (report.md, overview.jpg = one frame per shot).
   Weak spots seen in v3: jet nose is a blunt flat grey disc that reads as an open tube (shots 16-18); cockpit shots
   5/19 pale and low-contrast; pilot close-ups 8/10 are all head (framing); shot 14 race cars small, bare foreground;
   a flat blue rectangle on the runway in shot 16. Next: cheap Sonnet fix pass on these if the user wants, then
   re-render only the affected shots (`render_all.py --skip-export --shots 16,17,18` after deleting those shot dirs).
   FIX PASS (2026-11-12, done): user asked to remove the "stars" after the crash -> removed the fxStars card (cast.ts)
   and the spiral "dazed" eyes (toon.ts FACE.dazed now shockHalf eyes); cameras of shots 8/10 pulled back (story.ts);
   Sonnet agents fixed jet.py (longer pointed white nose, no radome disc), sets/cockpit.py (warmer/darker, thicker ink;
   sky still not in view since cameras look aft), sets/gimli.py (own grandstands instead of the flat Kenney slab, debris
   boards removed, saturated race cars + foreground clutter in shot 14). Sheets: render\jetfix_final\sheet2.jpg,
   cockpitfix_final\sheet.jpg, gimlifix_final\sheet.jpg. Export re-done.
   v4 RENDER PAUSED by the user at 01:23: shots 2-10 re-rendered; 11, 12, 14-21 still to do (sky shots 1, 9, 13 are
   kept from v3 on purpose; v3 renders of the re-rendered shots are in render\v3_shots\). To continue:
   `python -I D:\gimli3d\blender\render_all.py --skip-export` (skips existing frames, assembles out\gimli_v4.mp4),
   then QA with studio\scripts\short_qa.py and deliver. Nothing committed yet.
3. After the workflow: re-export cards (`node scripts/export_frames.mjs D:/gimli3d/export` via lockrun) because toon.ts
   changes; render all 21 shots (`render_shot.py --shot N --scale 100` for N=1..21; shot table in AGENT_BRIEF.md);
   `python assemble.py D:\gimli3d\render D:\gimli3d\export <mix.wav> <out.mp4>`; QA with `scripts\short_qa.py`;
   deliver v3 to the user with the reviewers' scores.
4. Later ideas: camera framing pass (heads ~0.25 of frame width, study gap #5), maybe a male voice (am_michael etc.).

## Gotchas learned
- Render in chunks with low concurrency; GPU context loss caused white frames before. Concat with ffmpeg concat FILTER.
- Kenney downloads need the browser (signed links + bot protection — don't bypass). The STUDIO path is too long for
  unzip/Expand-Archive and for `python` path args: keep heavy assets on D:.
- Don't delete files in the user's Downloads folder (one empty .tmp from Chrome is still there; user was told).
