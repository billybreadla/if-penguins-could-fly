# Composite hero v3: procedural plane + AI-generated penguin (from TripoSR).
#
#   blender --background --python tools/bake_hero_v3.py -- <plane.glb> <penguin.glb> <outdir> [probe]
#
# Renders the same four poses as bake_hero_strip.py (cruise/climb/bank/dive).
# Run with "probe" first to tune PENG_YAW / PENG_POS / PENG_SCALE.
import bpy, sys, math, os
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:]
PLANE, PENG, OUT = argv[0], argv[1], argv[2]
PROBE = len(argv) > 3 and argv[3] == "probe"
RES = 1040

# --- penguin tuning (set after eyeballing the probe) ---
PENG_YAW = -48        # deg — AI penguin faces +Y after import; game wants -X
PENG_X = -0.28       # cockpit x in plane raw units
PENG_FOOT_Z = 0.20   # penguin's lowest point sits here (sunk into fuselage)
PENG_SCALE = 0.70    # penguin normalized to 2 units, then scaled to raw units
POSES = [
    (0, 0), (14, 0), (8, 16), (-16, 0),
]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=PLANE)
plane_meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
plane_root = bpy.data.objects.new("PLANE_ROOT", None)
bpy.context.scene.collection.objects.link(plane_root)
for o in plane_meshes:
    o.parent = plane_root

# normalize the plane: center bounds, longest side -> the procedural plane's 3.64 span
pmins = Vector((1e9,) * 3); pmaxs = Vector((-1e9,) * 3)
for o in plane_meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        pmins = Vector(map(min, pmins, w)); pmaxs = Vector(map(max, pmaxs, w))
psize = max(pmaxs - pmins); pcenter = (pmins + pmaxs) / 2
plane_root.scale = ((3.64 / psize),) * 3
plane_root.location = tuple(-c * 3.64 / psize for c in pcenter)
PLANE_YAW = float(os.environ.get("PLANE_YAW", "-90"))
plane_root.rotation_euler = Euler((0, 0, math.radians(PLANE_YAW)))

bpy.ops.import_scene.gltf(filepath=PENG)
peng_meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o not in plane_meshes]
# normalize penguin: center bounds, longest side = 2
mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
for o in peng_meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
size = max(maxs - mins); center = (mins + maxs) / 2
peng_root = bpy.data.objects.new("PENG_ROOT", None)
bpy.context.scene.collection.objects.link(peng_root)
for o in peng_meshes:
    if o.parent is None or o.parent not in peng_meshes:
        o.parent = peng_root
peng_root.rotation_euler = Euler((0, 0, math.radians(PENG_YAW)))
peng_root.scale = ((2.0 / size) * PENG_SCALE,) * 3  # normalize to 2 units, then fit the cockpit
# after rotation, anchor: penguin bounds bottom lands at (PENG_X, 0, PENG_FOOT_Z),
# horizontally centered on its own bounds
bpy.context.view_layer.update()
mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
for o in peng_meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
peng_root.location = (
    PENG_X - (mins.x + maxs.x) / 2,
    0 - (mins.y + maxs.y) / 2,
    PENG_FOOT_Z - mins.z,
)

# --- lights / camera / render setup copied from bake_hero_strip.py ---
def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1), size=2):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    if kind == 'AREA': d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)

light("Key", 'SUN', (-4, -3, 5), 2.0, rot=(42, 0, 38))
light("Fill", 'AREA', (4, -2, 1), 200, rot=(65, 0, -55), color=(0.72, 0.82, 1.0), size=4)
light("Rim", 'AREA', (0, 3.5, 3), 300, rot=(-40, 0, 180), size=8)

world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.6, 0.68, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.12
bpy.context.scene.world = world

cam_d = bpy.data.cameras.new("Cam")
cam_d.type = 'ORTHO'
# plane raw wingspan ≈ 3.64; frame it with the same margin v2 had (2.55 / 2.0)
cam_d.ortho_scale = 4.65
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0, -8, 0)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        continue
else:
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.25
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import toon
EXPORT_MODE = len(argv) > 3 and argv[3] == "export"

