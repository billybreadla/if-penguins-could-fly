# Bake game-ready hero frames from a GLB in headless Blender.
#
#   blender --background --python tools/bake_hero_strip.py -- <in.glb> <outdir> [probe]
#
# Renders four poses matching heroFrame(): 0 cruise, 1 climb, 2 bank-left,
# 3 dive. Run once with "probe" to check which way the mesh faces, tune
# YAW_FIX/PITCH_FIX below, then run without "probe".
import bpy, sys, math, os
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB, OUT = argv[0], argv[1]
PROBE = len(argv) > 2 and argv[2] == "probe"
RES = 1040                      # rendered 2x, downscaled to 520 cells later

# --- pose tuning (set after eyeballing the probe render) ---
YAW_FIX = 0        # deg — model already faces screen-left from the -Y camera
POSES = [          # (pitch, roll) applied around the flight axes
    (0, 0),        # frame 0: neutral cruise
    (14, 0),       # frame 1: climb — nose up
    (8, 16),       # frame 2: bank left
    (-16, 0),      # frame 3: dive — nose down
]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

# --- toy-plastic material fed by vertex colors — only for bare meshes ---
mat = bpy.data.materials.new("HeroVertex")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
attr = nt.nodes.new('ShaderNodeVertexColor')
try:
    attr.attribute_name = "Col"
except Exception:
    pass
nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
for m in meshes:
    if not m.data.materials:          # keep real materials when the model has them
        m.data.materials.append(mat)

# --- normalize: center at origin, longest dimension = 2 units ---
mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
size = max(maxs - mins); center = (mins + maxs) / 2
root = bpy.data.objects.new("ROOT", None)
bpy.context.scene.collection.objects.link(root)
for o in meshes:
    o.parent = root
root.scale = (2.0 / size,) * 3
root.location = tuple(-c * 2.0 / size for c in center)

# --- lights: upper-left key, cool fill, white rim ---
def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1), size=2):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    if kind == 'AREA': d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)

light("Key", 'SUN', (-4, -3, 5), 2.0, rot=(42, 0, 38))
light("Fill", 'AREA', (4, -2, 1), 70, rot=(65, 0, -55), color=(0.72, 0.82, 1.0))
light("Rim", 'AREA', (0, 3.5, 3), 110, rot=(-40, 0, 180), size=5)

# soft ambient dome so vertex-colored shadows don't crush to black
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.6, 0.68, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.12
bpy.context.scene.world = world

cam_d = bpy.data.cameras.new("Cam")
cam_d.type = 'ORTHO'
cam_d.ortho_scale = 2.55
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
    try:
        sc.cycles.device = 'GPU'
    except Exception:
        pass
print("ENGINE:", sc.render.engine)
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'   # keeps painted colors true
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

os.makedirs(OUT, exist_ok=True)


def render_pose(i, yaw=None, tag=""):
    p, r = POSES[i]
    yaw = YAW_FIX if yaw is None else yaw
    rad = math.radians
    # yaw fix orients the model; pitch tilts the flight path, roll banks it.
    root.rotation_euler = Euler((rad(r), rad(yaw + p), 0), 'ZYX')
    sc.render.filepath = os.path.join(OUT, f"pose_{i}{tag}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", i, tag)


frames = range(1) if PROBE else range(4)
for i in frames:
    if PROBE:
        for yaw, tag in ((90, "_y90"), (-90, "_ym90"), (0, "_front")):
            render_pose(i, yaw, tag)
    else:
        render_pose(i)
print("DONE")
