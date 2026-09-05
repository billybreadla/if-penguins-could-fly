# Bake 16-frame animated strips for the collectible props (ring / fish / mine).
#
#   blender --background --python tools/bake_props_animated.py -- [outdir] [which]
#
# outdir default /tmp/opencode/props_anim
# which: all (default) | ring | fish | mine
#
# Packs into images/ via tools/_pack_strip.py:
#   ring-3d-v5.webp      16×400  turntable (holeFrac contract still 0.578)
#   fish3d-swim-v1.webp  16×256  swim cycle (hero blue/gold; compose_fish can recolor)
#   mine-3d-v1.webp      16×256  tumble + beacon pulse
import bpy, sys, math, os, subprocess
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = argv[0] if len(argv) > 0 else "/tmp/opencode/props_anim"
WHICH = argv[1] if len(argv) > 1 else "all"

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
CELLS = 16
RES = 800

# Ring geometry contract with the engine (index.html RING.holeFrac / RING.aspect).
# Animated strip cells are square 400x400 (game rescales); the torus itself still
# obeys hole height / outer height == HOLE_FRAC so collision math stays valid.
HOLE_FRAC = 0.578
ASPECT = 0.55
R_MAJOR = 1.0
R_MINOR = R_MAJOR * (1 - HOLE_FRAC) / (1 + HOLE_FRAC)


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


def gold_mat():
    m = mat("Gold", (0.95, 0.72, 0.18), rough=0.22, metal=0.9)
    b = m.node_tree.nodes["Principled BSDF"]
    try:
        b.inputs["Coat Weight"].default_value = 0.6
    except KeyError:
        try:
            b.inputs["Clearcoat"].default_value = 0.6
        except KeyError:
            pass
    return m


def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), material=None):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1)
    elif kind == 'cube':
        bpy.ops.mesh.primitive_cube_add()
    elif kind == 'cyl':
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=1)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, radius2=0, depth=1)
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
    if material is not None:
        o.data.materials.append(material)
    return o


def star_prism(name, material, R=1.0, r=0.45, depth=0.30):
    """5-point star prism facing the camera (star plane = XZ)."""
    pts = []
    for i in range(10):
        rad = R if i % 2 == 0 else r
        a = math.pi / 2 + i * math.pi / 5
        pts.append((rad * math.cos(a), rad * math.sin(a)))
    verts = [(x, -depth / 2, z) for (x, z) in pts] + [(x, depth / 2, z) for (x, z) in pts]
    faces = [tuple(range(9, -1, -1)), tuple(range(10, 20))]
    for i in range(10):
        j = (i + 1) % 10
        faces.append((i, j, j + 10, i + 10))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    bevel = o.modifiers.new("Bevel", 'BEVEL')
    bevel.width = 0.02; bevel.segments = 2; bevel.limit_method = 'ANGLE'
    for f in me.polygons:
        f.use_smooth = True
    o.data.materials.append(material)
    return o


def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(o)
    return o


