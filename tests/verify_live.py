import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import bpy
import popuri_live as live
live.register()
controller=bpy.data.objects['AutomaticDoor']
scene=bpy.context.scene
scene.camera.location=(-3.55,-5.6,1.65)
bpy.context.view_layer.update()
for _ in range(25):
    live._last-=.05
    live.tick()
assert controller['open']>.999,controller['open']
scene.camera.location=(20,-30,15)
bpy.context.view_layer.update()
live._hold=0
for _ in range(25):
    live._last-=.05
    live.tick()
assert controller['open']<.001,controller['open']
bpy.ops.popuri.time(night=False)
assert scene.world.name=='World | day'
bpy.ops.popuri.time(night=True)
assert scene.world.name=='World | night'
print('LIVE_CHECKS_OK')
