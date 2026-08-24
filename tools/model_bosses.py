# Models + bakes the boss fleet (roadmap #5): cruiser, gun deck, dreadnought —
# brass steampunk builds from primitives, one fresh render each. Damage states
# are generated in tools/compose_bosses.py (soot + embers over the fresh bake).
#
#   blender --background --python tools/model_bosses.py -- <out_dir>
#
# Contract: the game paints the muzzle bore glow at fractions (muzX, muzY) of
# the sprite: cruiser (-.24,-.18), gun deck (-.34,.04), dreadnought (-.42,.08).
# Each builder prints its bore world position + ortho scale; compose_bosses.py
# pads the tight crop so the bore lands on those fractions exactly, keeping the
# JS constants valid for BOTH art sets.
import bpy, sys, math
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]
PX_PER_UNIT = 300          # render density: RES = ortho_scale * this

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        continue
else:
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

def lin(*rgb):
    return tuple(v ** 2.2 for v in rgb)

def mat(name, rgb, rough=0.35, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(*rgb), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(*rgb), 1)
        b.inputs["Emission Strength"].default_value = emit
    return m

M = {
    "brass":  mat("brass", (0.78, 0.56, 0.22), 0.40, 0.70),
    "bronze": mat("bronze", (0.42, 0.27, 0.13), 0.50, 0.65),
    "gold":   mat("gold", (0.90, 0.70, 0.28), 0.30, 0.80),
    "dark":   mat("dark", (0.05, 0.04, 0.03), 0.85, 0.2),
    "window": mat("window", (1.0, 0.62, 0.18), 0.5, 0.0, emit=3.0),
    "copper": mat("copper", (0.66, 0.37, 0.20), 0.42, 0.70),
}

def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), mkey="brass"):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1)
    elif kind == 'cube':
        bpy.ops.mesh.primitive_cube_add()
    elif kind == 'cyl':
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=1)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=1, radius2=0, depth=1)
    elif kind == 'torus':
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.22,
                                         major_segments=64, minor_segments=28)
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    o.scale = scale
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M[mkey])
    return o

def ring_x(name, x, r, minor, mkey="bronze"):
    """decorative band around a barrel lying along X"""
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=minor,
                                     major_segments=64, minor_segments=24,
                                     rotation=(0, math.radians(90), 0))
    o = bpy.context.object; o.name = name; o.location = (x, 0, 0)
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M[mkey])
    return o

def rivet_row(name, x0, x1, z, y, r=0.05, n=7, mkey="gold"):
    objs = []
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        objs.append(prim(f"{name}{i}", 'sphere', (x, y, z), scale=(r, r, r), mkey=mkey))
    return objs

def build_cruiser():
    """Boss 1 — the hanging gatling pod. Bore mouth faces -X.
    Units: cylinder scale=(radiusY?, ...) — for rot=(0,90,0): (worldZ_radius,
    worldY_radius, FULL length along X). Cube scale = HALF edge. Cone depth scale = FULL length."""
    objs = []
    objs.append(prim("barrel", 'cyl', (0.2, 0, 0), rot=(0, 90, 0), scale=(0.55, 0.55, 2.2), mkey="brass"))
    objs.append(prim("breach", 'cyl', (1.45, 0, 0), rot=(0, 90, 0), scale=(0.70, 0.70, 0.55), mkey="bronze"))
    objs.append(prim("breachcap", 'sphere', (1.75, 0, 0), scale=(0.30, 0.34, 0.66), mkey="bronze"))
    objs.append(ring_x("muzzring", -0.88, 0.60, 0.10, "gold"))
    objs.append(ring_x("midring", -0.45, 0.585, 0.07, "gold"))
    objs.append(ring_x("midring2", 0.75, 0.585, 0.07, "bronze"))
    objs.append(prim("bore", 'cyl', (-0.94, 0, 0), rot=(0, 90, 0), scale=(0.42, 0.42, 0.06), mkey="dark"))
    objs.append(prim("drill", 'cone', (-1.30, 0, 0), rot=(0, -90, 0), scale=(0.30, 0.30, 0.55), mkey="gold"))
    objs.append(prim("housing", 'cube', (0.45, 0, 0.80), scale=(0.28, 0.25, 0.19), mkey="bronze"))
    objs.append(prim("dome", 'sphere', (0.45, 0, 1.00), scale=(0.24, 0.24, 0.20), mkey="brass"))
    objs.append(prim("stack", 'cyl', (1.10, 0, 0.75), rot=(0, 90, 0), scale=(0.16, 0.16, 0.50), mkey="copper"))
    objs.append(prim("pipe1", 'cyl', (0.3, 0, -0.62), rot=(0, 90, 0), scale=(0.10, 0.10, 2.0), mkey="copper"))
    objs.append(prim("pipe2", 'cyl', (0.3, 0, -0.80), rot=(0, 90, 0), scale=(0.07, 0.07, 1.6), mkey="bronze"))
    objs.append(prim("hanger", 'cube', (0.45, 0, 1.12), scale=(0.08, 0.15, 0.15), mkey="dark"))
    objs += rivet_row("riv", -0.7, 1.1, 0.30, -0.50, 0.05, 8)
    objs += rivet_row("rivb", -0.7, 1.1, -0.30, -0.50, 0.05, 8)
    return objs, (-0.94, 0.0)

