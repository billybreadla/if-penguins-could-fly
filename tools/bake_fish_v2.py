# Render the AI fish mesh once, side view, hi-res + transparent.
#   blender --background --python tools/bake_fish_v2.py -- <fish.glb> <out.png>
import bpy, sys, math, os
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

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


def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1), size=2):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    if kind == 'AREA':
        d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)


light("Key", 'SUN', (-4, -3, 5), 2.0, rot=(42, 0, 38))
light("Fill", 'AREA', (4, -2, 1), 70, rot=(65, 0, -55), color=(0.72, 0.82, 1.0))
light("Rim", 'AREA', (0, 3.5, 3), 110, rot=(-40, 0, 180), size=5)

world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.6, 0.68, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.12
bpy.context.scene.world = world

cam_d = bpy.data.cameras.new("Cam")
cam_d.type = 'ORTHO'
cam_d.ortho_scale = 2.35
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0, -8, 0)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
sc.render.resolution_x = 1440
sc.render.resolution_y = 960
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.25
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

import sys as _s, os as _o
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import toon
FISH_REF = _o.environ.get("FISH_REF")
if FISH_REF:
    import project_colors
    for o in meshes:
        mod = o.modifiers.new("dec", "DECIMATE")
        mod.ratio = 0.3
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
    bpy.context.view_layer.update()
    project_colors.project(meshes, FISH_REF, cam)
toon.toonify_scene(outline_frac=0.02)
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
