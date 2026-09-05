# Bake an 8-frame animated hero strip (penguin pilot + mini plane).
#
#   blender --background --python tools/bake_hero_animated.py -- [outdir]
#
# Default outdir: /tmp/opencode/hero_anim
# Packs images/hero-strip-3d-v7.webp (8×520).
import bpy, sys, math, os, subprocess
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = argv[0] if argv else "/tmp/opencode/hero_anim"
TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
CELLS = 8
RES = 1040
YAW_FIX = 0

PALETTE = {   # sRGB…
    "plane_blue":  (0.23, 0.55, 0.86, 1),
    "orange":      (1.00, 0.48, 0.27, 1),
    "snow":        (0.96, 0.98, 1.00, 1),
    "navy":        (0.06, 0.16, 0.34, 1),
    "leather":     (0.33, 0.20, 0.10, 1),
    "strap":       (0.20, 0.14, 0.09, 1),
    "scarf":       (0.91, 0.26, 0.21, 1),
    "gold":        (0.85, 0.65, 0.25, 1),
    "white":       (0.97, 0.97, 0.97, 1),
    "dark":        (0.02, 0.02, 0.03, 1),
}
# Blender reads material colors as LINEAR.
PALETTE = {k: tuple(v ** 2.2 if i < 3 else v for i, v in enumerate(c)) for k, c in PALETTE.items()}


def mat(name, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    # strip trailing _N from unique names like scarf.001 → look up base key
    key = name.split(".")[0]
    if key.endswith("_blur"):
        key = "gold"
    rgba = list(PALETTE.get(key, PALETTE["dark"]))
    rgba[3] = alpha
    b.inputs["Base Color"].default_value = tuple(rgba[:3]) + (1,)
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Roughness"].default_value = 0.85 if key == "gold" else 0.5
    try:
        b.inputs["Metallic"].default_value = 0.8 if key == "gold" else 0.0
    except KeyError:
        pass
    if alpha < 0.95:
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
        try:
            m.show_transparent_back = False
        except Exception:
            pass
    return m


def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), mkey=None, alpha=1.0):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, depth=2)
    elif kind == 'cyl':
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=2)
    elif kind == 'torus':
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.12,
                                         major_segments=32, minor_segments=12)
    elif kind == 'cube':
        bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    o.scale = scale
    o.data.materials.append(mat(mkey or name, alpha=alpha))
    for mod_kind, params in (('BEVEL', dict(width=0.05, segments=4)),
                             ('SUBSURF', dict(levels=2))):
        if kind == 'cube' and mod_kind == 'BEVEL' or kind != 'cube':
            m2 = o.modifiers.new(mod_kind, mod_kind)
            for k, v in params.items():
                setattr(m2, k, v)
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def empty(name, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o


def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1), size=2):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    if kind == 'AREA':
        d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)
    return o


bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------- plane (model_hero layout; nose → -X) ----------------
parts = []
parts.append(prim("fuselage", 'sphere', (0.15, 0, 0.10), scale=(1.25, 0.52, 0.50), mkey="plane_blue"))
parts.append(prim("nose",     'sphere', (-1.28, 0, 0.10), scale=(0.21, 0.31, 0.29), mkey="orange"))
parts.append(prim("wing",          'cube',  (0.05, 0, 0.13), scale=(0.50, 1.45, 0.09), mkey="white"))
parts.append(prim("wingtip_l",     'sphere', (0.05, -1.40, 0.16), scale=(0.42, 0.16, 0.10), mkey="white"))
parts.append(prim("wingtip_r",     'sphere', (0.05, 1.40, 0.16), scale=(0.42, 0.16, 0.10), mkey="white"))
parts.append(prim("fin",           'sphere', (1.33, 0, 0.58), rot=(-16, 0, 0), scale=(0.26, 0.05, 0.38), mkey="orange"))
parts.append(prim("tail",          'cube',  (1.28, 0, 0.16), scale=(0.24, 0.85, 0.06), mkey="white"))
parts.append(prim("wheel_pant_l",  'sphere', (-0.25, -0.42, -0.52), scale=(0.17, 0.11, 0.19), mkey="orange"))
parts.append(prim("wheel_pant_r",  'sphere', (-0.25, 0.42, -0.52), scale=(0.17, 0.11, 0.19), mkey="orange"))
parts.append(prim("wheel_l",       'sphere', (-0.25, -0.50, -0.60), scale=(0.10, 0.05, 0.10), mkey="dark"))
parts.append(prim("wheel_r",       'sphere', (-0.25, 0.50, -0.60), scale=(0.10, 0.05, 0.10), mkey="dark"))

