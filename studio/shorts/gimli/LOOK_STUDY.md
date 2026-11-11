# LOOK STUDY: Ricks Clips (reference) vs "The Jet That Couldn't Count" (gimli_v2)

Private style study, 2026-11-10. We copy the **style only** (rendering, lighting, colour, drawing construction,
camera grammar), never stories, characters, props or shots. All paths below are relative to the project root
`shorts-studio/` (ROOT) unless absolute.

## 0. Method and limits

- **Reference:** 12 shorts from @RicksClips3000 (7 newest + 5 most-viewed), 6 moments each at 1.5/6/14/24/36/50 s
  (clamped to the duration), plus two 3-frame motion triplets 0.1 s apart (QlDPMzGmYac 24.0-24.2,
  VS1Z_Q-Klt8 14.0-14.2). 76 screenshots in `references/ricks/<id>_<s>.jpg`. Captured from the browser player (video
  element pulled out of the overlay UI), nothing downloaded.
  - IDs: e9NoHjAXYIY (drivers/dashcam, 3M), QlDPMzGmYac (roller coasters, 8M), HxqtHI62otM (pink prison cell, 9.3M),
    7xS87iActkU (railroads, 27M), Mz72MuPgnGY (storm oil, 15M), 5WMQhPObNqQ (mirror horse race, 5.4M),
    ZDy3xXA2iHk (town button, 3.7M), VS1Z_Q-Klt8 (ancient jar, 33M), 0m6G8pDtzNs (job in Japan, 17M),
    eQR3pgMiUF0 (window gambling law, 15M), lnYLIWP2l-I (pirate cannonballs, 9.4M), PLe2Gu3FDuA (spear vs shield, 9.3M).
- **Limit:** signed-out stream = 360x640; captured at **337x600** (player upscale 1.2x, then screenshot 0.78x), YouTube
  compression on top. Fine texture, thin lines and mild blur are under-measured; colours, values, shapes and layout are
  reliable. To compare fairly, our frames were pushed through the same chain (1080 -> 360 box -> 432 bilinear -> 337
  bilinear) before measuring ("matched").
