"""Reference-led, unoccupied commuter train and elevated platform scene."""
from pathlib import Path
import sys
import math
import random
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
random.seed(2426)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'Commuter station / anime reference'
FLOOR, RAIL, TRAIN_X = 6.2, 5.03, 4.55
PLATFORM_HALF, CAR_HALF, CAR_LENGTH = 2.90, 1.51, 19.8
DOOR_CENTRES = (-7.35, -2.45, 2.45, 7.35)
DOOR_WIDTH, DOOR_TRAVEL = 1.30, 0.69


def collection(name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


C_PLATFORM = collection('STATION - platform and canopy')
C_TRACK = collection('STATION - tracks and catenary')
C_ENTRY = collection('STATION - street entrance and stairs')
C_CITY = collection('SITE - neighbourhood')
C_TRAIN = collection('TRAIN - two connected cars')
C_DAY = collection('LIGHTS - day')
C_NIGHT = collection('LIGHTS - night')
C_PRACTICAL = collection('LIGHTS - practicals')
C_CAMERA = collection('CAMERAS')


def material(name, color, glow=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = .8
    if glow:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = glow
    return mat


M = {key: material(name, color, glow) for key, name, color, glow in [
    ('steel', 'Structure | muted sage steel', (.12,.18,.15), 0),
    ('dark', 'Structure | graphite edges', (.07,.10,.10), 0),
    ('concrete', 'Concrete | warm grey', (.45,.47,.40), 0),
    ('tile', 'Platform | sage grey tiles', (.32,.39,.32), 0),
    ('tile_light', 'Platform | sunlit cream tiles', (.55,.56,.46), 0),
    ('grout', 'Platform | dark fine grout', (.14,.20,.15), 0),
    ('yellow', 'Platform | yellow tactile paving', (.93,.66,.045), 0),
    ('edge', 'Platform | pale green safety line', (.43,.69,.34), 0),
    ('body', 'Train | satin silver body', (.62,.67,.65), 0),
    ('blue', 'Train | blue exterior belt', (.065,.28,.49), 0),
    ('cream', 'Train | warm ivory panels', (.60,.59,.44), 0),
    ('floor', 'Train | warm orange floor', (.86,.40,.12), 0),
    ('seat', 'Train | olive green bench', (.11,.22,.015), 0),
    ('seat_top', 'Train | light green seat cushion', (.17,.30,.025), 0),
    ('rail', 'Train | sea green handrails', (.13,.25,.23), 0),
    ('white', 'Train | white triangular grips', (.90,.90,.80), 0),
    ('strap', 'Train | tan hanging straps', (.28,.22,.12), 0),
    ('glass', 'Glass | pale blue train glazing', (.70,.87,.88), 0),
    ('screen', 'Light | destination display', (.075,.12,.13), .5),
    ('light', 'Light | neutral warm diffuser', (.85,.91,.79), 1.8),
    ('beige', 'Entrance | cream facade', (.77,.68,.49), 0),
    ('brick', 'Entrance | ochre brick plinth', (.59,.34,.15), 0),
    ('pavement', 'Site | golden sidewalk', (.63,.49,.28), 0),
    ('asphalt', 'Site | desaturated road', (.18,.24,.26), 0),
    ('city', 'Site | pale blue city', (.52,.65,.66), 0),
    ('window', 'Site | hazy blue windows', (.44,.68,.72), 0),
    ('pink', 'Graphic | pastel salmon', (.83,.43,.30), 0),
    ('mint', 'Graphic | pale mint', (.46,.70,.49), 0),
    ('cyan', 'Graphic | muted blue', (.26,.63,.71), 0),
]}


def mesh_object(name, vertices, faces, mat, coll):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def box(name, pos, size, mat, coll, bevel=0, rotation=(0,0,0)):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for vertex in bm.verts:
        vertex.co.x *= size[0]; vertex.co.y *= size[1]; vertex.co.z *= size[2]
    bm.to_mesh(mesh); bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh); coll.objects.link(obj)
    obj.location = pos; obj.rotation_euler = rotation
    if bevel:
        modifier = obj.modifiers.new('Soft illustrated corner', 'BEVEL')
        modifier.width = bevel; modifier.segments = 2
    return obj


def tube(name, points, radius, mat, coll, closed=False):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'; curve.resolution_u = 1
    curve.bevel_depth = radius; curve.bevel_resolution = 1
    spline = curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for vertex, pos in zip(spline.points, points): vertex.co = (*pos,1)
    spline.use_cyclic_u = closed
    curve.materials.append(mat)
    obj = bpy.data.objects.new(name,curve); coll.objects.link(obj)
    return obj


def cylinder(name, pos, radius, depth, mat, coll, rotation=(0,0,0), segments=16):
    mesh=bpy.data.meshes.new(name); bm=bmesh.new()
    bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=segments,
                         radius1=radius,radius2=radius,depth=depth)
    bm.to_mesh(mesh);bm.free();mesh.materials.append(mat)
    obj=bpy.data.objects.new(name,mesh);coll.objects.link(obj)
    obj.location=pos;obj.rotation_euler=rotation
    return obj


def beam(name, a, b, thickness, mat, coll):
    a,b=Vector(a),Vector(b)
    obj=box(name,(a+b)/2,(thickness,thickness,(b-a).length),mat,coll)
    obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return obj


FONT=None
for path in ['C:/Windows/Fonts/YuGothB.ttc','C:/Windows/Fonts/arialbd.ttf']:
    if Path(path).exists(): FONT=bpy.data.fonts.load(path);break


def text(name, body, pos, size, mat, coll, rotation=(math.pi/2,0,0)):
    curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.size=size
    curve.align_x='CENTER';curve.align_y='CENTER';curve.resolution_u=3
    if FONT:curve.font=FONT
    curve.materials.append(mat)
    obj=bpy.data.objects.new(name,curve);coll.objects.link(obj)
    obj.location=pos;obj.rotation_euler=rotation
    return obj


