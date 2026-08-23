# Models + bakes the golden game ring as one tight-cropped transparent WebP.
#
#   blender --background --python tools/bake_ring.py -- <out.png>
#
# Geometry contract with the engine (index.html):
#   hole height / ring outer height == RING.holeFrac (0.578)  -> collision math
#   never changes; drawRing scales art so the painted hole lands on the
#   gameplay hole exactly. Width is pre-squashed to RING.aspect (0.55).
import bpy, sys, math, os
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]

HOLE_FRAC = 0.578          # must match RING.holeFrac
ASPECT    = 0.55           # must match RING.aspect
R_MAJOR   = 1.0
R_MINOR   = R_MAJOR * (1 - HOLE_FRAC) / (1 + HOLE_FRAC)   # -> hole frac exact
RES       = 1200

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_torus_add(
    major_radius=R_MAJOR, minor_radius=R_MINOR,
    major_segments=96, minor_segments=48,
    rotation=(math.radians(90), 0, 0))     # face the -Y camera
ring = bpy.context.object
ring.scale = (ASPECT, 1, 1)
for f in ring.data.polygons:
    f.use_smooth = True

m = bpy.data.materials.new("Gold")
m.use_nodes = True
b = m.node_tree.nodes["Principled BSDF"]
gold = tuple(v ** 2.2 for v in (0.95, 0.72, 0.18))      # sRGB->linear
b.inputs["Base Color"].default_value = (*gold, 1)
b.inputs["Roughness"].default_value = 0.22
try:
    b.inputs["Coat Weight"].default_value = 0.6         # candy gloss (name varies by version)
except KeyError:
    try:
        b.inputs["Clearcoat"].default_value = 0.6
    except KeyError:
        pass
ring.data.materials.append(m)


def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)

light("Key", 'SUN', (-4, -3, 5), 3.0, rot=(42, 0, 38))
light("Fill", 'AREA', (4, -2, 1), 90, rot=(65, 0, -55), color=(0.75, 0.84, 1.0))
light("Rim", 'AREA', (0, 3.5, 2), 140, rot=(-40, 0, 180))

world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.10
bpy.context.scene.world = world

cam_d = bpy.data.cameras.new("Cam")
cam_d.type = 'ORTHO'
outer_h = 2 * (R_MAJOR + R_MINOR)                        # world-units tall
cam_d.ortho_scale = outer_h * 1.01                       # near-tight crop
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
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)

# report the hole's pixel height at this resolution so the JS anchor can be exact
inner_h = 2 * (R_MAJOR - R_MINOR)
print(f"METRICS outer_frac={outer_h / (outer_h * 1.01):.4f} "
      f"hole_px={int(RES / 1.01 * HOLE_FRAC)} out_px={int(RES / 1.01)}")
