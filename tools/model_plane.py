# Exports the plane ONLY (no penguin) as GLB, for compositing with the
# AI-generated penguin mesh.
#
#   blender --background --python tools/model_plane.py -- /tmp/opencode/i23d/plane_proc.glb
import bpy, sys, math
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]

PALETTE = {
    "plane_blue":  (0.23, 0.55, 0.86, 1),
    "orange":      (1.00, 0.48, 0.27, 1),
    "snow":        (0.96, 0.98, 1.00, 1),
    "dark":        (0.02, 0.02, 0.03, 1),
}
PALETTE = {k: tuple(v ** 2.2 if i < 3 else v for i, v in enumerate(c)) for k, c in PALETTE.items()}


def mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = PALETTE[name]
    b.inputs["Roughness"].default_value = 0.5
    return m


def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), mkey=None):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1)
    elif kind == 'cube':
        bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    o.scale = scale
    o.data.materials.append(mat(mkey or name))
    for mod_kind, params in (('BEVEL', dict(width=0.05, segments=4)), ('SUBSURF', dict(levels=2))):
        if kind == 'cube' and mod_kind == 'BEVEL' or kind != 'cube':
            m2 = o.modifiers.new(mod_kind, mod_kind)
            for k, v in params.items():
                setattr(m2, k, v)
    for f in o.data.polygons:
        f.use_smooth = True
    return o


bpy.ops.wm.read_factory_settings(use_empty=True)

prim("fuselage", 'sphere', (0.15, 0, 0.10), scale=(1.25, 0.52, 0.50), mkey="plane_blue")
prim("nose",     'sphere', (-1.28, 0, 0.10), scale=(0.21, 0.31, 0.29), mkey="orange")
prim("wing",          'cube',  (0.05, 0, 0.13), scale=(0.50, 1.45, 0.09), mkey="snow")
prim("wingtip_l",     'sphere', (0.05, -1.40, 0.16), scale=(0.42, 0.16, 0.10), mkey="snow")
prim("wingtip_r",     'sphere', (0.05, 1.40, 0.16), scale=(0.42, 0.16, 0.10), mkey="snow")
prim("fin",           'sphere', (1.33, 0, 0.58), rot=(-16, 0, 0), scale=(0.26, 0.05, 0.38), mkey="orange")
prim("tail",          'cube',  (1.28, 0, 0.16), scale=(0.24, 0.85, 0.06), mkey="snow")
prim("wheel_pant_l",  'sphere', (-0.25, -0.42, -0.52), scale=(0.17, 0.11, 0.19), mkey="orange")
prim("wheel_pant_r",  'sphere', (-0.25, 0.42, -0.52), scale=(0.17, 0.11, 0.19), mkey="orange")
prim("wheel_l",       'sphere', (-0.25, -0.50, -0.60), scale=(0.10, 0.05, 0.10), mkey="dark")
prim("wheel_r",       'sphere', (-0.25, 0.50, -0.60), scale=(0.10, 0.05, 0.10), mkey="dark")

