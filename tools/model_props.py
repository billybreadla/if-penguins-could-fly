# Models + bakes the collectible props as tight transparent PNGs (roadmap #4):
#   7 fish color variants, star, magnet, stopwatch (slow), shield.
#
#   blender --background --python tools/model_props.py -- <out_dir>
#
# A second pass (tools/compose_props.py, system python + PIL) fits these into
# images/fish3d_0..6.webp and the powerups-3d.webp atlas. Orientation contract:
# camera looks from -Y, so world -X renders frame-LEFT — fish nose goes at -X,
# matching the painted art files (the game flips fish at draw time).
import bpy, sys, math
from mathutils import Euler, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]
RES = 800

# fish variant palettes sampled from the painted fish_0..6 art: (body, fin)
FISH = [
    ((0.10, 0.35, 0.88), (1.00, 0.76, 0.24)),   # blue + gold
    ((0.94, 0.38, 0.14), (0.75, 0.19, 0.00)),   # orange + red
    ((0.18, 0.48, 0.12), (0.85, 0.79, 0.24)),   # green + khaki
    ((0.96, 0.56, 0.42), (0.94, 0.63, 0.29)),   # coral + amber
    ((0.23, 0.54, 0.54), (0.76, 0.76, 0.56)),   # teal + pale
    ((0.60, 0.60, 0.63), (0.88, 0.85, 0.63)),   # silver + cream
    ((0.35, 0.29, 0.88), (0.94, 0.56, 0.00)),   # violet + orange
]

bpy.ops.wm.read_factory_settings(use_empty=True)
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

def lin(*rgb):                       # sRGB -> linear for Blender materials
    return tuple(v ** 2.2 for v in rgb)

def mat(name, rgb, rough=0.35, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(*rgb), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

M = {
    "steel": mat("steel", (0.86, 0.89, 0.94), 0.30, 0.75),
    "gold":  mat("gold", (0.98, 0.78, 0.20), 0.25, 0.9),
    "white": mat("white", (0.96, 0.97, 0.99), 0.3),
    "black": mat("black", (0.05, 0.07, 0.12), 0.4),
    "blue":  mat("blue", (0.12, 0.44, 0.82), 0.3),
    "dblue": mat("dblue", (0.08, 0.35, 0.66), 0.3),
    "pale":  mat("pale", (0.85, 0.95, 1.00), 0.25),
    "red":   mat("red", (0.90, 0.25, 0.10), 0.3),
}

def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), mkey=None):
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
                                         major_segments=64, minor_segments=32)
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    o.scale = scale
    for f in o.data.polygons:
        f.use_smooth = True
    if mkey:
        o.data.materials.append(M[mkey])
    return o

def star_prism(name, mkey, R=1.0, r=0.45, depth=0.30):
    """5-point star prism facing the camera (star plane = XZ)."""
    pts = []
    for i in range(10):
        rad = R if i % 2 == 0 else r
        a = math.pi / 2 + i * math.pi / 5          # point up (+Z)
        pts.append((rad * math.cos(a), rad * math.sin(a)))
    verts = [(-0.0, 0, 0)]                          # placeholder, replaced below
    verts = [(x, -depth / 2, z) for (x, z) in pts] + [(x, depth / 2, z) for (x, z) in pts]
    faces = [tuple(range(9, -1, -1)), tuple(range(10, 20))]
    for i in range(10):
        j = (i + 1) % 10
        faces.append((i, j, j + 10, i + 10))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    bevel = o.modifiers.new("Bevel", 'BEVEL')
    bevel.width = 0.03; bevel.segments = 3; bevel.limit_method = 'ANGLE'
    for f in me.polygons:
        f.use_smooth = True
    o.data.materials.append(M[mkey])
    return o

# ---------------- builders (each returns (objects, ortho_width)) ----------------

def build_fish(body_rgb, fin_rgb):
    body_m = mat("fb", body_rgb, 0.32)
    fin_m = mat("ff", fin_rgb, 0.4)
    objs = []
    o = prim("body", 'sphere', (0, 0, 0), scale=(0.95, 0.40, 0.42)); o.data.materials.append(body_m); objs.append(o)
    o = prim("tail", 'sphere', (1.02, 0, 0.02), scale=(0.38, 0.04, 0.32)); o.data.materials.append(fin_m); objs.append(o)
    o = prim("dorsal", 'sphere', (-0.05, 0, 0.42), rot=(-14, 0, 0), scale=(0.36, 0.05, 0.20)); o.data.materials.append(fin_m); objs.append(o)
    o = prim("pect", 'sphere', (-0.02, -0.34, -0.06), rot=(0, 18, -40), scale=(0.20, 0.04, 0.11)); o.data.materials.append(fin_m); objs.append(o)
    o = prim("eye", 'sphere', (-0.55, -0.24, 0.13), scale=(0.155, 0.155, 0.155), mkey="white"); objs.append(o)
    o = prim("pupil", 'sphere', (-0.66, -0.30, 0.13), scale=(0.085, 0.085, 0.085), mkey="black"); objs.append(o)
    return objs, 2.9

def build_star():
    return [star_prism("star", "gold")], 2.15