def build_gundeck():
    """Boss 2 — the broadside gun-deck segment. Bore faces -X."""
    objs = []
    objs.append(prim("hull", 'cyl', (0.2, 0, 0), rot=(0, 90, 0), scale=(0.92, 0.92, 2.8), mkey="brass"))
    objs.append(prim("hullplate", 'cube', (0.55, -0.78, 0.35), scale=(0.45, 0.16, 0.25), mkey="bronze"))
    objs.append(prim("hullplate2", 'cube', (1.05, -0.76, -0.3), scale=(0.30, 0.15, 0.20), mkey="bronze"))
    objs.append(ring_x("muzzring", -1.18, 0.98, 0.13, "gold"))
    objs.append(ring_x("ring2", -0.7, 0.96, 0.09, "gold"))
    objs.append(ring_x("ring3", 0.4, 0.95, 0.09, "bronze"))
    objs.append(prim("bore", 'cyl', (-1.24, 0, 0), rot=(0, 90, 0), scale=(0.68, 0.68, 0.08), mkey="dark"))
    objs.append(prim("spike", 'cone', (-1.60, 0, 0), rot=(0, -90, 0), scale=(0.22, 0.22, 0.5), mkey="gold"))
    # top tower + dome
    objs.append(prim("tower", 'cyl', (0.35, 0, 1.15), scale=(0.42, 0.42, 1.1), mkey="bronze"))
    objs.append(prim("towerring", 'cyl', (0.35, 0, 0.92), scale=(0.52, 0.52, 0.10), mkey="gold"))
    objs.append(prim("dome", 'sphere', (0.35, 0, 1.75), scale=(0.30, 0.30, 0.26), mkey="brass"))
    objs.append(prim("mast", 'cone', (0.35, 0, 2.12), scale=(0.07, 0.07, 0.36), mkey="gold"))
    # secondary cannons poking left, below/above the main bore
    for i, (zz, xx) in enumerate(((-0.62, -0.9), (0.62, -0.75), (-0.25, 0.9))):
        objs.append(prim(f"sec{i}", 'cyl', (xx, 0, zz), rot=(0, 90, 0), scale=(0.17, 0.17, 0.7), mkey="copper"))
        objs.append(prim(f"secring{i}", 'torus', (xx - 0.36, 0, zz), rot=(0, 90, 0),
                         scale=(0.19, 0.19, 0.19), mkey="gold"))
    # glowing windows on the camera-facing side
    for i in range(5):
        objs.append(prim(f"win{i}", 'cube', (-0.4 + i * 0.38, -0.86, 0.42), scale=(0.07, 0.03, 0.10), mkey="window"))
    for i in range(4):
        objs.append(prim(f"winb{i}", 'cube', (-0.2 + i * 0.38, -0.86, -0.38), scale=(0.07, 0.03, 0.10), mkey="window"))
    # engine ring at the right end
    bpy.ops.mesh.primitive_torus_add(major_radius=0.85, minor_radius=0.20,
                                     major_segments=64, minor_segments=28,
                                     rotation=(0, math.radians(90), 0))
    o = bpy.context.object; o.name = "engine"; o.location = (1.85, 0, 0)
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M["bronze"]); objs.append(o)
    objs.append(prim("englow", 'cyl', (1.88, 0, 0), rot=(0, 90, 0), scale=(0.62, 0.62, 0.06), mkey="window"))
    # keel fins
    objs.append(prim("keel", 'cube', (0.4, 0, -1.02), scale=(0.45, 0.10, 0.16), mkey="bronze"))
    objs.append(prim("keel2", 'cube', (1.3, 0, -0.95), scale=(0.20, 0.09, 0.12), mkey="bronze"))
    objs += rivet_row("riv", -0.9, 1.4, 0.55, -0.86, 0.055, 9)
    return objs, (-1.24, 0.0)

