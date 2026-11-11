import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
bpy.ops.object.grease_pencil_add(type="LINEART_SCENE")
o = bpy.context.object
print("OBJ", o.name, o.type, type(o.data).__name__)
for m in o.modifiers:
    print("MOD", m.name, m.type)
    for p in m.bl_rna.properties:
        if p.identifier in ("rna_type",): continue
        try: print("  ", p.identifier, getattr(m, p.identifier))
        except Exception as e: pass
print("MATS", [m.name for m in o.data.materials])
print("LAYERS", [l.name for l in o.data.layers] if hasattr(o.data, "layers") else None)