def build_magnet():
    bpy.ops.mesh.primitive_torus_add(major_radius=0.70, minor_radius=0.26,
                                     major_segments=64, minor_segments=32)
    o = bpy.context.object; o.name = "u"
    # bake the X-rotation into the mesh so local coords == world coords,
    # then a face's z really is its height (ring now in the XZ plane)
    o.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
    # true U: remove the upper half (faces + verts), white tips cap the tube ends
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > -0.001],
                     context='FACES')
    bm.to_mesh(o.data); bm.free()
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M["red"])
    o.data.materials.append(M["blue"])
    for f in o.data.polygons:
        f.material_index = 0 if f.center.x < 0 else 1
    objs = [o]
    for sx in (-1, 1):
        t = prim(f"tip{sx}", 'cube', (sx * 0.70, 0, 0.15), scale=(0.30, 0.30, 0.30), mkey="white")
        objs.append(t)
    return objs, 2.1

def build_slow():
    objs = []
    # prim scale is in LOCAL axes: for a cylinder rotated X+90 the local Z is
    # the world depth, local X/Y are the world X/Z radii
    o = prim("case", 'cyl', (0, 0, 0), rot=(90, 0, 0), scale=(0.85, 0.85, 0.35), mkey="blue"); objs.append(o)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.85, minor_radius=0.09,
                                     major_segments=64, minor_segments=24,
                                     rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.name = "bezel"
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M["dblue"]); objs.append(o)
    o = prim("face", 'cyl', (0, -0.19, 0), rot=(90, 0, 0), scale=(0.68, 0.68, 0.06), mkey="pale"); objs.append(o)
    o = prim("crown", 'cyl', (0, 0, 1.00), rot=(90, 0, 0), scale=(0.12, 0.12, 0.20), mkey="dblue"); objs.append(o)
    for sx in (-1, 1):
        o = prim(f"btn{sx}", 'cyl', (sx * 0.68, 0, 0.68), rot=(0, sx * 45, 0), scale=(0.08, 0.08, 0.14), mkey="dblue"); objs.append(o)
    o = prim("hand_m", 'cube', (0.09, -0.24, 0.12), rot=(0, 0, -35), scale=(0.035, 0.015, 0.28), mkey="black"); objs.append(o)
    o = prim("hand_h", 'cube', (-0.09, -0.24, -0.03), rot=(0, 0, 40), scale=(0.045, 0.015, 0.20), mkey="black"); objs.append(o)
    o = prim("hub", 'sphere', (0, -0.25, 0), scale=(0.05, 0.03, 0.05), mkey="black"); objs.append(o)
    for i in range(8):
        a = i * math.pi / 4
        o = prim(f"dot{i}", 'sphere', (0.50 * math.cos(a), -0.23, 0.50 * math.sin(a)), scale=(0.04, 0.02, 0.04), mkey="blue"); objs.append(o)
    # little snowflake: 3 crossed thin bars, low-poly but reads at 60px
    for i, rz in enumerate((0, 60, 120)):
        o = prim(f"flake{i}", 'cube', (0, -0.25, 0), rot=(0, 0, rz), scale=(0.26, 0.012, 0.04), mkey="white"); objs.append(o)
    return objs, 2.15

def build_shield():
    objs = []
    o = prim("disc", 'cyl', (0, 0, 0), rot=(90, 0, 0), scale=(0.90, 0.90, 0.25), mkey="blue"); objs.append(o)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.90, minor_radius=0.11,
                                     major_segments=64, minor_segments=24,
                                     rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.name = "rim"
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M["steel"]); objs.append(o)
    o = prim("boss", 'sphere', (0, -0.16, 0), scale=(0.28, 0.13, 0.28), mkey="steel"); objs.append(o)
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 6
        o = prim(f"riv{i}", 'sphere', (0.68 * math.cos(a), -0.14, 0.68 * math.sin(a)), scale=(0.06, 0.05, 0.06), mkey="steel"); objs.append(o)
    return objs, 2.1

# ---------------- render rig ----------------

def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    sc.collection.objects.link(o)

light("Key", 'SUN', (-4, -3, 5), 3.0, rot=(42, 0, 38))
light("Front", 'AREA', (0, -6, 1.5), 260, rot=(72, 0, 0), color=(1.0, 0.98, 0.94))
light("Fill", 'AREA', (4, -2, 1), 90, rot=(65, 0, -55), color=(0.75, 0.84, 1.0))
light("Rim", 'AREA', (0, 3.5, 2), 140, rot=(-40, 0, 180))
world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.30
sc.world = world

cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0, -8, 0); cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam); sc.camera = cam

def render(objs, width, path):
    cam_d.ortho_scale = width * 1.05
    sc.frame_set(1)
    for o in objs:
        o.hide_render = False
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

import os
os.makedirs(OUT, exist_ok=True)
for i, (body, fin) in enumerate(FISH):
    objs, w = build_fish(body, fin)
    render(objs, w, f"{OUT}/fish_{i}.png")
    print("fish", i, "done")
for name, builder in (("star", build_star), ("magnet", build_magnet),
                      ("slow", build_slow), ("shield", build_shield)):
    objs, w = builder()
    render(objs, w, f"{OUT}/{name}.png")
    print(name, "done")
print("ALL PROPS BAKED")
