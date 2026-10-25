"""Scene checks; run inside Blender with Popuri_Store.blend open."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

scene=bpy.context.scene
ROOT=Path(__file__).resolve().parents[1]
def bounds(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points=[evaluated.matrix_world@Vector(c) for c in evaluated.bound_box]
    return [(min(p[i] for p in points),max(p[i] for p in points)) for i in range(3)]
def overlap(a,b):
    return [min(x[1],y[1])-max(x[0],y[0]) for x,y in zip(bounds(a),bounds(b))]
def connected(a,b):
    values=overlap(bpy.data.objects[a],bpy.data.objects[b])
    assert min(values)>0,(a,b,values)

assert not any(o.name.startswith(('Clerk','Figure','Person','Human')) for o in scene.objects)
for a,b in [('Rear wall | structure','Left wall | structure'),
            ('Rear wall | structure','Right rear wall | structure'),
            ('Roof slab','Left wall | structure'),
            ('Roof slab','Rear wall | structure'),
            ('Dropped ceiling','Left wall | structure'),
            ('Dropped ceiling','Rear wall | structure'),
            ('Foundation slab','Left wall | structure')]:
    connected(a,b)
controller=bpy.data.objects['AutomaticDoor']
scene.frame_set(1);bpy.context.view_layer.update()
closed={s:bpy.data.objects['Door'+s].evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.x for s in ('Left','Right')}
scene.frame_set(25);bpy.context.view_layer.update()
for side,sign in [('Left',-1),('Right',1)]:
    root=bpy.data.objects['Door'+side]
    x=root.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.x
    assert abs(x-closed[side]-sign*1.47)<.0001,(side,x)
    for obj in root.children:
        if obj.type!='MESH':continue
        bb=bounds(obj)
        assert bb[0][1]<=-4.98-.035 if sign<0 else bb[0][0]>=-2.12+.035,(obj.name,bb)
        for printer in [o for o in scene.objects if o.name.startswith('Printer |')]:
            assert min(overlap(obj,printer))<=0,(obj.name,printer.name)
# Reference layout: truck on the road; houses behind the back wall; red food
# cabinet to the customer's right of the POS; coffee on the back worktop.
truck=bpy.data.objects['Truck | cargo body'];road=bounds(bpy.data.objects['Site | road'])
assert road[1][0]<truck.location.y<road[1][1]
assert all(o.location.y>7 for o in scene.objects if o.name.startswith('House ') and o.name.endswith('| body') and o.location.x>-21)
assert bpy.data.objects['Snack warmer | base'].location.y>bpy.data.objects['Checkout | register base'].location.y
assert bpy.data.objects['Coffee machine | body'].location.x<bpy.data.objects['Checkout | register base'].location.x
report={'noPeople':True,'shellJointsOverlap':True,'doorTravelMeters':1.47,'clearDoorwayMeters':2.75,'truckOnRoad':True,'referenceEquipmentOrder':True}
(ROOT/'web'/'scene-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('SCENE_CHECKS_OK',report)