def area(name,pos,target,power,size,color,coll):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    data.color=color;data.use_shadow=False
    obj=bpy.data.objects.new(name,data);coll.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj


def rounded_yz(x, y, z, width, height, radius):
    points=[]
    for cy,cz,start in [(width/2-radius,height/2-radius,0),
                        (-width/2+radius,height/2-radius,90),
                        (-width/2+radius,-height/2+radius,180),
                        (width/2-radius,-height/2+radius,270)]:
        for i in range(5):
            angle=math.radians(start+i*22.5)
            points.append((x,y+cy+radius*math.cos(angle),z+cz+radius*math.sin(angle)))
    return points


# Elevated island platform: two yellow edges, one central canopy support row.
for side in (-1,1):
    box(f'Viaduct | track deck {side}',(side*5.5,0,4.44),(4.7,260,.56),M['concrete'],C_TRACK)
box('Viaduct | island deck',(0,0,4.44),(6.4,78,.56),M['concrete'],C_TRACK)
box('Platform | continuous slab',(0,0,FLOOR-.75),(5.8,78,1.5),M['concrete'],C_PLATFORM)
box('Platform | continuous tiled surface',(0,0,FLOOR-.025),(5.8,78,.05),M['tile'],C_PLATFORM)
for side in (-1,1):
    box(f'Platform | cream edge {side}',(side*2.4,0,FLOOR+.002),(.98,78,.008),M['tile_light'],C_PLATFORM)
    box(f'Platform | tactile band {side}',(side*2.32,0,FLOOR+.012),(.32,78,.025),M['yellow'],C_PLATFORM)
    box(f'Platform | safety green line {side}',(side*2.82,0,FLOOR+.009),(.055,78,.018),M['edge'],C_PLATFORM)
    # Bumps are one low-poly mesh per edge, rather than thousands of objects.
    verts=[];faces=[]
    for iy in range(390):
        y=-38.9+iy*.20
        for dx in (-.105,0,.105):
            x=side*2.32+dx;start=len(verts)
            verts.extend([(x+math.cos(i*math.pi/3)*.022,y+math.sin(i*math.pi/3)*.022,FLOOR+.033) for i in range(6)])
            faces.append(tuple(range(start,start+6)))
    mesh_object(f'Platform | tactile studs {side}',verts,faces,M['yellow'],C_PLATFORM)
for i in range(-9,10):
    box(f'Platform | longitudinal grout {i}',(i*.30,0,FLOOR+.007),(.009,78,.012),M['grout'],C_PLATFORM)
for i in range(130):
    box(f'Platform | transverse grout {i}',(0,-38.7+i*.60,FLOOR+.008),(5.8,.009,.012),M['grout'],C_PLATFORM)
for y in (-22,-12,-2,8,18,28):
    for side in (-1,1):
        box(f'Platform | boarding marker {side} {y}',(side*2.64,y,FLOOR+.023),(.30,.42,.015),M['yellow'],C_PLATFORM)
        text(f'Platform | marker numeral {side} {y}','4',(side*2.64,y,FLOOR+.035),.18,M['dark'],C_PLATFORM,(0,0,0))

for y in (-30,-20,0,10,20,30):
    box(f'Canopy | column web {y}',(0,y,FLOOR+2.08),(.12,.23,4.16),M['steel'],C_PLATFORM)
    for x in (-.14,.14):
        box(f'Canopy | column flange {y} {x}',(x,y,FLOOR+2.08),(.065,.34,4.16),M['steel'],C_PLATFORM)
    box(f'Canopy | column base {y}',(0,y,FLOOR+.055),(.58,.58,.11),M['concrete'],C_PLATFORM)
    for x in (-.19,.19):
        for yy in (-.19,.19):
            cylinder(f'Canopy | base bolt {y} {x} {yy}',(x,y+yy,FLOOR+.13),.025,.055,M['dark'],C_PLATFORM,segments=6)
    for side in (-1,1):
        beam(f'Canopy | pitched rafter {y} {side}',(0,y,FLOOR+4.35),(side*3.28,y,FLOOR+3.88),.16,M['steel'],C_PLATFORM)
        beam(f'Canopy | knee brace {y} {side}',(0,y,FLOOR+3.12),(side*1.48,y,FLOOR+4.12),.095,M['steel'],C_PLATFORM)
for side in (-1,1):
    for i in range(12):
        x=side*(i+.5)*.278
        z=FLOOR+4.35-abs(x)*.143
        segments=[(-32,-18),(-7,32)] if abs(x)<1.55 else [(-32,32)]
        for start,end in segments:
            box(f'CanopyRoof | corrugated sheet {side} {i} {start}',(x,(start+end)/2,z),(.285,end-start,.055),M['steel'],C_PLATFORM,
                rotation=(0,side*math.atan(.143),0))
            box(f'Canopy | sheet seam {side} {i} {start}',(x,(start+end)/2,z-.035),(.025,end-start,.035),M['dark'],C_PLATFORM)
    box(f'Canopy | gutter {side}',(side*3.28,0,FLOOR+3.84),(.13,64,.13),M['steel'],C_PLATFORM)
    box(f'Canopy | lengthwise purlin {side}',(side*1.65,0,FLOOR+4.03),(.12,64,.17),M['steel'],C_PLATFORM)
    for start,end in [(-31,-18),(-7,31)]:
        tube(f'Canopy | utility conduit {side} {start}',[(side*.48,start,FLOOR+4.15),(side*.48,end,FLOOR+4.15)],.025,M['body'],C_PLATFORM)