# ---------------- penguin pilot ----------------
parts.append(prim("body",      'sphere', (-0.12, 0, 0.78), scale=(0.40, 0.36, 0.46), mkey="navy"))
parts.append(prim("belly",     'sphere', (-0.31, 0, 0.68), scale=(0.25, 0.27, 0.35), mkey="snow"))
parts.append(prim("head",      'sphere', (-0.16, 0, 1.32), scale=(0.30, 0.29, 0.30), mkey="navy"))
parts.append(prim("beak",      'cone',   (-0.50, 0, 1.30), rot=(0, -90, 0), scale=(0.11, 0.10, 0.24), mkey="orange"))
parts.append(prim("eye_l",     'sphere', (-0.34, -0.16, 1.40), scale=(0.105, 0.105, 0.115), mkey="white"))
parts.append(prim("pupil_l",   'sphere', (-0.41, -0.18, 1.40), scale=(0.05, 0.05, 0.055), mkey="dark"))
parts.append(prim("eye_r",     'sphere', (-0.34, 0.16, 1.40), scale=(0.105, 0.105, 0.115), mkey="white"))
parts.append(prim("pupil_r",   'sphere', (-0.41, 0.18, 1.40), scale=(0.05, 0.05, 0.055), mkey="dark"))
parts.append(prim("cap",       'sphere', (-0.13, 0, 1.47), scale=(0.315, 0.305, 0.235), mkey="leather"))
parts.append(prim("strap",     'torus',  (-0.13, 0, 1.47), rot=(0, 90, 0), scale=(0.30, 0.30, 0.30), mkey="strap"))
parts.append(prim("lens_l",    'cyl',    (-0.33, -0.14, 1.56), rot=(0, 90, 18), scale=(0.09, 0.045, 0.09), mkey="gold"))
parts.append(prim("lens_r",    'cyl',    (-0.33, 0.14, 1.56), rot=(0, 90, -18), scale=(0.09, 0.045, 0.09), mkey="gold"))
parts.append(prim("scarf",     'torus',  (-0.28, 0, 1.03), rot=(12, 0, 0), scale=(0.26, 0.26, 0.26), mkey="scarf"))

# ---------------- animatable extras ----------------
# Flipper pivots at shoulders; mesh tip extends ±Y.
flipper_l = empty("flipper_l", (-0.10, -0.30, 0.88))
flipper_r = empty("flipper_r", (-0.10,  0.30, 0.88))
fl_mesh = prim("flipper_l_mesh", 'sphere', (0, -0.22, 0), scale=(0.12, 0.28, 0.08), mkey="navy")
fr_mesh = prim("flipper_r_mesh", 'sphere', (0,  0.22, 0), scale=(0.12, 0.28, 0.08), mkey="navy")
fl_mesh.parent = flipper_l
fr_mesh.parent = flipper_r

# Scarf ribbons trailing aft (+X) from the neck knot.
scarf_tail_0 = prim("scarf_tail_0", 'cube', (0.05, -0.06, 0.98),
                    rot=(10, 8, -18), scale=(0.22, 0.045, 0.055), mkey="scarf")
scarf_tail_1 = prim("scarf_tail_1", 'cube', (0.18,  0.07, 0.94),
                    rot=(-8, -6, 22), scale=(0.18, 0.04, 0.05), mkey="scarf")
scarf0_rest = scarf_tail_0.location.copy()
scarf1_rest = scarf_tail_1.location.copy()
scarf0_rot0 = scarf_tail_0.rotation_euler.copy()
scarf1_rot0 = scarf_tail_1.rotation_euler.copy()

# Prop hub + spinning blades at the nose.
prop_hub = prim("prop_hub", 'cone', (-1.52, 0, 0.10), rot=(0, -90, 0),
                scale=(0.09, 0.09, 0.14), mkey="gold")
prop_spin = empty("prop_spin", (-1.52, 0, 0.10))
blade0 = prim("prop_blade_0", 'cube', (0, 0, 0), scale=(0.02, 0.04, 0.42), mkey="gold")
blade1 = prim("prop_blade_1", 'cube', (0, 0, 0), rot=(90, 0, 0),
              scale=(0.02, 0.04, 0.42), mkey="gold")
blade0.parent = prop_spin
blade1.parent = prop_spin

# Motion-blur disc (translucent; toon skips alpha < 0.95).
prop_blur = prim("prop_blur", 'cyl', (-1.52, 0, 0.10), rot=(0, 90, 0),
                 scale=(0.48, 0.48, 0.015), mkey="gold", alpha=0.35)

# ---------------- ROOT + normalize ----------------
root = empty("ROOT")
for o in parts + [flipper_l, flipper_r, scarf_tail_0, scarf_tail_1,
                  prop_hub, prop_spin, prop_blur]:
    o.parent = root

bpy.context.view_layer.update()
mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
for o in [x for x in bpy.context.scene.objects if x.type == 'MESH']:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
size = max(maxs - mins); center = (mins + maxs) / 2
root.scale = (2.0 / size,) * 3
root.location = tuple(-c * 2.0 / size for c in center)

# ---------------- studio (bake_hero_strip contract) ----------------
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
cam_d.ortho_scale = 2.7
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
print("ENGINE:", sc.render.engine)
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
try:
    sc.view_settings.view_transform = 'Standard'
