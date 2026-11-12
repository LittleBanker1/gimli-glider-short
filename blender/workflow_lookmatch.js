export const meta = {
  name: 'gimli-blender-lookmatch',
  description: 'Build the Gimli short sets, jet and characters in Blender to match the Ricks Clips look, with independent review and a fix round',
  phases: [
    { title: 'Build', detail: 'one builder per set / jet / characters' },
    { title: 'Review', detail: 'independent comparison against the reference frames' },
    { title: 'Fix', detail: 'owner applies the review fixes' },
    { title: 'Final review', detail: 'score after fixes' },
  ],
}

const STUDIO = 'D:\\gimli3d\\studio'
const BRIEF = 'D:\\gimli3d\\blender\\AGENT_BRIEF.md'
const COMMON = `Start by reading ${BRIEF} completely and following it (it has the goal, hard rules, GPU lock, asset paths, module contract, shot table and how to check your work). STUDIO = ${STUDIO}. Communicate in English. Work carefully; quality over speed. Iterate with real renders and LOOK at them.`

const ITEMS = [
  { key: 'jet', shots: '1, 9, 13 (flying), 2-4, 18, 20 (parked on the apron; 3-4 are low close-ups at the right main gear / wing), 11 (far on approach), 15-17 (landing, nose gear collapse, nose on the runway)',
    owns: 'D:\\gimli3d\\blender\\jet.py (replace the stub)',
    task: `Model the jet: a wide-body twinjet with the proportions of a Boeing 767-200 (48.5 m long, 47.6 m span, 5.0 m fuselage diameter, 15.8 m tall), built in Blender coordinates with the nose toward -Y, up +Z, origin on the fuselage centreline at mid-length (nose tip y = -24.2, tail y = +24.3), wheel bottoms at z = -3.3 with the gear down. Generic early-1980s livery painted as a texture (white upper fuselage, light grey belly, red cheatline under the windows, red tail; NO real airline logo or name): cabin windows, doors with outlines, cockpit windows, panel seams, rivet lines, registration-like stripe allowed but no real registration. Wings with sweep + dihedral, flap track fairings, winglet-free tips, two big turbofan nacelles with lip, fan face with blades + spinner (spins with jet.spin), pylons, horizontal + vertical tail, APU exhaust, landing-gear bogies (4-wheel mains, 2-wheel nose) with struts, doors, a ram-air turbine (small propeller) that drops out of the belly near the right wing root (jet.rat). Must look great in close-ups (shots 3-4: camera at the right main gear/wing at a few metres; shots 16-17: nose scraping the runway) and read as a clean cartoon jet from far. Ink: put it in ctx["ink"]. pose(h, jet, t): root matrix from lib.obj_matrix(jet["m"]); hide when not visible or scrap > 0.5; main gear and nose gear extend/retract with jet.gear (scale or rotate into wells), nose gear folds with jet.nose, RAT with jet.rat, fans rotate (fast spin -> motion-blur-ish disc texture swap or just rotation). Test in shots 1, 3, 13, 16 (e.g. --frames 60 / 300 / 1200 / 1560).` },
  { key: 'sky', shots: '1 (0-159), 9 (864-923), 13 (1159-1262), all golden/sunset',
    owns: 'D:\\gimli3d\\blender\\sets\\sky.py',
    task: `Build the sky set: the jet flies at the origin toward -Y high above a sunset cloud sea (about 150 m below). Stylised 3D cumulus (metaballs / remeshed spheres + displacement, three-tone toon: sunset lit #ffd2a8, mid #f2a08f, shade #a98fc4), several depth layers out to the horizon, some towering clouds, scattered cloud wisps at the jet's level for parallax, a big warm sun disc + glow near the horizon in the camera direction (it must read in the shot 1 framing), maybe a distant ground/lake visible through gaps for shot 9 (camera high and far behind the jet looking ahead: "every big airport was too far" — a faint distant city glow on the horizon helps). animate(): the cloud sea scrolls toward +Y at 70 m/s (wrap), see brief. Shot 13 the jet sinks (the camera rides along). Make it gorgeous: deep violet top, orange/pink horizon band, high contrast, not a flat orange haze (the study says our golden haze was the #2 problem).` },
  { key: 'apron', shots: '2 (160-263), 3 (264-390), 4 (391-554), 18 (1713-1764), 20 (1839-1939), all day',
    owns: 'D:\\gimli3d\\blender\\sets\\apron.py',
    task: `Build Montreal airport apron, 1983, sunny day, cobalt sky: the jet is parked at the origin (layout.APRON). Terminal with concrete fins + blue glass curtain wall + signage band (generic, no real brand), a jet bridge reaching toward the left front door, control tower, hangar, light masts, chain-link fence, grass strips, a detailed fuel truck (red cab, white tank, hoses to the wing, its round gauge dial at layout.APRON gauge_dial facing +X with an animated needle: full -> half between picture frames 484-498 in shot 4), baggage tug + carts with colourful suitcases, belt loader, ground power unit, cones, wheel chocks, apron markings (yellow lead-in line, stop bar, stand number), 1980s boxy cars/vans in a car park, maybe another parked airliner far away (simple). Use Kenney city/car kits (repaint to period colours) + your own models. Characters (cards) stand at layout.APRON captain/fueler (shots 2-4) and investigators at the nose (shot 18): keep the camera sight lines clear there. Shot 20 is a wide crane-up where the jet bursts into luggage tags (the jet hides itself). Add foreground objects at frame edges where it helps depth. Test shots 2, 3, 4 (incl. the gauge insert around final frame 520), 18, 20.` },
  { key: 'cockpit', shots: '5 (548-664), 6 (665-719), 8 (794-863), 10 (924-1007) golden sunset flight; 19 (1765-1838) daylight simulator',
    owns: 'D:\\gimli3d\\blender\\sets\\cockpit.py',
    task: `Build the 767 cockpit (layout.COCKPIT): instrument panel with six EFIS screens (paint your own on/off textures with Pillow: attitude blue/brown, map with magenta line, engine gauges), standby round gauges, glareshield with two amber master-caution lights + red warning lights, overhead panel with switch arrays (instanced), side consoles, yokes, throttle quadrant, two pilot seats (leather), side windows, windscreen frame with open panes. Outside the windows in golden shots: sunset sky (the world sky) + a cloud sea below (a few toon clouds out there). Shot 19 is a DAYLIGHT FLIGHT SIMULATOR: same cockpit but the windows show a projection screen with a runway image and a dark room beyond; red warning lights blink from picture frame 1767, crash 1796. animate(): screens on/off and blinking lights per the brief cues. Cameras: shots 5 and 19 film BOTH pilots from outside/at the windscreen looking back (+Y) — the windscreen posts and glareshield must not hide the pilots' faces (pilots sit at x +-0.55, heads z 1.25-1.6); shot 6 is a close-up of the screens going black; shots 8/10 are close-ups of each pilot. Rich, warm, detailed, lit by the sunset through the windows with practical glow from instruments.` },
  { key: 'cabin', shots: '7 (714-793) golden',
    owns: 'D:\\gimli3d\\blender\\sets\\cabin.py',
    task: `Build the 767 economy cabin (layout.CABIN): 14 rows of 2-3-2 seats with patterned fabric (early-80s colours), seat-back pockets, armrests, tray tables, overhead bins with latches, reading lights / air vents panel, window row with sunset light shafts (golden) and blinds, patterned carpet aisle, galley curtain/bulkhead at the end, exit signs, a few props (newspapers, cups, a hat). Passengers are seated cards facing -Y; the camera is at the front in the right aisle (x ~1.0, y -3.6..-5.6, z 1.6-1.75) looking aft down the cabin — seat backs of the row in front should hide passengers' legs. Warm sunset shafts + cool shadows, detailed, deep perspective.` },
  { key: 'gimli', shots: '11 (1008-1041 aerial golden), 12 (1034-1166 field, DAY), 14 (1263-1374), 15 (1375-1490), 16 (1491-1616), 17 (1617-1721) golden',
    owns: 'D:\\gimli3d\\blender\\sets\\gimli.py',
    task: `Build Gimli, Manitoba, 1983: a decommissioned air force base turned race track on race day (layout.GIMLI). Long runway along Y (cracked concrete with weeds, faded markings, threshold bars, numbers), the drag-strip guard rail down the centreline, jersey barriers, tyre stacks, cones, start-light tree, flags and banners (no real brands), parked race cars + tow trucks + trailers + campers/RVs, tents/awnings, lawn chairs, coolers, a small grandstand, old hangars + control tower (decommissioned look, west at layout hangars_x), prairie grass with flowers, poplar windbreak rows, distant farm with silos, Lake Winnipeg on the eastern horizon, power lines. The shot-14 race cars move (animate(): see brief cue). Shot 12 (DAY) is a separate open meadow at layout.GIMLI field: fence, trees, flowers, rocks, a hill line (a kid stands there). Keep the landing path clear (jet touches down at y = +260, stops at y = -120 with its nose at y ~ -144, main gear straddling the rail). Spectators (cards) stand around layout paddock and crowd_edge. Use Kenney racing/car/nature kits heavily. Dense, colourful, deep.` },
  { key: 'checkin', shots: '21 (1932-2056) day interior',
    owns: 'D:\\gimli3d\\blender\\sets\\checkin.py',
    task: `Build a modern airport check-in hall (layout.CHECKIN): counter with an airline-neutral logo panel, a baggage scale platform with a glowing digital display on a post facing -Y (animate(): blank until picture frame 1950, "23 kg" 1950-1992, "50 lb" 1992-2030, then alternating every 10 frames; make it big, crisp and readable), conveyor belt behind, a red suitcase on the scale with a luggage tag (white with red stripe = a piece of the jet), queue stanchions with blue belts, a departures board (emissive, generic flights, no real airline), colourful luggage and trolleys, signage pictograms, big windows with blue sky and a parked jet outside, plants, benches, ceiling lights, polished tiled floor. The agent card stands behind the counter, the traveller in front of the scale: keep the display, both faces and the suitcase readable in the camera. Bright, clean, colourful, detailed.` },
  { key: 'characters', shots: 'all (cards)',
    owns: `${STUDIO}\\src\\videos\\gimli\\toon.ts and the outfit definitions (CAPTAIN, FO, SIMPILOT, FUELER, INVESTIGATOR, AGENT, TRAVELLER, PAX, RACER) in ${STUDIO}\\src\\videos\\gimli\\cast.ts`,
    task: `Redraw the characters so they match the Ricks Clips character style (LOOK_STUDY sections 1.2 and 5, reference frames with characters, contact sheet look_sheet1_characters.jpg): WHITE heads (#fefaf7) with a lavender shade (#e4dde6) on the shadow side instead of skin tones; near-black outline ~4.5 % of head width, thicker on one side (~3:1); head shape not a perfect circle (the study describes it); better body structure and proportions, clothing detail (collars, pockets, belts, buttons, badges, ties, epaulettes), hands, expressive faces (eyes, brows, mouths). Outfits: airline pilots with peaked caps + badge + epaulettes + wings pin (captain with moustache), fueler in orange overalls with ear defenders and cap, 1980s passengers (varied hair, glasses, clothes), racers in driving suits (helmet under the arm or cap), investigators in suits with ties and hats, a check-in agent in uniform with scarf, a traveller in a cap. Keep every exported function signature, option and the drawing keys working (cast.ts calls bodyFront/bodySide with FrontOpts/SideOpts; keys must stay deterministic). To test: from STUDIO run (through the GPU lock, it starts headless Chrome) \`node scripts/export_frames.mjs D:/gimli3d/export_chars <from> <to>\` for a few frames of several shots (e.g. 300-302, 600-602, 760-762, 820-822, 1300-1302, 1700-1702, 2040-2042), then look at D:\\gimli3d\\export_chars\\cards\\*.png and make a sheet next to the reference characters. Optionally rename frames_<from>_<to>.jsonl to frames.jsonl and render with render_shot.py --export D:\\gimli3d\\export_chars to see them in a set. Run \`npx tsc --noEmit\` from STUDIO (pre-existing TS2322 errors in Gimli.tsx/Bridge.tsx are known; add no new ones).` },
]

