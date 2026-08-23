# Builds the chunky vinyl-toy hero (penguin pilot + mini plane) from
# primitives and exports it as GLB for the bake step.
#
#   blender --background --python tools/model_hero.py -- /tmp/opencode/hero.glb
#
# Side view convention: camera looks from -Y, so the plane's nose points -X.
# Palette comes from ART_DIRECTION.md.
import bpy, sys, math
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]

PALETTE = {   # hex-picked sRGB values…
    "plane_blue":  (0.23, 0.55, 0.86, 1),   # glacier-blue fuselage
    "orange":      (1.00, 0.48, 0.27, 1),   # signal-orange accents / beak
    "snow":        (0.96, 0.98, 1.00, 1),   # belly
    "navy":        (0.06, 0.16, 0.34, 1),   # penguin body (midnight navy)
    "leather":     (0.33, 0.20, 0.10, 1),   # aviator cap
    "strap":       (0.20, 0.14, 0.09, 1),
    "scarf":       (0.91, 0.26, 0.21, 1),
    "gold":        (0.85, 0.65, 0.25, 1),
    "white":       (0.97, 0.97, 0.97, 1),
    "dark":        (0.02, 0.02, 0.03, 1),
}
# …but Blender reads material colors as LINEAR. Convert or everything bakes
# out pastel (Blender 5.x ships no Standard view transform to do it for us).
PALETTE = {k: tuple(v ** 2.2 if i < 3 else v for i, v in enumerate(c)) for k, c in PALETTE.items()}


def mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = PALETTE[name]
    b.inputs["Roughness"].default_value = 0.85 if name == "gold" else 0.5
    try:
        b.inputs["Metallic"].default_value = 0.8 if name == "gold" else 0.0
    except KeyError:
        pass
    return m


def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), mkey=None):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, depth=2)
    elif kind == 'cyl':
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=2)
    elif kind == 'torus':
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.12, major_segments=32, minor_segments=12)
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

# ---------------- plane ----------------
prim("fuselage", 'sphere', (0.15, 0, 0.10), scale=(1.25, 0.52, 0.50), mkey="plane_blue")
prim("nose",     'sphere', (-1.28, 0, 0.10), scale=(0.21, 0.31, 0.29), mkey="orange")
prim("wing",          'cube',  (0.05, 0, 0.13), scale=(0.50, 1.45, 0.09), mkey="white")
prim("wingtip_l",     'sphere', (0.05, -1.40, 0.16), scale=(0.42, 0.16, 0.10), mkey="white")
prim("wingtip_r",     'sphere', (0.05, 1.40, 0.16), scale=(0.42, 0.16, 0.10), mkey="white")
prim("fin",           'sphere', (1.33, 0, 0.58), rot=(-16, 0, 0), scale=(0.26, 0.05, 0.38), mkey="orange")
prim("tail",          'cube',  (1.28, 0, 0.16), scale=(0.24, 0.85, 0.06), mkey="white")
prim("wheel_pant_l",  'sphere', (-0.25, -0.42, -0.52), scale=(0.17, 0.11, 0.19), mkey="orange")
prim("wheel_pant_r",  'sphere', (-0.25, 0.42, -0.52), scale=(0.17, 0.11, 0.19), mkey="orange")
prim("wheel_l",       'sphere', (-0.25, -0.50, -0.60), scale=(0.10, 0.05, 0.10), mkey="dark")
prim("wheel_r",       'sphere', (-0.25, 0.50, -0.60), scale=(0.10, 0.05, 0.10), mkey="dark")

# ---------------- penguin pilot ----------------
prim("body",      'sphere', (-0.12, 0, 0.78), scale=(0.40, 0.36, 0.46), mkey="navy")
prim("belly",     'sphere', (-0.31, 0, 0.68), scale=(0.25, 0.27, 0.35), mkey="snow")  # protrudes past body front -> visible in profile
prim("head",      'sphere', (-0.16, 0, 1.32), scale=(0.30, 0.29, 0.30), mkey="navy")
prim("beak",      'cone',   (-0.50, 0, 1.30), rot=(0, -90, 0), scale=(0.11, 0.10, 0.24), mkey="orange")
prim("eye_l",     'sphere', (-0.34, -0.16, 1.40), scale=(0.105, 0.105, 0.115), mkey="white")
prim("pupil_l",   'sphere', (-0.41, -0.18, 1.40), scale=(0.05, 0.05, 0.055), mkey="dark")
prim("eye_r",     'sphere', (-0.34, 0.16, 1.40), scale=(0.105, 0.105, 0.115), mkey="white")
prim("pupil_r",   'sphere', (-0.41, 0.18, 1.40), scale=(0.05, 0.05, 0.055), mkey="dark")
# aviator cap: squashed dome sitting high on the head
prim("cap",       'sphere', (-0.13, 0, 1.47), scale=(0.315, 0.305, 0.235), mkey="leather")
# goggle strap around the cap + pushed-up lenses
prim("strap",     'torus',  (-0.13, 0, 1.47), rot=(0, 90, 0), scale=(0.30, 0.30, 0.30), mkey="strap")
prim("lens_l",    'cyl',    (-0.33, -0.14, 1.56), rot=(0, 90, 18), scale=(0.09, 0.045, 0.09), mkey="gold")
prim("lens_r",    'cyl',    (-0.33, 0.14, 1.56), rot=(0, 90, -18), scale=(0.09, 0.045, 0.09), mkey="gold")
# scarf knot at the neck
prim("scarf",     'torus',  (-0.28, 0, 1.03), rot=(12, 0, 0), scale=(0.26, 0.26, 0.26), mkey="scarf")

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True)
print("EXPORTED", OUT)