except Exception:
    pass
try:
    sc.view_settings.exposure = 0.25
except Exception:
    pass
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

sys.path.insert(0, TOOLS)
import toon
toon.toonify_scene(outline_frac=0.018, skip_names=("prop_blur",))

# ---------------- poses ----------------
# (pitch, roll) — same Euler convention as bake_hero_strip
POSES = [
    (0, 0), (4, 2), (-2, -3), (3, 1),  # 0-3 cruise with light bob + flap
    (22, 0), (20, 4),                  # 4-5 climb — nose clearly up
    (10, 42),                          # 6 bank — strong roll toward camera
    (-24, 0),                          # 7 dive — nose clearly down
]

os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(os.path.join(REPO, "images"), exist_ok=True)

for i in range(CELLS):
    pitch, roll = POSES[i]
    root.rotation_euler = Euler((math.radians(roll), math.radians(YAW_FIX + pitch), 0), 'ZYX')

    t = i / 4.0 * 2 * math.pi
    fl_e = Euler((0, 0, 0))
    fr_e = Euler((0, 0, 0))
    if i <= 3:
        amp = math.radians(48)
        fl_e.x =  math.sin(t) * amp
        fr_e.x = -math.sin(t) * amp
        scarf_tail_0.rotation_euler = Euler((
            scarf0_rot0.x + math.sin(t) * math.radians(18),
            scarf0_rot0.y,
            scarf0_rot0.z + math.sin(t + 0.4) * math.radians(22),
        ))
        scarf_tail_1.rotation_euler = Euler((
            scarf1_rot0.x + math.sin(t + 1.1) * math.radians(20),
            scarf1_rot0.y,
            scarf1_rot0.z + math.sin(t + 0.7) * math.radians(24),
        ))
        scarf_tail_0.location = scarf0_rest + Vector((math.sin(t) * 0.03, 0, math.sin(t) * 0.04))
        scarf_tail_1.location = scarf1_rest + Vector((math.sin(t + 0.9) * 0.035, 0, math.sin(t + 0.9) * 0.05))
    elif i <= 5:
        amp = math.radians(55)
        phase = (i - 4) / 2.0 * 2 * math.pi
        fl_e.x =  math.sin(phase + 0.3) * amp
        fr_e.x = -math.sin(phase + 0.3) * amp
        # scarf hangs down behind the climb
        scarf_tail_0.rotation_euler = Euler((
            scarf0_rot0.x + math.radians(25), scarf0_rot0.y, scarf0_rot0.z))
        scarf_tail_1.rotation_euler = Euler((
            scarf1_rot0.x + math.radians(30), scarf1_rot0.y, scarf1_rot0.z))
        scarf_tail_0.location = scarf0_rest + Vector((0.04, 0, -0.06))
        scarf_tail_1.location = scarf1_rest + Vector((0.05, 0, -0.08))
    elif i == 6:
        fl_e.x = math.radians(35)
        fr_e.x = math.radians(-10)
        scarf_tail_0.rotation_euler = Euler((
            scarf0_rot0.x, scarf0_rot0.y, scarf0_rot0.z + math.radians(18)))
        scarf_tail_1.rotation_euler = Euler((
            scarf1_rot0.x, scarf1_rot0.y, scarf1_rot0.z + math.radians(10)))
        scarf_tail_0.location = scarf0_rest + Vector((0.02, -0.04, 0))
        scarf_tail_1.location = scarf1_rest + Vector((0.02, -0.02, 0))
    else:  # dive — swept back + lofted scarf
        fl_e.x = math.radians(-18); fl_e.z = math.radians(12)
        fr_e.x = math.radians(18);  fr_e.z = math.radians(-12)
        scarf_tail_0.rotation_euler = Euler((
            scarf0_rot0.x - math.radians(28), scarf0_rot0.y, scarf0_rot0.z))
        scarf_tail_1.rotation_euler = Euler((
            scarf1_rot0.x - math.radians(32), scarf1_rot0.y, scarf1_rot0.z))
        scarf_tail_0.location = scarf0_rest + Vector((-0.02, 0, 0.10))
        scarf_tail_1.location = scarf1_rest + Vector((-0.01, 0, 0.12))
    flipper_l.rotation_euler = fl_e
    flipper_r.rotation_euler = fr_e

    prop_spin.rotation_euler = Euler((math.radians(i * 110), 0, 0))

    sc.render.filepath = os.path.join(OUTDIR, f"f{i}.png")
    bpy.ops.render.render(write_still=True)
    print("frame", i)

frames = [os.path.join(OUTDIR, f"f{i}.png") for i in range(CELLS)]
out = os.path.join(REPO, "images", "hero-strip-3d-v7.webp")
subprocess.check_call([
    "python3", os.path.join(TOOLS, "_pack_strip.py"),
    "520", "520", out, *frames,
])
print("PACKED", out)
print("DONE")