def build_dread():
    """Boss 3 — the Dreadnought. Bore faces -X."""
    objs = []
    objs.append(prim("hull", 'cyl', (0.4, 0, 0), rot=(0, 90, 0), scale=(1.05, 1.05, 4.2), mkey="brass"))
    objs.append(prim("bow", 'cone', (-2.35, 0, 0), rot=(0, -90, 0), scale=(1.0, 1.0, 0.7), mkey="brass"))
    objs.append(prim("bore", 'cyl', (-2.04, 0, 0), rot=(0, 90, 0), scale=(0.72, 0.72, 0.10), mkey="dark"))
    objs.append(ring_x("muzzring", -1.95, 0.80, 0.12, "gold"))
    objs.append(ring_x("ring2", -1.35, 1.08, 0.10, "gold"))
    objs.append(ring_x("ring3", -0.3, 1.07, 0.09, "bronze"))
    objs.append(ring_x("ring4", 1.1, 1.07, 0.09, "bronze"))
    # armor plates camera-side (accents, not covers — the hull must read as a cylinder)
    objs.append(prim("plate1", 'cube', (0.3, -0.94, 0.42), scale=(0.575, 0.15, 0.275), mkey="bronze"))
    objs.append(prim("plate2", 'cube', (1.75, -0.90, -0.28), scale=(0.375, 0.14, 0.225), mkey="bronze"))
    # two towers
    objs.append(prim("tower1", 'cyl', (0.1, 0, 1.35), scale=(0.50, 0.50, 1.3), mkey="bronze"))
    objs.append(prim("tdome1", 'sphere', (0.1, 0, 2.10), scale=(0.34, 0.34, 0.30), mkey="brass"))
    objs.append(prim("tmast1", 'cone', (0.1, 0, 2.52), scale=(0.08, 0.08, 0.42), mkey="gold"))
    objs.append(prim("tower2", 'cyl', (1.5, 0, 1.27), scale=(0.38, 0.38, 1.0), mkey="bronze"))
    objs.append(prim("tdome2", 'sphere', (1.5, 0, 1.87), scale=(0.26, 0.26, 0.22), mkey="brass"))
    # secondary battery
    for i, (zz, xx) in enumerate(((-0.75, -1.2), (0.78, -0.95), (-0.3, -0.4), (0.35, 0.9), (-0.75, 1.6))):
        objs.append(prim(f"sec{i}", 'cyl', (xx, 0, zz), rot=(0, 90, 0), scale=(0.19, 0.19, 0.85), mkey="copper"))
    # window rows
    for r, zz in ((0, 0.55), (1, -0.45)):
        for i in range(6):
            objs.append(prim(f"win{r}{i}", 'cube', (-0.8 + i * 0.5, -0.97, zz), scale=(0.075, 0.03, 0.11), mkey="window"))
    # engine rings
    for k, (xx, rr) in enumerate(((2.75, 1.0), (2.35, 0.72))):
        bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=0.20,
                                         major_segments=64, minor_segments=28,
                                         rotation=(0, math.radians(90), 0))
        o = bpy.context.object; o.name = f"eng{k}"; o.location = (xx, 0, 0)
        for f in o.data.polygons:
            f.use_smooth = True
        o.data.materials.append(M["bronze"]); objs.append(o)
    objs.append(prim("englow", 'cyl', (2.78, 0, 0), rot=(0, 90, 0), scale=(0.72, 0.72, 0.06), mkey="window"))
    # keel + chains hint (dangling cones)
    objs.append(prim("keel", 'cube', (0.6, 0, -1.18), scale=(0.65, 0.12, 0.19), mkey="bronze"))
    for i, xx in enumerate((-0.2, 0.9, 2.0)):
        objs.append(prim(f"drop{i}", 'cone', (xx, 0, -1.55), rot=(180, 0, 0), scale=(0.09, 0.45, 0.09), mkey="gold"))
    objs += rivet_row("riv", -1.5, 2.3, 0.62, -1.0, 0.06, 10)
    return objs, (-2.04, 0.0)

def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    sc.collection.objects.link(o)

light("Key", 'SUN', (-4, -3, 5), 2.6, rot=(42, 0, 38))
light("Front", 'AREA', (0, -7, 2), 450, rot=(72, 0, 0), color=(1.0, 0.97, 0.92))
light("Fill", 'AREA', (5, -3, 1), 180, rot=(65, 0, -55), color=(0.78, 0.85, 1.0))
light("Rim", 'AREA', (0, 4, 2.5), 260, rot=(-40, 0, 180))
world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
sc.world = world

cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0, -9, 0); cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam); sc.camera = cam

import os
os.makedirs(OUT, exist_ok=True)

def render(objs, bore, width, path):
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import toon
    toon.toonify_objects([o for o in objs if o.type == "MESH"], outline_frac=0.010)
    s = width * 1.03
    cam_d.ortho_scale = s
    sc.render.resolution_x = sc.render.resolution_y = int(s * PX_PER_UNIT) // 16 * 16
    sc.render.filepath = path
    sc.frame_set(1)
    bpy.ops.render.render(write_still=True)
    print(f"BORE {os.path.basename(path)} {bore[0]:.4f} {bore[1]:.4f} {s:.4f} {sc.render.resolution_x}")
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

for name, builder, width in (("cruiser", build_cruiser, 3.7),
                             ("gundeck", build_gundeck, 4.1),
                             ("dread", build_dread, 5.6)):
    objs, bore = builder()
    render(objs, bore, width, f"{OUT}/boss3d-{name}.png")
    print(name, "done")
print("ALL BOSSES BAKED")
