# Anchor points of every set in BLENDER coordinates (z up), converted from src/videos/gimli/story.ts
# (three.js (x, y, z) -> Blender (x, -z, y)). Cameras and characters come from the exported film data, so sets MUST
# put their geometry where these anchors say. Units: metres. "Nose" = the jet's nose direction = Blender -Y.
#
# APRON (shots 2-4, 18, 20): jet parked at the origin, fuselage centreline z = 3.3, nose toward -Y (tip at y = -24.2,
# tail at y = +24.3), wingspan along X (left wing +X... in three the left wing is +x), main gear at y = +3.2.
APRON = dict(
    jet_centre=(0.0, 0.0, 3.3),
    fuel_truck=(15.7, -0.5, 0.0),       # vehicle centre, facing aft (+Y); its round gauge dial faces +X at z ~ 1.95
    gauge_dial=(14.43, 1.9, 1.95),     # the camera of shot 4 (frames ~486-520) looks at this from +X
    captain=(9.0, 0.6, 0.0),           # stands under the right... (+X) wing with the dipstick
    fueler=(11.6, -1.6, 0.0),          # holds the clipboard
    investigators=[(-1.2, -27.4, 0.0), (0.6, -26.8, 0.0), (1.9, -28.0, 0.0)],  # shot 18, at the nose
    terminal_front=(-70.0, -10.0, 0.0),  # terminal facade plane x = -70 facing +X, ~220 m long along Y, 14 m tall
)
# COCKPIT (shots 5, 6, 8, 10, 19): floor z = 0, nose toward -Y. Captain sits on the LEFT seat = +X, first officer -X.
COCKPIT = dict(
    captain_seat=(0.55, 0.1, 0.0), fo_seat=(-0.55, 0.1, 0.0),
    seat_height=0.5,                   # cushion top; the seated cards' hips sit here, heads at z ~ 1.25-1.6
    panel_y=-0.95,                     # instrument panel plane (faces +Y toward the pilots), screens centred z 0.74
    windscreen_y=-1.35,                # windscreen frame; glareshield top z ~ 1.12; overhead ~ z 1.8-2.05
    width=3.4,                         # x from -1.7 to 1.7
    # cameras: shot 5/19 film the pilots from OUTSIDE the windscreen at (x -1.3, y -2.4, z 1.42) looking back (+Y);
    # shots 8/10 are close-ups from just behind the glareshield; shot 6 is the panel close-up.
)
# CABIN (shot 7): aisles at x = +-1.05, 14 rows, row r seat-back at y = 10 - 0.86 r (rows advance toward -Y = nose),
# seats at x in SEATS (2-3-2), cushion top z ~ 0.5, passengers face -Y (toward the camera at y ~ -3.6..-5.6, z 1.6-1.75).
CABIN = dict(rows=14, row0_y=10.0, pitch=0.86, seats=[-2.05, -1.55, -0.5, 0.0, 0.5, 1.55, 2.05], wall_x=2.45, ceiling=2.3)
# GIMLI (shots 11, 12, 14-17): runway along Y, 60 m wide (x -30..30), from y = +1500 (approach end) to -1500.
# The jet lands toward -Y: touchdown y = +260, stops at y = -120 (nose tip y ~ -144); the drag-strip guard rail runs
# down the centreline x = 0 from y = -100 to y = -420 (the main gear straddles it at the stop).
GIMLI = dict(
    runway_half_width=30.0, touchdown_y=260.0, stop_y=-120.0, rail_y=(-100.0, -420.0),
    paddock=(55.0, -260.0, 0.0),       # campers, tents, spectators east of the runway around here
    race_lane_x=(4.0, 16.0),           # race cars pass the low camera of shot 14 at y ~ -300 in lanes x 4..16
    field=(-150.0, 460.0, 0.0),        # shot 12: the kid with the rock and paper plane stands here (open meadow)
    crowd_edge=(33.0, -205.0, 0.0),    # spectators along the runway edge, y -205..-230
    hangars_x=-270.0,                  # old hangars west of the runway (keep them out of the jet's path)
)
# CHECK-IN (shot 21): counter along X at y = 0 (public side = -Y), scale platform at (0.9, -0.85), the display on its
# post faces -Y at z ~ 1.3, agent behind the counter at (0, 0.9), traveller at (-0.5, -1.35). Back wall y ~ +6.
CHECKIN = dict(scale=(0.9, -0.85, 0.0), agent=(0.0, 0.9, 0.0), traveller=(-0.5, -1.35, 0.0), counter_y=0.0, back_wall_y=6.0)
# SKY (shots 1, 9, 13): the jet flies at the origin toward -Y; cloud sea ~150 m below; the camera moves around it.
SKY = dict(cloud_floor_z=-150.0)
# light per set: exterior sets use "day"/"golden" from the shot; interiors use "interior" / "interior_golden".
