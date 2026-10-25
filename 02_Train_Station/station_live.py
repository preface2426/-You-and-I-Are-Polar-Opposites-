"""Launch inside Blender: realtime EEVEE, viewport proximity door and view controls."""
import bpy
import math
import time
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty

class STATION_OT_time(bpy.types.Operator):
    bl_idname='station.time'
    bl_label='切换昼夜'
    night: BoolProperty(default=False)
    def execute(self,context):
        scene=context.scene
        for name,hide in [('LIGHTS - day',self.night),('LIGHTS - night',not self.night)]:
            for obj in bpy.data.collections[name].objects:
                obj.hide_render=hide
                obj.hide_set(hide)
        scene.world=bpy.data.worlds['World | night' if self.night else 'World | day']
        scene.view_settings.exposure=0
        return {'FINISHED'}

class STATION_OT_view(bpy.types.Operator):
    bl_idname='station.view'
    bl_label='切换视角'
    camera_name: EnumProperty(items=[('CAM | platform end','站台尽头',''),('CAM | platform reverse','站台反向',''),('CAM | platform across','站台横向',''),('CAM | train exterior','列车外观',''),('CAM | carriage aisle','车厢内部',''),('CAM | bench reference','长椅近景',''),('CAM | street entrance','车站入口',''),('CAM | station overview','总览','')])
    def execute(self,context):
        context.scene.camera=bpy.data.objects[self.camera_name]
        bpy.data.objects['TrainRoot'].location.y=90 if self.camera_name in ('CAM | platform end','CAM | platform across') else 0
        for area in context.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
        return {'FINISHED'}

class STATION_OT_roam(bpy.types.Operator):
    bl_idname='station.roam'
    bl_label='自由漫游'
    def execute(self,context):
        camera=context.scene.camera
        for area in context.screen.areas:
            if area.type!='VIEW_3D':continue
            view=area.spaces.active.region_3d
            rotation=camera.matrix_world.to_quaternion()
            view.view_rotation=rotation
            view.view_distance=5.0
            view.view_location=camera.matrix_world.translation+rotation@Vector((0,0,-5))
            view.view_perspective='PERSP'
            region=next(r for r in area.regions if r.type=='WINDOW')
            with context.temp_override(area=area,region=region):
                bpy.ops.view3d.walk('INVOKE_DEFAULT')
            return {'FINISHED'}
        return {'CANCELLED'}

class STATION_PT_live(bpy.types.Panel):
    bl_label='STATION 实时场景'
    bl_idname='STATION_PT_live'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='STATION'
    def draw(self,context):
        layout=self.layout
        row=layout.row(align=True)
        row.operator('station.time',text='日间').night=False
        row.operator('station.time',text='夜景').night=True
        for name,label in [('CAM | platform end','站台尽头'),('CAM | platform reverse','站台反向'),('CAM | platform across','站台横向'),('CAM | train exterior','列车外观'),('CAM | carriage aisle','车厢内部'),('CAM | bench reference','长椅近景'),('CAM | street entrance','车站入口'),('CAM | station overview','全景')]:
            layout.operator('station.view',text=label).camera_name=name
        layout.operator('station.roam',text='自由漫游（WASD）')
        layout.prop(context.scene,'station_auto_door',text='靠近站台侧车门时自动开门')
        layout.prop(context.scene,'station_hide_roof',text='隐藏车顶')
        layout.prop(bpy.data.objects['TrainDoors'],'["open"]',text='站台侧车门',slider=True)
        layout.label(text='点击自由漫游进入步行视角')
        layout.label(text='WASD 移动 / 鼠标转头 / 滚轮调速')
        layout.label(text='左键确认 / Esc 退出；N 收起面板')

_last=time.monotonic()
_amount=0.0
_hold=0.0

def tick():
    global _last,_amount,_hold
    controller=bpy.data.objects.get('TrainDoors')
    if not controller:return None
    now=time.monotonic();dt=min(.1,now-_last);_last=now
    scene=bpy.context.scene
    if not scene.station_auto_door:return .05
    point=scene.camera.matrix_world.translation
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                view=area.spaces.active.region_3d
                if view.view_perspective!='CAMERA':
                    point=view.view_matrix.inverted().translation
                break
    raw=controller['door_points']
    shift=bpy.data.objects['TrainRoot'].location.y
    near=any(math.hypot(point.x-raw[i],point.y-raw[i+1]-shift)<2.6
        and abs(point.z-(raw[i+2]+1.6))<1.2 for i in range(0,len(raw),3))
    if near:_hold=now+1.6
    target=1.0 if near or now<_hold else 0.0
    delta=target-_amount
    if abs(delta)>.0001:
        _amount+=math.copysign(min(abs(delta),dt/.85),delta)
        controller['open']=_amount*_amount*(3-2*_amount)
        controller.update_tag()
        bpy.context.view_layer.update()
    return .05

def hide_roof(self,context):
    for obj in bpy.data.collections['TRAIN - two connected cars'].objects:
        if obj.name.startswith('TrainRoofGroup'):
            obj.hide_set(context.scene.station_hide_roof)
            obj.hide_render=context.scene.station_hide_roof

def register():
    for cls in (STATION_OT_time,STATION_OT_view,STATION_OT_roam,STATION_PT_live):
        bpy.utils.register_class(cls)
    bpy.types.Scene.station_auto_door=BoolProperty(default=True)
    bpy.types.Scene.station_hide_roof=BoolProperty(default=False,update=hide_roof)
    controller=bpy.data.objects['TrainDoors']
    controller.animation_data_clear()
    controller['open']=0.0
    controller.update_tag()
    bpy.context.view_layer.update()
    bpy.app.timers.register(tick,first_interval=.1)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active
                space.show_region_ui=True
                space.shading.type='RENDERED'
                space.shading.use_scene_world_render=True
                space.shading.use_scene_lights_render=True
    bpy.ops.station.time(night=False)
    bpy.context.scene.camera=bpy.data.objects['CAM | train exterior']
    print('STATION_LIVE_READY')

if __name__=='__main__':
    register()