for y in (-25,5,20):
    box(f'Canopy | strip lamp {y}',(.5,y,FLOOR+4.01),(.15,2.4,.06),M['light'],C_PLATFORM)
    area(f'Platform practical {y}',(.6,y,FLOOR+3.8),(0,y,FLOOR),180,4,(.87,.96,.87),C_PRACTICAL)
for y in (-24,9,24):
    box(f'Platform | hanging direction board {y}',(-.55,y,FLOOR+2.9),(1.7,.13,.48),M['dark'],C_PLATFORM)
    box(f'Platform | sign backing {y}',(-.55,y-.071,FLOOR+2.9),(1.56,.018,.36),M['cream'],C_PLATFORM)
    for i,mat in enumerate((M['cyan'],M['yellow'],M['blue'])):
        box(f'Platform | sign graphic {y} {i}',(-1.19+i*.45,y-.085,FLOOR+2.9),(.11,.01,.30),mat,C_PLATFORM)
    for x in (-1.1,0):
        tube(f'Platform | sign suspension {y} {x}',[(x,y,FLOOR+3.15),(x,y,FLOOR+4.1)],.012,M['dark'],C_PLATFORM)
for y in (-4,16):
    for side in (-1,1):
        box(f'Platform | green bench seat {y} {side}',(side*.8,y,FLOOR+.45),(.48,2.2,.10),M['seat'],C_PLATFORM,.025)
        box(f'Platform | bench back {y} {side}',(side*.58,y,FLOOR+.76),(.08,2.2,.54),M['seat'],C_PLATFORM,.02)
        for dy in (-.8,.8):
            box(f'Platform | bench leg {y} {side} {dy}',(side*.8,y+dy,FLOOR+.22),(.10,.09,.44),M['steel'],C_PLATFORM)

# Screenshot 3 also shows a platform-to-upper-concourse stair. Its visible
# flight is modelled separately from the street entrance; the unseen hall is inferred.
UPPER_START,UPPER_COUNT,UPPER_RUN,UPPER_RISE=-18.0,26,.30,.13
upper_z=FLOOR+UPPER_COUNT*UPPER_RISE
for i in range(UPPER_COUNT):
    y=UPPER_START+(i+.5)*UPPER_RUN;h=(i+1)*UPPER_RISE
    box(f'Platform access | stair {i:02d}',(-.45,y,FLOOR+h/2),(1.30,UPPER_RUN+.008,h),M['tile_light'],C_PLATFORM)
    box(f'Platform access | escalator {i:02d}',(.80,y,FLOOR+h-.055),(.60,UPPER_RUN+.008,.11),M['dark'],C_PLATFORM)
    box(f'Platform access | escalator lip {i:02d}',(.80,y-UPPER_RUN/2+.02,FLOOR+h+.006),(.59,.025,.012),M['yellow'],C_PLATFORM)
end=UPPER_START+UPPER_COUNT*UPPER_RUN
for x in (-1.18,.27,.40,1.20):
    beam(f'Platform access | handrail {x}',(x,UPPER_START,FLOOR+.9),(x,end,upper_z+.9),.045,M['steel'],C_PLATFORM)
    for i in range(0,UPPER_COUNT,5):
        y=UPPER_START+(i+.5)*UPPER_RUN;z=FLOOR+(i+1)*UPPER_RISE
        beam(f'Platform access | rail post {x} {i}',(x,y,z),(x,y,z+.9),.035,M['steel'],C_PLATFORM)
box('Platform access | upper landing',(0,-9.0,upper_z-.10),(2.7,2.5,.20),M['tile_light'],C_PLATFORM)
for x in (-1.44,1.44):
    box(f'Platform access | hall side {x}',(x,-8.7,(FLOOR+12.14)/2),(.15,3.1,12.14-FLOOR),M['beige'],C_PLATFORM)
box('Platform access | hall rear',(0,-7.24,(FLOOR+12.14)/2),(3.0,.16,12.14-FLOOR),M['beige'],C_PLATFORM)
box('CanopyRoof | raised stair roof',(0,-12.6,12.14),(3.1,11.1,.18),M['steel'],C_PLATFORM)
for x in (-1.64,1.64):
    box(f'Canopy | stairwell transfer beam {x}',(x,-10,FLOOR+4.08),(.14,20,.18),M['steel'],C_PLATFORM)
box('Platform access | green guidance panel',(1.526,-8.9,FLOOR+1.1),(.012,.8,.65),M['mint'],C_PLATFORM)

# End railings, track-side acoustic panels and steel power-line gantries.
for y in (38.7,):
    for side in (-1,1):
        start,end=(-2.8,2.8) if y>0 else ((-2.8,-2.1) if side<0 else (1.2,2.8))
        if y>0 and side==1:continue
        for z in (FLOOR+.12,FLOOR+.95):
            tube(f'Platform | end rail {y} {side} {z}',[(start,y,z),(end,y,z)],.028,M['steel'],C_PLATFORM)
        count=max(2,int((end-start)/.26))
        for i in range(count+1):
            x=start+(end-start)*i/count
            tube(f'Platform | end vertical {y} {side} {i}',[(x,y,FLOOR),(x,y,FLOOR+1)],.021,M['steel'],C_PLATFORM)
