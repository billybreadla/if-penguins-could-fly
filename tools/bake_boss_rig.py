# Headless Blender bake: articulated Boss 1 (Aero-Cruiser) + Boss 3 (Titan Dread)
# with fresh / damaged / wrecked states. Packs WebP into repo images/.
#
#   blender --background --python tools/bake_boss_rig.py -- [outdir]
#
# Default outdir: /tmp/opencode/boss_rig
# Bore mouths face -X; camera looks from -Y (ortho). Prints bore world XZ.
import bpy, sys, math, os, subprocess
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/opencode/boss_rig"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "images")
PX_PER_UNIT = 300
RES_CAP = 1600

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
else:
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = 0.15

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toon

toon.TOON_POP = 0.25


def lin(*rgb):
    return tuple(v ** 2.2 for v in rgb)


def mat(name, rgb, rough=0.35, metal=0.0, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(*rgb), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(*rgb), 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 0.95:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            try:
                m.blend_method = "BLEND"
            except Exception:
                pass
    return m


def emit_mat(name, rgb, strength=4.0):
    """Pure emission — skipped by toonify (no Principled BSDF)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(*rgb), 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


M = {
    "brass":   mat("brass", (0.78, 0.56, 0.22), 0.40, 0.70),
    "bronze":  mat("bronze", (0.42, 0.27, 0.13), 0.50, 0.65),
    "gold":    mat("gold", (0.90, 0.70, 0.28), 0.30, 0.80),
    "dark":    mat("dark", (0.05, 0.04, 0.03), 0.85, 0.2),
    "copper":  mat("copper", (0.66, 0.37, 0.20), 0.42, 0.70),
    "window":  mat("window", (1.0, 0.62, 0.18), 0.5, 0.0, emit=3.0),
    "soot":    mat("soot", (0.10, 0.07, 0.05), 0.92, 0.15),
    "sootbrass": mat("sootbrass", (0.28, 0.18, 0.08), 0.70, 0.45),
    "sootbronze": mat("sootbronze", (0.16, 0.10, 0.06), 0.78, 0.40),
    "crack":   mat("crack", (0.04, 0.03, 0.02), 0.95, 0.05),
    "smoke":   mat("smoke", (0.12, 0.10, 0.09), 1.0, 0.0, alpha=0.32),
    "cyan":    emit_mat("cyan", (0.25, 0.85, 1.0), 5.0),
    "furnace": emit_mat("furnace", (1.0, 0.45, 0.08), 6.0),
    "beacon":  emit_mat("beacon", (1.0, 0.12, 0.05), 7.0),
}


def prim(name, kind, loc, rot=(0, 0, 0), scale=(1, 1, 1), mkey="brass"):
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1)
    elif kind == "cube":
        bpy.ops.mesh.primitive_cube_add()
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1, depth=1)
    elif kind == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=1, radius2=0, depth=1)
    elif kind == "torus":
        bpy.ops.mesh.primitive_torus_add(
            major_radius=1, minor_radius=0.22,
            major_segments=48, minor_segments=20,
        )
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
    bpy.ops.mesh.primitive_torus_add(
        major_radius=r, minor_radius=minor,
        major_segments=48, minor_segments=20,
        rotation=(0, math.radians(90), 0),
    )
    o = bpy.context.object
    o.name = name
    o.location = (x, 0, 0)
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(M[mkey])
    return o


def empty(name, loc, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    o.empty_display_size = 0.3
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    sc.collection.objects.link(o)
    return o


def parent_local(child, parent, loc, rot=(0, 0, 0), scale=None):
    child.parent = parent
    child.location = loc
    child.rotation_euler = Euler([math.radians(a) for a in rot])
    if scale is not None:
        child.scale = scale


def rivet_row(name, x0, x1, z, y, r=0.05, n=7, mkey="gold"):
    objs = []
    for i in range(n):
        x = x0 + (x1 - x0) * i / max(n - 1, 1)
        objs.append(prim(f"{name}{i}", "sphere", (x, y, z), scale=(r, r, r), mkey=mkey))
    return objs


def mk_mat(state, clean, dirty):
    if state == "fresh":
        return clean
    if state == "damaged":
        return dirty if dirty else "sootbrass"
    return "soot" if dirty else "sootbronze"


# ---------------------------------------------------------------------------
# Boss 1 — Aero-Cruiser
# ---------------------------------------------------------------------------
def build_cruiser(state="fresh"):
    """Hanging aero-cruiser pod + articulated deck turret. Bore faces -X."""
    objs = []
    hull_m = mk_mat(state, "brass", "sootbrass")
    accent = mk_mat(state, "bronze", "sootbronze")
    trim = mk_mat(state, "gold", "sootbrass")
    pipe_m = mk_mat(state, "copper", "soot")

    # main hull / barrel body
    objs.append(prim("barrel", "cyl", (0.15, 0, 0), rot=(0, 90, 0),
                     scale=(0.58, 0.58, 2.4), mkey=hull_m))
    objs.append(prim("breach", "cyl", (1.50, 0, 0), rot=(0, 90, 0),
                     scale=(0.74, 0.74, 0.58), mkey=accent))
    objs.append(prim("breachcap", "sphere", (1.82, 0, 0),
                     scale=(0.32, 0.36, 0.70), mkey=accent))
    objs.append(ring_x("muzzring", -0.95, 0.63, 0.10, trim))
    objs.append(ring_x("midring", -0.40, 0.61, 0.07, trim))
    objs.append(ring_x("midring2", 0.80, 0.61, 0.07, accent))
    bore = prim("bore", "cyl", (-1.02, 0, 0), rot=(0, 90, 0),
                scale=(0.44, 0.44, 0.07), mkey="dark")
    objs.append(bore)
    objs.append(prim("drill", "cone", (-1.38, 0, 0), rot=(0, -90, 0),
                     scale=(0.28, 0.28, 0.50), mkey=trim))

    # dorsal housing
    objs.append(prim("housing", "cube", (0.35, 0, 0.78),
                     scale=(0.42, 0.32, 0.22), mkey=accent))
    objs.append(prim("dome", "sphere", (0.35, 0, 1.02),
                     scale=(0.28, 0.28, 0.22), mkey=hull_m))

    # stacks (tipped when damaged)
    stack_rot = (12, 18, 8) if state != "fresh" else (0, 0, 0)
    stack_rot2 = (22, -14, -10) if state == "wrecked" else ((8, -6, 4) if state == "damaged" else (0, 0, 0))
    objs.append(prim("stack1", "cyl", (1.05, 0.05, 0.95), rot=stack_rot,
                     scale=(0.14, 0.14, 0.55), mkey=pipe_m))
    objs.append(prim("stack2", "cyl", (1.35, -0.05, 0.88), rot=stack_rot2,
                     scale=(0.11, 0.11, 0.42), mkey=accent))
    if state == "fresh":
        objs.append(prim("stackcap", "cyl", (1.05, 0.05, 1.26),
                         scale=(0.16, 0.16, 0.06), mkey=trim))

    # underside pipes
    objs.append(prim("pipe1", "cyl", (0.25, 0, -0.65), rot=(0, 90, 0),
                     scale=(0.10, 0.10, 2.1), mkey=pipe_m))
    objs.append(prim("pipe2", "cyl", (0.25, 0, -0.82), rot=(0, 90, 0),
                     scale=(0.07, 0.07, 1.7), mkey=accent))

    # hanging gantry pipe upward (+Z) from hull
    objs.append(prim("gantry_mast", "cyl", (0.40, 0, 1.55),
                     scale=(0.07, 0.07, 0.95), mkey="dark"))
    objs.append(prim("gantry_cross", "cyl", (0.40, 0, 2.05), rot=(0, 90, 0),
                     scale=(0.06, 0.06, 0.70), mkey="dark"))
    objs.append(prim("gantry_hook", "cube", (0.40, 0, 2.22),
                     scale=(0.10, 0.16, 0.08), mkey="dark"))
    objs.append(prim("gantry_brace", "cyl", (0.05, 0, 1.35), rot=(0, 25, 0),
                     scale=(0.045, 0.045, 0.55), mkey=pipe_m))

    # articulated double-barrel deck turret — yaw ~18° toward camera (-Y)
    yaw = empty("turret_yaw", (0.35, 0, 1.18), rot=(0, 0, 18))
    objs.append(yaw)
    base = prim("turret_base", "cyl", (0, 0, 0), scale=(0.22, 0.22, 0.14), mkey=accent)
    parent_local(base, yaw, (0, 0, 0))
    objs.append(base)
    cupola = prim("turret_cupola", "sphere", (0, 0, 0),
                  scale=(0.18, 0.18, 0.12), mkey=hull_m)
    parent_local(cupola, yaw, (0, 0, 0.12))
    objs.append(cupola)
    for i, yoff in enumerate((-0.09, 0.09)):
        b = prim(f"turret_barrel{i}", "cyl", (0, 0, 0), rot=(0, 90, 0),
                 scale=(0.055, 0.055, 0.55), mkey=hull_m)
        parent_local(b, yaw, (-0.28, yoff, 0.10), rot=(0, 90, 0),
                     scale=(0.055, 0.055, 0.55))
        objs.append(b)
        tip = prim(f"turret_muzz{i}", "cyl", (0, 0, 0), rot=(0, 90, 0),
                   scale=(0.065, 0.065, 0.05), mkey=trim)
        parent_local(tip, yaw, (-0.55, yoff, 0.10), rot=(0, 90, 0),
                     scale=(0.065, 0.065, 0.05))
        objs.append(tip)

    # armor panels (some hidden when wrecked)
    plates = []
    plates.append(prim("plate1", "cube", (0.2, -0.52, 0.25),
                       scale=(0.35, 0.08, 0.18), mkey=accent))
    plates.append(prim("plate2", "cube", (0.9, -0.50, -0.15),
                       scale=(0.28, 0.07, 0.14), mkey=accent))
    plates.append(prim("plate3", "cube", (-0.3, -0.50, -0.20),
                       scale=(0.22, 0.07, 0.12), mkey=hull_m))
    objs += plates
    if state == "wrecked":
        for p in plates[1:]:
            p.hide_render = True
            p.hide_viewport = True

    objs += rivet_row("riv", -0.7, 1.2, 0.32, -0.52, 0.045, 8, trim)
    objs += rivet_row("rivb", -0.7, 1.2, -0.28, -0.52, 0.045, 8, trim)

    # damage extras
    if state in ("damaged", "wrecked"):
        for i, loc in enumerate(((-0.2, -0.4, 0.1), (0.7, -0.35, 0.35),
                                 (1.2, 0.2, -0.1), (0.1, 0.45, 0.2))):
            objs.append(prim(f"scorch{i}", "sphere", loc,
                             scale=(0.22, 0.18, 0.16), mkey="soot"))
        objs.append(prim("crack1", "cube", (0.55, -0.55, 0.05),
                         scale=(0.18, 0.04, 0.08), mkey="crack"))
        objs.append(prim("crack2", "cube", (-0.15, -0.54, 0.30),
                         scale=(0.12, 0.035, 0.10), mkey="crack"))
    if state == "wrecked":
        objs.append(prim("furnace", "cube", (0.85, -0.42, 0.05),
                         scale=(0.16, 0.05, 0.12), mkey="furnace"))
        objs.append(prim("grate", "cube", (0.85, -0.48, 0.05),
                         scale=(0.18, 0.02, 0.14), mkey="dark"))
        for i, loc in enumerate(((0.4, -0.1, 1.4), (1.1, 0.15, 1.1),
                                 (0.9, -0.2, 0.6), (-0.1, 0.1, 0.5))):
            s = 0.28 + i * 0.06
            objs.append(prim(f"smoke{i}", "sphere", loc,
                             scale=(s, s * 0.85, s * 1.1), mkey="smoke"))
        # buckled stack tip
        objs.append(prim("buckle", "cube", (1.05, 0.12, 1.15), rot=(30, 20, 15),
                         scale=(0.10, 0.08, 0.12), mkey="soot"))

    bore_xy = (-1.02, 0.0)  # world X, Z (Y≈0); compose uses XZ
    return objs, bore_xy


# ---------------------------------------------------------------------------
# Boss 3 — Titan Dreadnought
# ---------------------------------------------------------------------------
def build_dread(state="fresh"):
    """Colossal ironclad with dual dorsal turrets + glowing thrusters."""
    objs = []
    hull_m = mk_mat(state, "brass", "sootbrass")
    accent = mk_mat(state, "bronze", "sootbronze")
    trim = mk_mat(state, "gold", "sootbrass")
    pipe_m = mk_mat(state, "copper", "soot")

    # long hull
    objs.append(prim("hull", "cyl", (0.5, 0, 0), rot=(0, 90, 0),
                     scale=(1.15, 1.15, 4.6), mkey=hull_m))
    objs.append(prim("hullbox", "cube", (0.6, 0, 0.15),
                     scale=(2.0, 0.95, 0.85), mkey=accent))
    objs.append(prim("bow", "cone", (-2.55, 0, 0), rot=(0, -90, 0),
                     scale=(1.10, 1.10, 0.85), mkey=hull_m))
    bore = prim("bore", "cyl", (-2.20, 0, 0), rot=(0, 90, 0),
                scale=(0.78, 0.78, 0.10), mkey="dark")
    objs.append(bore)
    objs.append(ring_x("muzzring", -2.10, 0.88, 0.12, trim))
    objs.append(ring_x("ring2", -1.40, 1.18, 0.10, trim))
    objs.append(ring_x("ring3", -0.20, 1.17, 0.09, accent))
    objs.append(ring_x("ring4", 1.20, 1.17, 0.09, accent))
    objs.append(ring_x("ring5", 2.20, 1.10, 0.10, accent))

    # armor plates
    plates = []
    plates.append(prim("plate1", "cube", (0.2, -1.02, 0.45),
                       scale=(0.70, 0.14, 0.30), mkey=accent))
    plates.append(prim("plate2", "cube", (1.6, -0.98, -0.25),
                       scale=(0.50, 0.13, 0.24), mkey=accent))
    plates.append(prim("plate3", "cube", (-0.8, -1.00, -0.35),
                       scale=(0.40, 0.12, 0.20), mkey=hull_m))
    plates.append(prim("plate4", "cube", (2.4, -0.92, 0.30),
                       scale=(0.35, 0.12, 0.22), mkey=accent))
    objs += plates
    if state == "wrecked":
        for p in (plates[1], plates[3]):
            p.hide_render = True
            p.hide_viewport = True

    # dual dorsal turrets (two empties)
    for ti, (tx, yaw_deg) in enumerate(((0.0, 16), (1.6, -12))):
        yaw = empty(f"dorsal_yaw{ti}", (tx, 0, 1.55), rot=(0, 0, yaw_deg))
        objs.append(yaw)
        base = prim(f"dorsal_base{ti}", "cyl", (0, 0, 0),
                    scale=(0.38 if ti == 0 else 0.30,) * 2 + (0.22,), mkey=accent)
        parent_local(base, yaw, (0, 0, 0))
        objs.append(base)
        dome = prim(f"dorsal_dome{ti}", "sphere", (0, 0, 0),
                    scale=(0.30 if ti == 0 else 0.24,) * 2 + (0.20,), mkey=hull_m)
        parent_local(dome, yaw, (0, 0, 0.18))
        objs.append(dome)
        for bi, yoff in enumerate((-0.12, 0.12)):
            blen = 0.70 if ti == 0 else 0.55
            b = prim(f"dorsal_b{ti}_{bi}", "cyl", (0, 0, 0), rot=(0, 90, 0),
                     scale=(0.07, 0.07, blen), mkey=hull_m)
            parent_local(b, yaw, (-blen * 0.45, yoff, 0.16), rot=(0, 90, 0),
                         scale=(0.07, 0.07, blen))
            objs.append(b)
        mast_rot = (18, 12, 6) if (state != "fresh" and ti == 0) else (0, 0, 0)
        if state == "wrecked" and ti == 1:
            mast_rot = (35, -20, 10)
        mast = prim(f"dorsal_mast{ti}", "cone", (0, 0, 0),
                    scale=(0.06, 0.06, 0.35), mkey=trim)
        parent_local(mast, yaw, (0, 0, 0.45), rot=mast_rot, scale=(0.06, 0.06, 0.35))
        objs.append(mast)

    # bridge tower + red beacon
    objs.append(prim("bridge", "cube", (0.9, 0, 1.95),
                     scale=(0.35, 0.28, 0.28), mkey=accent))
    objs.append(prim("bridge_roof", "cube", (0.9, 0, 2.28),
                     scale=(0.38, 0.30, 0.06), mkey=trim))
    objs.append(prim("beacon", "sphere", (0.9, 0, 2.45),
                     scale=(0.10, 0.10, 0.10), mkey="beacon"))

    # stacks
    srot = (14, 10, 5) if state != "fresh" else (0, 0, 0)
    srot2 = (28, -18, -12) if state == "wrecked" else ((10, -8, 4) if state == "damaged" else (0, 0, 0))
    objs.append(prim("funnel1", "cyl", (2.0, 0.15, 1.70), rot=srot,
                     scale=(0.20, 0.20, 0.70), mkey=pipe_m))
    objs.append(prim("funnel2", "cyl", (2.45, -0.10, 1.55), rot=srot2,
                     scale=(0.15, 0.15, 0.55), mkey=accent))

    # secondary battery
    for i, (zz, xx) in enumerate(((-0.80, -1.3), (0.85, -1.0), (-0.35, -0.3),
                                  (0.40, 1.0), (-0.80, 1.8), (0.70, 2.3))):
        objs.append(prim(f"sec{i}", "cyl", (xx, 0, zz), rot=(0, 90, 0),
                         scale=(0.18, 0.18, 0.80), mkey=pipe_m))

    # glowing windows
    for r, zz in ((0, 0.55), (1, -0.45)):
        for i in range(7):
            objs.append(prim(f"win{r}{i}", "cube",
                             (-1.0 + i * 0.55, -1.05, zz),
                             scale=(0.08, 0.03, 0.12), mkey="window"))

    # twin rear thruster nacelles + cyan glow
    for ni, (ny, nz) in enumerate(((-0.55, -0.15), (0.55, -0.15))):
        objs.append(prim(f"nacelle{ni}", "cyl", (3.15, ny, nz), rot=(0, 90, 0),
                         scale=(0.32, 0.32, 0.90), mkey=accent))
        objs.append(prim(f"nac_ring{ni}", "torus", (3.55, ny, nz), rot=(0, 90, 0),
                         scale=(0.34, 0.34, 0.34), mkey=trim))
        objs.append(prim(f"nac_glow{ni}", "cyl", (3.62, ny, nz), rot=(0, 90, 0),
                         scale=(0.24, 0.24, 0.08), mkey="cyan"))
        objs.append(prim(f"nac_core{ni}", "sphere", (3.70, ny, nz),
                         scale=(0.16, 0.16, 0.16), mkey="cyan"))

    # keel
    objs.append(prim("keel", "cube", (0.7, 0, -1.28),
                     scale=(0.80, 0.14, 0.22), mkey=accent))
    for i, xx in enumerate((-0.3, 1.0, 2.2)):
        objs.append(prim(f"drop{i}", "cone", (xx, 0, -1.65), rot=(180, 0, 0),
                         scale=(0.10, 0.50, 0.10), mkey=trim))

    objs += rivet_row("riv", -1.6, 2.6, 0.70, -1.08, 0.055, 11, trim)

    if state in ("damaged", "wrecked"):
        for i, loc in enumerate(((-0.5, -0.7, 0.3), (1.2, -0.6, 0.6),
                                 (2.0, 0.3, -0.2), (0.4, 0.8, 0.4),
                                 (-1.2, -0.5, -0.3))):
            r = 0.30 + (i % 3) * 0.08
            objs.append(prim(f"scorch{i}", "sphere", loc,
                             scale=(r, r * 0.8, r * 0.7), mkey="soot"))
        objs.append(prim("crack1", "cube", (0.8, -1.10, 0.20),
                         scale=(0.35, 0.04, 0.12), mkey="crack"))
        objs.append(prim("crack2", "cube", (-0.4, -1.08, 0.50),
                         scale=(0.22, 0.035, 0.15), mkey="crack"))
        objs.append(prim("crack3", "cube", (1.9, -1.02, -0.10),
                         scale=(0.20, 0.04, 0.10), mkey="crack"))
    if state == "wrecked":
        objs.append(prim("furnace", "cube", (1.4, -0.90, 0.10),
                         scale=(0.28, 0.06, 0.20), mkey="furnace"))
        objs.append(prim("grate", "cube", (1.4, -0.98, 0.10),
                         scale=(0.30, 0.025, 0.22), mkey="dark"))
        objs.append(prim("furnace2", "cube", (-0.2, -0.95, -0.20),
                         scale=(0.18, 0.05, 0.14), mkey="furnace"))
        for i, loc in enumerate(((0.5, -0.2, 2.2), (2.1, 0.2, 2.0),
                                 (1.5, -0.3, 1.2), (-0.3, 0.15, 1.0),
                                 (2.5, -0.1, 0.8))):
            s = 0.35 + i * 0.08
            objs.append(prim(f"smoke{i}", "sphere", loc,
                             scale=(s, s * 0.9, s * 1.15), mkey="smoke"))
        objs.append(prim("buckle1", "cube", (2.0, 0.25, 1.95), rot=(40, 15, 20),
                         scale=(0.14, 0.10, 0.16), mkey="soot"))
        objs.append(prim("buckle2", "cube", (0.1, -0.2, 1.7), rot=(-25, 30, -10),
                         scale=(0.12, 0.10, 0.14), mkey="sootbronze"))

    bore_xy = (-2.20, 0.0)
    return objs, bore_xy


# ---------------------------------------------------------------------------
# Studio / camera
# ---------------------------------------------------------------------------
def light(name, kind, loc, energy, rot=(0, 0, 0), color=(1, 1, 1), size=3):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy
    d.color = color
    if kind == "AREA":
        d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    sc.collection.objects.link(o)
    return o


light("Key", "SUN", (-4, -3, 5), 2.6, rot=(42, 0, 38), color=(1.0, 0.95, 0.88))
light("Front", "AREA", (0, -8, 2), 480, rot=(72, 0, 0), color=(1.0, 0.97, 0.92), size=5)
light("Fill", "AREA", (5, -3, 1), 200, rot=(65, 0, -55), color=(0.78, 0.85, 1.0), size=4)
light("Rim", "AREA", (0, 5, 3), 280, rot=(-40, 0, 180), color=(1.0, 0.92, 0.85), size=6)

world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.58, 0.65, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.40
sc.world = world

cam_d = bpy.data.cameras.new("Cam")
cam_d.type = "ORTHO"
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0, -12, 0)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam)
sc.camera = cam


def clear_meshes():
    for o in list(bpy.data.objects):
        if o.type in ("MESH", "EMPTY"):
            bpy.data.objects.remove(o, do_unlink=True)
    # orphan meshes
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)


def world_bounds(objs):
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    bpy.context.view_layer.update()
    for o in objs:
        if o.type != "MESH" or o.hide_render:
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    return mins, maxs


def fit_and_render(objs, bore_xz, path, pad=1.14):
    # strip prior toon hulls if any linger
    toon.toonify_scene(outline_frac=0.010)
    mins, maxs = world_bounds(objs)
    # ortho from -Y sees X (width) and Z (height)
    span = max(maxs.x - mins.x, maxs.z - mins.z, 1.0)
    # center framing on content mid
    mid = (mins + maxs) * 0.5
    cam.location = (mid.x, -max(12.0, span * 2.5), mid.z)
    s = span * pad
    cam_d.ortho_scale = s
    res = min(RES_CAP, max(256, int(s * PX_PER_UNIT) // 16 * 16))
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.filepath = path
    sc.frame_set(1)
    bpy.ops.render.render(write_still=True)
    print(f"BORE {os.path.basename(path)} x={bore_xz[0]:.4f} z={bore_xz[1]:.4f} "
          f"ortho={s:.4f} res={res} mid=({mid.x:.2f},{mid.z:.2f})")
    return res, s


def pack_webp(png_path, webp_name, res):
    os.makedirs(IMAGES, exist_ok=True)
    webp_path = os.path.join(IMAGES, webp_name)
    # thumbnail to max width 1500 keeping aspect, then WEBP
    max_w = 1500
    script = (
        "from PIL import Image; "
        f"im=Image.open({png_path!r}).convert('RGBA'); "
        f"w,h=im.size; "
        f"m={max_w}; "
        "im=im if w<=m else im.resize((m, int(h*m/w)), Image.LANCZOS); "
        f"im.save({webp_path!r}, 'WEBP', quality=88, method=6); "
        f"print('PACKED', {webp_path!r}, im.size)"
    )
    subprocess.check_call(["python3", "-c", script])
    return webp_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("cruiser", build_cruiser, ("", "-damaged", "-wrecked")),
    ("dread", build_dread, ("", "-damaged", "-wrecked")),
]
STATES = ("fresh", "damaged", "wrecked")

for name, builder, suffixes in JOBS:
    for state, suffix in zip(STATES, suffixes):
        clear_meshes()
        objs, bore = builder(state)
        png = os.path.join(OUT, f"boss3d-{name}{suffix}.png")
        res, ortho = fit_and_render(objs, bore, png)
        webp_name = f"boss3d-{name}{suffix}.webp"
        pack_webp(png, webp_name, res)
        print(f"DONE {name} {state} -> {png} + images/{webp_name}")

print("ALL BOSS RIG BAKES COMPLETE")
print(f"outdir={OUT}")
print(f"images={IMAGES}")

