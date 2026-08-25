"""Shared toon-shade helpers for the bake scripts (Blender EEVEE legacy).

toonify_scene(): converts every mesh material to a banded toon shader
(Diffuse -> ShaderToRGB -> constant ColorRamp -> Emission) and adds
inverted-hull black outlines around every mesh.

Import from a bake script:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import toon
    toon.toonify_scene(outline_frac=0.015)
"""
import bpy, os

# rim+sheen strength knob: 1.0 for characters, lower for big flat machines
TOON_POP = float(os.environ.get("TOON_POP", "1.0"))

BANDS = ((0.46, 0.48, 0.62, 1), (0.86, 0.87, 0.92, 1), (1.10, 1.10, 1.10, 1))
BAND_POS = (0.0, 0.42, 0.76)


def toonify_material(mat):
    if not mat or not mat.use_nodes or mat.get("toon_done"):
        return
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out is None:
        return
    # already converted (e.g. re-run) or a plain emission material
    if any(n.type == "SHADERTORGB" for n in nt.nodes):
        mat["toon_done"] = 1
        return
    src, src_node = None, None
    alpha = 1.0
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            inp = n.inputs["Base Color"]
            try:
                alpha = n.inputs["Alpha"].default_value
            except KeyError:
                pass
            if inp.is_linked:
                src = inp.links[0].from_socket
                src_node = inp.links[0].from_node
            else:
                src = inp.default_value
            break
    if src is None or alpha < 0.95:   # leave translucent materials alone
        return

    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = BAND_POS[0]
    ramp.color_ramp.elements[0].color = BANDS[0]
    ramp.color_ramp.elements[1].position = BAND_POS[2]
    ramp.color_ramp.elements[1].color = BANDS[2]
    e = ramp.color_ramp.elements.new(BAND_POS[1])
    e.color = BANDS[1]
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 1.0

    # toy sheen: tight glossy highlight band on the most-facing surfaces
    gloss = nt.nodes.new("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.28
    gs2r = nt.nodes.new("ShaderNodeShaderToRGB")
    gramp = nt.nodes.new("ShaderNodeValToRGB")
    gramp.color_ramp.interpolation = "CONSTANT"
    gramp.color_ramp.elements[0].position = 0.0
    gramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    gramp.color_ramp.elements[1].position = 0.93
    gramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    gadd = nt.nodes.new("ShaderNodeMixRGB")
    gadd.blend_type = "ADD"
    gadd.inputs["Fac"].default_value = 1.0

    # fresnel rim: soft light edge so characters pop off the sky
    fres = nt.nodes.new("ShaderNodeLayerWeight")
    fres.inputs["Blend"].default_value = 0.62
    framp = nt.nodes.new("ShaderNodeValToRGB")
    framp.color_ramp.interpolation = "CONSTANT"
    framp.color_ramp.elements[0].position = 0.0
    framp.color_ramp.elements[0].color = (1, 1, 1, 1)   # grazing angle = rim
    framp.color_ramp.elements[1].position = 0.14
    framp.color_ramp.elements[1].color = (0, 0, 0, 1)
    fmul = nt.nodes.new("ShaderNodeMixRGB")
    fmul.blend_type = "MULTIPLY"
    fmul.inputs["Fac"].default_value = 1.0
    fmul.inputs["Color2"].default_value = (1.0, 0.93, 0.80, 1)  # warm rim
    fadd = nt.nodes.new("ShaderNodeMixRGB")
    fadd.blend_type = "ADD"
    fadd.inputs["Fac"].default_value = 0.32 * TOON_POP

    if src_node is not None:
        nt.links.new(src, diff.inputs["Color"])
        nt.links.new(src, mix.inputs["Color2"])
    else:
        diff.inputs["Color"].default_value = src
        mix.inputs["Color2"].default_value = src

    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], mix.inputs["Color1"])
    # sheen chain: tight glossy band, toned to a subtle glint
    gmul = nt.nodes.new("ShaderNodeMixRGB")
    gmul.blend_type = "MULTIPLY"
    gmul.inputs["Fac"].default_value = 1.0
    gmul.inputs["Color2"].default_value = (0.45 * TOON_POP, 0.45 * TOON_POP, 0.5 * TOON_POP, 1)
    nt.links.new(gloss.outputs[0], gs2r.inputs[0])
    nt.links.new(gs2r.outputs[0], gramp.inputs[0])
    nt.links.new(mix.outputs[0], gmul.inputs["Color1"])
    nt.links.new(gramp.outputs[0], gmul.inputs["Color2"])
    nt.links.new(gmul.outputs[0], gadd.inputs["Color2"])
    nt.links.new(mix.outputs[0], gadd.inputs["Color1"])
    # rim chain (rim × base so it tints with the material)
    nt.links.new(fres.outputs["Facing"], framp.inputs[0])
    nt.links.new(gadd.outputs[0], fmul.inputs["Color1"])
    nt.links.new(framp.outputs[0], fmul.inputs["Color2"])
    nt.links.new(gadd.outputs[0], fadd.inputs["Color1"])
    nt.links.new(fmul.outputs[0], fadd.inputs["Color2"])
    nt.links.new(fadd.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    mat["toon_done"] = 1


def outline_material():
    om = bpy.data.materials.get("ToonOutline")
    if om is None:
        om = bpy.data.materials.new("ToonOutline")
        om.use_nodes = True
        b = om.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.012, 0.012, 0.02, 1)
        b.inputs["Roughness"].default_value = 1.0
        om.use_backface_culling = True
    return om


def add_hull(obj, thickness):
    from mathutils import Matrix
    hull = obj.copy()                     # copies transform, parent, modifiers
    hull.data = obj.data.copy()
    # bake the object's own scale into the hull data: solidify thickness is
    # local-space, and non-uniform scales were crushing the outline
    hull.data.transform(Matrix.Diagonal(hull.scale).to_4x4())
    hull.data.transform(Matrix.Scale(0.99, 4))
    hull.scale = (1.0, 1.0, 1.0)
    hull.name = obj.name + "_hull"
    bpy.context.scene.collection.objects.link(hull)
    sol = hull.modifiers.new("remesh", "REMESH")
    sol.mode = "VOXEL"
    sol.voxel_size = max(thickness * 1.5, max(hull.dimensions) * 0.015)
    sol = hull.modifiers.new("hull", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = 1.0
    sol.use_flip_normals = True
    sol.use_rim = False
    sol.use_even_offset = True
    hull.data.materials.clear()
    hull.data.materials.append(outline_material())
    return hull


def toonify_objects(objs, outline_frac=0.015):
    made = []
    for o in objs:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            toonify_material(slot.material)
        if outline_frac > 0:
            size = max(o.dimensions) if max(o.dimensions) > 0 else 1.0
            made.append(add_hull(o, outline_frac * size))
    return made


def toonify_scene(outline_frac=0.015, skip_names=()):
    made = []
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or o.name.endswith("_hull") or o.name in skip_names:
            continue
        for slot in o.material_slots:
            toonify_material(slot.material)
        if outline_frac > 0:
            size = max(o.dimensions) if max(o.dimensions) > 0 else 1.0
            made.append(add_hull(o, outline_frac * size))
    return made
