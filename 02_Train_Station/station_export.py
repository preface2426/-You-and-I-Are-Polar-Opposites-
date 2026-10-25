"""Export the station as spatially merged, vertex-coloured geometry."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import math
import bpy

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "web" / "Train_Station.glb"
scene = bpy.context.scene
bpy.data.objects["TrainRoot"].location.y=0
bpy.data.objects["TrainDoors"]["open"]=0
bpy.data.objects["TrainDoors"].update_tag()
bpy.context.view_layer.update()
assert not any(o.name.startswith(("Clerk", "Figure", "Person", "Human")) for o in scene.objects)
# The source .blend remains untouched; export changes only the background copy.
for obj in list(scene.objects):
    if obj.hide_render or obj.name.startswith(("Rooftop AC", "Roof vent", "Star")):
        bpy.data.objects.remove(obj, do_unlink=True)
        continue
    if obj.type == "MESH":
        # Tiny merchandise bevels dominate triangle count without affecting its silhouette.
        for mod in list(obj.modifiers):
            if obj.name.startswith(("Platform | tactile", "City |", "Track |")):
                obj.modifiers.remove(mod)
            elif mod.type == 'BEVEL':
                mod.segments = 1
    elif obj.type in {"FONT", "CURVE"}:
        obj.data.resolution_u = 2
        obj.data.bevel_resolution = 0
        if obj.type == "FONT":
            obj.data.extrude = 0
            obj.data.bevel_depth = 0

palette = [(0.70,.055,.04),(.92,.28,.035),(.94,.66,.05),(.11,.38,.16),
           (.04,.42,.50),(.05,.17,.54),(.48,.06,.36),(.86,.16,.34),
           (.55,.63,.16),(.88,.84,.69),(.20,.55,.72),(.72,.38,.10)]
materials = {}
for key in ("Opaque", "Glow", "Glass"):
    mat = bpy.data.materials.new("WEB_" + key)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (1,1,1,1)
    bsdf.inputs["Roughness"].default_value = .9
    vertex = mat.node_tree.nodes.new("ShaderNodeVertexColor")
    vertex.layer_name = "Color"
    mat.node_tree.links.new(vertex.outputs["Color"], bsdf.inputs["Base Color"])
    if key == "Glow":
        mat.node_tree.links.new(vertex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1
    if key == "Glass":
        bsdf.inputs["Alpha"].default_value = .14
        mat.surface_render_method = "DITHERED"
    materials[key] = mat

groups = defaultdict(list)
deps = bpy.context.evaluated_depsgraph_get()
source = [o for o in scene.objects if o.type in {"MESH", "FONT", "CURVE"}]
source_triangles = 0
for obj in source:
    evaluated = obj.evaluated_get(deps)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
    mesh.calc_loop_triangles()
    source_triangles += len(mesh.loop_triangles)
    slots = list(mesh.materials)
    categories = set()
    colours = []
    for mat in slots:
        name = mat.name if mat else ""
        category = "Glass" if name.startswith("Glass |") else "Opaque"
        colour = tuple(mat.diffuse_color[:3]) if mat else (.5,.5,.5)
        if name.startswith("Packaging |"):
            colour = palette[int(hashlib.md5(obj.name.encode()).hexdigest()[:4],16)%len(palette)]
        if mat and mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
            if bsdf and bsdf.inputs['Emission Strength'].default_value > 0:
                category = "Glow"
                colour = tuple(bsdf.inputs['Emission Color'].default_value[:3])
        colours.append((*colour,1))
        categories.add(category)
    assert len(categories) <= 1, (obj.name,categories)
    category = next(iter(categories),"Opaque")
    attr = mesh.color_attributes.new(name="Color",type='BYTE_COLOR',domain='CORNER')
    for poly in mesh.polygons:
        colour = colours[poly.material_index] if colours else (.5,.5,.5,1)
        for loop in poly.loop_indices:
            attr.data[loop].color = colour
        poly.material_index = 0
    mesh.materials.clear()
    mesh.materials.append(materials[category])
    mesh.transform(obj.matrix_world)
    new = bpy.data.objects.new('Export_'+obj.name,mesh)
    scene.collection.objects.link(new)
    parent = obj.parent
    if parent and parent.name.startswith("TrainLeaf") and parent.get("active_side"):
        group = parent.name
    elif obj.name.startswith(("CanopyRoof", "TrainRoofGroup", "EntranceRoof")):
        group = "TrainRoofGroup" if obj.name.startswith("TrainRoofGroup") else "CanopyRoofGroup"
    else:
        group = f"Cell_{math.floor(obj.matrix_world.translation.x/12)}_{math.floor(obj.matrix_world.translation.y/12)}"
    groups[(group,category)].append(new)
for obj in source:
    bpy.data.objects.remove(obj,do_unlink=True)

exported=[]
for (group,category),objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    if len(objects)>1: bpy.ops.object.join()
    obj=bpy.context.view_layer.objects.active
    obj.name=group+'_'+category
    exported.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in exported: obj.select_set(True)
bpy.context.view_layer.objects.active=exported[0]
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,
    export_apply=True,export_yup=True,export_texcoords=False,export_normals=True,
    export_materials='EXPORT',export_cameras=False,export_lights=False,
    export_animations=False,export_draco_mesh_compression_enable=False)
report={'triangles':source_triangles,'meshes':len(exported),'materials':3,'bytes':OUT.stat().st_size,
        'door_travel':0.69,'door_points':list(bpy.data.objects['TrainDoors']['door_points']),
        'platform_height':6.2,'rail_gauge':1.067}
assert source_triangles < 400000,report
assert any(o.name.startswith('TrainLeafLeft') for o in exported)
assert any(o.name.startswith('TrainLeafRight') for o in exported)
(ROOT/'web'/'model-stats.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('STATION_GLB_OK',report)
