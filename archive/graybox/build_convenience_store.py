"""Create a stylized convenience-store graybox and export it as glTF/GLB.
Run in Blender 5.4: Scripting > Open > Run Script.
"""
import bpy
import math
import os
from mathutils import Vector

# ---- Easy-to-edit settings ----
EXPORT_GLB = bpy.path.abspath('//convenience_store_graybox.glb')
SUN_ENERGY = 0.35
SUN_ANGLE_DEG = 18
AREA_ENERGY = 350
AREA_SIZE = 12
AREA_HEIGHT = 9
AREA_LOCATION = (0, -4, AREA_HEIGHT)
INTERIOR_LIGHT_ENERGY = 140
FACADE_LIGHT_ENERGY = 200
SIGN_EMISSION = 2.5
WORLD_STRENGTH = 0.16

# Dimensions in meters. Front of store faces negative Y.
STORE_W, STORE_D, STORE_H = 18.0, 11.0, 4.4
FLOOR_Z = 0.0
DOOR_CENTER_X = -3.8

# Clear current scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for data in bpy.data.collections:
    if data.name != 'Collection' and data.users == 0:
        bpy.data.collections.remove(data)
root = bpy.context.scene.collection

def collection(name):
    c = bpy.data.collections.new(name)
    root.children.link(c)
    return c

C_BUILD = collection('01 Store - graybox')
C_SITE = collection('02 Parking and site')
C_LIGHT = collection('03 Adjustable lighting')
C_INT = collection('04 Interior placeholders')

