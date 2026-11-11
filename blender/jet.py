# STUB jet: a white cylinder fuselage + wings, nose toward -Y. To be replaced by the jet builder (see AGENT_BRIEF.md).
import bpy


def build(ctx):
    lib = ctx["lib"]
    root = bpy.data.objects.new("JetRoot", None); ctx["ink"].objects.link(root)
    bpy.ops.mesh.primitive_cylinder_add(radius=2.5, depth=40, rotation=(1.5708, 0, 0))
    f = bpy.context.object; lib.link(f, ctx["ink"]); f.parent = root; f.data.materials.append(lib.toon("stub_jet", "#f3f1ec"))
    lib.box(ctx["ink"], "wings", (-23.8, -4, -1.6), (23.8, 4, -1.0), lib.toon("stub_wing", "#d3d6dc")).parent = root
    return dict(root=root)


def pose(h, jet, t):
    h["root"].hide_render = not jet["visible"]
    h["root"].matrix_world = __import__("lib").obj_matrix(jet["m"])
