"""Export a web-friendly GLB of the Popuri store.

Run inside an opened Popuri_Store.blend:
    blender -b Popuri_Store.blend --python export_popuri_web.py

- lights and cameras are excluded; the web viewer supplies its own lighting
- text/curves are converted to meshes
- procedural packaging materials are replaced with solid, exportable colours
- glass is simplified for glTF; the viewer upgrades it to physical glass
"""
from __future__ import annotations

import hashlib
import os

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "web", "Popuri_Store.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# Clean selection and convert text/curve geometry to meshes.
for obj in bpy.context.view_layer.objects:
    obj.select_set(False)

for obj in list(bpy.data.objects):
    if obj.type in {"FONT", "CURVE"}:
        try:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
            obj.select_set(False)
        except Exception as exc:
            print("CONVERT_FAIL", obj.name, exc)

# Web-safe packaging palette.
palette = [
    (0.70, 0.055, 0.04), (0.92, 0.28, 0.035), (0.94, 0.66, 0.05),
    (0.11, 0.38, 0.16), (0.04, 0.42, 0.50), (0.05, 0.17, 0.54),
    (0.48, 0.06, 0.36), (0.86, 0.16, 0.34), (0.55, 0.63, 0.16),
    (0.88, 0.84, 0.69), (0.20, 0.55, 0.72), (0.72, 0.38, 0.10),
]


def web_mat(idx):
    name = f"WEB | Packaging {idx:02d}"
    m = bpy.data.materials.get(name)
    if m:
        return m
    col = palette[idx % len(palette)]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.42
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (*col, 1.0)
    return m


WEB_PACKAGING = [web_mat(i) for i in range(len(palette))]

# Replace the procedural packing material with a stable solid colour per object.
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    h = int(hashlib.md5(obj.name.encode("utf-8")).hexdigest()[:4], 16)
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.name.startswith("Packaging |"):
            slot.material = WEB_PACKAGING[h % len(WEB_PACKAGING)]

# Simple, glTF-safe glass materials. The browser viewer replaces these with
# MeshPhysicalMaterial and enables reflections / thickness.
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.name.startswith("Glass |"):
            continue
        key = "WEB | Glass freezer" if "freezer" in mat.name.lower() else "WEB | Glass storefront"
        web = bpy.data.materials.get(key)
        if web is None:
            web = bpy.data.materials.new(key)
            web.use_nodes = True
            nt = web.node_tree
            nt.nodes.clear()
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.inputs["Base Color"].default_value = (0.72, 0.90, 0.88, 1.0) if "freezer" in key.lower() else (0.82, 0.94, 0.91, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.06
            bsdf.inputs["Transmission Weight"].default_value = 0.0
            bsdf.inputs["Alpha"].default_value = 0.24
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
            try:
                web.surface_render_method = "DITHERED"
            except Exception:
                pass
        slot.material = web

# Select all renderable geometry. The site and stars are kept for the browser.
for obj in bpy.context.view_layer.objects:
    obj.select_set(obj.type == "MESH")
bpy.context.view_layer.objects.active = next(
    (o for o in bpy.context.selected_objects if o.type == "MESH"), None
)
# Apply all bevels/modifiers before joining so the web mesh keeps its edges.
if bpy.context.view_layer.objects.active:
    bpy.ops.object.convert(target="MESH")

meshes = [o for o in bpy.context.view_layer.objects if o.type == "MESH"]


def is_glass(o):
    return any(s.material and s.material.name.startswith("WEB | Glass") for s in o.material_slots)


def join_group(objects, name):
    objects = [o for o in objects if o and o.name in bpy.data.objects]
    if not objects:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    result = bpy.context.view_layer.objects.active
    result.name = name
    return result


stars = [o for o in meshes if o.name.startswith("Star")]
roof = [o for o in meshes if o not in stars and not is_glass(o) and
        o.name.startswith(("Roof", "Rooftop", "Dropped ceiling", "Ceiling light", "Ceiling speaker"))]
glass = [o for o in meshes if is_glass(o) and o not in roof]
store = [o for o in meshes if o not in stars and o not in roof and o not in glass]

join_group(roof, "WEB | RoofGroup")
join_group(stars, "WEB | Stars")
join_group(glass, "WEB | Glass")
join_group(store, "WEB | Store")

for obj in bpy.context.view_layer.objects:
    obj.select_set(obj.type == "MESH")

bpy.context.view_layer.objects.active = next((o for o in bpy.context.selected_objects if o.type == "MESH"), None)

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_yup=True,
    export_texcoords=False,
    export_normals=True,
    export_materials="EXPORT",
    export_cameras=False,
    export_lights=False,
    export_animations=False,
    export_draco_mesh_compression_enable=False,
)
print("WEB_GLB_OK", OUT, os.path.getsize(OUT))
