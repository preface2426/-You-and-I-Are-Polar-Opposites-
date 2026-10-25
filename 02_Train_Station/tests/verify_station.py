"""Blender checks for rails, boarding openings, aisle and stair headroom."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
scene.objects['TrainRoot'].location.y=0
controller=scene.objects['TrainDoors']
controller['open']=0
controller.update_tag()
bpy.context.view_layer.update()


def bounds(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if obj.type=='CURVE':
        mesh=evaluated.to_mesh()
        points=[evaluated.matrix_world@v.co for v in mesh.vertices]
        evaluated.to_mesh_clear()
    else:
        points=[evaluated.matrix_world@Vector(c) for c in evaluated.bound_box]
    return [(min(p[i] for p in points),max(p[i] for p in points)) for i in range(3)]


assert not any(o.type=='ARMATURE' or o.name.startswith(('Clerk','Human','Person','Figure')) for o in scene.objects)
assert len([o for o in scene.objects if 'triangular grip' in o.name])==132
assert scene.objects['Car01 | green bench back -1 1'].data.materials[0].diffuse_color[1] > scene.objects['Car01 | green bench back -1 1'].data.materials[0].diffuse_color[0]
assert scene.objects['Car01 | blue belt -1 1'].data.materials[0].diffuse_color[2] > scene.objects['Car01 | blue belt -1 1'].data.materials[0].diffuse_color[0]
assert bounds(scene.objects['Viaduct | island deck'])[2][1] > bounds(scene.objects['Platform | continuous slab'])[2][0]
for obj in scene.objects:
    assert all(math.isfinite(v) for row in obj.matrix_world for v in row),obj.name

rails=[o for o in scene.objects if o.name.startswith('Track | continuous rail 1 ')]
assert len(rails)==2
assert abs(abs(rails[0].location.x-rails[1].location.x)-1.067)<1e-5
for obj in scene.objects:
    if '| wheel ' in obj.name:
        assert abs(bounds(obj)[2][0]-5.03)<.001,(obj.name,bounds(obj))
    if 'pantograph contact bar' in obj.name:
        assert abs(bounds(obj)[2][1]-10.4)<.001

active=[o for o in scene.objects if o.name.startswith('TrainLeaf') and o.get('active_side')]
inactive=[o for o in scene.objects if o.name.startswith('TrainLeaf') and not o.get('active_side')]
assert len(active)==16 and len(inactive)==16
closed={obj.name:obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.y for obj in active}
controller['open']=1
controller.update_tag()
bpy.context.view_layer.update()
for root in active:
    y=root.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.y
    assert abs(y-closed[root.name]-root['direction']*.69)<.0001
    for obj in root.children:
        if obj.type not in {'MESH','CURVE'}:continue
        bb=bounds(obj)
        assert bb[0][0]>2.90,(obj.name,'platform collision',bb)
        assert bb[0][1]<2.981,(obj.name,'side panel collision',bb)
for root in inactive:
    assert abs(root.location.y)<.0001,root.name

deps=bpy.context.evaluated_depsgraph_get()
for i in range(36):
    y=-51.1+(i+.5)*.32;expected=(i+1)*6.2/36
    hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((.25,y,expected+1.5)),Vector((0,0,-1)))
    assert hit and abs(point.z-expected)<.035,(i,obj.name if obj else '',point[:])
    hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((.25,y,expected+1.70)),Vector((0,0,1)))
    assert not hit or point.z>=expected+2.05,(i,'blocked stair headroom',obj.name,point[:])
for y in range(-13,4):
    hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((4.55,y,7.70)),Vector((0,0,-1)))
    assert hit and 6.19<point.z<6.24,(y,'aisle floor',obj.name if obj else '',point[:])
    hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((4.55,y,7.95)),Vector((0,0,1)))
    assert not hit or point.z>=8.05,(y,'aisle headroom',obj.name,point[:])

for i in range(26):
    y=-18+(i+.5)*.30;expected=6.2+(i+1)*.13
    hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((-.45,y,expected+1.5)),Vector((0,0,-1)))
    assert hit and abs(point.z-expected)<.02,(i,'upper stair tread',obj.name if obj else '')
    hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((-.45,y,expected+1.7)),Vector((0,0,1)))
    assert not hit or point.z>=expected+2.05,(i,'upper stair headroom',obj.name)
for x in (-1.8,1.8):
    for y in range(-35,36):
        hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((x,y,7.7)),Vector((0,0,-1)))
        assert hit and 6.19<point.z<6.24,(x,y,'platform circulation blocked',obj.name if obj else '')

camera=scene.objects['CAM | train exterior']
face=scene.objects['Cab | panoramic blue glazing']
target=face.matrix_world.translation
hit,point,_,_,obj,_=scene.ray_cast(deps,camera.matrix_world.translation,(target-camera.matrix_world.translation).normalized())
assert hit and obj.name=='Cab | panoramic blue glazing',('hero camera obstruction',obj.name if obj else '')

report={'noPeople':True,'railGaugeMeters':1.067,'wheelContact':True,'heroCameraClear':True,'pantographContact':True,
        'activeDoorLeaves':16,'oppositeSideStaysClosed':True,'doorTravelMeters':.69,
        'boardingPanelsClearPlatform':True,'stairSamplesChecked':36,'stairHeadroomMinMeters':2.05,
        'aisleSamplesChecked':17,'upperStairSamplesChecked':26,'platformSidePassageSamples':142,'visibleFeatures':'blue exterior belt / green seats / orange floor / triangular grips'}
(ROOT/'web'/'scene-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('STATION_CHECKS_OK',report)