def empty(name, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o


def reset_scene(world_strength=0.30):
    """Fresh empty scene + EEVEE + transparent PNG + studio lights/camera."""
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

    light("Key", 'SUN', (-4, -3, 5), 3.0, rot=(42, 0, 38))
    light("Front", 'AREA', (0, -6, 1.5), 260, rot=(72, 0, 0), color=(1.0, 0.98, 0.94))
    light("Fill", 'AREA', (4, -2, 1), 90, rot=(65, 0, -55), color=(0.75, 0.84, 1.0))
    light("Rim", 'AREA', (0, 3.5, 2), 140, rot=(-40, 0, 180))

    world = bpy.data.worlds.new("W"); world.use_nodes = True
    # metals need world ≥ 0.25 or the toon bands crush to black
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = world_strength
    sc.world = world

    cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("Cam", cam_d)
    cam.location = (0, -8, 0); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.collection.objects.link(cam); sc.camera = cam
    return sc, cam_d


def toonify(outline_frac=0.012, skip_names=()):
    sys.path.insert(0, TOOLS)
    import toon
    toon.toonify_scene(outline_frac=outline_frac, skip_names=skip_names)


def pack_strip(cell, out_name, frame_dir):
    frames = [os.path.join(frame_dir, f"f{i:02d}.png") for i in range(CELLS)]
    out = os.path.join(REPO, "images", out_name)
    cmd = ["python3", os.path.join(TOOLS, "_pack_strip.py"),
           str(cell), str(cell), out, *frames]
    subprocess.check_call(cmd)
    print("PACKED", out)


def render_frames(sc, frame_dir, animate_fn):
    os.makedirs(frame_dir, exist_ok=True)
    for i in range(CELLS):
        animate_fn(i)
        sc.render.filepath = os.path.join(frame_dir, f"f{i:02d}.png")
        bpy.ops.render.render(write_still=True)
        print("frame", i)


# ---------------- ring: 16-frame turntable ----------------

def bake_ring():
    sc, cam_d = reset_scene(world_strength=0.30)
    root = empty("RingRoot")

    bpy.ops.mesh.primitive_torus_add(
        major_radius=R_MAJOR, minor_radius=R_MINOR,
        major_segments=96, minor_segments=48,
        rotation=(math.radians(90), 0, 0))
    ring = bpy.context.object
    ring.name = "ring"
    ring.scale = (ASPECT, 1, 1)
    for f in ring.data.polygons:
        f.use_smooth = True
    ring.data.materials.append(gold_mat())
    ring.parent = root

    # thin emissive energy star in the hole — spins faster than the turntable
    energy_m = mat("Energy", (0.35, 0.95, 1.0), rough=0.2, emit=4.0)
    energy_spin = empty("EnergySpin")
    energy_spin.parent = root
    energy = star_prism("energy", energy_m, R=0.38, r=0.16, depth=0.10)
    energy.parent = energy_spin

    outer_h = 2 * (R_MAJOR + R_MINOR)
    cam_d.ortho_scale = outer_h * 1.08
    toonify(outline_frac=0.012, skip_names=("energy",))

    frame_dir = os.path.join(OUTDIR, "ring")
    cell_step = 360.0 / CELLS

    def animate(i):
        root.rotation_euler = Euler((0, 0, math.radians(-i * cell_step)))
        # +i*2 cells of local spin (through-hole / camera axis = Y)
        energy_spin.rotation_euler = Euler((0, math.radians(i * 2 * cell_step), 0))

    render_frames(sc, frame_dir, animate)
    pack_strip(400, "ring-3d-v5.webp", frame_dir)
    print("RING DONE  holeFrac=", HOLE_FRAC, "aspect=", ASPECT)


# ---------------- fish: 16-frame swim (hero blue/gold) ----------------

def bake_fish():
    # One hero rainbow fish (blue/gold). compose_fish / compose_fish_v2 can
    # recolor the strip into the 7 painted palettes later.
    sc, cam_d = reset_scene(world_strength=0.28)
    body_m = mat("fb", (0.10, 0.35, 0.88), 0.32)
    fin_m = mat("ff", (1.00, 0.76, 0.24), 0.4)
    white = mat("white", (0.96, 0.97, 0.99), 0.3)
    black = mat("black", (0.05, 0.07, 0.12), 0.4)

    root = empty("FishRoot")
    body = prim("body", 'sphere', (0.05, 0, 0), scale=(0.78, 0.38, 0.40), material=body_m)
    head = prim("head", 'sphere', (-0.55, 0, 0.02), scale=(0.42, 0.34, 0.36), material=body_m)

    # tail_fin empty at the rear attachment so Z-rotation flaps the fin mesh
    tail_fin = empty("tail_fin", loc=(0.70, 0, 0.02))
    tail_mesh = prim("tail_mesh", 'sphere', (0.32, 0, 0), scale=(0.38, 0.04, 0.32), material=fin_m)
    tail_mesh.parent = tail_fin

    dorsal = prim("dorsal", 'sphere', (-0.05, 0, 0.42), rot=(-14, 0, 0),
                  scale=(0.36, 0.05, 0.20), material=fin_m)
    pect_l = prim("pect_l", 'sphere', (-0.02, -0.34, -0.06), rot=(0, 18, -40),
                  scale=(0.20, 0.04, 0.11), material=fin_m)
    pect_r = prim("pect_r", 'sphere', (-0.02, 0.34, -0.06), rot=(0, -18, 40),
                  scale=(0.20, 0.04, 0.11), material=fin_m)
    eye = prim("eye", 'sphere', (-0.72, -0.22, 0.12), scale=(0.14, 0.14, 0.14), material=white)
    pupil = prim("pupil", 'sphere', (-0.82, -0.28, 0.12), scale=(0.075, 0.075, 0.075), material=black)

    for o in (body, head, tail_fin, dorsal, pect_l, pect_r, eye, pupil):
        o.parent = root

    cam_d.ortho_scale = 2.9 * 1.05
    toonify(outline_frac=0.016)

    frame_dir = os.path.join(OUTDIR, "fish")

    def animate(i):
        phase = i / CELLS * 2 * math.pi
        tail_fin.rotation_euler.z = math.sin(phase) * math.radians(35)
        # slight body undulation
        root.rotation_euler = Euler((
            math.sin(phase) * math.radians(4),
            math.sin(phase * 2) * math.radians(3),
            math.sin(phase) * math.radians(6),
        ))

    render_frames(sc, frame_dir, animate)
    pack_strip(256, "fish3d-swim-v1.webp", frame_dir)
    print("FISH DONE")


# ---------------- mine: 16-frame tumble ----------------

def bake_mine():
    sc, cam_d = reset_scene(world_strength=0.28)
    dark = mat("mine_dark", (0.10, 0.10, 0.14), rough=0.40, metal=0.80)
    beacon_m = mat("beacon", (1.0, 0.08, 0.05), rough=0.3, emit=2.0)
    beacon_bsdf = beacon_m.node_tree.nodes["Principled BSDF"]

    root = empty("MineRoot")
    core = prim("core", 'sphere', (0, 0, 0), scale=(0.70, 0.70, 0.70), material=dark)
    core.parent = root

    # 12 spikes toward icosahedron-ish directions
    phi = (1 + math.sqrt(5)) / 2
    raw = [
        (0, 1, phi), (0, -1, phi), (0, 1, -phi), (0, -1, -phi),
        (1, phi, 0), (-1, phi, 0), (1, -phi, 0), (-1, -phi, 0),
        (phi, 0, 1), (-phi, 0, 1), (phi, 0, -1), (-phi, 0, -1),
    ]
    core_r, spike_len, spike_r = 0.70, 0.55, 0.13
    for si, d in enumerate(raw):
        direction = Vector(d).normalized()
        tip = direction * (core_r + spike_len * 0.35)
        sp = prim(f"spike{si}", 'cone', tuple(tip),
                  scale=(spike_r, spike_r, spike_len), material=dark)
        sp.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        sp.parent = root

    # red emissive beacon on +Z
    beacon = prim("beacon", 'sphere', (0, 0, core_r + 0.12),
                  scale=(0.16, 0.16, 0.16), material=beacon_m)
    beacon.parent = root

    cam_d.ortho_scale = 2.4
    toonify(outline_frac=0.014, skip_names=("beacon",))

    frame_dir = os.path.join(OUTDIR, "mine")

    def animate(i):
        ang = math.radians(i * 22.5)
        root.rotation_euler = Euler((ang, 0, ang))
        phase = i / CELLS * 2 * math.pi
        beacon_bsdf.inputs["Emission Strength"].default_value = 2.0 + 2.0 * math.sin(phase)

    render_frames(sc, frame_dir, animate)
    pack_strip(256, "mine-3d-v1.webp", frame_dir)
    print("MINE DONE")


# ---------------- main ----------------

os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(os.path.join(REPO, "images"), exist_ok=True)

which = WHICH.lower()
if which in ("all", "ring"):
    bake_ring()
if which in ("all", "fish"):
    bake_fish()
if which in ("all", "mine"):
    bake_mine()
if which not in ("all", "ring", "fish", "mine"):
    raise SystemExit(f"unknown which={WHICH!r}; expected all|ring|fish|mine")

print("ALL ANIMATED PROPS BAKED", which)
