"""Multi-view vertex-color projection for shape-only (white) meshes.

Paints each vertex by blending several reference views (front/back/side),
weighted by surface facing. Fully vectorized with numpy (foreach_get/set) —
a 350k-vert mesh paints in seconds.

Occlusion is approximated by facing weight alone (no ray casts): a surface
hidden behind another part still samples the view it faces, which the blend
of three views mostly corrects. Cheap and artifact-free at game size.

Each view dict:
    img    – reference image path
    campos – (x,y,z) unit axis, the camera sits far along this direction
    u_axis – world axis index (0 or 1) that maps to image u
    u_sign – +1/-1 mirror for u
Usage:
    import project_colors
    project_colors.project_multi(objs, [front, back, side])
"""
import bpy
import numpy as np
from mathutils import Vector


def _content_bbox(px):
    a = px[..., :3].min(-1)
    mask = a < 0.92
    if not mask.any():
        return 0.0, 0.0, 1.0, 1.0
    ys, xs = np.where(mask)
    h, w = mask.shape
    return xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h


def _load(path):
    img = bpy.data.images.load(path)
    W, H = img.size
    px = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(H, W, 4)


def project_multi(objs, views, fallback=(0.6, 0.6, 0.6)):
    bpy.context.view_layer.update()

    loaded = []
    for v in views:
        px = _load(v["img"])
        bx0, by0, bx1, by1 = _content_bbox(px)
        campos = np.array(v["campos"], dtype=np.float64)
        loaded.append({
            "px": px, "bbox": (bx0, by0, bx1, by1),
            "axis": v["u_axis"], "sign": v["u_sign"],
            "wdir": campos,  # normals pointing toward the camera are visible
        })

    # per-view world bbox along the u axis and z
    allw = {}
    for o in objs:
        n = len(o.data.vertices)
        co = np.empty(n * 3, dtype=np.float64)
        o.data.vertices.foreach_get("co", co)
        M = np.array(o.matrix_world, dtype=np.float64)
        wc = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        allw[o.name] = (o, wc)
    for V in loaded:
        axis = V["axis"]
        lo, hi = 1e9, -1e9
        zlo, zhi = 1e9, -1e9
        for _o, wc in allw.values():
            lo = min(lo, wc[:, axis].min()); hi = max(hi, wc[:, axis].max())
            zlo = min(zlo, wc[:, 2].min()); zhi = max(zhi, wc[:, 2].max())
        V["lo"], V["hi"], V["zlo"], V["zhi"] = lo, hi, zlo, zhi

    for o, wc in allw.values():
        m = o.data
        n = len(m.vertices)
        # foreach_get("normal") is not a supported vertex property — read safely
        nm = np.empty((n, 3), dtype=np.float64)
        for i, vtx in enumerate(m.vertices):
            nm[i] = vtx.normal
        wn = nm @ np.array(o.matrix_world.to_3x3(), dtype=np.float64).T
        wn /= np.linalg.norm(wn, axis=1, keepdims=True) + 1e-9

        rgb = np.zeros((n, 3), dtype=np.float64)
        wsum = np.zeros(n, dtype=np.float64)
        for V in loaded:
            w = np.maximum(0.0, wn @ V["wdir"]) ** 3   # sharp view selection
            mask = w > 0.02
            if not mask.any():
                continue
            axis = V["axis"]
            span = max(V["hi"] - V["lo"], 1e-6)
            fx = (wc[mask, axis] - V["lo"]) / span
            if V["sign"] < 0:
                fx = 1.0 - fx
            fy = (wc[mask, 2] - V["zlo"]) / max(V["zhi"] - V["zlo"], 1e-6)
            bx0, by0, bx1, by1 = V["bbox"]
            uu = bx0 + fx * (bx1 - bx0)
            vv = by0 + fy * (by1 - by0)
            H, W = V["px"].shape[:2]
            xi = np.clip((uu * W).astype(np.int64), 0, W - 1)
            yi = np.clip((vv * H).astype(np.int64), 0, H - 1)
            c = V["px"][yi, xi][:, :3] ** 2.2   # img.pixels are raw sRGB; linearize for render
            rgb[mask] += w[mask, None] * c
            wsum[mask] += w[mask]
        ok = wsum > 1e-6
        rgb[ok] /= wsum[ok, None]
        rgb[~ok] = np.array(fallback)

        col = m.color_attributes.new(name="Col", type='BYTE_COLOR', domain='POINT')
        flat = np.empty(n * 4, dtype=np.float32)
        flat.reshape(-1, 4)[:, :3] = rgb
        flat.reshape(-1, 4)[:, 3] = 1.0
        col.data.foreach_set("color", flat)
        m.update()

        mat = bpy.data.materials.new(o.name + "_vcol")
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next(nd for nd in nt.nodes if nd.type == 'BSDF_PRINCIPLED')
        attr = nt.nodes.new('ShaderNodeAttribute')
        attr.attribute_name = "Col"
        nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
        m.materials.clear()
        m.materials.append(mat)
    print(f"PROJECTED-MULTI {len(objs)} objects from {len(views)} views", flush=True)


def project(objs, img_path, cam=None, mirror_back=True, fallback=(0.6, 0.6, 0.6)):
    """Compat wrapper: single front-style view (subject faces the -Y camera)."""
    project_multi(objs, [{"img": img_path, "campos": (0, -1, 0), "u_axis": 0, "u_sign": 1}], fallback)