def move_to(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj

def gray_material(name, value):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*value, 1)
    m.use_nodes = True
    shader = next((node for node in m.node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if shader:
        shader.inputs['Base Color'].default_value = (*value, 1)
        shader.inputs['Roughness'].default_value = 0.72
    return m

MAT_CONCRETE = gray_material('Gray | concrete', (0.25, 0.28, 0.31))
MAT_WALL = gray_material('Gray | wall', (0.48, 0.50, 0.52))
MAT_DARK = gray_material('Gray | roof and trim', (0.12, 0.14, 0.17))
MAT_GLASS = gray_material('Gray | glazing', (0.35, 0.43, 0.46))
MAT_MARK = gray_material('Gray | parking paint', (0.72, 0.74, 0.74))
MAT_FIXTURE = gray_material('Gray | fixtures', (0.34, 0.36, 0.37))
MAT_SIGN = gray_material('Sign | purple', (0.62, 0.08, 0.72))
MAT_SIGN_EDGE = gray_material('Sign | pink light strip', (1.0, 0.35, 0.82))
MAT_SIGN_TEXT = gray_material('Sign | warm lettering', (1.0, 0.82, 0.25))
MAT_PRODUCT = [
    gray_material('Product | cream', (0.82, 0.72, 0.50)),
    gray_material('Product | red', (0.72, 0.16, 0.15)),
    gray_material('Product | blue', (0.15, 0.38, 0.68)),
    gray_material('Product | green', (0.25, 0.55, 0.30)),
    gray_material('Product | yellow', (0.88, 0.68, 0.16)),
]
MAT_COUNTER = gray_material('Interior | warm counter', (0.48, 0.27, 0.17))
MAT_COLDCASE = gray_material('Interior | refrigerator glass', (0.40, 0.62, 0.68))
MAT_LIGHT = gray_material('Light | diffuser', (1.0, 0.93, 0.72))
MAT_FLOOR = gray_material('Interior | warm tile', (0.48, 0.53, 0.42))

def emissive(mat, color, strength):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    shader = next((node for node in nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if shader:
        shader.inputs['Base Color'].default_value = (*color, 1)
        if 'Emission Color' in shader.inputs:
            shader.inputs['Emission Color'].default_value = (*color, 1)
        elif 'Emission' in shader.inputs:
            shader.inputs['Emission'].default_value = (*color, 1)
        if 'Emission Strength' in shader.inputs:
            shader.inputs['Emission Strength'].default_value = strength

emissive(MAT_SIGN_EDGE, (1.0, 0.28, 0.78), SIGN_EMISSION)
emissive(MAT_LIGHT, (1.0, 0.88, 0.63), 1.8)

def cube(name, loc, scale, mat, coll, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Soft edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return move_to(o, coll)

def cyl(name, loc, radius, depth, mat, coll, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    return move_to(o, coll)

# Building base and shell
cube('Store | foundation', (0, 0, 0.16), (STORE_W, STORE_D, 0.32), MAT_CONCRETE, C_BUILD, 0.08)
cube('Store | rear wall', (0, STORE_D/2-0.15, STORE_H/2), (STORE_W, 0.30, STORE_H), MAT_WALL, C_BUILD)
cube('Store | left wall', (-STORE_W/2+0.15, 0, STORE_H/2), (0.30, STORE_D, STORE_H), MAT_WALL, C_BUILD)
cube('Store | right wall', (STORE_W/2-0.15, 0, STORE_H/2), (0.30, STORE_D, STORE_H), MAT_WALL, C_BUILD)
cube('Store | roof slab', (0, 0, STORE_H+0.12), (STORE_W+0.3, STORE_D+0.3, 0.24), MAT_DARK, C_BUILD)
cube('Interior floor | tile', (0, 0, 0.335), (STORE_W-0.55, STORE_D-0.55, 0.03), MAT_FLOOR, C_INT)

# Storefront glazing and an off-center automatic sliding entrance from the floor plan.
front_y = -STORE_D/2 + 0.06
cube('Storefront | upper header', (0, front_y, 3.78), (STORE_W-0.6, 0.18, 0.28), MAT_WALL, C_BUILD)
front_windows = [(-7.65, 2.05), (0.15, 2.35), (2.65, 2.45), (5.25, 2.45), (7.85, 2.25)]
for i, (x, width) in enumerate(front_windows, 1):
    cube(f'Front glazing {i:02}', (x, front_y+0.02, 2.10), (width, 0.08, 2.90), MAT_GLASS, C_BUILD)
    cube(f'Front mullion {i:02}', (x-width/2, front_y-0.06, 2.10), (0.07, 0.10, 2.94), MAT_DARK, C_BUILD)
    cube(f'Storefront | window sill {i:02}', (x, front_y, 0.48), (width, 0.16, 0.32), MAT_WALL, C_BUILD)

door_y = front_y - 0.08
door_half_width = 2.60
for x in (DOOR_CENTER_X-door_half_width, DOOR_CENTER_X+door_half_width):
    cube('Entrance | outer jamb', (x, door_y-0.04, 2.08), (0.12, 0.16, 2.96), MAT_DARK, C_BUILD)
cube('Entrance | overhead motor track', (DOOR_CENTER_X, door_y-0.08, 3.56), (5.25, 0.16, 0.12), MAT_DARK, C_BUILD)
cube('Entrance | motion sensor', (DOOR_CENTER_X, door_y-0.22, 3.70), (0.42, 0.18, 0.13), MAT_SIGN_EDGE, C_BUILD, 0.025)
door_leaves = []
for i, (closed_offset, open_offset) in enumerate(((-1.05, -2.30), (1.05, 2.30)), 1):
    leaf = cube(f'Entrance | glass sliding leaf {i}', (DOOR_CENTER_X+closed_offset, door_y+0.16, 2.08), (2.10, 0.07, 2.84), MAT_GLASS, C_BUILD)
    for edge in (-1.0, 1.0):
        rail = cube(f'Entrance | leaf {i} frame', (DOOR_CENTER_X+closed_offset+edge, door_y+0.11, 2.08), (0.045, 0.045, 2.88), MAT_DARK, C_BUILD)
        rail_world = rail.matrix_world.copy()
        rail.parent = leaf
        rail.matrix_parent_inverse = leaf.matrix_world.inverted()
        rail.matrix_world = rail_world
    door_leaves.append((leaf, closed_offset, open_offset))

door_scene = bpy.context.scene
door_scene.frame_end = 21
for leaf, closed_offset, open_offset in door_leaves:
    leaf.location.x = DOOR_CENTER_X + closed_offset
    leaf.keyframe_insert(data_path='location', index=0, frame=1)
    leaf.location.x = DOOR_CENTER_X + open_offset
    leaf.keyframe_insert(data_path='location', index=0, frame=21)
door_scene.frame_set(1)
cube('Entrance | threshold', (DOOR_CENTER_X, front_y-0.02, 0.34), (5.15, 0.22, 0.045), MAT_DARK, C_BUILD)
cube('Entrance | interior mat', (DOOR_CENTER_X, -4.15, 0.36), (4.8, 2.25, 0.07), MAT_DARK, C_INT, 0.035)
for x, width in front_windows:
    cube('Storefront | purple window band', (x, front_y-0.07, 0.93), (width, 0.055, 0.38), MAT_SIGN, C_BUILD)
# Right-side windows
side_x = STORE_W/2 - 0.06
for i in range(5):
    y = -3.9 + i * 1.85
    cube(f'Side glazing {i+1:02}', (side_x, y, 2.05), (0.08, 1.68, 2.72), MAT_GLASS, C_BUILD)
    cube(f'Side mullion {i+1:02}', (side_x+0.06, y-0.88, 2.05), (0.10, 0.07, 2.78), MAT_DARK, C_BUILD)

# Continuous purple-pink sign band, matching the reference image.
cube('Sign fascia | front', (0, -STORE_D/2-0.18, 4.02), (STORE_W+0.2, 0.38, 0.72), MAT_FIXTURE, C_BUILD, 0.04)
cube('Sign fascia | right', (STORE_W/2+0.12, 0, 4.02), (0.38, STORE_D+0.25, 0.72), MAT_FIXTURE, C_BUILD, 0.04)
# Purple panels, pink border lines and modular joints.
cube('Sign panel | right wrap', (STORE_W/2+0.34, 0, 4.02), (0.035, STORE_D-0.25, 0.56), MAT_SIGN, C_BUILD, 0.02)
for i in range(6):
    x = -7.5 + i*3.0
    cube(f'Sign panel {i+1:02}', (x, -STORE_D/2-0.39, 4.02), (2.92, 0.035, 0.56), MAT_SIGN, C_BUILD, 0.02)
cube('Sign | front upper light strip', (0, -STORE_D/2-0.42, 4.35), (STORE_W, 0.04, 0.055), MAT_SIGN_EDGE, C_BUILD)
cube('Sign | front lower light strip', (0, -STORE_D/2-0.42, 3.69), (STORE_W, 0.04, 0.055), MAT_SIGN_EDGE, C_BUILD)
cube('Sign | right upper light strip', (STORE_W/2+0.34, 0, 4.35), (0.04, STORE_D, 0.055), MAT_SIGN_EDGE, C_BUILD)
cube('Sign | right lower light strip', (STORE_W/2+0.34, 0, 3.69), (0.04, STORE_D, 0.055), MAT_SIGN_EDGE, C_BUILD)

# Main Japanese shop name. Convert to mesh so it travels in the GLB.
font = None
for font_path in ('C:/Windows/Fonts/YuGothM.ttc', 'C:/Windows/Fonts/meiryo.ttc', 'C:/Windows/Fonts/msgothic.ttc'):
    if os.path.exists(font_path):
        try:
            font = bpy.data.fonts.load(font_path)
            break
        except Exception:
            pass
bpy.ops.object.text_add(location=(0, -STORE_D/2-0.47, 3.82), rotation=(math.radians(90), 0, 0))
sign_text = bpy.context.object
sign_text.name = 'Sign lettering | Popuri'
sign_text.data.body = 'ポプリ' if font else 'POPURI'
if font:
    sign_text.data.font = font
sign_text.data.align_x = 'CENTER'
sign_text.data.align_y = 'CENTER'
sign_text.data.size = 0.50
sign_text.data.extrude = 0.006
sign_text.data.materials.append(MAT_SIGN_TEXT)
move_to(sign_text, C_BUILD)
bpy.context.view_layer.objects.active = sign_text
sign_text.select_set(True)
bpy.ops.object.convert(target='MESH')
sign_text.select_set(False)

# Two simple lidded waste bins beside the entrance.
for i, x in enumerate((4.25, 5.35), 1):
    y = -6.10
    cube(f'Waste bin {i} | body', (x, y, 0.62), (0.78, 0.72, 1.18), MAT_FIXTURE, C_SITE, 0.08)
    cube(f'Waste bin {i} | lid', (x, y, 1.25), (0.84, 0.78, 0.12), MAT_DARK, C_SITE, 0.04)
    cube(f'Waste bin {i} | front slot', (x, y-0.37, 0.83), (0.42, 0.035, 0.12), MAT_DARK, C_SITE, 0.02)
    for wheel_x in (x-0.25, x+0.25):
        cyl(f'Waste bin {i} | wheel', (wheel_x, y-0.10, 0.14), 0.09, 0.07, MAT_DARK, C_SITE, vertices=12)

# Parking forecourt
cube('Parking lot | asphalt', (0, -15.8, -0.08), (33, 20.0, 0.16), MAT_CONCRETE, C_SITE)
cube('Store apron', (0, -6.2, 0.00), (20, 1.6, 0.20), MAT_WALL, C_SITE)
# Six parking bays, painted end lines and short wheel stops
for i in range(6):
    x = -12.5 + i*5.0
    cube(f'Parking line {i+1:02}', (x, -15.1, 0.015), (0.11, 7.4, 0.03), MAT_MARK, C_SITE)
    cube(f'Wheel stop {i+1:02}', (x+2.0, -10.7, 0.12), (2.8, 0.22, 0.22), MAT_FIXTURE, C_SITE, 0.04)
cube('Parking bay front boundary', (0, -18.8, 0.015), (30, 0.11, 0.03), MAT_MARK, C_SITE)
# Roadside edge and a simple sidewalk strip
cube('Road edge', (0, -26.0, -0.02), (38, 0.20, 0.18), MAT_DARK, C_SITE)
cube('Sidewalk', (0, -27.0, -0.12), (38, 1.8, 0.22), MAT_WALL, C_SITE)

# Perimeter fence along right and far parking boundary
fence_mat = MAT_DARK
for y in [-24, -20, -16, -12, -8, -4, 0, 4, 8]:
    cyl(f'Fence post right {y}', (16.1, y, 1.05), 0.07, 2.1, fence_mat, C_SITE)
for z in (0.35, 1.7):
    cube('Fence rail right', (16.1, -8, z), (0.09, 32, 0.09), fence_mat, C_SITE)
for x in [-16, -12, -8, -4, 0, 4, 8, 12, 16]:
    cyl(f'Fence post rear {x}', (x, 4.2, 1.05), 0.07, 2.1, fence_mat, C_SITE)
for z in (0.35, 1.7):
    cube('Fence rail rear', (0, 4.2, z), (32, 0.09, 0.09), fence_mat, C_SITE)

# Streetlights with simple pole, cross arm and fixture
for idx, (x, y) in enumerate([(-15, -12), (14, -11), (14, 2)], 1):
    cyl(f'Streetlight {idx} | pole', (x, y, 3.5), 0.13, 7.0, MAT_DARK, C_SITE)
    cube(f'Streetlight {idx} | arm', (x-0.65, y, 6.75), (1.3, 0.14, 0.14), MAT_DARK, C_SITE)
    cube(f'Streetlight {idx} | head', (x-1.2, y, 6.62), (0.9, 0.35, 0.18), MAT_FIXTURE, C_SITE)
    light_data = bpy.data.lights.new(f'Streetlight {idx} | adjustable', 'AREA')
    light_data.energy = AREA_ENERGY * 0.35
    light_data.shape = 'DISK'
    light_data.size = 4.0
    light_obj = bpy.data.objects.new(light_data.name, light_data)
    C_LIGHT.objects.link(light_obj)
    light_obj.location = (x-1.2, y, 6.45)
    light_obj.rotation_euler = (0, 0, 0)

# Interior follows the supplied plan: wall rack left, L-counter, transverse gondolas,
# printer near the entrance, and a long ice-cream case at the front-right.
def wall_shelf(x, y0, length):
    center_y = y0 + length/2
    cube('Left wall rack | backboard', (x, center_y, 1.45), (0.12, length, 2.65), MAT_FIXTURE, C_INT)
    shelf_x = x + 0.52
    for level, z in enumerate((0.42, 1.02, 1.62, 2.22, 2.82), 1):
        cube(f'Left wall rack | tier {level}', (shelf_x, center_y, z), (1.05, length, 0.075), MAT_WALL, C_INT)
        if level < 5:
            for row in range(12):
                y = y0 + (row+0.5)*length/12
                for depth in (-0.24, 0.18):
                    mat = MAT_PRODUCT[(row+level) % len(MAT_PRODUCT)]
                    cube(f'Left wall goods L{level} R{row}', (shelf_x+depth, y, z+0.22), (0.30, 0.28, 0.38), mat, C_INT, 0.025)
    for z in (0.72, 1.32, 1.92, 2.52):
        cube('Left wall rack | price rail', (shelf_x+0.49, center_y, z), (0.035, length, 0.06), MAT_SIGN_EDGE, C_INT)

def gondola(name, center_x, center_y):
    length = 9.6
    cube(f'{name} | center spine', (center_x, center_y, 1.42), (length, 0.12, 2.55), MAT_FIXTURE, C_INT)
    for side in (-1, 1):
        shelf_y = center_y + side*0.36
        for level, z in enumerate((0.40, 0.98, 1.56, 2.14, 2.72), 1):
            cube(f'{name} | side {side} tier {level}', (center_x, shelf_y, z), (length, 0.62, 0.075), MAT_WALL, C_INT)
            if level < 5:
                for row in range(16):
                    x = center_x - 4.45 + row*0.58
                    mat = MAT_PRODUCT[(row+level+int(side > 0)) % len(MAT_PRODUCT)]
                    cube(f'{name} | goods {side} L{level} R{row}', (x, shelf_y, z+0.21), (0.34, 0.34, 0.36), mat, C_INT, 0.025)
        cube(f'{name} | price rail {side}', (center_x, center_y+side*0.68, 0.72), (length, 0.035, 0.06), MAT_SIGN_EDGE, C_INT)

wall_shelf(-8.35, -0.15, 4.8)
gondola('Gondola A', 2.35, 2.35)
gondola('Gondola B', 2.35, -1.85)

# L-shaped cashier counter in the front-left corner.
cube('Checkout | long counter body', (-5.40, 1.20, 0.67), (1.65, 5.15, 1.26), MAT_COUNTER, C_INT, 0.06)
cube('Checkout | long countertop', (-5.40, 1.20, 1.34), (1.82, 5.28, 0.12), MAT_WALL, C_INT, 0.035)
cube('Checkout | front counter body', (-7.05, -2.22, 0.67), (3.55, 1.78, 1.26), MAT_COUNTER, C_INT, 0.06)
cube('Checkout | front countertop', (-7.05, -2.22, 1.34), (3.70, 1.88, 0.12), MAT_WALL, C_INT, 0.035)
cube('Checkout | register base', (-6.20, -2.20, 1.50), (0.72, 0.48, 0.24), MAT_FIXTURE, C_INT, 0.04)
cube('Checkout | display screen', (-6.20, -2.02, 1.84), (0.68, 0.10, 0.52), MAT_DARK, C_INT, 0.04)
cube('Checkout | scanner', (-5.42, -2.28, 1.43), (0.38, 0.28, 0.07), MAT_SIGN_EDGE, C_INT, 0.025)

# Printer cabinet and paper tray just left of the entrance.
cube('Printer station | cabinet', (-7.35, -4.60, 0.43), (1.95, 1.35, 0.78), MAT_COUNTER, C_INT, 0.04)
cube('Printer | body', (-7.35, -4.55, 0.95), (1.05, 0.72, 0.34), MAT_WALL, C_INT, 0.05)
cube('Printer | paper tray', (-7.35, -4.90, 0.78), (0.72, 0.40, 0.05), MAT_DARK, C_INT)
for i in range(3):
    cube(f'Entrance | shopping basket stack {i+1}', (-6.15, -4.25, 0.52+i*0.22), (0.62, 0.48, 0.18), MAT_PRODUCT[1], C_INT, 0.035)

# Back-wall promo boards.
for i, x in enumerate((-6.6, -4.0, -1.4, 1.2, 3.8, 6.4)):
    cube(f'Back wall | promo board {i+1}', (x, 5.18, 2.55), (1.9, 0.08, 1.55), MAT_PRODUCT[i % len(MAT_PRODUCT)], C_INT, 0.025)
    cube(f'Back wall | promo inset {i+1}', (x, 5.12, 2.55), (1.55, 0.04, 1.15), MAT_WALL, C_INT)

# Low ice-cream freezer in the front-right bay, set back to preserve the entrance aisle.
cube('Ice cream freezer | base', (4.35, -4.30, 0.78), (8.55, 2.00, 1.42), MAT_WALL, C_INT, 0.08)
cube('Ice cream freezer | front plinth', (4.35, -5.32, 0.40), (8.35, 0.08, 0.42), MAT_SIGN_EDGE, C_INT, 0.025)
cube('Ice cream freezer | glass lid', (4.35, -4.30, 1.53), (8.35, 1.83, 0.08), MAT_COLDCASE, C_INT, 0.035)
for x in (0.15, 2.25, 4.35, 6.45, 8.55):
    cube('Ice cream freezer | lid frame', (x, -4.30, 1.60), (0.07, 1.85, 0.06), MAT_DARK, C_INT)
for i in range(9):
    x = 0.25 + i*1.00
    cube(f'Ice cream tub {i+1}', (x, -4.30, 1.20), (0.52, 0.52, 0.44), MAT_PRODUCT[i % len(MAT_PRODUCT)], C_INT, 0.035)

# Adjustable global illumination: exterior, sign, interior fixtures and fill.
def area_light(name, loc, target, energy, size, color=(1.0, 0.88, 0.72), size_y=None):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.color = color
    data.use_shadow = False
    data.shape = 'RECTANGLE' if size_y else 'DISK'
    data.size = size
    if size_y:
        data.size_y = size_y
    obj = bpy.data.objects.new(name, data)
    C_LIGHT.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj

# Ceiling strips are separate meshes so the fixture layout remains visible in blockout.
for x in (-5.5, 0.5, 6.5):
    for y in (-2.7, 2.2):
        cube('Ceiling | luminous diffuser', (x, y, 4.16), (2.5, 0.18, 0.08), MAT_LIGHT, C_INT, 0.025)
        area_light('Interior | ceiling panel', (x, y, 4.08), (x, y, 0.4), INTERIOR_LIGHT_ENERGY, 2.8, size_y=0.8)

# Warm pools on the storefront and pink accent illumination beneath the sign.
for x in (-7.0, DOOR_CENTER_X, 2.8, 7.0):
    area_light('Facade | warm downlight', (x, -5.6, 4.05), (x, -5.0, 0.4), FACADE_LIGHT_ENERGY, 3.0)
area_light('Sign | pink wash', (0, -5.85, 4.0), (0, -7.2, 3.0), 140, 7.0, color=(1.0, 0.12, 0.55))
area_light('Interior | checkout fill', (-5.1, -0.9, 3.95), (-5.1, -1.8, 1.1), 240, 2.6)
area_light('Interior | freezer fill', (4.4, -3.8, 3.95), (4.4, -4.3, 0.8), 200, 3.0)

# Adjustable global fill and directional night light.
area_data = bpy.data.lights.new('Key | adjustable area', 'AREA')
area_data.energy = AREA_ENERGY
area_data.shape = 'DISK'
area_data.size = AREA_SIZE
area_obj = bpy.data.objects.new('Key | adjustable area', area_data)
C_LIGHT.objects.link(area_obj)
area_obj.location = AREA_LOCATION
area_obj.rotation_euler = (math.radians(28), 0, math.radians(-8))

sun_data = bpy.data.lights.new('Fill | adjustable sun', 'SUN')
sun_data.energy = SUN_ENERGY
sun_data.angle = math.radians(SUN_ANGLE_DEG)
sun_obj = bpy.data.objects.new('Fill | adjustable sun', sun_data)
C_LIGHT.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(28), math.radians(-18), math.radians(-32))

world = bpy.data.worlds.new('Graybox world') if not bpy.data.worlds else bpy.data.worlds[0]
bpy.context.scene.world = world
world.use_nodes = True
world_bg = next(node for node in world.node_tree.nodes if node.bl_idname == 'ShaderNodeBackground')
world_bg.inputs['Color'].default_value = (0.12, 0.14, 0.17, 1)
world_bg.inputs['Strength'].default_value = WORLD_STRENGTH

# Set the render engine using identifiers supported by this Blender build.
scene = bpy.context.scene
available_engines = {item.identifier for item in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
scene.render.engine = next(engine for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'CYCLES', 'BLENDER_WORKBENCH') if engine in available_engines)
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = False
scene.view_settings.exposure = -0.8
scene.render.fps = 24
scene.frame_set(1)
view_transforms = {item.identifier for item in scene.view_settings.bl_rna.properties['view_transform'].enum_items}
scene.view_settings.view_transform = 'AgX' if 'AgX' in view_transforms else 'Standard'

# Wide interior camera looks from the entry down the clear center aisle.
camera_data = bpy.data.cameras.new('Interior overview camera')
camera = bpy.data.objects.new('Camera | interior overview', camera_data)
C_BUILD.objects.link(camera)
camera.location = (-1.55, 0.15, 1.72)
camera_target = Vector((5.6, 0.15, 1.52))
camera.rotation_euler = (camera_target - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.lens = 22
camera_data.clip_start = 0.08
camera_data.clip_end = 120
scene.camera = camera

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces.active.region_3d.view_location = (-2, -3, 1.4)
        area.spaces.active.region_3d.view_distance = 43

# Export the complete model, then render a still of the interior.
export_path = os.path.abspath(bpy.path.abspath(EXPORT_GLB))
os.makedirs(os.path.dirname(export_path), exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=export_path, export_format='GLB', use_selection=False, export_lights=True, export_animations=True)
render_path = os.path.abspath(bpy.path.abspath('//ConvenienceStore_render.png'))
scene.render.filepath = render_path
bpy.ops.render.render(write_still=True)
print(f'Graybox created. GLB exported to: {export_path}')
print(f'Interior render saved to: {render_path}')