for side in (-1,1):
    cx=side*TRAIN_X
    box(f'Track | ballast bed {side}',(cx,0,4.79),(3.0,260,.20),M['dark'],C_TRACK)
    for x in (cx-.5335,cx+.5335):
        box(f'Track | continuous rail {side} {x}',(x,0,RAIL-.04),(.07,260,.08),M['body'],C_TRACK)
    for i in range(400):
        box(f'Track | sleeper {side} {i}',(cx,-129.5+i*.65,4.92),(2.15,.17,.10),M['concrete'],C_TRACK)
    box(f'Track | acoustic wall {side}',(side*7.15,0,5.3),(.14,190,1.5),M['concrete'],C_TRACK)
    for y in range(-92,93,4):
        box(f'Track | acoustic panel frame {side} {y}',(side*7.15,y,5.8),(.22,.065,2.4),M['steel'],C_TRACK)
        box(f'Track | upper acoustic panel {side} {y}',(side*7.15,y+1.94,6.3),(.045,3.82,.73),M['cream'],C_TRACK)
    for y in range(-90,91,18):
        for dx in (-.23,.23):
            box(f'Catenary | upright {side} {y} {dx}',(side*6.6+dx,y,8.6),(.065,.09,6.0),M['body'],C_TRACK)
        for i in range(10):
            z=5.6+i*.6
            beam(f'Catenary | lattice {side} {y} {i}',(side*6.6-.23,y,z),(side*6.6+.23,y,z+.6),.035,M['body'],C_TRACK)
        beam(f'Catenary | cross arm {side} {y}',(side*6.6,y,11.45),(side*3.9,y,11.45),.10,M['body'],C_TRACK)
        tube(f'Catenary | dropper {side} {y}',[(cx,y,11.4),(cx,y,10.4)],.016,M['dark'],C_TRACK)
    tube(f'Catenary | contact wire {side}',[(cx,-130,10.4),(cx,130,10.4)],.013,M['dark'],C_TRACK)
    for y in range(-105,106,15):
        box(f'Viaduct | pier {side} {y}',(side*5.8,y,2.1),(1.1,1.3,4.2),M['concrete'],C_TRACK,.05)

# Street entrance: broad central stair, escalator on the right, open left passage.
STAIR_Y, STEP_RUN, STEP_COUNT = -51.1, .32, 36
rise=FLOOR/STEP_COUNT
for i in range(STEP_COUNT):
    height=(i+1)*rise
    box(f'Entrance | stair step {i:02d}',(-.65,STAIR_Y+(i+.5)*STEP_RUN,height/2),
        (3.8,STEP_RUN+.008,height),M['tile_light'],C_ENTRY)
    box(f'Entrance | stair nosing {i:02d}',(-.65,STAIR_Y+i*STEP_RUN+.025,height+.004),
        (3.8,.045,.008),M['concrete'],C_ENTRY)
landing_start=STAIR_Y+STEP_COUNT*STEP_RUN
box('Entrance | platform landing',(-.65,(landing_start-38)/2,FLOOR-.12),
    (3.8,-38-landing_start+.04,.24),M['tile_light'],C_ENTRY)
for x in (-2.65,-.65,1.35):
    beam(f'Entrance | stair handrail {x}',(x,STAIR_Y+.12,.90),(x,landing_start,FLOOR+.90),.055,M['steel'],C_ENTRY)
    for i in range(0,STEP_COUNT,6):
        y=STAIR_Y+(i+.5)*STEP_RUN;z=(i+1)*rise
        beam(f'Entrance | stair rail post {x} {i}',(x,y,z),(x,y,z+.9),.04,M['steel'],C_ENTRY)
ESC_X=2.22
for i in range(STEP_COUNT):
    z=(i+1)*rise
    box(f'Entrance | escalator tread {i:02d}',(ESC_X,STAIR_Y+(i+.5)*STEP_RUN,z-.06),
        (1.06,STEP_RUN+.005,.12),M['dark'],C_ENTRY)
    box(f'Entrance | escalator yellow lip {i:02d}',(ESC_X,STAIR_Y+i*STEP_RUN+.02,z+.005),
        (1.04,.025,.009),M['yellow'],C_ENTRY)
for x in (ESC_X-.64,ESC_X+.64):
    beam(f'Entrance | escalator balustrade {x}',(x,STAIR_Y-.3,.55),(x,landing_start,FLOOR+.55),.18,M['beige'],C_ENTRY)
    tube(f'Entrance | escalator black handrail {x}',[(x,STAIR_Y-.6,.88),(x,STAIR_Y+.1,1.0),
         (x,landing_start-.2,FLOOR+1.0),(x,landing_start+.7,FLOOR+.9)],.055,M['dark'],C_ENTRY)
for x,width in ((-6.25,.55),(-2.95,.48),(1.48,.26),(3.15,.32),(6.3,.5)):
    box(f'Entrance | facade pier {x}',(x,-51.6,2.35),(width,.65,4.7),M['beige'],C_ENTRY)
box('Entrance | continuous facade header',(0,-51.6,6.6),(13.1,.65,4.0),M['beige'],C_ENTRY)
box('Entrance | left return wall',(-6.4,-45,4.3),(.3,13.8,8.6),M['beige'],C_ENTRY)
box('Entrance | right return wall',(3.25,-45,4.3),(.25,13.8,8.6),M['beige'],C_ENTRY)
box('EntranceRoof | continuous hall roof',(-1.6,-45,8.61),(10.15,14.1,.22),M['beige'],C_ENTRY)
box('Entrance | left passage floor',(-4.5,-45,-.05),(3.3,14.1,.10),M['pavement'],C_ENTRY)
box('Entrance | name sign frame',(0,-51.98,5.30),(3.8,.14,.56),M['tile_light'],C_ENTRY,.025)
box('Entrance | name sign blue panel',(.15,-52.06,5.30),(3.2,.018,.34),M['city'],C_ENTRY)
box('Entrance | sign square',(-1.62,-52.07,5.30),(.30,.015,.34),M['window'],C_ENTRY)
for i in range(17):
    x=-6.3+i*.75
    box(f'Entrance | facade panel joint {i}',(x,-51.935,6.45),(.012,.008,2.9),M['concrete'],C_ENTRY)