- **Ours:** `out/gimli/gimli_v2.mp4` at t = 2, 7, 11, 16, 21, 25, 31, 34, 38, 42, 47, 50, 55, 58, 61, 66 s ->
  `out/cmp/ours/ours_NN.jpg` (360x640). Also `out/cmp/his_*.jpg` (the skill author's bridge short, same engine).
  (`references/frames/` named in the brief does not exist; the skill author's measured reports in
  `references/reports/*.md` were read instead.)
- **Caption band** y = 0.66-0.75 of the frame height is masked out of every statistic in all three sets.
- Scripts and raw numbers: `out/cmp/look_measure/` (`measure.py`, `heads.py`, `measure.json`, `map.txt` = which
  screenshot became which file, `motion/` our motion frames).
- Definitions: Y' = Rec.709 luma of the sRGB code values (0-1). S = HSV saturation. C*/L* = CIELAB (D65).
  **ink%** = near-black pixels (Y' < 0.12 and C* < 18). **line%** = thin dark strokes (5x5 black-top-hat > 0.22 and
  Y' < 0.40). **edge%** = Sobel gradient > 0.10 (proxy for detail/texture density). **local contrast** = std of
  (Y' minus 9x9 box blur). **soft share** = share of 16x16 blocks with contrast >= 0.15 whose edges are blurred
  (max|Laplacian|/contrast < 0.35); the background-blur proxy.

Contact sheets (reference on top, ours below), all 1620x992:
- `out/cmp/look_sheet1_characters.jpg` (character shots)
- `out/cmp/look_sheet2_exteriors.jpg` (exteriors, day and golden)
- `out/cmp/look_sheet3_mood.jpg` (night/interior/practical lighting vs our golden shots + 2 bridge frames)
- `out/cmp/look_zoom_ref_ink.jpg` (2x nearest-neighbour crops: reference heads, outlines, world ink)
- `out/cmp/look_ours_overview.jpg` (all 16 of our frames + the 6 bridge frames)

---

## 1. The reference look

### 1.1 Numbers (medians of per-frame values; IQR in brackets)

| metric | ref all (n=72) | ref day exterior (16) | ref night/dusk (12) | ref interior (16) |
|---|---|---|---|---|
| Y' p5 | **0.145** (0.10-0.23) | 0.243 | 0.102 | 0.134 |
| Y' p50 | **0.438** (0.31-0.58) | 0.573 | 0.277 | 0.446 |
| Y' p95 | **0.836** (0.71-0.92) | 0.871 | 0.693 | 0.902 |
| Y' std | 0.199 | 0.175 | 0.193 | 0.237 |
| HSV S p50 | **0.438** (0.33-0.58) | 0.478 | 0.622 | 0.373 |
| HSV S p90 | 0.748 | | | |
| C*ab lit p50 (L* 40-85) | **30.7** (19.7-45.2) | 37.9 | 37.0 | 22.3 |
| local contrast | **0.069** (0.055-0.085) | 0.068 | 0.053 | 0.085 |
| edge% (detail) | **7.0 %** (4.8-9.5) | 7.0 | 4.2 | 9.6 |
| line% (thin ink strokes) | **1.45 %** (0.9-2.3) | 1.9 | 1.0 | 2.2 |
| ink% (near-black area) | 1.4 % (0.25-3.6) | 0.3 | 2.3 | 2.9 |
| dark non-ink "shadow" share (Y' .08-.30, C* >= 8) | 0.17 | 0.07 | 0.55 | 0.16 |
| highlight share (Y' > 0.75) | 0.09 | 0.17 | 0.03 | 0.13 |
| soft share (blur) | **0.008** (0-0.027) | 0.023 | 0.009 | 0.009 |

- **Value structure:** a full range in almost every frame: real darks (p5 0.10-0.24, never crushed: darkest cores are
  coloured navy/maroon), bright clean whites (heads, lit walls), mids around 0.44. Night and interior shots are
  common (28 of 72 frames), so the channel as a whole is mid-dark, not high-key.
- **Pooled palette** (k-means, share of pixels): dark navy-plum #2e2b39 14 %, near-white #e1dde1 13 % (heads, lit
  walls), blue-grey #828696 12 %, deep indigo #2c356b 10 %, tan wood #9c7c63 10 %, sky blue #739ee4 9 %,
  dark brown #5c2e21 9 %, cobalt #3054cf 7 %, warm orange #e6a548 6 %, grass green #609835 5 %, rust #a94a1a 4 %,
  magenta-pink #dd4f9c 2 %.
- **Hue mix** (saturation-weighted, S > 0.25): red 10 %, orange **28 %**, yellow 3 %, chartreuse 5 %, green 1 %,
  cyan 1 %, azure **22 %**, blue **20 %**, violet 3 %, magenta 1 %, rose 4 %. Warm/cool split ≈ 45/50: every frame has
  a warm-vs-blue contrast (warm lit object vs blue ambient or blue sky).
- **Skies** (n = 42 frames with > 12 % sky): top median Y' 0.41, horizon 0.56, top S 0.54. Day examples
  (top -> horizon): #3058ba -> #3d69ce, #2b71dc -> #3f9afa, #3f78f6 -> #73a9fe, #376ac6 -> #477ad8,
  #4a77cc -> #84aae6, #668bcc -> #98b5dc. Night: #253368 -> #1e3379, #1d2eba -> #5359c5, #0c1030 -> #575b81.
  Sunset/dusk: #46286c -> #8a4e7d (violet top, rose band), #392444 -> #7a4c5e. Clouds: white cumulus with soft
  blue-grey undersides, often with a thin ink contour (painterly-cartoon, not photo).
- **Shadow colour** (dark non-ink pixels): median a* +13.5, b* -2.3, saturation-weighted hue ≈ 230° (blue) overall;
  day exteriors lean maroon-violet (#3d3649, #5a261f), night/interior lean blue (#213892, #24385b, #2c3a6b). Shadows
  are coloured and fairly light, never grey or black.
- **Head colour** (sampled): lit #fefaf7 / #ffffff / #fcf9fa / #fffff9; shaded crescent #e4dde6 (lavender grey,
  ratio ≈ 0.90/0.88/0.93). **Character outline cores**: #00030b, #07070e, #0a081a, #1e181f (near-black navy-plum).
  **World ink cores** are dark but tinted by the surface: #2a1515, #2e3140, #0f1327, #482b1a.
- **Outline width on heads** (scanlines through 5 heads): 1.6-6 % of head width on the same head, thick side
  ≈ 4.5 % W, thin side ≈ 2 % W, thick/thin ≈ 2.5-3.5 (confirms characters.md: 5 % W, 3:1, heavy at the bottom/shadow
  side).
- **Characters in frame** (eyeballed on all 72 frames): a readable character in **49/72 = 68 %**; the rest are
  establishing/insert shots of the world or props. Main-character head width as a fraction of the frame width:
  median **0.25**, p10 0.15, p25 0.17, p75 0.32, p90 0.38, max 0.68 (one close-up); never below 0.10 when a character
  is the subject, only 1 of 49 above 0.6. Typical shot: medium shot, 2-4 characters, whole head + torso + often legs
  visible, environment visible around them.
- **Motion** (phase correlation over the top 60 % of the frame, px at 337 wide): QlDPMzGmYac 24.0 -> 24.2: (-1,-6),
  (-1,-5) per 0.1 s = ~2 px/frame = **~6 px/frame at 1080p** slow continuous drift; VS1Z_Q-Klt8 14.0 -> 14.2:
  (0,10),(0,11) = ~3.5 px/frame = **~11 px/frame at 1080p** crane. Camera keeps moving during holds.

### 1.2 In words

**World assets.** Full 3D environments built from *asset-store style* models, densely dressed. Two families are mixed,
sometimes in one frame:
1. *Cartoon-painted* sets (prison block, office, Japanese alley, casino, castle hall, horse-race town): simple
   geometry, flat/hand-painted textures with drawn detail (brick lines, wood planks, tile grout, posters, labels,
   signs with text), dark ink outlines on edges, light gradients painted on walls.
2. *Stylised-realistic* sets (suburban house and lawn, highway with cars, roller-coaster park, railway): PBR-ish
   models with real textures (grass blades, asphalt, clapboard, chrome, glass), no ink, smooth lighting with AO.
   Even these read as "cartoon" because the sky, colours and characters are cartoon.
- **Density:** every frame is full. Typical exterior: 15-40 distinct objects (trees, poles + wires, birds, cars,
  fences, flags, buildings with signage, mountains, castle, crowds). Typical interior: 10-25 props (tables, stools,
  posters, shelves with products, lamps, pipes, AC units, crates, plants, bottles, cat). Surfaces always carry
  texture or pattern (planks, tiles, bricks, carpet patterns, wallpaper). Measured: edge density 7 %, local contrast
  0.069.
- **Composition in depth:** foreground occluder (desk edge, bench, cannon, banner, railing) + characters in the middle
  + a detailed background (street through a window, town, mountains) + sky. Background is usually *sharp* (soft share
  0.8 %); blur is used sparingly, mostly on a near foreground object.
- **Terrain/foliage:** stylised trees (round canopies, clumps), textured grass with colour variation, dirt roads with
  track lines, flowers as small colour accents (red poppies, blue cornflowers), cliffs with painted strata.

**Lighting.**
- Day: high sun, crisp but not black shadows; deep cobalt sky; warm wood/orange vs blue. Characters lit almost
  white.
- Night and interiors are a major mode: **dark blue/indigo ambient + warm practical lights** (hanging bulb,
  window, desk lamp, candle, street lamps, glowing house windows, string lights) with **volumetric light shafts**
  (prison window, alley lamp, sunbeam in the betting hall), **bloom/glow** around every light, light pools on floors and
  on characters, sun-star glints. Coloured light tints characters (pink cell -> pink, blue night -> blue-grey heads,
  orange lamp -> warm rim).
- Sunset: violet sky, orange-lit objects (ship sails glowing orange), violet-blue water/shadows. Golden is an accent
  on objects, not a haze over the whole frame.
- AO: soft contact darkening under props and in corners on the realistic assets; cartoon assets rely on ink +
  painted gradients.
- Rim light: occasional warm rim on characters/objects from practicals; no systematic rim.

**Outlines.**
- Characters: always outlined, near-black navy-plum, ~4.5 % of head width on the heavy side, thick-thin, round
  joins.
- World: on cartoon assets, ink on silhouettes, depth jumps and convex creases, ~1.5-2 px at 337 wide
  (≈ 4-6 px at 1080), often tinted dark (brown on wood, navy on blue walls); plus *painted* lines in textures
  (hatching on the gold button, plank seams, brick joints). On realistic assets: none. Whole-frame line% 1.45 %
  (ours 0.31 %).

**Characters** (`look_zoom_ref_ink.jpg`, `look_sheet1_characters.jpg`):
- **Head:** big, **white** (#fefaf7), a slightly irregular round: often a bit wider than tall (bun/"mochi"
  shape, H/W ≈ 0.85-0.95), sometimes egg/lumpy, slightly tilted; a soft **lavender-grey crescent** (#e4dde6) on the
  side away from the light, hardly any other shading. Outline thick-thin, heavy at the bottom.
- **Face:** solid black vertical-oval eyes (≈ 0.08-0.10 W wide, 0.12-0.15 W tall) or lidded half-eyes / happy arcs;
  thick tapered brows that do most of the acting; mouths are big when open (toothy grin with drawn teeth boxes,
  0.35-0.45 W wide), small dashes when neutral; moustaches as solid shapes; sweat drops, glasses, freckles as
  extra marks. No nose in front view, no blush.
- **Hair / hats:** big readable silhouettes that sit low on the head and break the head contour (caps with panel
  seams and stitching, chef hat with pleats, police caps with badge and glossy highlight, crowns, bicorne with
  cockade, curly orange hair as lumps). Each has its own shading (lit/shade + a highlight) and inner detail lines.
- **Body:** bean/capsule torso ≈ 0.7-0.95 head widths wide, **shaded** with a clear gradient (lit side to shadow side
  ≈ 1.0 -> 0.6) and **clothing detail** (overalls with pocket and dashed stitching, bow tie, suspenders, tie, uniform
  buttons and epaulettes, armour scales, name badges). Legs and arms are thin dark strokes (≈ 0.05 W), hands are ink
  dots, feet short strokes. Body total ≈ 3.3-3.6 head heights. Poses asymmetric; props held up to the camera.
- **Lit by the scene** (tinted by local light, cast ground shadows), but heads stay near-white.

**Camera.** Mostly eye-level medium shots at a normal-to-wide lens; frequent top-down/high angles for "map" shots
(circular town, ship from above, pendulum), POV shots (dashboard, cannon), low angles on tall things (ladder on a
wall). Moves are continuous: slow push/drift during holds, cranes and follows for transitions (measured 6-11
px/frame at 1080p). DOF light and rare.

**Grade.** Saturated but not neon; clean whites (p95 0.84-0.92), lifted coloured darks, strong blue component in
most frames, warm accents. No grain, no haze filter. Mild vignette in night shots.

**Text.** One burned-in word at a time, white heavy rounded sans with a thin black outline and a soft shadow, centred
at ≈ 0.70 of frame height. (Our rule: no captions. Note that the band they occupy is where our action often sits; if
captions are ever added, keep faces out of y = 0.65-0.76.)

---

## 2. Our look (gimli_v2) in numbers

| metric | ours all (n=16, matched) | ours day (07,11,16,38,58,66) | ours golden ext (02,34,42,47,50,55) | ours golden int (21,25,31,61) | ref all | bridge his_* (6) |
|---|---|---|---|---|---|---|
| Y' p5 | 0.199 | 0.180 | **0.392** | 0.058 | 0.145 | 0.050 |
| Y' p50 | **0.602** | 0.660 | 0.685 | 0.425 | 0.438 | 0.507 |
| Y' p95 | 0.858 | 0.919 | 0.858 | 0.785 | 0.836 | 0.854 |
| Y' std | 0.182 | 0.208 | 0.158 | 0.261 | 0.199 | 0.252 |
| HSV S p50 | 0.480 | **0.149** | 0.480 | 0.778 | 0.438 | 0.499 |
| C* lit p50 | 38.4 | **15.0** | 42.6 | 40.6 | 30.7 | 36.3 |
| local contrast | **0.038** | 0.050 | **0.030** | 0.035 | 0.069 | 0.092 |
| edge% | **2.3 %** | 4.4 | **1.5** | 2.3 | 7.0 | 12.5 |
| line% | **0.31 %** | 0.72 | 0.27 | 0.12 | 1.45 | 2.1 |
| ink% | 0.6 % | 0.7 | 0.05 | **10.1** | 1.4 | 8.7 |
| shadow share | 0.065 | 0.118 | **0.019** | 0.249 | 0.171 | 0.171 |
| highlight share | **0.234** | 0.219 | 0.354 | 0.096 | 0.089 | 0.110 |
| soft share (blur) | **0.249** | 0.360 | 0.033 | **0.553** | 0.008 | 0.179 |

- **Palette** (k-means): peach #f4c79a 13 %, grey #a4a3ae 13 %, ochre #c57f22 10 %, olive #788b02 10 %, salmon
  #d7947c 8 %, cream #ebe2d7 8 %, slate #5a6392 8 %, light orange #fcb87f 8 %, navy-black #131334 8 %, sky #71abe5
  6 %, dark brown #361d0b 6 %, red #da0a1c 2 %.
- **Hue mix:** red 8, orange **48**, yellow **15**, chartreuse 6, azure 13, blue 8, violet 1 % -> one warm note;
  the reference has 42 % azure+blue, we have 21 %.
- **Skies:** top median Y' 0.61, horizon 0.78, top S 0.40. Golden (11 of 21 shots): #e0a785 -> #fecc97,
  #ddaa91 -> #fecf8f, #c68181 -> #feae75 (peach/salmon, the same colour as the haze and the ground). Day: #529bde ->
  #cadff3, #75ade1 -> #c9dbf6 (pale).
- **Characters in frame:** readable character in 11/16 frames, but head width is bimodal: median 0.17, **36 % of them
  below 0.10** (tiny figures in wide golden fields: 11, 38, 47, 55) and **18 % above 0.6** (ours_31 0.85, ours_61
  0.95: the head fills and is cut by the frame). Reference: 0 % below 0.10, 2 % above 0.6.
- **Heads render tan/orange** (SKIN #ffe2c2 x golden charTint [1, .78, .56] applied at TINT_K 0.55 in cardshade.ts, plus the orange fog/grade) instead of white; in golden interiors the
  faces are #c57f22-ish.
- **Motion:** t = 16 s static (0,0)/(0,0); 38 s ≈ static; 50 s 12 then 23 px per 0.1 s at 337 (accelerating snap).
- **In words:** big empty planes (grey apron, flat green field, peach cloud floor), a few large simple objects
  (the jet, a terminal box with a window texture, a light mast), almost no small props, no signage, no texture
  detail; one golden haze over everything (fog #efb489, peach sky, orange-tinted characters) so there are no darks,
  no light pools and no blue counterpoint; heavy DOF/lens blur in close shots and interiors; interiors (cockpit,
  cabin) are dark brown blocks with blurred rows of heads; world ink is almost absent. The bridge short (his_*) is
  better mainly because it has dense repeating detail (planks, chains, brick facades, many soldiers: edge% 12.5,
  local contrast 0.092) and a blue sky, not because of different technology.

---

## 3. Gap list, ranked by visual impact (each with a concrete fix)

1. **Empty, low-detail worlds** (edge% 2.3 vs 7.0, local contrast 0.038 vs 0.069, golden exteriors 1.5 %).
   *Fix:* dress every set to 15-40 objects per exterior frame and 10-25 per interior frame (list per set in 4.5);
   every large surface gets a texture with readable detail at 1080p (planks, tiles, panel lines, markings, grass
   variation, stains, signage); add a foreground occluder in at least half the shots. Acceptance: matched edge% ≥ 5,
   local contrast ≥ 0.06 on every non-sky shot.
2. **One-note golden haze** (11/21 shots golden; golden exterior p5 0.39, local contrast 0.030, highlight share 0.35,
   48 % orange hues). *Fix:* lighting by story beat with real darks: day = cobalt sky + warm sun; sunset = **violet
   sky + orange-lit objects + violet-blue shadows** (lit/shade contrast ≥ 2:1, Y' p5 ≤ 0.15); cockpit after the
   engines quit = **dusk/night blue ambient + warm instrument glow + practicals**. Remove the distance fog as a colour
   wash (fog only beyond ~60 % of the far plane, ≤ 25 % mix). Target per frame: Y' p5 0.10-0.25, p50 0.35-0.58,
   hue mix ≥ 30 % azure/blue.
3. **Heads are tan/orange, not white.** Reference heads are #fefaf7 lit / #e4dde6 shade in every light. *Fix:* white
   head fill, lavender crescent, card light tint capped so head luma stays ≥ 0.85 (5.1, 4.6).
4. **Over-blur** (soft share 0.25 vs 0.008; interiors 0.55; tiny figures in golden fields are blurred). *Fix:* DOF off by
   default; only for close-ups and only on far background or a near foreground occluder; max background CoC ≈ 6 px
   at 1080. Backgrounds must stay readable: they carry half the comedy in the reference.
5. **Framing extremes** (head width < 0.10 W in 36 % of character frames, > 0.6 W in 18 %). *Fix:* default medium
   shot with head width 0.17-0.32 W, 2-4 characters, head + torso (+ legs) and set visible; close-up max 0.65 W with
   the whole head and the hat inside the frame; wide shots that must show tiny figures use a top-down/high angle or
   add a nearer character in the foreground.
6. **No world ink** (line% 0.31 vs 1.45; ours cards supply most of it). *Fix:* Line Art/Freestyle on all cartoon
   assets: silhouettes, creases > ~40° (crease angle ≈ 140°), depth jumps, contacts; ≈ 3-4 px at 1080 constant
   screen width, near-black tinted (#1a1420 base, multiplied toward the surface colour 20-30 %); plus painted lines
   in textures.
7. **Day colours grey and pale** (day S p50 0.15 vs 0.48, C* 15 vs 38; sky top #529bde vs ref #3058ba-#3f78f6).
   *Fix:* saturated albedos (apron concrete with warm/cool patches and bright yellow markings, red/white service
   vehicles, green grass strips, blue terminal glass), sky stops in 4.4.
8. **No light effects.** *Fix:* emissive windows, lamps, screens, sun disc; volumetric shafts through windows
   (cabin windows at sunset, cockpit windscreen, hangar door, check-in skylights); bloom threshold ≈ 0.9 on
   emissives only; sparkles/glints on chrome.
9. **Character bodies too plain** (flat uniform torso + 4 buttons; plain helmet hair). *Fix:* clothing-detail layer,
   stronger torso gradient + rim, hair/hat shapes with inner lines and highlights (section 5).
10. **Camera mostly static or snapping** (our 16 s and 38 s holds: 0 px/frame; 50 s: a 23 px/0.1 s snap). *Fix:*
    continuous slow drift/push during holds (≈ 3-6 px/frame at 1080) and smooth cranes/follows for transitions
    (10-15 px/frame peak, ease-in-out over ~20 frames), as in motion.md.

---

## 4. Blender rebuild (Blender 4.2+ / EEVEE "Next")

### 4.1 Shading: soft toon on the world

Use one node group for all world materials ("ToonSurf"):
`Diffuse BSDF (albedo, roughness 1)` -> `Shader to RGB` -> `RGB to BW` -> `ColorRamp` (ease, 3 stops) -> factor of a
`Mix (Color)` between `albedo x ShadowTint` and `albedo x LitTint`, + `Ambient Occlusion` node (distance 0.3-0.5 m,
multiply 0.85-1.0 into the result) -> `Emission` (strength 1) -> Material Output.
- Ramp stops (on light intensity): 0.00-0.30 shadow, 0.30-0.45 soft transition (ease), > 0.45 lit. Not a hard cel:
  the reference terminator is soft on realistic assets and only slightly hard on cartoon ones.
- **ShadowTint per light preset** (multiplier on albedo, display-referred because the output goes through Standard):
  day (0.55, 0.50, 0.62) (warm-violet, shade/lit Y ≈ 0.5, as lighting.md measured); sunset (0.32, 0.30, 0.62)
  (violet-blue, B > R); night (0.22, 0.26, 0.55) with practical lights adding warm on top; interior day (0.62, 0.60,
  0.72). LitTint: day (1.0, 0.98, 0.94); sunset (1.15, 0.85, 0.60); night (0.55, 0.62, 0.95) moonlight.
- Practical lights (point/area/spot) are added *after* the ramp (second Shader-to-RGB branch from a Diffuse that only
  sees the practicals via light linking, or simply let them push the ramp input) so their pools stay warm and soft.
- Metals (chrome trim, cockpit bezels, jet skin): add a `Glossy` -> Shader to RGB -> ramp with a hard stop at 0.8 to
  get one painted highlight band.
- Realistic-family assets (vehicles, terminal glass) may keep Principled BSDF with lowered roughness contrast; the
  mix of toon and semi-realistic assets is part of the reference look.

### 4.2 Ink outlines

- **Primary: Grease Pencil Line Art** (Object > Add > Grease Pencil > Collection Line Art) on a `World_Ink` collection
  (all set geometry, not the cards, not sky, not clouds' interiors). Edge types: Contour, Silhouette, Crease (crease
  threshold ≈ 140°, i.e. edges sharper than ~40°), Intersection, Material borders (only where a material change should
  read as a line), Edge marks for hand-picked lines. Occlusion on. Colour #1a1420, opacity 1. Thickness tuned on a
  1080x1920 test render to **3-4 px near, ≥ 2 px far** (constant screen width; outlines.md measured 3.1/2.8/2.2 px
  near/mid/far at 1080). Chaining: "Chain: Geometry space", smooth tolerance small; keep "Overlapping edges as
  contour".
- **Fallback: Freestyle** (Render Properties > Freestyle, works with EEVEE): Line Thickness Mode Absolute, 3.0 px;
  line set selection by Visibility + Edge Types (Silhouette, Border, Crease 140°, Contour, External Contour,
  Material Boundary), exclude the `Cards` collection; colour #1a1420; Thickness modifier "Distance from Camera" 1.0 ->
  0.65 between 5 m and 80 m. Freestyle gives exact pixel widths but renders slower.
- Tint: put the lines on a view layer / GP layer with blend "Multiply" at 0.8-0.9 so they pick up 10-20 % of the
  surface hue, matching the tinted world-ink cores (#2a1515 on wood, #2e3140 on blue walls).
- Painted lines stay in textures (plank seams, tiles, panel lines, rivets) at 3-5 px at 1080, soft-ish, tinted dark.
- Lines are rendered before DOF (GP objects are depth-of-field aware in EEVEE when the camera DOF is on); keep DOF
  rare anyway.

### 4.3 Colour management and post

- **View transform: Standard**, Look: None, exposure 0, gamma 1, display sRGB. Reason: the toon node group outputs
  display colours directly (emission through Standard = what you paint), whites stay #fefaf7, and saturated primaries
  are not desaturated. AgX (default in 4.x) compresses and desaturates bright saturated colours, which pushes exactly
  toward our current dull look; if AgX is used anyway, use the "Punchy" look and re-check head luma ≥ 0.9.
- Compositor: `Glare` node type **Bloom** (4.2+; EEVEE's old bloom checkbox is gone) on emissives only (threshold
  ≈ 0.9-1.0, size 6-7, mix ≈ -0.5), `Ellipse Mask` vignette (corners x0.86 day, x0.6-0.7 night; grade.md), no grain,
  no global haze. Optional subtle `Hue Correct` to push shadows toward the preset ShadowTint.

### 4.4 World lighting, sky and HDRI

- Camera-visible sky: World shader `Light Path: Is Camera Ray` mixes a **painted gradient** (Gradient Texture on the
  view vector's Z -> ColorRamp) for the camera and a **flat low ambient** for lighting:
  - day sky stops (elevation): 0° #a9c8f2, 5° #79a8ef, 12° #4f86e8, 25° #3366d6, 45° #2a55c4 (ref tops #3058ba-#3f78f6,
    horizon #3f9afa-#9acdfe); ambient #8fa6dc strength 0.35.
  - sunset: 0° #ffb060, 3° #f08a6a, 8° #a8608a, 16° #5e3f86, 35° #33285e (ref #46286c top -> #8a4e7d band); ambient
    #5a4a8c strength 0.4; sun disc + glow sprite on the horizon.
  - night/dusk: 0° #5359c5, 10° #2c3a8f, 30° #1d2560; ambient #2c3a8f strength 0.5; moon + stars.
- Sun lamp: angle 1.5-3° (crisp but soft-edged shadows, lighting.md: 3-12 px edges at 720p); day el 45-55°, side-back
  (az ≈ 50-75° from the view axis); sunset el 5-10°, **backlight** (az 0-40°), long shadows toward camera.
- HDRI: optional, low strength (0.2-0.4), only for reflections on chrome/glass: Poly Haven (CC0) outdoor clear-sky
  or sunset HDRIs; never as the visible background. The built-in Sky Texture (Nishita) is an alternative for the
  ambient but its colours are too realistic for the visible sky.
- Volumetrics: World Volume Scatter density 0.002-0.006 (anisotropy 0.6) only in shots with shafts; or a local
  cube with Principled Volume around the shaft (cheaper, controllable).
- Clouds (sky set): modelled stylised cumulus (metaballs or remeshed spheres + Displace with a large-scale noise),
  three-tone toon (day lit #fbf8f1, mid #e1e5f3, shade #c3cbe9; sunset lit #ffd2a8, mid #f2a08f, shade #a98fc4),
  Line Art silhouette only.

### 4.5 Assets per set (free CC0 sources, list only; check each licence page before use)

Sources (all CC0 unless noted): **Poly Haven** (polyhaven.com: HDRIs, PBR textures, ~some props/furniture),
**ambientCG** (ambientcg.com: PBR textures: concrete, asphalt, tiles, carpet, fabric, metal, painted plaster, grass),
**Kenney** (kenney.nl: low-poly kits incl. City Kit [roads/commercial/suburban/industrial], Car Kit, Racing Kit,
Furniture Kit, Nature Kit), **Quaternius** (quaternius.com: stylised nature/trees/rocks, vehicles, buildings, props),
**Poly Pizza** (poly.pizza: aggregator, *mixed CC0 and CC-BY*, filter by licence), **OpenGameArt** (mixed licences,
check). Textures from ambientCG/Poly Haven should be simplified for the cartoon family (posterise to 3-5 values,
raise saturation, paint lines on top) rather than used photoreal.

| set (shots) | must-have assets | where |
|---|---|---|
| **Sky / cloud sea** (1, 9, 13) | 767 exterior (model in-house: no reliable CC0 767; fuselage = beveled cylinder, wings/tail from extruded profiles, engines as nacelles, painted livery texture with windows/door outlines, ink on silhouette + panel lines in texture); 8-15 cumulus clusters at 3 depths; sun disc; contrails optional | own model; clouds own (metaballs) |
| **Montreal apron, 1983** (2-4, 18, 20) | terminal with concrete fins + blue glass curtain wall + signage band, jet bridge or air stairs, fuel truck, baggage tug + 3-4 carts with suitcases, GPU cart, belt loader, cones, wheel chocks, apron markings (yellow lead-in line, stop bar, numbers), light masts, chain-link fence, grass strip, distant hangar + control tower, a few period cars/vans (1980s boxy), ground crew cards | Kenney City Kit (Commercial/Industrial) + Car Kit for vehicles (repaint 1983 colours), Quaternius vehicles/props, ambientCG Concrete/Asphalt/PaintedMetal, own: fuel truck/tug from primitives |
| **767 cockpit** (5, 6, 8, 10, 19) | panel with EFIS screens (on/off textures exist in sets.ts), standby round gauges (bezels + painted dials), glareshield, overhead panel with switch arrays (Geometry Nodes instancing), yokes, throttle quadrant, two seats (leather), side windows, windscreen frames with the sky/sunset visible outside, checklist clipboards, coffee cup | own model (boxes + bevel + instancing), ambientCG Leather/Fabric/PaintedMetal, gauge faces painted as textures; warm instrument glow emissives |
| **Cabin** (7) | seat model x array (3-2-3 or 2-3-2 rows), overhead bins, window row with sunset shafts, carpet aisle with pattern, galley curtain, reading lights, seat-back pockets, passengers as cards (several per row), a few props (newspaper, cups) | own seat model + Array modifier, Kenney Furniture Kit for galley bits, ambientCG Carpet/Fabric |
| **Gimli airfield / race track** (11, 14-17) | cracked runway concrete with weeds and faded markings, drag-strip barriers (concrete jersey + guard rail), tyre stacks, start tree/lights, flags/banners, race cars + tow trucks + trailers + campers, families on lawn chairs, coolers, tents/awnings, old hangar and control tower (decommissioned look), prairie grass with flowers, poplar windbreak rows, distant farm/silos, fire extinguishers (shot 17) | Kenney Racing Kit (barriers, tyres, flags, pit buildings) + Car Kit, Quaternius nature (trees, bushes, grass clumps, rocks), ambientCG Concrete (cracked) + Grass, Poly Haven grass/ground textures |
| **Analogy field** (12) | open meadow with fence, a few trees, rocks, a paper plane prop, a rock prop, flowers; hill line and a few clouds | Quaternius nature, Kenney Nature Kit |
| **Check-in hall** (21) | counters with baggage scale + glowing kg/lb display, queue stanchions with belts, departure board (emissive), luggage of many colours, signage, tiled floor with reflections, big windows with a jet outside, plants, benches, trash bins, ceiling lights | Kenney Furniture Kit + City Kit interior bits, Poly Haven furniture where available, ambientCG Tiles/Terrazzo/PaintedPlaster, own counters/board |

### 4.6 2D character cards

- **Image planes with alpha** (File > Import > Images as Planes, built into 4.2+), not Grease Pencil: our drawing system
  is `toon.ts` (Canvas2D, design space 600x1000, soles at y = 975). Export every needed drawing (pose x expression x
  blink x walk phase) to PNG (premultiplied off, straight alpha) at **2x design = 1200x2000 px**; a headless page that
  imports `toon.ts` and dumps canvases is the simplest route. Animate by swapping textures (image sequence on the
  Image Texture node, frame offset keyed) or by keyed visibility of pre-built planes.
- Placement: plane origin at the soles, `Locked Track` (or `Damped Track` with Z locked) to the camera = yaw-only
  billboard; scale so 1 design unit = 1.6 m / 975.
- Material ("CardLit"): `Image Texture` -> colour x `CardTint` -> `Emission` (strength 1), alpha from the texture
  (Render Method: Dithered; or Blended for soft edges), Backface culling off. CardTint = mix(white, preset light
  colour, 0.25) x side gradient (Gradient Texture across the plane, lit side 1.0 -> far side 0.86-0.90, lavender
  (0.92, 0.90, 0.96)), practical light pools via a light-sampled term (a Diffuse -> Shader to RGB branch, clamped
  to [0.85, 1.15]) so heads never drop below luma 0.85 and never go orange.
- Shadows: material "Transparent Shadows" on so the alpha cuts the shadow; day = soft contact blob plane under the
  feet (multiply, 0.5 W x 0.06 W, alpha 0.3, blurred texture), sunset = cast card shadows on.
- Exclude cards from Line Art/Freestyle (they carry their own drawn outline). Put them in a `Cards` collection.

### 4.7 Camera

- Lens 28-35 mm (sensor fit Auto, 36 mm on the long side) for medium shots, 50 mm for close-ups, 18-24 mm for
  interiors/top-downs. Eye height ≈ 0.8 x character height (depth.md), horizon ≈ 0.45 of frame height.
- DOF: off by default; close-ups f/2.8-4 at 50 mm focused on the head; test that background stays readable
  (CoC ≤ 6 px at 1080).
- Motion: keyed with Bezier ease-in-out; holds keep a 1-3 %/s push; transitions are follows/cranes (10-15 px/frame
  peak at 1080), motion blur on.

### 4.8 Render settings (1080x1920, 30 fps)

- Engine EEVEE (4.2+). Resolution 1080 x 1920, 100 %, frame rate 30, frame range 0-2056 (68.6 s).
- Sampling: render 64 (32 is acceptable for previews); Film filter 1.50 px; Clamp off.
- Shadows: resolution limit 1 px, rays 1-2, steps 6, sun angle 2°; light threshold 0.01.
- Raytracing on, method Screen-Trace, resolution 1/2, Fast GI (Approx.) on for bounce in interiors; Horizon scan AO
  distance 0.4 m.
- Volumes: only in shafted shots (tile size 8, samples 64).
- Motion blur on, shutter 0.5 (whips/fast moves only show it).
- Colour management: Standard (4.3). Compositor: Glare Bloom + vignette (4.3).
- Output: PNG 8-bit RGB sequence, rendered in chunks (e.g. 0-689, 690-1379, 1380-2056) -> ffmpeg
  `-c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -r 30 -movflags +faststart`, then mux the existing audio.
- Acceptance check: re-run `out/cmp/look_measure/measure.py` on new stills; targets: Y' p5 0.10-0.25, p50 0.38-0.58,
  local contrast ≥ 0.06, edge% ≥ 5, line% ≥ 1.0, soft share ≤ 0.05, azure+blue ≥ 30 % of saturated hues, head luma
  ≥ 0.85, head width 0.15-0.35 W in medium shots.

---

## 5. Character drawing improvements (`src/videos/gimli/toon.ts`)

The v2 construction already follows characters.md (superellipse heads, bean torsos, single-stroke limbs, dot hands,
thick-thin plum ring, crescent shading). What still separates ours from Ricks Clips on screen:

1. **Head fill white, not skin.** `SKIN = "#ffe2c2"` -> `"#fefaf7"`. `SKINS` -> mostly white:
   `["#fefaf7", "#fefaf7", "#f7f2ee", "#f6e9dc"]` (at most one cream). `SH_SKIN` -> `[0.90, 0.885, 0.93]`
   (#fefaf7 -> #e4dde6, the measured lavender crescent). In `cardshade.ts`/`lights.ts` cap the golden `charTint`
   at about `[1.0, 0.92, 0.84]` (now `[1.0, 0.78, 0.56]` at TINT_K 0.55, which with peach skin and the golden fog turns heads tan/orange).
2. **Head shape: more character, less ellipse.** `headBlob()` currently: H/W 0.94 ± 0.04, nTop 1.75, nBot 2.3,
   egg -0.12, asym 0.06-0.10, rot ±4°, noise 0.008. On screen this still reads as a clean circle. Change to
   per-character archetypes chosen by seed:
   - "bun" (most common in the reference): H/W 0.86-0.92, nTop 2.1, nBot 2.6 (flat-ish top, full cheeks), egg -0.06;
   - "egg": H/W 1.0-1.06, nTop 1.6, egg -0.15;
   - "lumpy": H/W 0.92, noise 0.018 with the 2nd/3rd harmonics dominant (one bump at the crown or a cheek).
   Raise `rot` to ±6°, `noise` default to 0.012 (low harmonics only, no wobble at k ≥ 5). Under caps/hats flatten the
   crown (nTop 2.4) so the hat seats deep (characters.md: hats cover the top 25-40 %).
3. **Outline.** Keep `ow = 5 * u` but set the thick-thin factor in `inkRing(..., k)` from 0.45 to **0.55**
   (ratio 3.4:1; measured 2.5-3.5) and darken `INK` from `#241726` to **`#16121e`** (measured cores #00030b-#1e181f).
   Keep round joins; inner lines (brows, mouth, clothing) 0.6-0.9x, seams 0.4x.
4. **Face.** Dot eyes 3.8u x 5.5u -> **4.5u x 6.8u** (ref ≈ 0.09 x 0.13 W, solid black, no catchlight). `grin`
   `dmouth(..., 12u, 8u)` -> **18-22u wide** (0.36-0.44 W) with 3-5 tooth dividers drawn as ink lines (the reference's
   big toothy grin is its signature expression); keep neutral mouths small (`dash` 11u ok). Brows 5u -> 6u thick end.
5. **Hair as shapes with detail**, not a cut cap. In `hatOn()` for `"hair"`: extend the hair silhouette 4-8u outside
   the head contour (tufts at the crown and over the ear side), add 3-5 inner strand strokes (2u, mix(hair, INK,
   0.6)), and one highlight band (mix(hair, #ffffff, 0.25)) on the lit side. Add styles: side part, bowl, curly
   lumps (blobPts with high noise), bald with side tufts, bun. Caps/police hats: panel seam lines + a dashed stitch
   line (2u dashes) + glossy highlight on the peak.
6. **Torso shading and clothing.** `gradFill(tp, jacket, mul(jacket, SH_CLOTH))` is right in principle; make the
   ramp longer (`flat` 0.22 -> 0.1) and add a **light rim** 3-4u inside the shadow-side edge (mix(jacket, white,
   0.15)), as measured on half of the reference torsos. Add a per-outfit detail layer clipped to `tp` (max 5
   elements): collar V or lapels, a pocket rectangle with dashed stitching, belt with buckle, tie or bow tie, name
   badge, epaulettes/wings for pilots, scarf/neck tie for cabin crew, overalls straps for ground crew. Thin lines 0.4x
   outline.
7. **Proportions and limbs** (keep): adult 3.5 head heights (`BUILD.adult` torso 1.1, legs 1.4), legs 5.8u strokes,
   arms 5.2u, hands 5.5u dots. Feet: keep strokes, never ovals.
8. **Poses:** at least one arm doing something in every shot (pointing, holding a clipboard/prop to camera,
   hand on hip), torso lean 3-8°, head tilt ±5°; props are drawn with the same outline weight (0.6-1.0x).
9. **Framing rule for cards** (cast/story): head width 0.17-0.32 of frame width in dialogue shots; close-ups ≤ 0.65 W
   with the whole head inside the frame; never cut the head at the frame top except in deliberate extreme reaction
   shots (≤ 1 per video).

---

## 6. Confirmations / corrections to the earlier reports (`references/reports/*.md`)

- Confirmed: white heads (luma ≈ 0.93-1.0) with lavender crescent; near-black plum/navy thick-thin outlines (~5 % W,
  ~3:1); stick limbs and dot hands; no blush/catchlights; world ink on cartoon geometry ≈ 3 px at 1080 (outlines.md);
  coloured, lifted darks (grade.md); continuous camera glides (motion.md).
- New/corrected for gimli_v2: we are now **too bright and hazy**, not too dark (all-frames Y' p50 0.60 vs ref 0.44;
  golden exteriors p5 0.39 vs ref night/dusk 0.10), and **over-blurred** (soft share 0.25 vs 0.008: the lens blur that
  depth.md asked for overshoots). The reference set studied here has many night/interior shots (28/72), so contrast
  between dark ambient and warm practicals matters more than the day grade.
- World ink is **asset-dependent**: cartoon-painted assets carry it, semi-realistic assets (cars, suburban house,
  coaster, railway) do not; both appear side by side. A Blender rebuild should outline the cartoon family and may leave
  vehicles/realistic props un-inked.

## 7. Reference image list (`references/ricks/`, 337x600 JPEG q95)

- QlDPMzGmYac: _1.5, _6, _14, _24, _24.1, _24.2 (motion triplet), _36, _50
- e9NoHjAXYIY: _1.5, _6, _14, _24, _36, _50
- HxqtHI62otM: _1.5, _6, _14, _24, _36, _50
- 7xS87iActkU: _1.5, _6, _14, _24, _36, _50
- Mz72MuPgnGY: _1.5, _6, _14, _24, _36, _50
- 5WMQhPObNqQ: _1.5, _6, _14, _24, _36, _50
- ZDy3xXA2iHk: _1.5, _6, _14, _24, _36, _50
- VS1Z_Q-Klt8: _1.5, _6, _14, _14.1, _14.2 (motion triplet), _24, _36, _50
- 0m6G8pDtzNs: _1.5, _6, _14, _24, _36, _50
- eQR3pgMiUF0: _1.5, _6, _14, _24, _36, _44.7 (duration 45.1 s)
- lnYLIWP2l-I: _1.5, _6, _14, _24, _36, _50
- PLe2Gu3FDuA: _1.5, _6, _14, _24, _36, _44.6 (duration 45.0 s)

File name pattern: `references/ricks/<id>_<seconds>.jpg`, e.g. `references/ricks/HxqtHI62otM_36.jpg`.
Our frames: `out/cmp/ours/ours_{02,07,11,16,21,25,31,34,38,42,47,50,55,58,61,66}.jpg`.