const builderPrompt = (it) => `${COMMON}

You are the **${it.key}** builder. You own ONLY: ${it.owns}. Your shots: ${it.shots}.

Task: ${it.task}

When done, write your final report as the brief says.`

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    score: { type: 'number', description: '1-10: how close to the Ricks Clips look (10 = indistinguishable in style)' },
    sheet: { type: 'string', description: 'path of the comparison sheet you made' },
    strengths: { type: 'array', items: { type: 'string' } },
    fixes: { type: 'array', items: { type: 'string' }, description: 'ranked concrete fixes, most visual impact first, each actionable in the owner file' },
  },
  required: ['score', 'fixes'],
}

const reviewPrompt = (it, label) => `${COMMON}

You are an independent, demanding art-director REVIEWER (${label}) for the **${it.key}** part (owner file(s): ${it.owns}; shots: ${it.shots}). Do NOT edit any project file. Render fresh frames yourself (through the GPU lock; tag ${it.key}_${label.replace(/\s+/g, '')}) for 4-6 well-spread frames of these shots${it.key === 'characters' ? ' (for characters: export a few frames with the exporter into D:/gimli3d/export_review and look at the card PNGs; you may also render them in a set)' : ''}, make a side-by-side sheet against the most relevant reference frames in STUDIO\\references\\ricks, and LOOK at it closely. Judge colour richness, value contrast, detail density, ink lines, depth/foreground, lighting mood, readability of story beats, and anything that looks cheap. Return a 1-10 score and a ranked list of concrete, actionable fixes (what to change, where, by how much) for the owner.`