for x in (-5.4,5.2):
    box(f'Entrance | upper window {x}',(x,-51.94,7.05),(1.3,.015,.8),M['window'],C_ENTRY)
box('Entrance | pedestrian forecourt',(0,-55,-.12),(23,8,.24),M['pavement'],C_ENTRY)
for x in range(-11,12):
    box(f'Entrance | forecourt joint {x}',(x,-55,.006),(.012,8,.012),M['concrete'],C_ENTRY)
for i in range(11):
    box(f'Entrance | forecourt cross joint {i}',(0,-58.7+i*.72,.007),(23,.012,.014),M['concrete'],C_ENTRY)
box('Entrance | guidance tactile line',(-.65,-54.7,.025),(.32,6.8,.05),M['yellow'],C_ENTRY)
for x in (-6.4,6.5):
    cylinder(f'Entrance | bollard {x}',(x,-54.0,.42),.09,.84,M['dark'],C_ENTRY)
    cylinder(f'Entrance | bollard reflective band {x}',(x,-54.0,.66),.094,.10,M['tile_light'],C_ENTRY)
box('Entrance | timetable pole',(5.0,-54.0,1.3),(.12,.12,2.6),M['steel'],C_ENTRY)
box('Entrance | timetable case',(5.0,-54.0,2.05),(.64,.22,1.5),M['tile_light'],C_ENTRY,.025)
box('Entrance | timetable graphic',(5.0,-54.12,2.10),(.50,.015,1.28),M['cream'],C_ENTRY)
box('Entrance | timetable orange cap',(5.0,-54.13,2.62),(.50,.01,.21),M['pink'],C_ENTRY)
for i in range(8):
    box(f'Entrance | timetable rule {i}',(5.0,-54.135,2.38-i*.11),(.40,.006,.013),M['concrete'],C_ENTRY)

