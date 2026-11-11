# STUB for the "apron" set: a ground plane only. To be replaced by the set builder (see AGENT_BRIEF.md).
INK_RADIUS = 0.03


def build(ctx):
    lib = ctx["lib"]
    if "apron" != "sky":
        lib.plane(ctx["ink"], "ground", 2000, 2000, lib.toon("stub_ground", "#7fb86a"), uv_scale=4)
