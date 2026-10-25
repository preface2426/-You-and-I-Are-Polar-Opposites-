import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import bpy
import station_live as live
live.register()
scene=bpy.context.scene
scene.objects['TrainRoot'].location.y=0
scene.camera=scene.objects['CAM | carriage aisle']
scene.camera.location=(3.8,-13.35,7.8)
bpy.context.view_layer.update()
for _ in range(25):live._last-=.05;live.tick()
assert scene.objects['TrainDoors']['open']>.999
leaf=next(o for o in scene.objects if o.name.startswith('TrainLeafLeft') and o.get('active_side'))
assert abs(leaf.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.y+.69)<.0001
scene.camera.location=(20,30,15)
bpy.context.view_layer.update();live._hold=0
for _ in range(25):live._last-=.05;live.tick()
assert scene.objects['TrainDoors']['open']<.001
assert abs(leaf.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.y)<.0001
bpy.ops.station.time(night=True)
assert scene.world.name=='World | night'
bpy.ops.station.time(night=False)
assert scene.world.name=='World | day'
scene.station_hide_roof=True
assert all(o.hide_render for o in scene.objects if o.name.startswith('TrainRoofGroup'))
scene.station_hide_roof=False
assert all(not o.hide_render for o in scene.objects if o.name.startswith('TrainRoofGroup'))
print('STATION_LIVE_CHECKS_OK')