# Two connected cars, with a real central aisle and openings cut around windows/doors.
train_root=bpy.data.objects.new('TrainRoot',None);C_TRAIN.objects.link(train_root)
controller=bpy.data.objects.new('TrainDoors',None);C_TRAIN.objects.link(controller)
controller['open']=1.0;controller['travel']=DOOR_TRAVEL
controller.id_properties_ui('open').update(min=0,max=1)
DOOR_POINTS=[]
for car,cy in enumerate((-6.0,14.5)):
    prefix=f'Car{car+1:02d}'
    y0,y1=cy-CAR_LENGTH/2,cy+CAR_LENGTH/2
    box(f'{prefix} | floor slab',(TRAIN_X,cy,FLOOR-.12),(2.92,CAR_LENGTH,.24),M['body'],C_TRAIN)
    box(f'{prefix} | orange aisle floor',(TRAIN_X,cy,FLOOR+.003),(2.87,CAR_LENGTH-.35,.012),M['floor'],C_TRAIN)
    box(f'{prefix} | underframe',(TRAIN_X,cy,FLOOR-.34),(2.48,CAR_LENGTH-1.4,.25),M['dark'],C_TRAIN)
    for by in (cy-6.7,cy+6.7):
        box(f'{prefix} | bogie {by}',(TRAIN_X,by,RAIL+.62),(2.2,2.6,.32),M['dark'],C_TRAIN)
        for ay in (by-.8,by+.8):
            for side in (-1,1):
                cylinder(f'{prefix} | wheel {side} {ay}',(TRAIN_X+side*.67,ay,RAIL+.43),.43,.19,
                    M['dark'],C_TRAIN,(0,math.pi/2,0),segments=20)
    roof_profile=[(-1.51,2.43),(-1.37,2.66),(-.95,2.81),(0,2.88),(.95,2.81),(1.37,2.66),(1.51,2.43)]
    vertices=[(TRAIN_X+x,y,FLOOR+z) for y in (y0,y1) for x,z in roof_profile]
    mesh_object(f'TrainRoofGroup | {prefix} curved roof',vertices,
        [(i,i+1,i+8,i+7) for i in range(6)],M['body'],C_TRAIN)
    box(f'TrainRoofGroup | {prefix} ivory ceiling',(TRAIN_X,cy,FLOOR+2.57),(2.86,CAR_LENGTH-.1,.10),M['cream'],C_TRAIN)
    for side in (-1,1):
        x=TRAIN_X+side*CAR_HALF
        inner_x=x-side*.045
        intervals=[(y0+.08,cy+DOOR_CENTRES[0]-DOOR_WIDTH/2)]
        intervals += [(cy+a+DOOR_WIDTH/2,cy+b-DOOR_WIDTH/2) for a,b in zip(DOOR_CENTRES,DOOR_CENTRES[1:])]
        intervals.append((cy+DOOR_CENTRES[-1]+DOOR_WIDTH/2,y1-.08))
        for index,(a,b) in enumerate(intervals):
            mid=(a+b)/2;length=b-a
            box(f'{prefix} | side lower {side} {index}',(x,mid,FLOOR+.46),(.09,length+.015,.92),M['body'],C_TRAIN)
            box(f'{prefix} | inner lower {side} {index}',(inner_x-side*.02,mid,FLOOR+.56),(.035,length+.015,1.12),M['cream'],C_TRAIN)
            box(f'{prefix} | blue belt {side} {index}',(x+side*.051,mid,FLOOR+.81),(.018,length+.018,.22),M['blue'],C_TRAIN)
            box(f'{prefix} | upper ivory {side} {index}',(x,mid,FLOOR+2.32),(.095,length+.015,.48),M['cream'],C_TRAIN)
            width=max(.32,length-.22)
            points=rounded_yz(x,mid,FLOOR+1.60,width,1.17,.10)
            mesh_object(f'{prefix} | broad window {side} {index}',points,[tuple(range(len(points)))],M['glass'],C_TRAIN)
            tube(f'{prefix} | dark window gasket {side} {index}',points,.032,M['dark'],C_TRAIN,True)
            for yy in (a+.055,b-.055):
                box(f'{prefix} | window pillar {side} {index} {yy}',(x,yy,FLOOR+1.60),(.095,.12,1.23),M['cream'],C_TRAIN)
            if length>2:
                seat_x=TRAIN_X+side*1.14
                box(f'{prefix} | green bench back {side} {index}',(seat_x+side*.22,mid,FLOOR+.84),(.12,length-.23,.62),M['seat'],C_TRAIN,.025)
                box(f'{prefix} | green bench cushion {side} {index}',(seat_x,mid,FLOOR+.46),(.54,length-.23,.12),M['seat_top'],C_TRAIN,.03)
                box(f'{prefix} | bench vent base {side} {index}',(seat_x,mid,FLOOR+.20),(.47,length-.29,.39),M['dark'],C_TRAIN)
                verts=[];faces=[]
                for row in range(4):
                    for j in range(int(length/.15)):
                        yy=a+.15+j*.15+(row%2)*.04;zz=FLOOR+.07+row*.075
                        start=len(verts);xx=seat_x-side*.241
                        verts.extend([(xx,yy,zz),(xx,yy+.10,zz),(xx,yy+.10,zz+.025),(xx,yy,zz+.025)])
                        faces.append((start,start+1,start+2,start+3))
                mesh_object(f'{prefix} | patterned heater grille {side} {index}',verts,faces,M['body'],C_TRAIN)
                for yy in (a+.10,b-.10):
                    box(f'{prefix} | ivory seat end {side} {index} {yy}',(seat_x,yy,FLOOR+.65),(.57,.085,.69),M['cream'],C_TRAIN,.025)
                    tube(f'{prefix} | seat end rail {side} {index} {yy}',[(seat_x-side*.25,yy,FLOOR+.99),(seat_x-side*.25,yy,FLOOR+2.48)],.024,M['rail'],C_TRAIN)
                rack_x=TRAIN_X+side*1.18
                for dx in (-.24,.24):
                    tube(f'{prefix} | luggage rack rail {side} {index} {dx}',[(rack_x+dx,a+.10,FLOOR+2.10),(rack_x+dx,b-.10,FLOOR+2.10)],.022,M['rail'],C_TRAIN)
                for j in range(int(length/.24)):
                    yy=a+.13+j*.24
                    tube(f'{prefix} | luggage rack bar {side} {index} {j}',[(rack_x-.24,yy,FLOOR+2.10),(rack_x+.24,yy,FLOOR+2.10)],.012,M['rail'],C_TRAIN)
                box(f'{prefix} | upper ad panel {side} {index}',(inner_x-side*.055,mid,FLOOR+2.31),(.018,length-.25,.30),M['pink' if index%2 else 'mint'],C_TRAIN)
        for gate,offset in enumerate(DOOR_CENTRES):
            dy=cy+offset
            for yy in (dy-DOOR_WIDTH/2-.04,dy+DOOR_WIDTH/2+.04):
                box(f'{prefix} | door jamb {side} {gate} {yy}',(x,yy,FLOOR+1.20),(.12,.085,2.40),M['body'],C_TRAIN)
            box(f'{prefix} | door header {side} {gate}',(x,dy,FLOOR+2.38),(.13,DOOR_WIDTH+.12,.18),M['cream'],C_TRAIN)
            box(f'{prefix} | door threshold {side} {gate}',(x-side*.03,dy,FLOOR+.02),(.20,DOOR_WIDTH+.06,.04),M['body'],C_TRAIN)
            if side==-1:DOOR_POINTS.append((x,dy,FLOOR))
            for leaf,direction in (('Left',-1),('Right',1)):
                root=bpy.data.objects.new(f'TrainLeaf{leaf}_{car}_{gate}_{side}',None)
                C_TRAIN.objects.link(root);root.parent=train_root
                root['direction']=direction;root['active_side']=side==-1
                if side==-1:
                    driver=root.driver_add('location',1).driver
                    driver.expression=f'{direction*DOOR_TRAVEL} * opening'
                    var=driver.variables.new();var.name='opening';var.targets[0].id=controller
                    var.targets[0].data_path='["open"]'
                before=set(C_TRAIN.objects)
                leaf_y=dy+direction*DOOR_WIDTH/4
                leaf_x=x+side*.085
                leaf_name=f'{prefix} | door {side} {gate} {leaf}'
                box(leaf_name+' lower',(leaf_x,leaf_y,FLOOR+.50),(.045,DOOR_WIDTH/2,.90),M['cream'],C_TRAIN)
                box(leaf_name+' upper',(leaf_x,leaf_y,FLOOR+2.17),(.045,DOOR_WIDTH/2,.23),M['cream'],C_TRAIN)
                for yy in (leaf_y-DOOR_WIDTH/4+.025,leaf_y+DOOR_WIDTH/4-.025):
                    box(leaf_name+f' stile {yy}',(leaf_x,yy,FLOOR+1.49),(.045,.05,1.23),M['body'],C_TRAIN)
                points=rounded_yz(leaf_x,leaf_y,FLOOR+1.49,DOOR_WIDTH/2-.12,1.15,.08)
                mesh_object(leaf_name+' glass',points,[tuple(range(len(points)))],M['glass'],C_TRAIN)
                tube(leaf_name+' gasket',points,.024,M['dark'],C_TRAIN,True)
                for part in set(C_TRAIN.objects)-before:part.parent=root
    for side in (-1,1):
        x=TRAIN_X+side*.88
        tube(f'{prefix} | overhead handrail {side}',[(x,y0+.6,FLOOR+2.26),(x,y1-.6,FLOOR+2.26)],.027,M['rail'],C_TRAIN)
        for j in range(33):
            yy=y0+.9+j*.55
            tube(f'{prefix} | strap {side} {j}',[(x,yy,FLOOR+2.26),(x,yy,FLOOR+2.02)],.018,M['strap'],C_TRAIN)
            tube(f'{prefix} | triangular grip {side} {j}',[(x,yy,FLOOR+2.03),(x-.11,yy,FLOOR+1.82),
                (x+.11,yy,FLOOR+1.82)],.021,M['white'],C_TRAIN,True)
    for yy in (cy-7,cy-2,cy+3,cy+7):
        tube(f'{prefix} | transverse rail {yy}',[(TRAIN_X-.88,yy,FLOOR+2.26),(TRAIN_X+.88,yy,FLOOR+2.26)],.024,M['rail'],C_TRAIN)
        box(f'{prefix} | hanging ad backing {yy}',(TRAIN_X,yy,FLOOR+2.14),(1.22,.035,.42),M['cream'],C_TRAIN)
        box(f'{prefix} | hanging ad graphic {yy}',(TRAIN_X,yy-.023,FLOOR+2.14),(.91,.01,.27),M['cyan' if int(yy)%2 else 'mint'],C_TRAIN)
        for xx,zz,ww,hh,mat in [(-.27,.04,.16,.14,'cream'),(.20,.01,.22,.19,'pink'),(0,-.09,.62,.024,'cream')]:
            box(f'{prefix} | ad print {yy} {xx} {zz}',(TRAIN_X+xx,yy-.032,FLOOR+2.14+zz),
                (ww,.006,hh),M[mat],C_TRAIN)
    for x in (TRAIN_X-.51,TRAIN_X+.51):
        for yy in (cy-5.1,cy+5.1):
            box(f'TrainRoofGroup | {prefix} ceiling diffuser {x} {yy}',(x,yy,FLOOR+2.51),(.10,7.0,.025),M['light'],C_TRAIN)
    for yy in (cy-6,cy,cy+6):
        area(f'Train interior {car} {yy}',(TRAIN_X,yy,FLOOR+2.42),(TRAIN_X,yy,FLOOR),130,2.0,(1,.94,.80),C_PRACTICAL)
    for end in (-1,1):
        yy=cy+end*CAR_LENGTH/2
        cap=[(TRAIN_X-CAR_HALF,yy,FLOOR+2.34)]+[(TRAIN_X+x,yy,FLOOR+z) for x,z in roof_profile]+[(TRAIN_X+CAR_HALF,yy,FLOOR+2.34)]
        mesh_object(f'TrainRoofGroup | {prefix} arched end cap {end}',cap,[tuple(range(len(cap)))],M['body'],C_TRAIN)
        box(f'{prefix} | end wall left {end}',(TRAIN_X-.99,yy,FLOOR+1.18),(1.03,.09,2.36),M['cream'],C_TRAIN)
        box(f'{prefix} | end wall right {end}',(TRAIN_X+.99,yy,FLOOR+1.18),(1.03,.09,2.36),M['cream'],C_TRAIN)
        box(f'{prefix} | end door head {end}',(TRAIN_X,yy,FLOOR+2.28),(.98,.09,.27),M['cream'],C_TRAIN)
        if not (car==0 and end==-1):
            box(f'{prefix} | gangway door sill {end}',(TRAIN_X,yy,FLOOR+.35),(.89,.05,.70),M['cream'],C_TRAIN)
            points=[(TRAIN_X-.38,yy,FLOOR+.78),(TRAIN_X+.38,yy,FLOOR+.78),
                    (TRAIN_X+.38,yy,FLOOR+2.12),(TRAIN_X-.38,yy,FLOOR+2.12)]
            mesh_object(f'{prefix} | gangway glazed door {end}',points,[(0,1,2,3)],M['glass'],C_TRAIN)
    if car==0:
        # A cab face consistent with the screenshot, without claiming a precise series.
        front=y0-.10
        box('Cab | lower silver nose',(TRAIN_X,front,FLOOR+.36),(3.02,.25,.77),M['body'],C_TRAIN,.08)
        box('Cab | blue face belt',(TRAIN_X,front-.14,FLOOR+.82),(2.94,.035,.23),M['blue'],C_TRAIN)
        box('Cab | windshield frame',(TRAIN_X,front,FLOOR+1.54),(2.94,.16,1.20),M['dark'],C_TRAIN,.08)
        box('Cab | panoramic blue glazing',(TRAIN_X,front-.095,FLOOR+1.54),(2.63,.018,.94),M['window'],C_TRAIN,.06)
        box('Cab | destination display',(TRAIN_X,front-.105,FLOOR+2.26),(1.92,.025,.25),M['screen'],C_TRAIN)
        for side in (-1,1):
            box(f'Cab | headlight {side}',(TRAIN_X+side*1.12,front-.15,FLOOR+.48),(.30,.03,.15),M['light'],C_TRAIN,.015)
            beam(f'Cab | wiper {side}',(TRAIN_X+side*.25,front-.12,FLOOR+1.15),
                 (TRAIN_X+side*.77,front-.12,FLOOR+1.75),.025,M['dark'],C_TRAIN)
        box('Cab | internal bulkhead',(TRAIN_X,y0+.70,FLOOR+1.18),(2.88,.10,2.36),M['cream'],C_TRAIN)
    else:
        # Visible bellows joining the cars; actual aisle spans the inter-car gap.
        box('Gangway | bridging floor',(TRAIN_X,4.25,FLOOR-.02),(.90,.75,.08),M['dark'],C_TRAIN)
        for yy in (4.00,4.12,4.24,4.36,4.48):
            for x in (TRAIN_X-.61,TRAIN_X+.61):
                box(f'Gangway | folded side {x} {yy}',(x,yy,FLOOR+1.08),(.10,.045,2.16),M['dark'],C_TRAIN)
    # Low rooftop ventilation unit and a simple diamond pantograph.
    box(f'TrainRoofGroup | {prefix} ventilation unit',(TRAIN_X,cy,FLOOR+3.03),(1.4,4.0,.26),M['body'],C_TRAIN,.05)
    px,py=TRAIN_X,cy+4.6
    for x in (px-.35,px+.35):
        beam(f'{prefix} | pantograph lower {x}',(x,py-.65,FLOOR+2.95),(x,py,FLOOR+3.65),.035,M['dark'],C_TRAIN)
        beam(f'{prefix} | pantograph upper {x}',(x,py,FLOOR+3.65),(x,py-.65,10.4),.035,M['dark'],C_TRAIN)
    box(f'{prefix} | pantograph contact bar',(px,py-.65,10.38),(1.25,.10,.04),M['dark'],C_TRAIN)