const fixPrompt = (it, review) => `${COMMON}

You are the **${it.key}** builder (second pass). You own ONLY: ${it.owns}. Your shots: ${it.shots}.
Original task (for context): ${it.task}

An independent art director reviewed the current state (score ${review ? review.score : '?'}/10). Their ranked fixes:
${review ? review.fixes.map((f, i) => `${i + 1}. ${f}`).join('\n') : '(review missing: do your own careful comparison against the references and improve the weakest points)'}

Apply as many fixes as you can, best first, verifying each with real renders. Then write your final report.`

const results = await pipeline(
  ITEMS,
  (it) => agent(builderPrompt(it), { label: `build:${it.key}`, phase: 'Build' }),
  (built, it) => agent(reviewPrompt(it, 'review 1'), { label: `review:${it.key}`, phase: 'Review', schema: REVIEW_SCHEMA })
    .then((r) => ({ built, review1: r })),
  (st, it) => agent(fixPrompt(it, st.review1), { label: `fix:${it.key}`, phase: 'Fix' }).then((fixed) => ({ ...st, fixed })),
  (st, it) => agent(reviewPrompt(it, 'final review'), { label: `final:${it.key}`, phase: 'Final review', schema: REVIEW_SCHEMA })
    .then((r) => ({ key: it.key, score1: st.review1 ? st.review1.score : null, score2: r ? r.score : null, remaining: r ? r.fixes.slice(0, 6) : [], sheet: r ? r.sheet : null, builderReport: String(st.fixed || st.built || '').slice(0, 1500) })),
)
return results