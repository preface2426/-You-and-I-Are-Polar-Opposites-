"""Render individual reference viewpoints with the native EEVEE materials."""
from pathlib import Path
import argparse
import sys
import bpy

ROOT=Path(__file__).resolve().parent
VIEWS={
    'platform':('CAM | platform end','Platform_Day.png'),
    'across':('CAM | platform across','Platform_Across.png'),
    'reverse':('CAM | platform reverse','Platform_Reverse.png'),
    'exterior':('CAM | train exterior','Train_Exterior.png'),
    'aisle':('CAM | carriage aisle','Carriage_Aisle.png'),
    'bench':('CAM | bench reference','Carriage_Bench.png'),
    'entrance':('CAM | street entrance','Station_Entrance.png'),
    'overview':('CAM | station overview','Station_Overview.png'),
}
parser=argparse.ArgumentParser()
parser.add_argument('--view',choices=VIEWS,default='platform')
parser.add_argument('--preview',action='store_true')
parser.add_argument('--evening',action='store_true')
parser.add_argument('--out')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
scene=bpy.context.scene
scene.camera=bpy.data.objects[VIEWS[args.view][0]]
for name,hidden in [('LIGHTS - day',args.evening),('LIGHTS - night',not args.evening)]:
    for obj in bpy.data.collections[name].objects:
        obj.hide_render=hidden;obj.hide_set(hidden)
scene.world=bpy.data.worlds['World | night' if args.evening else 'World | day']
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=960 if args.preview else 1920
scene.render.resolution_y=540 if args.preview else 1080
scene.render.resolution_percentage=100
scene.eevee.taa_render_samples=24 if args.preview else 80
scene.view_settings.exposure=0
# The distant approaching train and parked train are two moments of one scene.
bpy.data.objects['TrainRoot'].location.y=90 if args.view in ('platform','across') else 0
bpy.data.objects['TrainDoors']['open']=0 if args.view in ('platform','across','aisle','bench') else 1
bpy.data.objects['TrainDoors'].update_tag()
bpy.context.view_layer.update()
name=args.out or VIEWS[args.view][1].replace('.png','_preview.png' if args.preview else '.png')
scene.render.filepath=str(ROOT/'renders'/name)
bpy.ops.render.render(write_still=True)
print('STATION_RENDER_OK',scene.render.filepath)