for obj in list(C_TRAIN.objects):
    if obj not in (train_root,controller) and obj.parent is None:obj.parent=train_root
controller['door_points']=[value for point in DOOR_POINTS for value in point]
scene['station_platform_height']=FLOOR
scene['station_rail_gauge']=1.067
scene['station_door_travel']=DOOR_TRAVEL
scene['station_reference_train_blue']=True
scene['station_no_people']=True

# Pale city backdrop: low-detail blocks beyond the sound barriers.
box('Site | continuous ground',(0,0,-.25),(180,340,.4),M['asphalt'],C_CITY)
box('Site | street in front of entrance',(0,-62,-.04),(120,7,.08),M['asphalt'],C_CITY)
for i in range(15):
    box(f'Site | road centre dash {i}',(-54+i*7.5,-62,.012),(3.0,.10,.024),M['tile_light'],C_CITY)
for side in (-1,1):
    for i in range(13):
        x=side*random.uniform(12,18);y=-40+i*9.0
        w=random.uniform(4.5,7.0);depth=random.uniform(4,7);height=random.uniform(8,14)
        box(f'City | building {side} {i}',(x,y,height/2),(w,depth,height),M['beige'] if i%3==0 else M['city'],C_CITY)
        for row in range(2,int(height/2)):
            for col in (-1,0,1):
                wx=x-side*(w/2+.01);wy=y+col*depth*.26
                box(f'City | window {side} {i} {row} {col}',(wx,wy,row*1.85),(.022,depth*.19,1.12),M['window'],C_CITY)
        box(f'City | rooftop edge {side} {i}',(x,y,height+.08),(w+.14,depth+.14,.16),M['concrete'],C_CITY)

