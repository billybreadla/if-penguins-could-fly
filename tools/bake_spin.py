# Bake a 16-frame turntable strip of the hero toy for the title screen.
#
#   blender --background --python tools/bake_spin.py -- <in.glb> <out.png>
#
# Output: one horizontal strip, 16 square cells (yaw every 22.5deg), nose-left
# at yaw 0 — same convention as the flight strip. The title screen steps
# through the cells at ~6fps.
import bpy, sys, math
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB, OUT = argv[0], argv[1]
CELLS = 16
RES = 768                      # per-cell render, downscaled to 384 in the strip

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

mat = bpy.data.materials.new("HeroVertex")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
bsdf.inputs["Roughness"].default_value = 0.45
try:
    bsdf.inputs["Coat Weight"].default_value = 0.3
except KeyError:
    pass
attr = nt.nodes.new('ShaderNodeVertexColor')
try:
    attr.attribute_name = "Color"
except Exception:
    pass
nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
for o in meshes:
    if not o.data.materials:          # keep the GLB's real palette materials
        o.data.materials.append(mat)

# --- normalize: center at origin, longest dimension = 2 units ---
from mathutils import Vector
mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
size = max(maxs - mins); center = (mins + maxs) / 2
root = bpy.data.objects.new("Root", None)
bpy.context.scene.collection.objects.link(root)
for o in meshes:
    o.parent = root
root.scale = (2.0 / size,) * 3
root.location = tuple(-c * 2.0 / size for c in center)

def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)

# lights parented to the root so the rig spins WITH the hero (stable studio look)
def rig():
    light("Key", 'SUN', (-4, -3, 5), 2.0, rot=(42, 0, 38))
    light("Fill", 'AREA', (4, -2, 1), 70, rot=(65, 0, -55), color=(0.75, 0.84, 1.0))
    light("Rim", 'AREA', (0, 3.5, 2), 110, rot=(-40, 0, 180))
    w = bpy.data.worlds.new("W"); w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.12
    bpy.context.scene.world = w
rig()

cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 2.55
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0, -8, 0); cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        continue
else:
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

import sys as _s, os as _o
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import toon
toon.toonify_scene(outline_frac=0.016)

import os
tmp = "/tmp/opencode/spin"
os.makedirs(tmp, exist_ok=True)
for i in range(CELLS):
    root.rotation_euler = Euler((0, 0, math.radians(-i * 360 / CELLS)))
    sc.render.filepath = f"{tmp}/c{i:02d}.png"
    bpy.ops.render.render(write_still=True)
    print("cell", i)

# compose the strip (system PIL via blender python? no — save PNGs, compose outside)
print("STRIP CELLS DONE", CELLS, RES)
