# Smoke test: EEVEE headless on this GPU, a Kenney GLB with a soft-toon material, Line Art ink, Standard view.
# blender -b --factory-startup -P test_toon.py -- <out.png>
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 50
sc.view_settings.view_transform = "Standard"
sc.render.film_transparent = False

# world: flat blue
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.45, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6

# ground
bpy.ops.mesh.primitive_plane_add(size=40)
g = bpy.context.object

# assets
bpy.ops.import_scene.gltf(filepath=r"D:\gimli3d\kenney\car-kit\Models\GLB format\sedan.glb")
car = bpy.context.selected_objects[0]
bpy.ops.import_scene.gltf(filepath=r"D:\gimli3d\kenney\nature-kit\Models\GLTF format\tree_oak.glb") if False else None


def toon(mat_name, base):
    m = bpy.data.materials.new(mat_name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    d = nt.nodes.new("ShaderNodeBsdfDiffuse"); d.inputs[0].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18; ramp.color_ramp.elements[0].color = (0.55, 0.5, 0.65, 1)
    ramp.color_ramp.elements[1].position = 0.32; ramp.color_ramp.elements[1].color = (1, 0.98, 0.94, 1)
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
    em = nt.nodes.new("ShaderNodeEmission")
    l = nt.links
    l.new(d.outputs[0], s2r.inputs[0]); l.new(s2r.outputs[0], bw.inputs[0]); l.new(bw.outputs[0], ramp.inputs[0])
    l.new(ramp.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = base
    l.new(mul.outputs[2], em.inputs[0]); l.new(em.outputs[0], o.inputs[0])
    return m


g.data.materials.append(toon("ground", (0.35, 0.7, 0.3, 1)))

sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4; sun.angle = 0.03
so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so); so.rotation_euler = (0.9, 0.2, 0.8)

cam = bpy.data.cameras.new("cam"); cam.lens = 35
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
co.location = (5, -7, 3);
import mathutils
d = mathutils.Vector((0, 0, 0.6)) - co.location
co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

# line art over the scene collection
bpy.ops.object.grease_pencil_add(type="LINEART_SCENE") if hasattr(bpy.ops.object, "grease_pencil_add") else bpy.ops.object.gpencil_add(type="LINEART_SCENE")
la = [o for o in sc.objects if o.type == "GREASEPENCIL"][0]; la.modifiers[0].radius = 0.035; la.modifiers[0].use_material = True
print("ENGINE", sc.render.engine, "OBJECTS", [o.name for o in sc.objects])
sc.render.filepath = out
import time
sc.frame_start, sc.frame_end = 1, 3; sc.render.filepath = out.replace(".png", "_####.png"); t0 = time.time()
bpy.ops.render.render(animation=True)
print("ANIM 3 frames", round(time.time() - t0, 1), "s")
print("WROTE", out)