# Day and evening rigs use the same stepped shading as the convenience store.
sun_data=bpy.data.lights.new('Sun | day','SUN');sun_data.energy=2.2;sun_data.angle=math.radians(1.5)
sun_data.color=(1,.94,.80)
sun=bpy.data.objects.new('Sun | day',sun_data);C_DAY.objects.link(sun)
sun.rotation_euler=(math.radians(27),math.radians(-24),math.radians(-30))
area('Day | platform sky fill',(-8,0,14),(0,0,FLOOR),1600,35,(.79,.94,1),C_DAY)
area('Day | entry fill',(0,-56,7),(0,-44,3),700,8,(1,.91,.74),C_DAY)
area('Night | sky key',(0,0,25),(0,0,0),1100,70,(.37,.53,.84),C_NIGHT)
area('Night | entry fill',(0,-55,7),(0,-44,3),500,8,(1,.78,.49),C_NIGHT)
for name,color,strength in [('World | day',(.64,.84,.88),.8),('World | night',(.035,.06,.12),.5)]:
    world=bpy.data.worlds.new(name);world.use_nodes=True;world.use_fake_user=True
    background=world.node_tree.nodes.get('Background');background.inputs[0].default_value=(*color,1)
    background.inputs[1].default_value=strength
scene.world=bpy.data.worlds['World | day']
for obj in C_NIGHT.objects:obj.hide_render=True;obj.hide_set(True)


def camera(name,pos,target,lens=35,ortho=None):
    data=bpy.data.cameras.new(name);data.lens=lens;data.clip_start=.04;data.clip_end=450
    if ortho:data.type='ORTHO';data.ortho_scale=ortho
    obj=bpy.data.objects.new(name,data);C_CAMERA.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj


camera('CAM | platform end',(-.85,23,FLOOR+1.65),(.1,48,FLOOR+1.60),27)
camera('CAM | platform reverse',(-1.5,27,FLOOR+1.70),(.2,-37,FLOOR+1.7),30)
camera('CAM | platform across',(10,-23,FLOOR+1.7),(0,-16,FLOOR+1.65),36)
camera('CAM | train exterior',(7,-28,9.8),(TRAIN_X,-6,7.4),37)
camera('CAM | carriage aisle',(TRAIN_X,-12.0,FLOOR+1.55),(TRAIN_X,3.7,FLOOR+1.40),25)
camera('CAM | bench reference',(TRAIN_X+1.20,-5.6,FLOOR+1.50),(TRAIN_X-1.4,-5.8,FLOOR+1.12),22)
camera('CAM | street entrance',(.2,-68,2.8),(-.4,-51.0,3.6),36)
camera('CAM | station overview',(36,-67,37),(0,-5,5),40,98)
scene.camera=bpy.data.objects['CAM | platform end']
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(ROOT/'renders/Platform_Day.png')
scene.render.fps=24
from station_style import apply_style
apply_style()
scene['station_notes']='Screenshots drive visible features; station identity, precise rolling-stock series and unseen connections are not established.'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Train_Station.blend'))
print('STATION_BUILD_OK',len(scene.objects),'objects')
