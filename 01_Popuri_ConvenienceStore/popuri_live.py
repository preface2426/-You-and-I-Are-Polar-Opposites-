"""Launch inside Blender: realtime EEVEE, viewport proximity door and view controls."""
import bpy
import math
import time
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty

class POPURI_OT_time(bpy.types.Operator):
    bl_idname='popuri.time'
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

class POPURI_OT_view(bpy.types.Operator):
    bl_idname='popuri.view'
    bl_label='切换视角'
    camera_name: EnumProperty(items=[('CAM | exterior night','店外',''),('CAM | interior hero','店内',''),('CAM | aisle reference','通道',''),('CAM | checkout machines','设备','')])
    def execute(self,context):
        context.scene.camera=bpy.data.objects[self.camera_name]
        for area in context.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
        return {'FINISHED'}

class POPURI_OT_roam(bpy.types.Operator):
    bl_idname='popuri.roam'
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

class POPURI_PT_live(bpy.types.Panel):
    bl_label='POPURI 实时场景'
    bl_idname='POPURI_PT_live'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='POPURI'
    def draw(self,context):
        layout=self.layout
        row=layout.row(align=True)
        row.operator('popuri.time',text='日间').night=False
        row.operator('popuri.time',text='夜景').night=True
        for name,label in [('CAM | exterior night','店外'),('CAM | interior hero','店内'),('CAM | aisle reference','通道'),('CAM | checkout machines','收银设备')]:
            layout.operator('popuri.view',text=label).camera_name=name
        layout.operator('popuri.roam',text='自由漫游（WASD）')
        layout.prop(context.scene,'popuri_auto_door',text='靠近自动开门')
        layout.prop(bpy.data.objects['AutomaticDoor'],'["open"]',text='门扇开合',slider=True)
        layout.label(text='点击自由漫游进入步行视角')
        layout.label(text='WASD 移动 / 鼠标转头 / 滚轮调速')
        layout.label(text='左键确认 / Esc 退出；N 收起面板')

_last=time.monotonic()
_amount=0.0
_hold=0.0

def tick():
    global _last,_amount,_hold
    controller=bpy.data.objects.get('AutomaticDoor')
    if not controller:return None
    now=time.monotonic();dt=min(.1,now-_last);_last=now
    scene=bpy.context.scene
    if not scene.popuri_auto_door:return .05
    point=scene.camera.matrix_world.translation
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                view=area.spaces.active.region_3d
                if view.view_perspective!='CAMERA':
                    point=view.view_matrix.inverted().translation
                break
    center=controller['sensor_center']
    near=math.hypot(point.x-center[0],point.y-center[1])<3.0 and point.z<3.2
    if near:_hold=now+1.6
    target=1.0 if near or now<_hold else 0.0
    delta=target-_amount
    if abs(delta)>.0001:
        _amount+=math.copysign(min(abs(delta),dt/.85),delta)
        controller['open']=_amount*_amount*(3-2*_amount)
        controller.update_tag()
        bpy.context.view_layer.update()
    return .05

def register():
    for cls in (POPURI_OT_time,POPURI_OT_view,POPURI_OT_roam,POPURI_PT_live):
        bpy.utils.register_class(cls)
    bpy.types.Scene.popuri_auto_door=BoolProperty(default=True)
    controller=bpy.data.objects['AutomaticDoor']
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
    bpy.ops.popuri.time(night=True)
    bpy.context.scene.camera=bpy.data.objects['CAM | exterior night']
    print('POPURI_LIVE_READY')

if __name__=='__main__':
    register()