# Hunyuan shape meshes are untextured: project colors from the Codex refs.
PENG_REF = _os.environ.get("PENG_REF")
if PENG_REF:
    import project_colors
    # thin the very dense AI mesh first (projection loops per-vertex)
    for o in peng_meshes:
        mod = o.modifiers.new("dec", "DECIMATE")
        mod.ratio = 0.4
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
        o.select_set(False)
    # penguin faces -Y at import (verified by yaw test): front cam at -Y,
    # back at +Y, side (left flank, image faces left) at +X
    views = [{"img": PENG_REF, "campos": (0, -1, 0), "u_axis": 0, "u_sign": 1}]
    if _os.environ.get("PENG_BACK"):
        views.append({"img": _os.environ["PENG_BACK"], "campos": (0, 1, 0), "u_axis": 0, "u_sign": -1})
    if _os.environ.get("PENG_SIDE"):
        views.append({"img": _os.environ["PENG_SIDE"], "campos": (1, 0, 0), "u_axis": 1, "u_sign": 1})
    for o in plane_meshes:
        o.hide_set(True)            # keep ray casts on the penguin's own surface
    bpy.context.view_layer.update()
    project_colors.project_multi(peng_meshes, views)
    for o in plane_meshes:
        o.hide_set(False)

# v24: paint the plane sculpt from its own ref (side + mirrored back, boss-style).
# The plane is rotated PLANE_YAW so its nose faces -X; the painted flank then
# faces -Y (the default camera side).
PLANE_REF = os.environ.get("PLANE_REF")
if PLANE_REF:
    import project_colors
    for o in plane_meshes:
        mod = o.modifiers.new("dec", "DECIMATE")
        mod.ratio = 0.35
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
        o.select_set(False)
    bpy.context.view_layer.update()
    pviews = [{"img": PLANE_REF, "campos": (0, -1, 0), "u_axis": 0, "u_sign": 1}]
    if os.environ.get("PLANE_BACK"):
        pviews.append({"img": os.environ["PLANE_BACK"], "campos": (0, 1, 0), "u_axis": 0, "u_sign": -1})
    for o in peng_meshes:
        o.hide_set(True)
    bpy.context.view_layer.update()
    project_colors.project_multi(plane_meshes, pviews)
    for o in peng_meshes:
        o.hide_set(False)

if not EXPORT_MODE:
    toon.toonify_scene(outline_frac=0.022)

os.makedirs(OUT, exist_ok=True)


def render_pose(i, yaw=None, tag=""):
    p, r = POSES[i]
    yaw = 0 if yaw is None else yaw
    rad = math.radians
    # whole rig (plane+penguin together) gets the flight pose
    plane_root.rotation_euler = Euler((rad(r), rad(yaw + p), 0), 'ZYX')
    peng_root.rotation_euler = Euler((0, 0, math.radians(PENG_YAW)), 'ZYX')
    sc.render.filepath = os.path.join(OUT, f"pose_{i}{tag}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", i, tag)


# pose the whole composite by rotating a shared parent
rig = bpy.data.objects.new("RIG", None)
bpy.context.scene.collection.objects.link(rig)
plane_root.parent = rig
peng_root.parent = rig


def render_pose2(i, yaw=None, tag=""):
    p, r = POSES[i]
    yaw = 0 if yaw is None else yaw
    rad = math.radians
    rig.rotation_euler = Euler((rad(r), rad(yaw + p), 0), 'ZYX')
    sc.render.filepath = os.path.join(OUT, f"pose_{i}{tag}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", i, tag)


if PROBE:
    for yaw, tag in ((0, "_y0"), (90, "_y90"), (-90, "_ym90"), (180, "_y180")):
        render_pose2(0, yaw, tag)
elif EXPORT_MODE:
    # bake the visual transforms into the meshes and export the composite
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for o in peng_meshes + plane_meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = plane_meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # apply is per-object; parents' transforms need baking through children
    for o in peng_meshes + plane_meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    bpy.ops.object.select_all(action="DESELECT")
    for o in peng_meshes + plane_meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = plane_meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.export_scene.gltf(filepath=argv[4], export_format='GLB', export_apply=True)
    print("EXPORTED", argv[4])
else:
    for i in range(4):
        render_pose2(i)
print("DONE")
