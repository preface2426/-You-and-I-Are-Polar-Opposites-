"""Popuri convenience store - reference-driven Blender build.

Creates a tight, fully enclosed store shell with real glass storefront and
freezer lids, a floor-plan-accurate interior, and a night-time parking lot.
Run with Blender 5.4:
    blender -b --python popuri_build.py
"""
from __future__ import annotations

import bpy
import bmesh
import math
import os
import random
from mathutils import Vector

# ----------------------------------------------------------------------------
# Paths / deterministic look
# ----------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(ROOT, "Popuri_Store.blend")
os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
random.seed(20261025)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "Popuri Store"

# ----------------------------------------------------------------------------
# Collections
# ----------------------------------------------------------------------------
def coll(name: str):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

C_ARCH = coll("ARCH - shell and storefront")
C_INT = coll("INTERIOR - fixtures")
C_GOODS = coll("INTERIOR - merchandise")
C_SIGN = coll("SIGNAGE and graphics")
C_SITE = coll("SITE - parking and neighbourhood")
C_LIGHT_DAY = coll("LIGHTS - day")
C_LIGHT_NIGHT = coll("LIGHTS - night")
C_GLOW = coll("LIGHTS - sign and practicals")
C_CAM = coll("CAMERAS")
C_STARS = coll("SITE - stars")

# ----------------------------------------------------------------------------
# Material helpers
# ----------------------------------------------------------------------------
def _set(bsdf, name, value):
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value
        return True
    return False


def material(name, color, roughness=0.5, metallic=0.0, transmission=0.0,
             ior=1.45, emission=None, emission_strength=0.0, coat=0.0,
             bump_scale=0.0, bump_strength=0.0, anisotropy=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (420, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (40, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    _set(bsdf, "Base Color", (*color, 1.0))
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Metallic", metallic)
    _set(bsdf, "IOR", ior)
    _set(bsdf, "Transmission Weight", transmission)
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Anisotropic IOR", anisotropy)
    if emission is not None:
        _set(bsdf, "Emission Color", (*emission, 1.0))
        _set(bsdf, "Emission Strength", emission_strength)
    if bump_scale > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.location = (-360, -220)
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        tex.inputs["Roughness"].default_value = 0.55
        bump = nt.nodes.new("ShaderNodeBump")
        bump.location = (-140, -210)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.035
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (*color, 1.0)
    return m


def glass_material(name, tint=(0.88, 0.97, 0.94), roughness=0.018, ior=1.45):
    """Thin architectural glass: realistic reflections/transmission, but
    transparent to shadow rays so daylight enters without caustic noise."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (520, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (180, 20)
    _set(bsdf, "Base Color", (*tint, 1.0))
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "IOR", ior)
    _set(bsdf, "Transmission Weight", 1.0)
    _set(bsdf, "Coat Weight", 0.15)
    _set(bsdf, "Coat Roughness", 0.02)
    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (-300, 240)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.location = (-60, -160)
    tr.inputs["Color"].default_value = (*tint, 1.0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (350, 0)
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs[0])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m.diffuse_color = (*tint, 0.28)
    return m


M = {}
M["wall"] = material("Wall | warm white", (0.74, 0.72, 0.65), 0.58, bump_scale=130, bump_strength=0.05)
M["wall_exterior"] = material("Wall | exterior cream", (0.76, 0.74, 0.65), 0.62, bump_scale=75, bump_strength=0.055)
M["concrete"] = material("Concrete | warm grey", (0.48, 0.47, 0.43), 0.78, bump_scale=55, bump_strength=0.12)
M["ceiling"] = material("Ceiling | satin white", (0.81, 0.80, 0.74), 0.48)
M["trim"] = material("Trim | white enamel", (0.91, 0.90, 0.84), 0.32)
M["trim_dark"] = material("Trim | graphite", (0.10, 0.12, 0.14), 0.35, metallic=0.35)
M["floor"] = material("Floor | mint tile", (0.40, 0.72, 0.37), 0.78, coat=0.0,
                      bump_scale=38, bump_strength=0.03)
M["grout"] = material("Floor | grout", (0.19, 0.32, 0.17), 0.72)
M["wood"] = material("Counter | honey wood", (0.44, 0.23, 0.11), 0.40, coat=0.22,
                     bump_scale=18, bump_strength=0.07)
M["counter_top"] = material("Counter | warm white top", (0.84, 0.82, 0.75), 0.24, coat=0.3)
M["shelf"] = material("Shelving | off white", (0.80, 0.79, 0.73), 0.40, metallic=0.12)
M["pegboard"] = material("Shelving | pegboard", (0.68, 0.67, 0.61), 0.55)
M["metal"] = material("Metal | brushed", (0.33, 0.35, 0.36), 0.30, metallic=0.72)
M["metal_dark"] = material("Metal | dark", (0.08, 0.09, 0.10), 0.38, metallic=0.65)
M["rubber"] = material("Rubber", (0.035, 0.038, 0.04), 0.72)
M["glass"] = glass_material("Glass | clear storefront")
M["glass_cool"] = glass_material("Glass | freezer", tint=(0.74, 0.91, 0.94), roughness=0.055)
M["purple"] = material("Sign | deep purple", (0.23, 0.02, 0.42), 0.26, metallic=0.25,
                       emission=(0.20, 0.012, 0.42), emission_strength=0.35)
M["purple_glow"] = material("Sign | purple emission", (0.12, 0.006, 0.25), 0.22,
                            emission=(0.30, 0.008, 0.66), emission_strength=1.25)
M["pink_glow"] = material("Sign | pink strips", (1.0, 0.08, 0.40), 0.20,
                          emission=(1.0, 0.025, 0.36), emission_strength=3.4)
M["sign_letter"] = material("Sign | ivory letters", (0.93, 0.69, 0.22), 0.28,
                            emission=(1.0, 0.57, 0.07), emission_strength=3.0)
M["ceiling_light"] = material("Light | warm diffuser", (1.0, 0.91, 0.74), 0.26,
                              emission=(1.0, 0.84, 0.58), emission_strength=5.5)
M["cold_light"] = material("Light | cold case", (0.54, 0.86, 1.0), 0.2,
                           emission=(0.30, 0.72, 1.0), emission_strength=3.5)
M["asphalt"] = material("Site | asphalt", (0.105, 0.145, 0.15), 0.86,
                        bump_scale=95, bump_strength=0.16)
M["paint"] = material("Site | parking paint", (0.78, 0.78, 0.69), 0.55)
M["kerb"] = material("Site | concrete kerb", (0.44, 0.43, 0.39), 0.8)
M["grass"] = material("Site | grass", (0.12, 0.19, 0.085), 0.9,
                      bump_scale=40, bump_strength=0.2)
M["hedge"] = material("Site | hedge", (0.055, 0.12, 0.05), 0.88,
                      bump_scale=18, bump_strength=0.35)
M["tree"] = material("Site | tree", (0.035, 0.075, 0.032), 0.9)
M["house"] = material("Site | house", (0.31, 0.31, 0.28), 0.7)
M["roof"] = material("Site | roof tile", (0.10, 0.11, 0.12), 0.65)
M["warm_window"] = material("Site | warm window", (0.96, 0.68, 0.33), 0.3,
                            emission=(1.0, 0.57, 0.20), emission_strength=3.2)
M["banner"] = material("Banner | New Open red", (0.62, 0.045, 0.055), 0.42)
M["banner_cream"] = material("Banner | cream lettering", (0.95, 0.85, 0.62), 0.4,
                             emission=(1.0, 0.78, 0.45), emission_strength=0.8)
M["white_sign"] = material("Sign | white backing", (0.94, 0.92, 0.85), 0.4,
                           emission=(1.0, 0.92, 0.78), emission_strength=0.35)
M["paper"] = material("Paper | display", (0.93, 0.91, 0.82), 0.55)
M["black"] = material("Black | matte", (0.025, 0.027, 0.03), 0.45)
M["red"] = material("Accent | red", (0.58, 0.045, 0.045), 0.42)
M["orange"] = material("Accent | orange", (0.78, 0.28, 0.055), 0.42)
M["green"] = material("Accent | green", (0.06, 0.28, 0.11), 0.5)
M["ice_blue"] = material("Accent | ice blue", (0.30, 0.64, 0.80), 0.34)
M["screen"] = material("Light | POS screen", (0.02, 0.07, 0.09), 0.18,
                       emission=(0.10, 0.42, 0.55), emission_strength=1.8)

# Merchandise palette: saturated Japanese convenience-store packaging.
PALETTE = [
    (0.72, 0.055, 0.045), (0.95, 0.38, 0.04), (0.94, 0.70, 0.06),
    (0.09, 0.34, 0.20), (0.04, 0.42, 0.48), (0.055, 0.19, 0.55),
    (0.48, 0.08, 0.38), (0.85, 0.17, 0.34), (0.13, 0.49, 0.32),
    (0.95, 0.52, 0.10), (0.55, 0.55, 0.13), (0.88, 0.86, 0.74),
    (0.22, 0.58, 0.78), (0.78, 0.22, 0.12), (0.36, 0.22, 0.50),
]
GOODS = []
for i, col in enumerate(PALETTE):
    GOODS.append(material(f"Goods | {i:02d}", col, 0.38, metallic=0.04, coat=0.06))
GOODS_METAL = [material(f"Can | {i:02d}", col, 0.24, metallic=0.55) for i, col in enumerate(PALETTE[:7])]
LABEL_WHITE = material("Goods | label white", (0.96, 0.94, 0.86), 0.5)
LABEL_DARK = material("Goods | label dark", (0.10, 0.105, 0.11), 0.5)


def packaging_material(name="Packaging | printed", metallic=0.0, roughness=0.38,
                       band_center=0.53, band_half=0.065,
                       band_color=(0.95, 0.93, 0.85), stripe_color=(0.08, 0.08, 0.075)):
    """One procedural wrapper for all merchandise: per-object random colour,
    printed label band and a thin brand stripe. Several variants break up the
    repetition of hundreds of packages without hundreds of materials."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (720, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (460, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    _set(bsdf, "Metallic", metallic)
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Coat Weight", 0.12)
    _set(bsdf, "Coat Roughness", 0.18)

    info = nt.nodes.new("ShaderNodeObjectInfo")
    info.location = (-780, 180)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-570, 180)
    cr = ramp.color_ramp
    while len(cr.elements) > 2:
        cr.elements.remove(cr.elements[-1])
    stops = [
        (0.00, (0.74, 0.045, 0.035)), (0.12, (0.93, 0.28, 0.03)),
        (0.25, (0.96, 0.67, 0.04)), (0.38, (0.20, 0.46, 0.10)),
        (0.50, (0.04, 0.42, 0.52)), (0.62, (0.045, 0.16, 0.52)),
        (0.74, (0.48, 0.08, 0.38)), (0.86, (0.93, 0.52, 0.10)),
        (1.00, (0.86, 0.82, 0.70)),
    ]
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = (*stops[0][1], 1)
    cr.elements[1].position = stops[-1][0]
    cr.elements[1].color = (*stops[-1][1], 1)
    for pos, col in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    nt.links.new(info.outputs["Random"], ramp.inputs["Fac"])

    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-780, -140)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-590, -140)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])

    def band(center, half, location):
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[1].default_value = center
        sub.location = (location[0], location[1])
        nt.links.new(sep.outputs["Z"], sub.inputs[0])
        ab = nt.nodes.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        ab.location = (location[0] + 140, location[1])
        nt.links.new(sub.outputs[0], ab.inputs[0])
        lt = nt.nodes.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        lt.inputs[1].default_value = half
        lt.location = (location[0] + 280, location[1])
        nt.links.new(ab.outputs[0], lt.inputs[0])
        return lt

    mask = band(band_center, band_half, (-380, -90))
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.location = (-40, 80)
    mix.inputs[2].default_value = (*band_color, 1)
    nt.links.new(mask.outputs[0], mix.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[1])

    mask2 = band(min(0.86, band_center + 0.21), 0.022, (-380, -340))
    mix2 = nt.nodes.new("ShaderNodeMixRGB")
    mix2.blend_type = "MIX"
    mix2.location = (170, 80)
    mix2.inputs[2].default_value = (*stripe_color, 1)
    nt.links.new(mask2.outputs[0], mix2.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], mix2.inputs[1])
    nt.links.new(mix2.outputs["Color"], bsdf.inputs["Base Color"])

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-260, -500)
    noise.inputs["Scale"].default_value = 95
    noise.inputs["Detail"].default_value = 2
    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (210, -350)
    bump.inputs["Strength"].default_value = 0.035
    bump.inputs["Distance"].default_value = 0.005
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

PKG = packaging_material()
PKG_B = packaging_material("Packaging | dark label", band_center=0.38, band_half=0.055,
                           band_color=(0.055, 0.055, 0.05), stripe_color=(1.0, 0.68, 0.08))
PKG_C = packaging_material("Packaging | cream label", band_center=0.63, band_half=0.105,
                           band_color=(0.88, 0.82, 0.67), stripe_color=(0.62, 0.08, 0.06))
PKG_SET = (PKG, PKG_B, PKG_C)
PKG_METAL = packaging_material("Packaging | can metal", metallic=0.55, roughness=0.24)

# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def link(obj, c):
    c.objects.link(obj)
    return obj


def box(name, loc, size, mat, c, bevel=0.0, rot=(0, 0, 0), segments=2):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    c.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    if mat is not None:
        me.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Micro bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(40)
        mod.harden_normals = True
    return obj


def cyl(name, loc, radius, depth, mat, c, segments=24, rot=(0, 0, 0), bevel=0.0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    c.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    me.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Micro bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def sphere(name, loc, radius, mat, c, scale=(1, 1, 1), subdiv=2):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    c.objects.link(obj)
    obj.location = loc
    obj.scale = scale
    me.materials.append(mat)
    return obj


def plane(name, loc, size, mat, c, rot=(math.pi / 2, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    c.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    me.materials.append(mat)
    return obj


def curve_tube(name, points, radius, mat, c, resolution=2):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = resolution
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, cu)
    c.objects.link(obj)
    cu.materials.append(mat)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def load_font(paths):
    for path in paths:
        if os.path.exists(path):
            try:
                return bpy.data.fonts.load(path)
            except Exception:
                pass
    return None

FONT_JP = load_font([
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
])
FONT_SCRIPT = load_font([r"C:\Windows\Fonts\segoesc.ttf", r"C:\Windows\Fonts\BRUSHSCI.TTF"])
FONT_LATIN = load_font([r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"])


def text(name, body, loc, size, mat, c, rot=(math.pi / 2, 0, 0), font=None,
         extrude=0.008, align_x="CENTER", align_y="CENTER", shear=0.0,
         space=1.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = 0.002
    cu.align_x = align_x
    cu.align_y = align_y
    cu.shear = shear
    cu.space_line = space
    if font is not None:
        cu.font = font
    obj = bpy.data.objects.new(name, cu)
    c.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    cu.materials.append(mat)
    return obj


def light_area(name, loc, target, energy, sx, sy, color=(1, 1, 1), c=None, spread=180):
    if c is None:
        c = C_LIGHT_DAY
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "RECTANGLE"
    data.size = sx
    data.size_y = sy
    data.color = color
    data.spread = math.radians(spread)
    obj = bpy.data.objects.new(name, data)
    c.objects.link(obj)
    obj.location = loc
    aim(obj, target)
    return obj


def light_point(name, loc, energy, color=(1, 1, 1), radius=0.25, c=None):
    if c is None:
        c = C_LIGHT_DAY
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    c.objects.link(obj)
    obj.location = loc
    return obj


def light_spot(name, loc, target, energy, angle, blend, color=(1, 1, 1), c=None, radius=0.1):
    if c is None:
        c = C_LIGHT_NIGHT
    data = bpy.data.lights.new(name, "SPOT")
    data.energy = energy
    data.spot_size = math.radians(angle)
    data.spot_blend = blend
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    c.objects.link(obj)
    obj.location = loc
    aim(obj, target)
    return obj

# ----------------------------------------------------------------------------
# Dimensions
# ----------------------------------------------------------------------------
W, D, H = 15.2, 9.8, 3.62
T = 0.24
X0, X1 = -W / 2, W / 2
Y0, Y1 = -D / 2, D / 2
FRONT = Y0
CEIL = H
FLOOR = 0.0

# ----------------------------------------------------------------------------
# Shell: continuous solid walls, interior linings, ceiling and roof
# ----------------------------------------------------------------------------
# Foundation slab, slightly larger than the building.
box("Foundation slab", (0, 0, -0.18), (W + 0.7, D + 0.7, 0.34), M["concrete"], C_ARCH, 0.025)
box("Interior floor slab", (0, 0, -0.05), (W + 0.04, D + 0.04, 0.10), M["floor"], C_ARCH)
# Tile grout lines on top of the floor, kept below 1 mm.
tile = 1.08
n_x = int(W / tile)
for i in range(1, n_x):
    x = X0 + i * tile
    box(f"Floor grout X {i:02d}", (x, 0, 0.002), (0.012, D - 0.04, 0.004), M["grout"], C_ARCH)
n_y = int(D / tile)
for i in range(1, n_y):
    y = Y0 + i * tile
    box(f"Floor grout Y {i:02d}", (0, y, 0.002), (W - 0.04, 0.012, 0.004), M["grout"], C_ARCH)

# Outer shell. Walls overlap at the corners (solid join, no cracks).
box("Rear wall | structure", (0, Y1 + T / 2, H / 2), (W + 2 * T, T + 0.04, H + 0.04), M["wall_exterior"], C_ARCH)
box("Left wall | structure", (X0 - T / 2, 0, H / 2), (T + 0.04, D + 2 * T, H + 0.04), M["wall_exterior"], C_ARCH)
box("Right rear wall | structure", (X1 + T / 2, (0.72 + Y1) / 2, H / 2),
    (T, Y1 - 0.72 + T, H), M["wall_exterior"], C_ARCH)

# Interior linings: these are continuous panels 20 mm inside the structure.
box("Rear interior lining", (0, Y1 - 0.012, H / 2), (W, 0.024, H), M["wall"], C_ARCH)
box("Left interior lining", (X0 + 0.012, 0, H / 2), (0.024, D, H), M["wall"], C_ARCH)
box("Right interior lining (rear)", (X1 - 0.012, (0.72 + Y1) / 2, H / 2),
    (0.024, Y1 - 0.72, H), M["wall"], C_ARCH)

# Continuous dropped ceiling + roof cap. The ceiling closes onto all four walls.
box("Dropped ceiling", (0, 0, H - 0.035), (W + 2 * T + 0.04, D + 2 * T + 0.04, 0.09), M["ceiling"], C_ARCH)
box("Roof slab", (0, 0, H + 0.10), (W + 0.50, D + 0.50, 0.28), M["roof"], C_ARCH)
box("Roof parapet front", (0, Y0 - 0.15, H + 0.36), (W + 0.5, 0.18, 0.3), M["trim_dark"], C_ARCH, 0.015)
box("Roof parapet back", (0, Y1 + 0.15, H + 0.36), (W + 0.5, 0.18, 0.3), M["trim_dark"], C_ARCH, 0.015)
box("Roof parapet left", (X0 - 0.15, 0, H + 0.36), (0.18, D + 0.5, 0.3), M["trim_dark"], C_ARCH, 0.015)
box("Roof parapet right", (X1 + 0.15, 0, H + 0.36), (0.18, D + 0.5, 0.3), M["trim_dark"], C_ARCH, 0.015)

# Baseboards and cornice close the wall/floor and wall/ceiling joints.
box("Rear baseboard", (0, Y1 - 0.045, 0.07), (W, 0.045, 0.14), M["trim"], C_ARCH, 0.006)
box("Left baseboard", (X0 + 0.045, 0, 0.07), (0.045, D, 0.14), M["trim"], C_ARCH, 0.006)
box("Right baseboard", (X1 - 0.045, -1.98, 0.07), (0.045, 5.9, 0.14), M["trim"], C_ARCH, 0.006)
box("Rear cornice", (0, Y1 - 0.05, H - 0.1), (W, 0.07, 0.14), M["trim"], C_ARCH, 0.006)
box("Left cornice", (X0 + 0.05, 0, H - 0.1), (0.07, D, 0.14), M["trim"], C_ARCH, 0.006)
box("Right cornice", (X1 - 0.05, 0, H - 0.1), (0.07, D, 0.14), M["trim"], C_ARCH, 0.006)

# Exterior plinth and service door.
box("Exterior plinth front", (0, Y0 - T / 2 - 0.02, 0.095), (W + 0.5, 0.06, 0.19), M["concrete"], C_ARCH, 0.008)
box("Exterior plinth right", (X1 + T / 2 + 0.02, 0, 0.095), (0.06, D + 0.5, 0.19), M["concrete"], C_ARCH, 0.008)
box("Service door | rear", (-5.9, Y1 - 0.035, 1.14), (1.18, 0.07, 2.28), M["metal_dark"], C_ARCH, 0.015)
box("Service door | handle", (-5.5, Y1 - 0.09, 1.12), (0.06, 0.06, 0.55), M["metal"], C_ARCH, 0.01)
box("Service door | sign", (-5.9, Y1 - 0.08, 2.48), (0.56, 0.03, 0.2), M["white_sign"], C_ARCH, 0.006)

# ----------------------------------------------------------------------------
# Storefront: one continuous frame, glass in rebates, no gaps at corners
# ----------------------------------------------------------------------------
FY = Y0 - T / 2           # centreline of the front wall
GLASS_Y = FY + 0.02
KNEE = 0.44
HEAD = 3.04
PANEL_TOP = 3.04
PIER_L = -7.08
PIER_R = 7.08
# The entrance moves to the left third of the shopfront and becomes a proper
# recessed, horizontally sliding glass door assembly with its own portal.
DOOR_CENTER = -3.55
DOOR_W = 2.86
DOOR_L = DOOR_CENTER - DOOR_W / 2
DOOR_R = DOOR_CENTER + DOOR_W / 2
PORTAL_L = DOOR_L - 0.12
PORTAL_R = DOOR_R + 0.12
DOOR_Y = FY + 0.34
LEFT_GLASS_END = DOOR_L - 0.14
RIGHT_GLASS_START = DOOR_R + 0.14

# Knee wall and header are split around the entrance so the doorway is a real
# floor-to-head opening, not a glazed panel sitting behind a knee wall.
box("Storefront | knee wall left", ((PIER_L + DOOR_L) / 2, FY, KNEE / 2),
    (DOOR_L - PIER_L, T, KNEE), M["trim"], C_ARCH, 0.01)
box("Storefront | knee wall right", ((DOOR_R + PIER_R) / 2, FY, KNEE / 2),
    (PIER_R - DOOR_R, T, KNEE), M["trim"], C_ARCH, 0.01)
box("Storefront | continuous header", (0, FY, (HEAD + H) / 2),
    (PIER_R - PIER_L, T, H - HEAD), M["trim"], C_ARCH, 0.01)
box("Storefront | left pier", ((X0 + PIER_L) / 2, FY, H / 2), (PIER_L - X0, T, H), M["wall_exterior"], C_ARCH, 0.012)
box("Storefront | right pier", ((PIER_R + X1) / 2, FY, H / 2), (X1 - PIER_R, T, H), M["wall_exterior"], C_ARCH, 0.012)
box("Storefront | interior left pier face", ((X0 + PIER_L) / 2, Y0 + 0.012, H / 2),
    (PIER_L - X0, 0.024, H), M["wall"], C_ARCH)
box("Storefront | interior right pier face", ((PIER_R + X1) / 2, Y0 + 0.012, H / 2),
    (X1 - PIER_R, 0.024, H), M["wall"], C_ARCH)
box("Storefront | left pier base", ((X0 + PIER_L) / 2, FY - 0.02, 0.18),
    (PIER_L - X0 + 0.04, 0.08, 0.36), M["concrete"], C_ARCH, 0.006)
box("Storefront | right pier base", ((PIER_R + X1) / 2, FY - 0.02, 0.18),
    (X1 - PIER_R + 0.04, 0.08, 0.36), M["concrete"], C_ARCH, 0.006)

# Fixed glazing left of the entrance: one tall pane behind the printer.
box("Front glass | left of door", ((PIER_L + LEFT_GLASS_END) / 2, GLASS_Y, (KNEE + PANEL_TOP) / 2),
    (LEFT_GLASS_END - PIER_L - 0.04, 0.018, PANEL_TOP - KNEE), M["glass"], C_ARCH)
box("Front glass | left purple band", ((PIER_L + LEFT_GLASS_END) / 2, GLASS_Y - 0.013, 1.24),
    (LEFT_GLASS_END - PIER_L - 0.05, 0.005, 0.25), M["purple"], C_ARCH)

# Fixed glazing right of the entrance: six bays.
right_mullions = [RIGHT_GLASS_START, -0.51, 0.99, 2.49, 3.99, 5.49, PIER_R]
for i in range(len(right_mullions) - 1):
    a, b = right_mullions[i], right_mullions[i + 1]
    width = b - a - 0.045
    cx = (a + b) / 2
    box(f"Front glass | right pane {i+1}", (cx, GLASS_Y, (KNEE + PANEL_TOP) / 2),
        (width, 0.018, PANEL_TOP - KNEE), M["glass"], C_ARCH)
    box(f"Front glass | right purple band {i+1}", (cx, GLASS_Y - 0.013, 1.24),
        (width, 0.005, 0.25), M["purple"], C_ARCH)

# Sill and intermediate rails stop at the entrance portal; the head rail is
# split as well so the door assembly reads as an independent element.
box("Storefront | sill rail left", ((PIER_L + DOOR_L) / 2, FY - 0.055, KNEE + 0.025),
    (DOOR_L - PIER_L, 0.12, 0.09), M["trim"], C_ARCH, 0.005)
box("Storefront | sill rail right", ((DOOR_R + PIER_R) / 2, FY - 0.055, KNEE + 0.025),
    (PIER_R - DOOR_R, 0.12, 0.09), M["trim"], C_ARCH, 0.005)
box("Storefront | head rail left", ((PIER_L + DOOR_L) / 2, FY - 0.055, PANEL_TOP - 0.04),
    (DOOR_L - PIER_L, 0.12, 0.09), M["trim"], C_ARCH, 0.005)
box("Storefront | head rail right", ((DOOR_R + PIER_R) / 2, FY - 0.055, PANEL_TOP - 0.04),
    (PIER_R - DOOR_R, 0.12, 0.09), M["trim"], C_ARCH, 0.005)
box("Storefront | mid rail left", ((PIER_L + DOOR_L) / 2, FY - 0.055, 1.08),
    (DOOR_L - PIER_L, 0.12, 0.075), M["trim"], C_ARCH, 0.004)
box("Storefront | mid rail right", ((DOOR_R + PIER_R) / 2, FY - 0.055, 1.08),
    (PIER_R - DOOR_R, 0.12, 0.075), M["trim"], C_ARCH, 0.004)

# Fixed-window mullions.
for x in right_mullions[1:-1]:
    box(f"Storefront | mullion {x:.2f}", (x, FY - 0.055, (KNEE + PANEL_TOP) / 2),
        (0.085, 0.16, PANEL_TOP - KNEE), M["trim"], C_ARCH, 0.006)
for x, width in ((PIER_L, 0.13), (PIER_R, 0.13)):
    box(f"Storefront | jamb {x:.2f}", (x, FY - 0.055, (KNEE + PANEL_TOP) / 2),
        (width, 0.17, PANEL_TOP - KNEE + 0.02), M["trim"], C_ARCH, 0.008)

# Recessed entrance portal: side reveals, a dark independent frame and a
# separate soffit. The glass door plane sits 340 mm inside the shopfront.
REVEAL_D = FY - DOOR_Y
box("Entrance | left reveal", (DOOR_L - 0.07, (FY + DOOR_Y) / 2, HEAD / 2),
    (0.14, abs(REVEAL_D) + 0.16, HEAD), M["trim"], C_ARCH, 0.006)
box("Entrance | right reveal", (DOOR_R + 0.07, (FY + DOOR_Y) / 2, HEAD / 2),
    (0.14, abs(REVEAL_D) + 0.16, HEAD), M["trim"], C_ARCH, 0.006)
box("Entrance | portal soffit", (DOOR_CENTER, (FY + DOOR_Y) / 2, HEAD - 0.045),
    (DOOR_W + 0.12, abs(REVEAL_D) + 0.10, 0.09), M["trim"], C_ARCH, 0.005)
box("Entrance | outer left jamb", (DOOR_L - 0.015, FY - 0.015, HEAD / 2),
    (0.075, 0.10, HEAD), M["metal_dark"], C_ARCH, 0.006)
box("Entrance | outer right jamb", (DOOR_R + 0.015, FY - 0.015, HEAD / 2),
    (0.075, 0.10, HEAD), M["metal_dark"], C_ARCH, 0.006)
box("Entrance | outer header", (DOOR_CENTER, FY - 0.015, HEAD - 0.035),
    (DOOR_W + 0.10, 0.10, 0.09), M["metal_dark"], C_ARCH, 0.006)
box("Entrance | inner left jamb", (DOOR_L + 0.018, DOOR_Y, HEAD / 2),
    (0.065, 0.14, HEAD), M["metal_dark"], C_ARCH, 0.005)
box("Entrance | inner right jamb", (DOOR_R - 0.018, DOOR_Y, HEAD / 2),
    (0.065, 0.14, HEAD), M["metal_dark"], C_ARCH, 0.005)
box("Entrance | threshold", (DOOR_CENTER, DOOR_Y, 0.022),
    (DOOR_W, 0.28, 0.045), M["metal"], C_ARCH, 0.004)
box("Entrance | recess floor", (DOOR_CENTER, (FY + DOOR_Y) / 2, 0.005),
    (DOOR_W - 0.08, abs(FY - DOOR_Y) + 0.10, 0.05), M["floor"], C_ARCH, 0.004)
box("Entrance | floor guide", (DOOR_CENTER, DOOR_Y - 0.02, 0.008),
    (DOOR_W - 0.10, 0.035, 0.016), M["metal_dark"], C_ARCH, 0.002)
box("Entrance | top track", (DOOR_CENTER, DOOR_Y, HEAD - 0.085),
    (DOOR_W, 0.13, 0.10), M["metal_dark"], C_ARCH, 0.005)
box("Entrance | track rail front", (DOOR_CENTER, DOOR_Y - 0.055, HEAD - 0.10),
    (DOOR_W, 0.025, 0.04), M["metal"], C_ARCH, 0.003)
box("Entrance | track rail rear", (DOOR_CENTER, DOOR_Y + 0.055, HEAD - 0.10),
    (DOOR_W, 0.025, 0.04), M["metal"], C_ARCH, 0.003)
box("Entrance | motion sensor", (DOOR_CENTER, DOOR_Y + 0.22, HEAD - 0.16),
    (0.42, 0.12, 0.13), M["metal_dark"], C_ARCH, 0.018)
box("Entrance | sensor window", (DOOR_CENTER, DOOR_Y + 0.155, HEAD - 0.16),
    (0.24, 0.015, 0.055), M["purple_glow"], C_ARCH, 0.006)
# Recessed vestibule light: keeps the glass entrance legible day and night.
box("Entrance | soffit light", (DOOR_CENTER, DOOR_Y + 0.26, HEAD - 0.085),
    (2.05, 0.10, 0.025), M["ceiling_light"], C_ARCH, 0.004)
light_area("Entrance | vestibule light", (DOOR_CENTER, DOOR_Y + 0.26, HEAD - 0.16),
           (DOOR_CENTER, DOOR_Y + 0.05, 0.0), 24.0, 1.9, 0.18,
           (1.0, 0.82, 0.55), C_GLOW, 160)

# Bi-parting electric glass door. Leaves slide behind the fixed shopfront,
# on an interior track clear of the portal jambs (no geometry in the passage).
LEAF_W = DOOR_W / 2
DOOR_TRAVEL = LEAF_W + 0.04
DOOR_PLANE = DOOR_Y + 0.24
controller = bpy.data.objects.new("AutomaticDoor", None)
C_ARCH.objects.link(controller)
controller["open"] = 0.0
controller.id_properties_ui("open").update(min=0.0, max=1.0)
controller["travel"] = DOOR_TRAVEL
controller["sensor_center"] = (DOOR_CENTER, DOOR_PLANE, 1.5)
for frame, value in ((1, 0), (25, 1), (85, 1), (109, 0), (144, 0)):
    controller["open"] = float(value)
    controller.keyframe_insert(data_path='["open"]', frame=frame)
for side, direction in (("Left", -1), ("Right", 1)):
    root = bpy.data.objects.new(f"Door{side}", None)
    C_ARCH.objects.link(root)
    root["direction"] = direction
    root["travel"] = DOOR_TRAVEL
    driver = root.driver_add("location", 0).driver
    driver.expression = f"{direction * DOOR_TRAVEL} * opening"
    var = driver.variables.new(); var.name = "opening"
    var.targets[0].id = controller; var.targets[0].data_path = '["open"]'
    cx = DOOR_CENTER + direction * LEAF_W / 2
    before = set(bpy.data.objects)
    name = f"Door{side} |"
    box(f"{name} glass", (cx, DOOR_PLANE, HEAD / 2),
        (LEAF_W - 0.10, 0.018, HEAD - 0.18), M["glass"], C_ARCH)
    for z in (0.065, HEAD - 0.065):
        box(f"{name} rail {z:.2f}", (cx, DOOR_PLANE, z),
            (LEAF_W, 0.065, 0.13), M["metal"], C_ARCH, 0.004)
    for dx in (-LEAF_W / 2 + 0.025, LEAF_W / 2 - 0.025):
        box(f"{name} stile {dx:.2f}", (cx + dx, DOOR_PLANE, HEAD / 2),
            (0.05, 0.065, HEAD), M["metal"], C_ARCH, 0.004)
    box(f"{name} meeting seal", (DOOR_CENTER + direction * 0.006, DOOR_PLANE, HEAD / 2),
        (0.012, 0.032, HEAD - 0.16), M["rubber"], C_ARCH)
    box(f"{name} safety band", (cx, DOOR_PLANE - 0.016, 1.24),
        (LEAF_W - 0.08, 0.006, 0.25), M["purple"], C_ARCH)
    text(f"{name} decal", "自動ドア", (cx, DOOR_PLANE - 0.038, 1.65), 0.11,
         M["white_sign"], C_SIGN, font=FONT_JP, extrude=0)
    for part in set(bpy.data.objects) - before:
        part.parent = root
box("Entrance | electric motor housing", (DOOR_CENTER, DOOR_PLANE, HEAD + 0.075),
    (2 * DOOR_W + 0.12, 0.20, 0.20), M["trim"], C_ARCH, 0.008)
for y in (DOOR_PLANE - 0.12, DOOR_PLANE + 0.12):
    box("Entrance | radar sensor", (DOOR_CENTER, y, HEAD + 0.07),
        (0.24, 0.08, 0.08), M["metal_dark"], C_ARCH, 0.012)
box("Entrance | exterior mat", (DOOR_CENTER, FY - 1.02, 0.057),
    (DOOR_W + 0.4, 1.65, 0.035), M["metal_dark"], C_SITE, 0.01)
box("Entrance | interior mat", (DOOR_CENTER, DOOR_Y + 0.95, 0.018),
    (DOOR_W - 0.20, 1.35, 0.035), M["metal_dark"], C_INT, 0.01)
scene.frame_end = 144
scene.frame_set(1)

# Three recycling / waste bins outside, left of the sliding entrance, as in
# the reference. They sit on a small concrete pad clear of the door swing.
BIN_Y = FY - 0.53
M_BIN = material("Waste bin | ivory enamel", (0.80, 0.79, 0.72), 0.48, coat=0.12)
box("Waste bins | pad", (-6.10, BIN_Y, 0.035), (2.25, 0.72, 0.07), M["concrete"], C_SITE, 0.02)
bin_specs = [
    (-6.82, M["ice_blue"], "かん", "CANS"),
    (-6.10, M["orange"], "びん", "BOTTLES"),
    (-5.38, M["green"], "もえる", "PAPER"),
]
for i, (x, accent, jp, en) in enumerate(bin_specs):
    box(f"Waste bin {i+1} | body", (x, BIN_Y, 0.51), (0.62, 0.50, 0.88), M_BIN, C_SITE, 0.055, segments=3)
    box(f"Waste bin {i+1} | lid", (x, BIN_Y, 0.975), (0.66, 0.54, 0.10), M["trim"], C_SITE, 0.03)
    box(f"Waste bin {i+1} | lid slope", (x, BIN_Y - 0.11, 1.015), (0.58, 0.26, 0.05), accent, C_SITE, 0.02,
        rot=(math.radians(-12), 0, 0))
    box(f"Waste bin {i+1} | dark slot", (x, BIN_Y - 0.255, 0.84), (0.34, 0.018, 0.13), M["metal_dark"], C_SITE, 0.02)
    box(f"Waste bin {i+1} | slot rim", (x, BIN_Y - 0.267, 0.84), (0.40, 0.012, 0.17), accent, C_SITE, 0.012)
    box(f"Waste bin {i+1} | color band", (x, BIN_Y - 0.256, 0.58), (0.58, 0.012, 0.30), accent, C_SITE, 0.012)
    text(f"Waste bin {i+1} | jp", jp, (x, BIN_Y - 0.270, 0.59), 0.085,
         M["white_sign"], C_SIGN, font=FONT_JP, extrude=0.002)
    text(f"Waste bin {i+1} | en", en, (x, BIN_Y - 0.270, 0.44), 0.045,
         M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.001)
    box(f"Waste bin {i+1} | foot", (x, BIN_Y - 0.02, 0.10), (0.46, 0.42, 0.12), M["metal_dark"], C_SITE, 0.02)
    box(f"Waste bin {i+1} | handle", (x, BIN_Y - 0.266, 0.69), (0.16, 0.018, 0.035), M["metal"], C_SITE, 0.008)
    box(f"Waste bin {i+1} | hinge L", (x - 0.24, BIN_Y - 0.27, 0.915), (0.05, 0.015, 0.045), M["metal"], C_SITE, 0.004)
    box(f"Waste bin {i+1} | hinge R", (x + 0.24, BIN_Y - 0.27, 0.915), (0.05, 0.015, 0.045), M["metal"], C_SITE, 0.004)
# Right-side glazing (three bays) meets the solid rear wall with a pier.
right_glass_ys = [Y0, -3.35, -1.95, -0.55, 0.78]
for i in range(len(right_glass_ys) - 1):
    a, b = right_glass_ys[i], right_glass_ys[i + 1]
    width = b - a - 0.04
    cy = (a + b) / 2
    box(f"Side glass | pane {i+1}", (X1 - 0.11, cy, (KNEE + PANEL_TOP) / 2),
        (0.018, width, PANEL_TOP - KNEE), M["glass"], C_ARCH)
box("Side glass | knee wall", (X1 - 0.12, (-4.9 + 0.78) / 2, KNEE / 2),
    (T, 5.68, KNEE), M["trim"], C_ARCH, 0.01)
box("Side glass | header", (X1 - 0.12, (-4.9 + 0.78) / 2, (HEAD + H) / 2),
    (T, 5.68, H - HEAD), M["trim"], C_ARCH, 0.01)
box("Side glass | front corner pier", (X1 - 0.12, Y0 + 0.06, H / 2),
    (T, 0.12, H), M["trim"], C_ARCH, 0.008)
box("Side glass | rear pier", (X1 - 0.12, 0.78, H / 2),
    (T, 0.16, H), M["trim"], C_ARCH, 0.008)
for cy in (-3.35, -1.95, -0.55):
    box(f"Side glass | mullion {cy:.2f}", (X1 - 0.12, cy, (KNEE + PANEL_TOP) / 2),
        (0.17, 0.085, PANEL_TOP - KNEE), M["trim"], C_ARCH, 0.006)
box("Side glass | sill", (X1 - 0.12, (-4.9 + 0.78) / 2, KNEE + 0.025),
    (0.17, 5.68, 0.09), M["trim"], C_ARCH, 0.005)
box("Side glass | head rail", (X1 - 0.12, (-4.9 + 0.78) / 2, PANEL_TOP - 0.04),
    (0.17, 5.68, 0.09), M["trim"], C_ARCH, 0.005)
box("Side glass | purple band", (X1 - 0.135, (-4.9 + 0.78) / 2, 1.24),
    (0.005, 5.66, 0.25), M["purple"], C_ARCH)

# Window graphics: three bold vinyl promotion panels. Text is duplicated on
# the inside face so the graphics read correctly from both sides of the glass.
for i, (x, z, sx, sz, mat, label, sub) in enumerate((
    (-6.10, 2.24, 0.82, 1.02, M["orange"], "SALE", "TODAY"),
    (3.10, 2.29, 0.98, 0.96, M["red"], "NEW", "OPEN"),
    (5.86, 2.12, 0.58, 0.82, M["green"], "COLD", "DRINKS"),
)):
    y = FY - 0.075
    box(f"Window poster {i+1}", (x, y, z), (sx, 0.012, sz), mat, C_SIGN, 0.004)
    cyl(f"Window poster {i+1} dot", (x, y - 0.009, z + 0.29), 0.16, 0.006,
        M["white_sign"], C_SIGN, segments=28, rot=(math.radians(90), 0, 0))
    text(f"Window poster {i+1} front", label, (x, y - 0.014, z - 0.14), 0.22,
         M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.002)
    text(f"Window poster {i+1} front sub", sub, (x, y - 0.014, z - 0.38), 0.08,
         M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.001)
    text(f"Window poster {i+1} back", label, (x, FY - 0.056, z - 0.14), 0.22,
         M["white_sign"], C_SIGN, rot=(math.pi / 2, 0, math.pi), font=FONT_LATIN, extrude=0.002)
    text(f"Window poster {i+1} back sub", sub, (x, FY - 0.056, z - 0.38), 0.08,
         M["white_sign"], C_SIGN, rot=(math.pi / 2, 0, math.pi), font=FONT_LATIN, extrude=0.001)

# ----------------------------------------------------------------------------
# Facade sign: wrapped purple light box with dimensional lettering
# ----------------------------------------------------------------------------
SIGN_Y = FY - 0.20
SIGN_Z = H + 0.48
box("Sign | continuous carcass", (0, SIGN_Y, SIGN_Z), (W + 0.24, 0.36, 0.94), M["metal_dark"], C_SIGN, 0.025)
box("Sign | front purple face", (0, SIGN_Y - 0.195, SIGN_Z), (W + 0.18, 0.035, 0.68),
    M["purple_glow"], C_SIGN, 0.012)
box("Sign | front upper pink rail", (0, SIGN_Y - 0.215, SIGN_Z + 0.38), (W + 0.18, 0.035, 0.055),
    M["pink_glow"], C_SIGN, 0.008)
box("Sign | front lower pink rail", (0, SIGN_Y - 0.215, SIGN_Z - 0.38), (W + 0.18, 0.035, 0.055),
    M["pink_glow"], C_SIGN, 0.008)
for i, x in enumerate((-6.9, -5.0, -2.9, 0.95, 3.3, 5.6)):
    box(f"Sign | seam {i+1}", (x, SIGN_Y - 0.216, SIGN_Z), (0.018, 0.02, 0.64),
        M["pink_glow"], C_SIGN, 0.003)
# Purple side return.
box("Sign | right side carcass", (X1 + 0.13, -0.1, SIGN_Z), (0.36, D + 0.2, 0.94),
    M["metal_dark"], C_SIGN, 0.025)
box("Sign | right side purple face", (X1 + 0.31, -0.1, SIGN_Z), (0.035, D + 0.16, 0.68),
    M["purple_glow"], C_SIGN, 0.012)
box("Sign | right upper strip", (X1 + 0.33, -0.1, SIGN_Z + 0.38), (0.035, D + 0.16, 0.055),
    M["pink_glow"], C_SIGN, 0.008)
box("Sign | right lower strip", (X1 + 0.33, -0.1, SIGN_Z - 0.38), (0.035, D + 0.16, 0.055),
    M["pink_glow"], C_SIGN, 0.008)
# Warm ivory letters are separate meshes for crisp edges and clean emission.
text("Sign | Japanese name", "ポプリ", (-1.55, SIGN_Y - 0.245, SIGN_Z + 0.005), 0.78,
     M["sign_letter"], C_SIGN, font=FONT_JP, extrude=0.022)
text("Sign | Chinese name", "波普利", (1.75, SIGN_Y - 0.245, SIGN_Z - 0.005), 0.44,
     M["sign_letter"], C_SIGN, font=FONT_JP, extrude=0.018)
# Small English sub-line.
text("Sign | romaji", "P O P U R I", (-1.55, SIGN_Y - 0.248, SIGN_Z - 0.36), 0.08,
     M["sign_letter"], C_SIGN, font=FONT_LATIN, extrude=0.004)
# Purple side lettering "24".
text("Sign | side 24", "24", (X1 + 0.335, -1.90, SIGN_Z - 0.01), 0.32,
     M["sign_letter"], C_SIGN, rot=(math.pi / 2, 0, math.pi / 2), font=FONT_LATIN, extrude=0.012)

# Red New Open banner beneath the main sign.
BANNER_Y = FY - 0.13
box("Banner | red field", (-0.70, BANNER_Y, 2.88), (8.25, 0.035, 0.55), M["banner"], C_SIGN, 0.012)
box("Banner | top trim", (-0.70, BANNER_Y - 0.02, 3.16), (8.25, 0.02, 0.03), M["banner_cream"], C_SIGN, 0.003)
box("Banner | bottom trim", (-0.70, BANNER_Y - 0.02, 2.60), (8.25, 0.02, 0.03), M["banner_cream"], C_SIGN, 0.003)
text("Banner | New Open", "New Open", (-0.72, BANNER_Y - 0.035, 2.88), 0.40,
     M["banner_cream"], C_SIGN, font=FONT_SCRIPT, extrude=0.008, shear=0.16)
# Party balloons and simple strings printed on the banner.
for i, (x, z, col, r) in enumerate((
    (-4.25, 2.94, M["ice_blue"], 0.105), (-3.82, 3.03, M["orange"], 0.075),
    (2.58, 3.00, M["pink_glow"], 0.09), (2.98, 2.85, M["green"], 0.075),
    (3.36, 2.98, M["ice_blue"], 0.065),
)):
    sphere(f"Banner balloon {i+1}", (x, BANNER_Y - 0.045, z), r, col, C_SIGN,
           scale=(1, 0.18, 1.15), subdiv=2)
    curve_tube(f"Banner balloon {i+1} string",
               [(x, BANNER_Y - 0.048, z - r * 1.1), (x + 0.015, BANNER_Y - 0.048, z - 0.38)],
               0.0018, M["banner_cream"], C_SIGN)

# Vertical OPEN board next to the entrance.
box("OPEN board | white", (4.55, FY - 0.16, 2.18), (0.62, 0.055, 1.75), M["white_sign"], C_SIGN, 0.018)
box("OPEN board | red inset", (4.55, FY - 0.193, 2.18), (0.5, 0.012, 1.58), M["red"], C_SIGN, 0.012)
for j, letter in enumerate("OPEN"):
    text(f"OPEN letter {letter}", letter, (4.55, FY - 0.205, 2.72 - j * 0.34), 0.25,
         M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.004)

# Soffit downlights under the sign.
for i, x in enumerate((-6.2, -3.8, -1.4, 1.0, 3.4, 5.8)):
    cyl(f"Soffit downlight {i+1}", (x, FY - 0.36, HEAD + 0.26), 0.075, 0.05,
        M["metal_dark"], C_SIGN, segments=20, rot=(math.radians(90), 0, 0))
    cyl(f"Soffit downlight {i+1} lens", (x, FY - 0.39, HEAD + 0.26), 0.052, 0.012,
        M["ceiling_light"], C_SIGN, segments=20, rot=(math.radians(90), 0, 0))
    light_point(f"Soffit downlight {i+1}", (x, FY - 0.43, HEAD + 0.22), 26.0,
                (1.0, 0.78, 0.46), 0.12, C_LIGHT_NIGHT)

# ----------------------------------------------------------------------------
# Interior: checkout, back bar, gondolas, wall rack, freezer, printer
# ----------------------------------------------------------------------------
# L-shaped checkout counter, matching the floor plan.
MAIN_X = -5.65
MAIN_Y = -0.20
box("Checkout | main body", (MAIN_X, MAIN_Y, 0.48), (0.95, 5.30, 0.96), M["orange"], C_INT, 0.025)
box("Checkout | main toe kick", (MAIN_X, MAIN_Y, 0.08), (0.80, 5.30, 0.16), M["metal_dark"], C_INT, 0.01)
box("Checkout | main top", (MAIN_X, MAIN_Y, 0.995), (1.10, 5.44, 0.075), M["counter_top"], C_INT, 0.015)
box("Checkout | return body", (-6.32, -2.85, 0.48), (2.28, 1.00, 0.96), M["orange"], C_INT, 0.025)
box("Checkout | return toe kick", (-6.32, -2.85, 0.08), (2.10, 0.86, 0.16), M["metal_dark"], C_INT, 0.01)
box("Checkout | return top", (-6.32, -2.85, 0.995), (2.42, 1.13, 0.075), M["counter_top"], C_INT, 0.015)
# Beveled customer-side panels.
for i in range(5):
    y = -2.40 + i * 0.98
    box(f"Checkout | front panel {i+1}", (MAIN_X + 0.481, y, 0.54), (0.016, 0.78, 0.56),
        M["orange"], C_INT, 0.008)
for i in range(2):
    x = -7.05 + i * 0.9
    box(f"Checkout | return panel {i+1}", (x, -3.351, 0.54), (0.72, 0.016, 0.56),
        M["orange"], C_INT, 0.008)
# Countertop equipment.
box("Checkout | register base", (MAIN_X - 0.10, -1.55, 1.11), (0.42, 0.42, 0.18), M["metal_dark"], C_INT, 0.012)
box("Checkout | register neck", (MAIN_X - 0.10, -1.62, 1.28), (0.08, 0.08, 0.26), M["metal_dark"], C_INT, 0.005)
box("Checkout | register screen", (MAIN_X - 0.10, -1.68, 1.48), (0.58, 0.05, 0.38), M["black"], C_INT, 0.012,
    rot=(math.radians(-12), 0, 0))
box("Checkout | screen face", (MAIN_X - 0.10, -1.713, 1.48), (0.50, 0.01, 0.30), M["screen"], C_INT, 0.006,
    rot=(math.radians(-12), 0, 0))
box("Checkout | receipt printer", (MAIN_X + 0.18, -2.10, 1.10), (0.27, 0.32, 0.18), M["trim"], C_INT, 0.012)
box("Checkout | scanner", (MAIN_X - 0.02, -0.87, 1.045), (0.35, 0.28, 0.055), M["metal_dark"], C_INT, 0.006)
box("Checkout | scanner glass", (MAIN_X - 0.02, -0.87, 1.077), (0.27, 0.18, 0.008), M["glass_cool"], C_INT, 0.003)
box("Checkout | card terminal", (MAIN_X + 0.22, -1.14, 1.11), (0.16, 0.22, 0.13), M["black"], C_INT, 0.018,
    rot=(0, 0, math.radians(-18)))
box("Checkout | customer display", (MAIN_X + 0.43, -1.98, 1.30), (0.05, 0.30, 0.22), M["black"], C_INT, 0.01)
box("Checkout | basket", (MAIN_X - 0.02, -0.25, 1.10), (0.43, 0.33, 0.16), M["green"], C_INT, 0.02)
# Under-counter wash light.
box("Checkout | toe light", (MAIN_X + 0.50, -0.70, 0.17), (0.02, 3.9, 0.025), M["ceiling_light"], C_INT, 0.005)
# Back bar behind the checkout (against the left wall).
box("Back bar | cabinet", (X0 + 0.34, -0.60, 0.80), (0.56, 4.20, 1.60), M["wood"], C_INT, 0.018)
box("Back bar | top", (X0 + 0.36, -0.60, 1.64), (0.62, 4.30, 0.08), M["counter_top"], C_INT, 0.012)
box("Back bar | header", (X0 + 0.30, -1.55, 2.24), (0.38, 2.3, 0.38), M["red"], C_INT, 0.012)
text("Back bar | header text", "POPURI", (X0 + 0.482, -1.55, 2.24), 0.15,
     M["white_sign"], C_INT, rot=(math.pi / 2, 0, math.pi / 2), font=FONT_LATIN, extrude=0.003)
for tier in range(4):
    z = 0.94 + tier * 0.30
    box(f"Back bar | shelf {tier+1}", (X0 + 0.60, -1.55, z), (0.34, 2.0, 0.035), M["shelf"], C_INT, 0.006)
    for j in range(9):
        y = -2.42 + j * 0.215
        box(f"Back bar | pack {tier+1}-{j+1}", (X0 + 0.71, y, z + 0.12),
            (0.16, 0.13, 0.19), random.choice(PKG_SET), C_GOODS, 0.004)
        box(f"Back bar | pack label {tier+1}-{j+1}", (X0 + 0.795, y, z + 0.13),
            (0.006, 0.085, 0.045), LABEL_WHITE, C_GOODS, 0.002)
# Small LED strip under the back-bar header.
box("Back bar | light strip", (X0 + 0.49, -1.55, 2.045), (0.02, 2.15, 0.025), M["ceiling_light"], C_INT, 0.004)

# Raise the wall display and move it right in the customer-facing view.
for obj in list(C_INT.objects) + list(C_GOODS.objects):
    if obj.name.startswith(("Back bar | header", "Back bar | shelf", "Back bar | pack", "Back bar | light strip")):
        obj.location += Vector((0, 1.50, 0.30))

# ----------------------------------------------------------------------------
# Checkout machines: hot-food roller grill, coffee station and snack warmer
# ----------------------------------------------------------------------------
M_SAUSAGE = material("Food | sausage", (0.46, 0.16, 0.055), 0.42)
M_BUN = material("Food | bun", (0.72, 0.50, 0.20), 0.58)
M_COFFEE = material("Coffee | dark", (0.035, 0.018, 0.010), 0.35)
M_STEEL = material("Metal | food equipment", (0.56, 0.58, 0.59), 0.22, metallic=0.85)
M_WARM = material("Light | heat lamp", (1.0, 0.40, 0.10), 0.25,
                  emission=(1.0, 0.22, 0.04), emission_strength=2.4)

HOT_BASE_Z = 1.033

# Hot snack warmer at the right end of the return counter.
WARM_X, WARM_Y = MAIN_X, 0.65
box("Snack warmer | base", (WARM_X, WARM_Y, HOT_BASE_Z + 0.08),
    (0.52, 0.50, 0.16), M_STEEL, C_INT, 0.02)
# Four thin glass panels rather than a solid glass block, so the food reads.
for s in (-1, 1):
    box(f"Snack warmer | glass side {s}", (WARM_X + s * 0.24, WARM_Y, HOT_BASE_Z + 0.34),
        (0.012, 0.46, 0.32), M["glass"], C_INT)
    box(f"Snack warmer | glass end {s}", (WARM_X, WARM_Y + s * 0.23, HOT_BASE_Z + 0.34),
        (0.48, 0.012, 0.32), M["glass"], C_INT)
box("Snack warmer | glass top", (WARM_X, WARM_Y, HOT_BASE_Z + 0.50),
    (0.50, 0.48, 0.012), M["glass"], C_INT)
box("Snack warmer | top frame", (WARM_X, WARM_Y, HOT_BASE_Z + 0.505),
    (0.52, 0.50, 0.03), M_STEEL, C_INT, 0.006)
for i in range(3):
    box(f"Snack warmer | tray {i+1}", (WARM_X, WARM_Y, HOT_BASE_Z + 0.21 + i * 0.09),
        (0.43, 0.39, 0.012), M["metal"], C_INT, 0.003)
    for j in range(3):
        sphere(f"Snack warmer | item {i+1}-{j+1}",
               (WARM_X - 0.13 + j * 0.13, WARM_Y, HOT_BASE_Z + 0.26 + i * 0.09),
               0.045, M_BUN, C_INT, scale=(1.0, 0.8, 0.65), subdiv=2)
box("Snack warmer | warm lamp", (WARM_X, WARM_Y + 0.13, HOT_BASE_Z + 0.46),
    (0.34, 0.025, 0.01), M_WARM, C_INT, 0.002)
text("Snack warmer | sign", "HOT", (WARM_X, WARM_Y - 0.255, HOT_BASE_Z + 0.07), 0.085,
     M["white_sign"], C_INT, font=FONT_LATIN, extrude=0.002)

# Coffee station at the left end of the back worktop, behind the register.
CF_X, CF_Y, CF_Z = X0 + 0.36, -1.80, 1.68
box("Coffee machine | body", (CF_X, CF_Y, CF_Z + 0.29),
    (0.52, 0.44, 0.58), M["metal_dark"], C_INT, 0.028)
box("Coffee machine | face", (CF_X + 0.266, CF_Y, CF_Z + 0.31),
    (0.015, 0.38, 0.50), M["black"], C_INT, 0.01)
box("Coffee machine | top warmer", (CF_X, CF_Y, CF_Z + 0.59),
    (0.48, 0.40, 0.035), M["metal"], C_INT, 0.008)
box("Coffee machine | screen", (CF_X + 0.278, CF_Y + 0.02, CF_Z + 0.43),
    (0.012, 0.20, 0.10), M["screen"], C_INT, 0.004)
for i, dy in enumerate((-0.11, -0.04, 0.03)):
    cyl(f"Coffee machine | button {i+1}", (CF_X + 0.278, CF_Y + dy, CF_Z + 0.31),
        0.018, 0.012, M["metal"], C_INT, segments=14, rot=(0, math.radians(90), 0))
cyl("Coffee machine | group head", (CF_X + 0.28, CF_Y - 0.03, CF_Z + 0.21),
    0.068, 0.08, M_STEEL, C_INT, segments=20, rot=(0, math.radians(90), 0))
cyl("Coffee machine | portafilter", (CF_X + 0.335, CF_Y - 0.14, CF_Z + 0.17),
    0.025, 0.20, M["metal_dark"], C_INT, segments=12, rot=(math.radians(90), 0, 0))
cyl("Coffee machine | spout L", (CF_X + 0.285, CF_Y - 0.055, CF_Z + 0.14),
    0.010, 0.07, M_STEEL, C_INT, segments=10)
cyl("Coffee machine | spout R", (CF_X + 0.285, CF_Y + 0.005, CF_Z + 0.14),
    0.010, 0.07, M_STEEL, C_INT, segments=10)
box("Coffee machine | drip tray", (CF_X + 0.28, CF_Y, CF_Z + 0.055),
    (0.10, 0.38, 0.045), M_STEEL, C_INT, 0.006)
box("Coffee machine | drip grille", (CF_X + 0.30, CF_Y, CF_Z + 0.082),
    (0.07, 0.32, 0.008), M["metal_dark"], C_INT, 0.002)
cyl("Coffee machine | steam wand", (CF_X + 0.30, CF_Y - 0.19, CF_Z + 0.20),
    0.012, 0.28, M_STEEL, C_INT, segments=10, rot=(math.radians(18), 0, 0))
# Cups, lids and a little counter menu.
for i in range(3):
    cyl(f"Coffee | cup stack {i+1}", (CF_X - 0.38, CF_Y + 0.30, CF_Z + 0.055 + i * 0.042),
        0.045, 0.040, M["white_sign"], C_INT, segments=18)
    cyl(f"Coffee | cup lid {i+1}", (CF_X - 0.38, CF_Y + 0.30, CF_Z + 0.079 + i * 0.042),
        0.050, 0.012, M["trim_dark"], C_INT, segments=18)
box("Coffee | napkin box", (CF_X - 0.40, CF_Y - 0.13, CF_Z + 0.065), (0.20, 0.15, 0.13),
    M["paper"], C_INT, 0.008)
box("Coffee | menu tent", (CF_X + 0.35, CF_Y + 0.34, CF_Z + 0.105), (0.04, 0.28, 0.21),
    M["black"], C_INT, 0.008, rot=(0, 0, math.radians(-10)))
text("Coffee | menu text", "COFFEE\n¥120", (CF_X + 0.372, CF_Y + 0.34, CF_Z + 0.11), 0.045,
     M["sign_letter"], C_INT, rot=(math.pi / 2, 0, math.pi / 2), font=FONT_LATIN,
     extrude=0.002, space=0.9)

# Cup dispenser and condiment pump bottles beside the coffee machine.
cyl("Coffee | cup dispenser", (CF_X - 0.40, CF_Y - 0.44, CF_Z + 0.17), 0.075, 0.34, M["metal"], C_INT, segments=18)
for i in range(4):
    cyl(f"Coffee | cup {i+1}", (CF_X - 0.40, CF_Y - 0.44, CF_Z + 0.05 + i * 0.03), 0.04, 0.026,
        M["white_sign"], C_INT, segments=16)
for i, dy in enumerate((-0.22, -0.13, -0.04)):
    cyl(f"Coffee | syrup {i+1}", (CF_X - 0.40, CF_Y + 0.62 + dy, CF_Z + 0.10), 0.032, 0.18,
        M_COFFEE if i == 0 else M["wood"], C_INT, segments=14)
    cyl(f"Coffee | syrup cap {i+1}", (CF_X - 0.40, CF_Y + 0.62 + dy, CF_Z + 0.205), 0.022, 0.025,
        M["metal_dark"], C_INT, segments=12)

# Face the POS toward customers down the aisle; keep all components together.
from mathutils import Matrix
pos_pivot = Vector((MAIN_X - 0.10, -1.55, 0))
turn = Matrix.Rotation(math.pi / 2, 4, 'Z')
for obj in list(C_INT.objects):
    if obj.name.startswith(("Checkout | register", "Checkout | screen face")):
        obj.location = pos_pivot + turn.to_3x3() @ (obj.location - pos_pivot)
        obj.rotation_euler = (turn.to_3x3() @ obj.rotation_euler.to_matrix()).to_euler()
# Taller red-rimmed hot-food cabinet to the right of the register.
for obj in list(C_INT.objects):
    if obj.name.startswith("Snack warmer |"):
        obj.location.z = HOT_BASE_Z + (obj.location.z - HOT_BASE_Z) * 1.75
        obj.scale.z *= 1.75
        dx, dy = obj.location.x - WARM_X, obj.location.y - WARM_Y
        obj.location.x, obj.location.y = WARM_X - dy, WARM_Y + dx
        obj.rotation_euler.z += math.pi / 2
        if obj.name.startswith(("Snack warmer | base", "Snack warmer | top frame")):
            obj.data.materials.clear(); obj.data.materials.append(M["red"])
for dz in (0.0, 0.90):
    box(f"Snack warmer | red rim {dz}", (WARM_X, WARM_Y, HOT_BASE_Z + dz),
        (0.54, 0.56, 0.065), M["red"], C_INT, 0.008)
# Brown curved hot-food showcase beside the red upright cabinet.
CASE_X, CASE_Y, CASE_Z = MAIN_X, 1.70, 1.033
M_CASE = material("Food case | brown frame", (0.40,0.21,0.12),0.8)
box("Curved food case | plinth", (CASE_X,CASE_Y,CASE_Z+0.04),
    (0.72,1.22,0.08),M_CASE,C_INT,0.008)
profile=[(0.34,0.08),(0.34,0.42),(0.32,0.55),(0.27,0.66),
         (0.18,0.74),(0.06,0.79),(-0.12,0.81),(-0.34,0.81)]
vertices=[(CASE_X+x,CASE_Y+y,CASE_Z+z) for y in (-.58,.58) for x,z in profile]
faces=[(i,i+1,i+1+len(profile),i+len(profile)) for i in range(len(profile)-1)]
mesh=bpy.data.meshes.new("Curved food case glazing")
mesh.from_pydata(vertices,[],faces);mesh.materials.append(M["glass"])
obj=bpy.data.objects.new("Curved food case | curved glazing",mesh);C_INT.objects.link(obj)
for y in (-.60,.60):
    curve_tube(f"Curved food case | arched frame {y}",
        [(CASE_X+x,CASE_Y+y,CASE_Z+z) for x,z in profile],.022,M_CASE,C_INT)
    box(f"Curved food case | glass end {y}",(CASE_X,CASE_Y+y,CASE_Z+.43),
        (.60,.009,.65),M["glass"],C_INT)
for level in range(3):
    z=CASE_Z+.16+level*.21
    box(f"Curved food case | shelf {level}",(CASE_X-.015,CASE_Y,z),
        (.59,1.13,.018),M["shelf"],C_INT)
    box(f"Curved food case | shelf rim {level}",(CASE_X+.29,CASE_Y,z),
        (.035,1.16,.045),M_CASE,C_INT)
    for j in range(5):
        sphere(f"Curved food case | snack {level}-{j}",
            (CASE_X+.05,CASE_Y-.44+j*.22,z+.055),.07,
            M_BUN if level%2==0 else M["orange"],C_INT,scale=(1,.9,.6),subdiv=2)
for y in (-.34,.32):
    curve_tube(f"Curved food case | highlight {y}",
        [(CASE_X+.347,CASE_Y+y-.1,CASE_Z+.16),
         (CASE_X+.347,CASE_Y+y+.1,CASE_Z+.43)],.012,M["white_sign"],C_INT)
# Reference POS has a pale enclosure and an unlit grey display.
M_POS=material("POS | grey display",(.18,.20,.25),.8,
    emission=(.18,.20,.25),emission_strength=.7)
for obj in C_INT.objects:
    if obj.name.startswith(("Checkout | register base","Checkout | register neck","Checkout | register screen")):
        obj.data.materials.clear();obj.data.materials.append(M["trim"])
    elif obj.name.startswith("Checkout | screen face"):
        obj.data.materials.clear();obj.data.materials.append(M_POS)
# Pale paper cups on the back worktop, as visible behind the register.
for y in (-1.9,-1.55):
    cyl(f"Back bar | cup sleeve {y}",(X0+.41,y,1.91),.055,.40,M["paper"],C_INT,segments=16)

# Left wall shelving, starting behind the checkout.
RACK_X = X0 + 0.30
RACK_Y0, RACK_Y1 = 1.90, 4.43
box("Left wall rack | base", (RACK_X + 0.21, (RACK_Y0 + RACK_Y1) / 2, 0.12),
    (0.62, RACK_Y1 - RACK_Y0, 0.24), M["shelf"], C_INT, 0.012)
box("Left wall rack | back", (RACK_X + 0.02, (RACK_Y0 + RACK_Y1) / 2, 1.16),
    (0.055, RACK_Y1 - RACK_Y0, 2.2), M["pegboard"], C_INT, 0.008)
for i, z in enumerate((0.35, 0.74, 1.13, 1.52, 1.91)):
    box(f"Left wall rack | shelf {i+1}", (RACK_X + 0.31, (RACK_Y0 + RACK_Y1) / 2, z),
        (0.54, RACK_Y1 - RACK_Y0 - 0.04, 0.06), M["shelf"], C_INT, 0.006)
    box(f"Left wall rack | price rail {i+1}", (RACK_X + 0.585, (RACK_Y0 + RACK_Y1) / 2, z + 0.02),
        (0.026, RACK_Y1 - RACK_Y0 - 0.06, 0.075), M["shelf"], C_INT, 0.003)
    for j in range(21):
        y = RACK_Y0 + 0.14 + j * (RACK_Y1 - RACK_Y0 - 0.28) / 20
        w = random.uniform(0.090, 0.180)
        h = random.uniform(0.120, 0.255)
        depth = random.uniform(0.140, 0.240)
        box(f"Wall goods {i+1}-{j+1}", (RACK_X + 0.29, y, z + 0.035 + h / 2),
            (depth, w, h), random.choice(PKG_SET), C_GOODS, 0.004)
box("Left wall rack | top cap", (RACK_X + 0.30, (RACK_Y0 + RACK_Y1) / 2, 2.20),
    (0.66, RACK_Y1 - RACK_Y0, 0.08), M["trim"], C_INT, 0.012)

# Two long double-sided gondolas on the right, positions taken from the plan.
def gondola(name, cx, cy, length=6.75, width=1.18, height=1.58):
    box(f"{name} | plinth", (cx, cy, 0.07), (length, width, 0.14), M["metal_dark"], C_INT, 0.008)
    box(f"{name} | centre spine", (cx, cy, height / 2), (length, 0.075, height), M["pegboard"], C_INT, 0.006)
    box(f"{name} | top cap", (cx, cy, height + 0.035), (length + 0.06, width, 0.07), M["trim"], C_INT, 0.012)
    for side in (-1, 1):
        for t, z in enumerate((0.25, 0.64, 1.03, 1.42)):
            shelf_y = cy + side * 0.295
            box(f"{name} | side {side} shelf {t+1}", (cx, shelf_y, z),
                (length - 0.08, 0.55, 0.045), M["shelf"], C_INT, 0.005)
            box(f"{name} | side {side} price rail {t+1}", (cx, cy + side * 0.567, z + 0.018),
                (length - 0.10, 0.026, 0.075), M["shelf"], C_INT, 0.003)
            # goods, facing outwards; dense mixed packaging
            n = 31
            for j in range(n):
                x = cx - (length - 0.45) / 2 + j * ((length - 0.45) / (n - 1))
                w = random.uniform(0.090, 0.185)
                d = random.uniform(0.110, 0.230)
                h = random.uniform(0.120, 0.270)
                yy = shelf_y + side * (0.055 + d / 2)
                if random.random() < 0.12:
                    # a slim bottle or can
                    cyl(f"{name} | can {side} {t+1}-{j+1}", (x, yy, z + 0.025 + h / 2),
                        w * 0.46, h, PKG_METAL, C_GOODS, segments=14, bevel=0.004)
                else:
                    mat = random.choice(PKG_SET)
                    box(f"{name} | goods {side} {t+1}-{j+1}", (x, yy, z + 0.025 + h / 2),
                        (w, d, h), mat, C_GOODS, 0.004,
                        rot=(0, 0, math.radians(random.uniform(-4.0, 4.0))))
    # A few small price cards on the shelf edge, not a continuous glowing bar.
    for side in (-1, 1):
        for t, z in enumerate((0.25, 0.64, 1.03, 1.42)):
            for j in range(5):
                x = cx - 2.55 + j * 1.28
                box(f"{name} | price card {side} {t+1}-{j+1}",
                    (x, cy + side * 0.572, z + 0.035), (0.19, 0.008, 0.075),
                    M["paper"], C_GOODS, 0.002)
                box(f"{name} | price dot {side} {t+1}-{j+1}",
                    (x - 0.055, cy + side * 0.578, z + 0.035), (0.035, 0.006, 0.035),
                    GOODS[(t + j) % len(GOODS)], C_GOODS, 0.001)
        # Endcap promo board, visible down the aisle.
        ex = cx - length / 2 - 0.025
        box(f"{name} | endcap {side}", (ex, cy + side * 0.24, 0.86),
            (0.04, 0.44, 0.95), M["paper"], C_INT, 0.006)
        box(f"{name} | endcap stripe {side}", (ex - 0.025, cy + side * 0.24, 1.25),
            (0.012, 0.40, 0.11), M["red"] if side < 0 else M["green"], C_INT, 0.003)
    # Product-filled endcaps at both ends; these stop the shelves reading as
    # blank white blocks from the entrance side.
    for end, sign in ((-1, -1), (1, 1)):
        ex = cx + end * (length / 2 + 0.26)
        box(f"{name} | endcap display {end} body", (ex, cy, 0.78),
            (0.48, 1.02, 1.48), M["shelf"], C_INT, 0.012)
        box(f"{name} | endcap display {end} header", (ex, cy, 1.60),
            (0.52, 1.06, 0.18), M["red"] if end < 0 else M["green"], C_INT, 0.008)
        for t, z in enumerate((0.46, 0.86, 1.26)):
            box(f"{name} | endcap display {end} shelf {t+1}", (ex, cy, z),
                (0.50, 0.96, 0.045), M["shelf"], C_INT, 0.004)
            for j in range(3):
                yy = cy - 0.31 + j * 0.31
                col = random.choice(GOODS)
                box(f"{name} | endcap goods {end} {t+1}-{j+1}",
                    (ex + sign * 0.12, yy, z + 0.16), (0.20, 0.22, 0.26),
                    random.choice(PKG_SET), C_GOODS, 0.006)
    # A row of tiny shelf talkers on the top cap.
    for j in range(7):
        x = cx - 2.85 + j * 0.95
        box(f"{name} | shelf talker {j+1}", (x, cy - 0.60, height + 0.12),
            (0.44, 0.018, 0.14), M["paper"], C_INT, 0.004)
        box(f"{name} | shelf talker stripe {j+1}", (x, cy - 0.612, height + 0.09),
            (0.36, 0.006, 0.04), GOODS[j % len(GOODS)], C_INT, 0.002)

gondola("Gondola A", 2.90, -0.95, width=1.05)
gondola("Gondola B", 2.90, 1.25, width=1.05)

# Ice-cream freezer: long low case at the front-right of the plan.
FREEZE_X0, FREEZE_X1 = 1.75, 7.20
FREEZE_Y = -3.85
FREEZE_W = 1.32
FREEZE_H = 1.07
FX = (FREEZE_X0 + FREEZE_X1) / 2
FW = FREEZE_X1 - FREEZE_X0
box("Freezer | insulated body", (FX, FREEZE_Y, 0.47), (FW, FREEZE_W, 0.86), M["trim"], C_INT, 0.03)
box("Freezer | base kick", (FX, FREEZE_Y, 0.075), (FW - 0.12, FREEZE_W - 0.14, 0.15), M["metal_dark"], C_INT, 0.012)
box("Freezer | top rim", (FX, FREEZE_Y, 0.925), (FW + 0.04, FREEZE_W + 0.04, 0.07), M["metal"], C_INT, 0.012)
box("Freezer | front rail", (FX, FREEZE_Y - FREEZE_W / 2 - 0.03, 0.91), (FW, 0.06, 0.15), M["red"], C_INT, 0.01)
# Ice-cream graphic panel breaks up the white front of the case.
box("Freezer | graphic panel", (FX + 0.9, FREEZE_Y - FREEZE_W / 2 - 0.031, 0.52),
    (2.6, 0.018, 0.48), M["ice_blue"], C_SIGN, 0.012)
box("Freezer | graphic stripe", (FX + 0.9, FREEZE_Y - FREEZE_W / 2 - 0.043, 0.70),
    (2.35, 0.01, 0.055), M["pink_glow"], C_SIGN, 0.003)
text("Freezer | graphic text", "ICE CREAM", (FX + 0.9, FREEZE_Y - FREEZE_W / 2 - 0.041, 0.48), 0.16,
     M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.003)
text("Freezer | graphic sub", "COLD & SWEET", (FX + 0.9, FREEZE_Y - FREEZE_W / 2 - 0.041, 0.33), 0.07,
     M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.002)
for i in range(3):
    sphere(f"Freezer | graphic scoop {i+1}", (FX - 0.55 + i * 0.24, FREEZE_Y - FREEZE_W / 2 - 0.05, 0.53 + (i % 2) * 0.08),
           0.085, GOODS[i * 3], C_SIGN, scale=(1, 0.18, 1), subdiv=2)
# Side graphic visible from the checkout-side camera.
box("Freezer | side panel", (FX + 1.0, FREEZE_Y + FREEZE_W / 2 + 0.025, 0.56),
    (2.6, 0.018, 0.62), M["ice_blue"], C_SIGN, 0.012)
box("Freezer | side stripe", (FX + 1.0, FREEZE_Y + FREEZE_W / 2 + 0.037, 0.82),
    (2.35, 0.008, 0.055), M["pink_glow"], C_SIGN, 0.003)
text("Freezer | side text", "ICE CREAM", (FX + 1.0, FREEZE_Y + FREEZE_W / 2 + 0.045, 0.57), 0.22,
     M["white_sign"], C_SIGN, rot=(math.pi / 2, 0, math.pi), font=FONT_LATIN, extrude=0.003)
text("Freezer | side sub", "COLD & SWEET", (FX + 1.0, FREEZE_Y + FREEZE_W / 2 + 0.045, 0.40), 0.085,
     M["white_sign"], C_SIGN, rot=(math.pi / 2, 0, math.pi), font=FONT_LATIN, extrude=0.002)
for i in range(3):
    sphere(f"Freezer | side scoop {i+1}", (FX - 0.4 + i * 0.24, FREEZE_Y + FREEZE_W / 2 + 0.05,
           0.58 + (i % 2) * 0.09), 0.085, GOODS[i * 3 + 2], C_SIGN,
           scale=(1, 0.18, 1), subdiv=2)
# Cold interior, visible through the lid.
box("Freezer | inner well", (FX, FREEZE_Y, 0.90), (FW - 0.12, FREEZE_W - 0.16, 0.03), M["cold_light"], C_INT, 0.006)
for i in range(9):
    x = FREEZE_X0 + 0.45 + i * 0.57
    tub_col = random.choice(GOODS)
    box(f"Freezer | ice cream tub {i+1}", (x, FREEZE_Y, 0.985), (0.45, 0.92, 0.055), tub_col, C_GOODS, 0.02)
    box(f"Freezer | tub lid {i+1}", (x, FREEZE_Y, 1.017), (0.43, 0.88, 0.02), M["paper"], C_GOODS, 0.008)
box("Freezer | cold LED", (FX, FREEZE_Y + FREEZE_W / 2 - 0.12, 1.03), (FW - 0.3, 0.025, 0.018),
    M["cold_light"], C_INT, 0.004)
# Three sliding glass lids; the centre one is slid left to reveal the tubs
# while the neighbouring two remain glazed.
for i, (a, b) in enumerate(((FREEZE_X0 + 0.06, FREEZE_X0 + FW / 3 + 0.02),
                            (FREEZE_X0 + FW / 3 - 0.01, FREEZE_X0 + 2 * FW / 3 + 0.02),
                            (FREEZE_X0 + 2 * FW / 3 - 0.01, FREEZE_X1 - 0.06))):
    shift = 0.0 if i != 1 else -0.75
    cx = (a + b) / 2 + shift
    w = b - a
    box(f"Freezer | lid glass {i+1}", (cx, FREEZE_Y, 1.079), (w - 0.06, FREEZE_W - 0.12, 0.013),
        M["glass_cool"], C_INT)
    for dx, dy, sx, sy in ((0, -FREEZE_W / 2 + 0.055, w, 0.06),
                           (0, FREEZE_W / 2 - 0.055, w, 0.06),
                           (-w / 2 + 0.03, 0, 0.06, FREEZE_W - 0.1),
                           (w / 2 - 0.03, 0, 0.06, FREEZE_W - 0.1)):
        box(f"Freezer | lid frame {i+1}", (cx + dx, FREEZE_Y + dy, 1.088),
            (sx, sy, 0.045), M["metal"], C_INT, 0.006)
    box(f"Freezer | lid handle {i+1}", (cx + w / 2 - 0.12, FREEZE_Y - FREEZE_W / 2 + 0.07, 1.13),
        (0.25, 0.05, 0.035), M["metal_dark"], C_INT, 0.006)
# Open section: dark gasket and two visible tubs.
box("Freezer | open gasket", (FX + 1.55, FREEZE_Y, 1.057), (0.78, 0.07, 0.035), M["rubber"], C_INT, 0.006)
light_point("Freezer | cold display light", (FX + 1.45, FREEZE_Y, 1.04), 22.0,
            (0.55, 0.82, 1.0), 0.12, C_GLOW)
for j in range(5):
    x = FX + 1.16 + j * 0.22
    box(f"Freezer | rim price tag {j+1}", (x, FREEZE_Y - FREEZE_W / 2 + 0.09, 1.105),
        (0.13, 0.012, 0.08), M["white_sign"], C_SIGN, 0.002)
text("Freezer | sign", "アイス", (FX, FREEZE_Y - FREEZE_W / 2 - 0.035, 0.70), 0.18,
     M["white_sign"], C_SIGN, font=FONT_JP, extrude=0.004)

# Printer / multi-function copier near the entrance, as in the plan.
box("Printer | cabinet", (-6.85, -4.04, 0.42), (1.10, 0.82, 0.84), M["trim"], C_INT, 0.025)
box("Printer | main body", (-6.85, -4.04, 0.95), (1.02, 0.74, 0.28), M["trim"], C_INT, 0.035)
box("Printer | scanner top", (-6.85, -4.04, 1.13), (0.96, 0.68, 0.09), M["metal_dark"], C_INT, 0.018)
box("Printer | scanner glass", (-6.85, -4.04, 1.183), (0.84, 0.55, 0.008), M["glass_cool"], C_INT, 0.004)
box("Printer | paper tray", (-6.70, -4.46, 0.53), (0.55, 0.12, 0.08), M["metal_dark"], C_INT, 0.008)
box("Printer | control arm", (-6.40, -4.34, 1.06), (0.25, 0.18, 0.08), M["metal_dark"], C_INT, 0.008)
box("Printer | control screen", (-6.31, -4.38, 1.13), (0.18, 0.035, 0.10), M["screen"], C_INT, 0.004,
    rot=(0, 0, math.radians(18)))
box("Printer | green button", (-6.32, -4.38, 1.02), (0.06, 0.03, 0.025), M["green"], C_INT, 0.008)
box("Printer | output slot", (-6.85, -4.43, 0.88), (0.55, 0.025, 0.08), M["black"], C_INT, 0.004)
# Basket stack by the door: open wire baskets, not solid blocks.
for i in range(4):
    z = 0.16 + i * 0.17
    mat = M["green"] if i % 2 == 0 else M["red"]
    box(f"Baskets | stack {i+1} bottom", (0.95, -4.24, z), (0.55, 0.44, 0.035), mat, C_INT, 0.008)
    for dy in (-0.205, 0.205):
        box(f"Baskets | stack {i+1} side Y {dy}", (0.95, -4.24 + dy, z + 0.075),
            (0.55, 0.028, 0.14), mat, C_INT, 0.004)
    for dx in (-0.26, 0.26):
        box(f"Baskets | stack {i+1} side X {dx}", (0.95 + dx, -4.24, z + 0.075),
            (0.028, 0.44, 0.14), mat, C_INT, 0.004)
    for dx in (-0.20, 0.20):
        box(f"Baskets | stack {i+1} handle {dx}", (0.95 + dx, -4.24, z + 0.17),
            (0.045, 0.44, 0.035), mat, C_INT, 0.006)
# Small standing poster by the entrance.
box("Poster stand | base", (-1.55, -3.96, 0.035), (0.62, 0.38, 0.07), M["metal_dark"], C_INT, 0.01)
box("Poster stand | board", (-1.55, -3.96, 0.78), (0.55, 0.04, 1.25), M["red"], C_INT, 0.008)
box("Poster stand | white band", (-1.55, -3.99, 1.23), (0.55, 0.012, 0.28), M["white_sign"], C_INT, 0.006)
text("Poster stand | text", "NEW\nOPEN", (-1.55, -4.005, 0.72), 0.13,
     M["white_sign"], C_INT, font=FONT_LATIN, extrude=0.002, space=0.8)
text("Poster stand | text back", "NEW\nOPEN", (-1.55, -3.916, 0.72), 0.13,
     M["white_sign"], C_INT, rot=(math.pi / 2, 0, math.pi), font=FONT_LATIN, extrude=0.002, space=0.8)
box("Poster stand | arrow", (-1.55, -3.925, 1.23), (0.26, 0.012, 0.07), M["red"], C_INT, 0.003)

# Ceiling: linear LED fixtures and frames.
for ix, x in enumerate((-4.8, 0.0, 4.8)):
    for iy, y in enumerate((-2.55, 0.25, 3.05)):
        box(f"Ceiling light | frame {ix}-{iy}", (x, y, H - 0.095), (2.70, 0.22, 0.04), M["metal"], C_INT, 0.005)
        box(f"Ceiling light | diffuser {ix}-{iy}", (x, y, H - 0.115), (2.58, 0.15, 0.025),
            M["ceiling_light"], C_INT, 0.006)
        light_area(f"Interior ceiling light {ix}-{iy}", (x, y, H - 0.16), (x, y, 0), 18.0,
                   2.35, 0.14, (1.0, 0.78, 0.56), C_GLOW, 150)
# Hanging aisle signs (double-sided).
for idx, (x, y, label, col) in enumerate(((1.15, 0.38, "おにぎり", M["orange"]),
                                          (1.15, 2.22, "飲み物", M["ice_blue"]),
                                          (-3.25, 0.35, "レジ", M["red"]))):
    box(f"Aisle sign {idx+1} | board", (x, y, 2.58), (1.55, 0.06, 0.42), M["white_sign"], C_INT, 0.012)
    box(f"Aisle sign {idx+1} | stripe", (x, y - 0.033, 2.40), (1.55, 0.008, 0.08), col, C_INT, 0.002)
    text(f"Aisle sign {idx+1} | front", label, (x, y - 0.036, 2.61), 0.16,
         M["black"], C_INT, font=FONT_JP, extrude=0.002)
    text(f"Aisle sign {idx+1} | back", label, (x, y + 0.035, 2.61), 0.16,
         M["black"], C_INT, rot=(math.pi / 2, 0, math.pi), font=FONT_JP, extrude=0.002)
    for dx in (-0.55, 0.55):
        curve_tube(f"Aisle sign {idx+1} | hanger {dx}", [(x + dx, y, 2.79), (x + dx, y, H - 0.08)],
                   0.004, M["metal"], C_INT)

# Small practical details: security camera, speakers, smoke detector.
box("Security camera | mount", (-0.15, Y0 + 0.22, H - 0.32), (0.12, 0.15, 0.12), M["metal_dark"], C_INT, 0.01)
sphere("Security camera | dome", (-0.15, Y0 + 0.25, H - 0.42), 0.12, M["glass_cool"], C_INT, scale=(1, 1, 0.7), subdiv=2)
box("Security camera | LED", (-0.15, Y0 + 0.38, H - 0.34), (0.03, 0.012, 0.02), M["red"], C_INT, 0.003)
for x in (-4.8, 0.0, 4.8):
    for y in (-2.8, 2.8):
        cyl(f"Ceiling speaker {x:.0f}-{y:.0f}", (x, y, H - 0.085), 0.14, 0.035,
            M["metal"], C_INT, segments=32)
        cyl(f"Ceiling speaker grille {x:.0f}-{y:.0f}", (x, y, H - 0.106), 0.12, 0.006,
            M["metal_dark"], C_INT, segments=32)
sphere("Smoke detector", (4.0, 0.2, H - 0.075), 0.09, M["white_sign"], C_INT, scale=(1, 1, 0.4), subdiv=2)

# Stockroom door and back-wall poster panels.
box("Back wall | stockroom door", (3.75, Y1 - 0.028, 1.12), (1.10, 0.055, 2.25), M["metal_dark"], C_INT, 0.012)
for dx in (-0.28, 0.28):
    box("Back wall | stockroom door inset", (3.75 + dx, Y1 - 0.062, 1.12), (0.38, 0.012, 1.95),
        M["trim_dark"], C_INT, 0.008)
box("Back wall | stockroom handle", (3.32, Y1 - 0.09, 1.10), (0.05, 0.08, 0.34), M["metal"], C_INT, 0.012)
text("Back wall | stockroom label", "STAFF", (3.75, Y1 - 0.07, 2.02), 0.12,
     M["white_sign"], C_INT, rot=(math.pi / 2, 0, 0), font=FONT_LATIN, extrude=0.002)

# Back-wall glass-door drink cooler: adds depth and a cool counterpoint to
# the warm interior lighting.
COOL_X, COOL_W, COOL_Y = -0.35, 3.30, Y1 - 0.34
COOL_H = 2.22
box("Drink cooler | carcass", (COOL_X, COOL_Y, COOL_H / 2), (COOL_W, 0.66, COOL_H), M["metal_dark"], C_INT, 0.02)
box("Drink cooler | illuminated back", (COOL_X, COOL_Y + 0.30, COOL_H / 2), (COOL_W - 0.18, 0.03, COOL_H - 0.24),
    M["cold_light"], C_INT, 0.006)
box("Drink cooler | base", (COOL_X, COOL_Y - 0.02, 0.12), (COOL_W, 0.70, 0.24), M["metal"], C_INT, 0.012)
box("Drink cooler | top canopy", (COOL_X, COOL_Y - 0.02, COOL_H - 0.05), (COOL_W + 0.1, 0.76, 0.12),
    M["metal"], C_INT, 0.012)
text("Drink cooler | header", "DRINKS", (COOL_X, COOL_Y - 0.405, COOL_H - 0.34), 0.14,
     M["white_sign"], C_SIGN, font=FONT_LATIN, extrude=0.002)
for door in range(3):
    dx = COOL_X - COOL_W / 2 + COOL_W / 6 + door * COOL_W / 3
    box(f"Drink cooler | door {door+1} glass", (dx, COOL_Y - 0.345, COOL_H / 2),
        (COOL_W / 3 - 0.07, 0.012, COOL_H - 0.28), M["glass_cool"], C_INT)
    box(f"Drink cooler | door {door+1} frame L", (dx - COOL_W / 6 + 0.035, COOL_Y - 0.35, COOL_H / 2),
        (0.055, 0.05, COOL_H - 0.24), M["metal"], C_INT, 0.006)
    box(f"Drink cooler | door {door+1} frame R", (dx + COOL_W / 6 - 0.035, COOL_Y - 0.35, COOL_H / 2),
        (0.055, 0.05, COOL_H - 0.24), M["metal"], C_INT, 0.006)
    box(f"Drink cooler | door {door+1} top", (dx, COOL_Y - 0.35, COOL_H - 0.15),
        (COOL_W / 3 - 0.04, 0.05, 0.06), M["metal"], C_INT, 0.006)
    box(f"Drink cooler | door {door+1} bottom", (dx, COOL_Y - 0.35, 0.21),
        (COOL_W / 3 - 0.04, 0.05, 0.06), M["metal"], C_INT, 0.006)
for tier, z in enumerate((0.56, 0.96, 1.36, 1.76)):
    box(f"Drink cooler | shelf {tier+1}", (COOL_X, COOL_Y - 0.02, z), (COOL_W - 0.16, 0.48, 0.035),
        M["glass_cool"], C_INT, 0.004)
    for j in range(12):
        x = COOL_X - COOL_W / 2 + 0.20 + j * (COOL_W - 0.4) / 11
        h = random.uniform(0.15, 0.25)
        cyl(f"Drink cooler | bottle {tier+1}-{j+1}", (x, COOL_Y - 0.04, z + 0.02 + h / 2),
            random.uniform(0.045, 0.065), h, PKG_METAL, C_GOODS, segments=12, bevel=0.005)
        cyl(f"Drink cooler | cap {tier+1}-{j+1}", (x, COOL_Y - 0.04, z + 0.025 + h + 0.02),
            0.035, 0.04, M["white_sign"], C_GOODS, segments=12)
box("Drink cooler | cold strip", (COOL_X, COOL_Y - 0.375, COOL_H - 0.11),
    (COOL_W - 0.2, 0.02, 0.025), M["cold_light"], C_INT, 0.004)
light_area("Drink cooler | glow", (COOL_X, COOL_Y - 0.5, 1.5), (COOL_X, COOL_Y - 0.1, 1.2), 35.0,
           2.8, 1.7, (0.38, 0.78, 1.0), C_GLOW, 180)

for i, x in enumerate((-5.9, -3.9, 5.7, 6.7)):
    col = GOODS[i % len(GOODS)]
    box(f"Back wall poster {i+1}", (x, Y1 - 0.06, 2.45), (1.35, 0.015, 1.35), M["paper"], C_SIGN, 0.006)
    box(f"Back wall poster {i+1} graphic", (x, Y1 - 0.072, 2.45), (1.16, 0.01, 0.78), col, C_SIGN, 0.004)
    box(f"Back wall poster {i+1} caption", (x, Y1 - 0.08, 1.92), (0.95, 0.006, 0.12), M["white_sign"], C_SIGN, 0.002)

# Right-wall posters above the rear shelving.
for i, (y, z, label, mat) in enumerate(((2.3, 2.55, "COFFEE", M["orange"]),
                                        (3.8, 2.55, "SWEETS", M["red"]))):
    box(f"Right wall poster {i+1}", (X1 - 0.045, y, z), (0.02, 1.15, 1.15), M["paper"], C_SIGN, 0.008)
    box(f"Right wall poster {i+1} graphic", (X1 - 0.058, y, z + 0.12), (0.01, 1.0, 0.64), mat, C_SIGN, 0.004)
    text(f"Right wall poster {i+1} text", label, (X1 - 0.068, y, z - 0.3), 0.16,
         M["white_sign"], C_SIGN, rot=(math.pi / 2, 0, -math.pi / 2), font=FONT_LATIN, extrude=0.002)

# Wall clock and brand board above the checkout.
box("Wall clock | backing", (-4.55, Y1 - 0.055, 2.83), (0.52, 0.04, 0.52), M["metal_dark"], C_INT, 0.008)
cyl("Wall clock | face", (-4.55, Y1 - 0.085, 2.83), 0.22, 0.03, M["white_sign"], C_INT,
    segments=32, rot=(math.radians(90), 0, 0))
box("Wall clock | hand hour", (-4.55, Y1 - 0.102, 2.88), (0.02, 0.008, 0.13), M["black"], C_INT, 0.002,
    rot=(0, 0, math.radians(-28)))
box("Wall clock | hand minute", (-4.55, Y1 - 0.103, 2.83), (0.015, 0.008, 0.17), M["black"], C_INT, 0.002,
    rot=(0, 0, math.radians(48)))
box("Back wall | brand board", (-3.15, Y1 - 0.055, 2.88), (1.8, 0.03, 0.56), M["red"], C_SIGN, 0.012)
text("Back wall | brand text", "P O P U R I", (-3.15, Y1 - 0.075, 2.88), 0.22,
     M["white_sign"], C_SIGN, rot=(math.pi / 2, 0, 0), font=FONT_LATIN, extrude=0.003)

# ----------------------------------------------------------------------------
# Exterior site, parking, truck, utility pole, houses, trees, stars
# ----------------------------------------------------------------------------
box("Site | asphalt forecourt", (0, -6.6, -0.10), (46, 24, 0.18), M["asphalt"], C_SITE)
box("Site | road", (0, -22.8, -0.12), (70, 7.5, 0.20), M["asphalt"], C_SITE)
box("Site | sidewalk", (0, -18.75, 0.01), (46, 1.9, 0.24), M["concrete"], C_SITE, 0.02)
box("Site | store apron", (0, -5.75, -0.06), (25, 2.5, 0.20), M["concrete"], C_SITE, 0.015)
box("Site | curb", (0, -19.72, 0.02), (46, 0.22, 0.24), M["kerb"], C_SITE, 0.01)
box("Site | grass verge", (0, 8.6, -0.11), (55, 9, 0.19), M["grass"], C_SITE)
box("Site | grass right", (18, -1, -0.11), (14, 28, 0.19), M["grass"], C_SITE)
box("Road | near edge", (0, -19.2, -0.005), (66, 0.12, 0.02), M["paint"], C_SITE)
box("Road | far edge", (0,-26.3,-0.005),(66,0.10,0.02),M["paint"],C_SITE)
for i in range(10):
    box(f"Road | dash {i+1}", (-30 + i * 6.4, -23.0, -0.004), (2.0, 0.12, 0.02), M["paint"], C_SITE)

# Low neighbourhood across the road: the view through the storefront glass
# needs a readable horizon, especially in the daytime interior shot.
for i, (x, w, h, dep) in enumerate(((-23.0, 5.5, 3.2, 4.0), (-16.5, 5.0, 4.0, 3.6),
                                    (-10.2, 4.2, 2.8, 3.5), (12.4, 4.8, 3.8, 3.8),
                                    (18.2, 4.0, 2.9, 3.4), (24.0, 5.6, 4.2, 4.2))):
    box(f"Across road building {i+1}", (x, -36.5, h / 2 - 0.1), (w, dep, h), M["house"], C_SITE, 0.02)
    box(f"Across road building {i+1} roof", (x, -36.5, h + 0.08), (w + 0.3, dep + 0.3, 0.2), M["roof"], C_SITE, 0.01)
    for j in range(3):
        box(f"Across road building {i+1} window {j+1}", (x - w / 2 + 0.9 + j * (w - 1.6) / 2,
                                                          -36.5 + dep / 2 + 0.012, h * 0.58),
            (0.55, 0.02, 0.55), M["glass_cool"], C_SITE, 0.004)
for i, (x, r, h) in enumerate(((-27.5, 1.8, 4.2), (-20.0, 2.1, 5.0), (-5.5, 1.7, 4.0),
                                (7.8, 2.2, 5.2), (25.8, 1.9, 4.5))):
    cyl(f"Across road tree {i+1} trunk", (x, -29.0, h / 2), 0.12, h, M["roof"], C_SITE, segments=10)
    sphere(f"Across road tree {i+1} crown", (x, -29.0, h + 0.3), r, M["tree"], C_SITE,
           scale=(1, 0.9, 1.2), subdiv=2)
# A dense tree line closes the horizon seen through the shop windows.
for i in range(17):
    x = -32 + i * 4.0
    h = random.uniform(3.2, 5.6)
    sphere(f"Horizon tree {i+1}", (x, -27.2, h * 0.62), random.uniform(1.4, 2.1),
           M["tree"], C_SITE, scale=(1.0, 0.75, 1.3), subdiv=2)
    cyl(f"Horizon tree {i+1} trunk", (x, -27.2, h / 2), 0.09, h, M["roof"], C_SITE, segments=8)
for i, x in enumerate((-30.0, -7.0, 7.0, 30.0)):
    box(f"Road lamp {i+1} pole", (x, -25.9, 2.5), (0.08, 0.08, 5.0), M["metal_dark"], C_SITE, 0.01)
    box(f"Road lamp {i+1} arm", (x + 0.5, -25.9, 4.95), (1.1, 0.07, 0.07), M["metal_dark"], C_SITE, 0.006)
    box(f"Road lamp {i+1} head", (x + 0.95, -25.9, 4.86), (0.34, 0.18, 0.12), M["ceiling_light"], C_SITE, 0.012)
# Parking spaces directly in front of the shop: five numbered bays with
# wheel stops, sized for a compact Japanese convenience-store forecourt.
BAY_L, BAY_R = -6.50, 6.50
BAY_Y0, BAY_Y1 = -7.05, -12.10
BAY_W = (BAY_R - BAY_L) / 5
for i in range(6):
    x = BAY_L + i * BAY_W
    box(f"Parking line {i+1}", (x, (BAY_Y0 + BAY_Y1) / 2, 0.007),
        (0.12, BAY_Y1 - BAY_Y0, 0.024), M["paint"], C_SITE)
for i in range(5):
    cx = BAY_L + (i + 0.5) * BAY_W
    # Wheel stop at the head of each bay, nearest the store (cars nose in).
    box(f"Wheel stop {i+1}", (cx, BAY_Y0 - 0.22, 0.10),
        (1.75, 0.24, 0.20), M["concrete"], C_SITE, 0.03)
    box(f"Wheel stop {i+1} stripe", (cx, BAY_Y0 - 0.22, 0.205),
        (1.38, 0.16, 0.015), M["paint"], C_SITE, 0.002)
    text(f"Parking number {i+1}", str(i + 1), (cx, BAY_Y0 - 1.0, 0.009), 0.28,
         M["paint"], C_SITE, rot=(0, 0, 0), font=FONT_LATIN, extrude=0.001)
box("Parking | stop line", (0, BAY_Y1, 0.007), (BAY_R - BAY_L + 0.12, 0.12, 0.024), M["paint"], C_SITE)
box("Parking | front boundary", (0, BAY_Y0 - 0.06, 0.007),
    (BAY_R - BAY_L + 0.12, 0.12, 0.024), M["paint"], C_SITE)
# Drive-lane arrow, outside the stalls.
box("Parking | arrow", (-9.8, -13.55, 0.006), (2.0, 0.18, 0.022), M["paint"], C_SITE,
    rot=(0, 0, math.radians(-28)))
box("Parking | arrow head 1", (-10.45, -13.88, 0.006), (0.9, 0.18, 0.022), M["paint"], C_SITE,
    rot=(0, 0, math.radians(32)))
box("Parking | arrow head 2", (-9.15, -13.88, 0.006), (0.9, 0.18, 0.022), M["paint"], C_SITE,
    rot=(0, 0, math.radians(-88)))

# Fence and hedge along the right boundary.
for i, y in enumerate((-21.4, -18.1, -14.8, -11.5, -8.2, -4.9, -1.6, 1.7, 5.0)):
    box(f"Fence | post {i+1}", (10.9, y, 1.05), (0.09, 0.09, 2.1), M["metal_dark"], C_SITE, 0.012)
for i, z in enumerate((0.40, 1.16, 1.92)):
    box(f"Fence | rail {i+1}", (10.9, -8.2, z), (0.06, 26.4, 0.06), M["metal_dark"], C_SITE, 0.006)
for i in range(29):
    y = -21.4 + i * 0.93
    sphere(f"Hedge {i+1}", (11.55, y, 0.72), 0.58, M["hedge"], C_SITE,
           scale=(1.0, 0.78, 0.86), subdiv=1)

# Utility pole with cross arms and wires.
box("Utility pole | trunk", (11.80, -7.2, 4.45), (0.20, 0.20, 8.9), M["concrete"], C_SITE, 0.025)
box("Utility pole | cross arm", (11.80, -7.2, 7.8), (2.2, 0.12, 0.12), M["metal_dark"], C_SITE, 0.012)
for i, x in enumerate((11.03, 11.35, 11.80, 12.25, 12.57)):
    cyl(f"Utility pole | insulator {i+1}", (x, -7.2, 7.89), 0.055, 0.12, M["trim"], C_SITE, segments=16)
box("Utility pole | transformer", (11.80, -7.2, 6.75), (0.58, 0.42, 0.78), M["metal_dark"], C_SITE, 0.04)
for i in range(3):
    curve_tube(f"Overhead wire {i+1}", [(11.80, -7.2, 7.9), (2.0, -8.0, 6.5), (-8.0, -8.8, 6.1)],
               0.018, M["metal_dark"], C_SITE)
# Street lamp by the fence.
box("Street lamp | pole", (12.90, -6.0, 3.4), (0.14, 0.14, 6.8), M["metal_dark"], C_SITE, 0.015)
box("Street lamp | arm", (12.35, -6.0, 6.65), (1.15, 0.10, 0.10), M["metal_dark"], C_SITE, 0.01)
box("Street lamp | head", (11.77, -6.0, 6.55), (0.52, 0.28, 0.14), M["metal_dark"], C_SITE, 0.02)
box("Street lamp | lens", (11.77, -6.0, 6.47), (0.40, 0.19, 0.012), M["ceiling_light"], C_SITE, 0.006)
light_point("Street lamp | light", (11.77, -6.0, 6.32), 420.0, (1.0, 0.72, 0.38), 0.22, C_LIGHT_NIGHT)
light_area("Street lamp | pool", (11.77, -6.0, 6.25), (11.77, -6.0, 0), 190.0, 3.4, 2.4,
           (1.0, 0.69, 0.36), C_LIGHT_NIGHT, 160)
# Facade sign wash.
light_area("Sign | magenta wash front", (0, -8.1, 4.25), (0, -5.0, 3.4), 22.0, 12.0, 1.8,
           (0.72, 0.06, 1.0), C_LIGHT_NIGHT, 140)
light_area("Sign | magenta wash right", (9.8, -2.0, 4.0), (7.7, -2.0, 3.5), 12.0, 5.0, 1.4,
           (0.72, 0.06, 1.0), C_LIGHT_NIGHT, 140)
light_area("Facade | white wash", (0, -8.8, 2.4), (0, -5.1, 1.7), 110.0, 13.0, 2.0,
           (0.66, 0.78, 1.0), C_LIGHT_NIGHT, 150)
light_area("Canopy | apron pool", (0, -7.4, 3.1), (0, -7.4, 0.0), 240.0, 11.0, 2.2,
           (1.0, 0.72, 0.40), C_LIGHT_NIGHT, 165)
light_area("Night | lot fill", (0, -12.0, 8.0), (0, -11.0, 0.0), 110.0, 22.0, 14.0,
           (0.47, 0.60, 0.92), C_LIGHT_NIGHT, 170)

# Low-poly neighbouring houses and trees, mainly seen as silhouettes.
houses = [
    ((-17.8, 10.0), (6.2, 5.4, 6.2), 0.0),
    ((-9.7, 10.5), (6.5, 5.2, 6.0), 0.0),
    ((-1.3, 10.8), (6.0, 5.4, 6.5), 0.0),
    ((7.0, 10.8), (6.0, 5.1, 6.1), 0.0),
    ((-25.0, -1.0), (5.0, 6.0, 6.2), 0.0),
    ((-25.0, -10.0), (5.0, 6.0, 5.8), 0.0),
]
for i, ((hx, hy), (sx, sy, sz), rot) in enumerate(houses):
    box(f"House {i+1} | body", (hx, hy, sz / 2 - 0.05), (sx, sy, sz), M["house"], C_SITE, 0.02, rot=(0, 0, rot))
    box(f"House {i+1} | flat roof", (hx,hy,sz+0.08),
        (sx+0.3,sy+0.3,0.22),M["roof"],C_SITE,0.01)
    for j, (wx, wz) in enumerate(((-sx * 0.24, sz * 0.58), (sx * 0.20, sz * 0.55))):
        box(f"House {i+1} | window {j+1}", (hx + wx, hy - sy / 2 - 0.012, wz),
            (0.72, 0.025, 0.82), M["warm_window"], C_SITE, 0.005)
    box(f"House {i+1} | door", (hx, hy - sy / 2 - 0.014, 0.95), (0.8, 0.03, 1.8), M["black"], C_SITE, 0.01)
for i, (x, y, r, h) in enumerate(((-18, 0.5, 2.5, 5.0), (-12.2, 2.4, 2.0, 4.2), (-6.5, 7.0, 2.7, 5.8),
                                   (6.3, 7.8, 2.2, 4.9), (13.8, 1.0, 2.8, 5.7), (18.5, 4.0, 2.4, 5.5))):
    cyl(f"Tree {i+1} | trunk", (x, y, h / 2), 0.16, h, M["roof"], C_SITE, segments=10)
    for k in range(3):
        sphere(f"Tree {i+1} | crown {k+1}", (x + (k - 1) * 0.55, y + (k % 2) * 0.45, h + 0.14 * k),
               r * (0.78 - k * 0.12), M["tree"], C_SITE, scale=(1, 0.9, 1.25), subdiv=2)
# Small lit planter by the storefront.
for i, x in enumerate((-7.85, 7.80)):
    box(f"Planter {i+1}", (x, -5.65, 0.22), (0.9, 0.75, 0.44), M["concrete"], C_SITE, 0.03)
    sphere(f"Planter {i+1} shrub", (x, -5.65, 0.65), 0.38, M["hedge"], C_SITE, scale=(1, 1, 0.8), subdiv=2)

# Delivery truck at the left of the lot, headlamps on.
truck_x, truck_y = -12.9, -22.4
box("Truck | cargo body", (truck_x - 0.9, truck_y, 2.30), (4.8, 2.35, 2.55), M["trim"], C_SITE, 0.05)
box("Truck | cargo side panel", (truck_x - 0.9, truck_y - 1.185, 2.35), (4.4, 0.025, 2.05), M["metal"], C_SITE, 0.012)
box("Truck | side stripe", (truck_x - 0.9, truck_y - 1.201, 2.02), (4.15, 0.012, 0.12), M["purple_glow"], C_SITE, 0.004)
text("Truck | side logo", "POPURI", (truck_x - 1.1, truck_y - 1.211, 2.65), 0.34,
     M["sign_letter"], C_SITE, font=FONT_LATIN, extrude=0.003)
text("Truck | side sub", "DELIVERY SERVICE", (truck_x - 1.1, truck_y - 1.211, 2.39), 0.10,
     M["white_sign"], C_SITE, font=FONT_LATIN, extrude=0.002)
box("Truck | cab", (truck_x + 2.22, truck_y, 1.56), (1.58, 2.25, 1.72), M["trim"], C_SITE, 0.06)
box("Truck | windshield", (truck_x + 2.76, truck_y, 1.96), (0.55, 1.95, 0.62), M["glass_cool"], C_SITE, 0.03,
    rot=(0, math.radians(13), 0))
box("Truck | bumper", (truck_x + 3.02, truck_y, 0.62), (0.22, 2.30, 0.30), M["metal_dark"], C_SITE, 0.03)
for sx in (truck_x + 2.85,):
    for sy in (truck_y - 0.82, truck_y + 0.82):
        box("Truck | headlamp", (sx, sy, 1.18), (0.04, 0.22, 0.16), M["ceiling_light"], C_SITE, 0.02)
for sx in (truck_x + 1.95, truck_x - 2.75):
    for sy in (truck_y - 1.08, truck_y + 1.08):
        cyl(f"Truck | wheel {sx:.1f}-{sy:.1f}", (sx, sy, 0.45), 0.45, 0.24, M["rubber"], C_SITE,
            segments=20, rot=(math.radians(90), 0, 0))
        cyl(f"Truck | hub {sx:.1f}-{sy:.1f}", (sx, sy - 0.14 if sy < truck_y else sy + 0.14, 0.45),
            0.20, 0.02, M["metal"], C_SITE, segments=16, rot=(math.radians(90), 0, 0))
light_spot("Truck | left headlight", (truck_x + 2.98, truck_y - 0.82, 1.18),
           (truck_x + 12, truck_y - 0.6, 0.1), 250.0, 38, 0.5, (1.0, 0.82, 0.55), C_LIGHT_NIGHT, 0.08)
light_spot("Truck | right headlight", (truck_x + 2.98, truck_y + 0.82, 1.18),
           (truck_x + 12, truck_y + 0.6, 0.1), 250.0, 38, 0.5, (1.0, 0.82, 0.55), C_LIGHT_NIGHT, 0.08)
# Tail lamps.
box("Truck | tail lamp L", (truck_x - 3.32, truck_y - 0.92, 1.15), (0.03, 0.12, 0.11), M["red"], C_SITE, 0.01)
box("Truck | tail lamp R", (truck_x - 3.32, truck_y + 0.92, 1.15), (0.03, 0.12, 0.11), M["red"], C_SITE, 0.01)

# Continuous neighbourhood ground and masonry boundaries close the site.
box("Neighbourhood | ground", (0, 0, -0.25), (160, 160, 0.18), M["asphalt"], C_SITE)
box("Boundary | rear wall", (0, 7.0, 0.84), (43.0, 0.22, 1.8), M["concrete"], C_SITE)
box("Boundary | rear cap", (0, 7.0, 1.77), (43.12, 0.30, 0.12), M["trim_dark"], C_SITE)
box("Boundary | left wall", (-21.4, -3.9, 0.84), (0.24, 22.0, 1.8), M["concrete"], C_SITE)
for i in range(43):
    box(f"Boundary | vertical mortar {i}", (-21 + i, 6.883, 0.82),
        (0.012, 0.008, 1.72), M["grout"], C_SITE)
for z in (0.25, 0.65, 1.05, 1.45):
    box(f"Boundary | horizontal mortar {z}", (0, 6.88, z),
        (43, 0.008, 0.012), M["grout"], C_SITE)
# Roof panel lines are paint on an unbroken slab.
for x in (-5.0, -2.5, 0, 2.5, 5.0):
    box(f"Roof | panel line {x}", (x, 0, H + 0.241),
        (0.018, D - 0.2, 0.006), M["trim_dark"], C_ARCH)
for y in (-2.4, 0, 2.4):
    box(f"Roof | panel crossline {y}", (0, y, H + 0.242),
        (W - 0.2, 0.018, 0.006), M["trim_dark"], C_ARCH)
# A tall 24-hour roadside sign and a second utility pole frame the forecourt.
box("Road sign | pole", (-16.4, -3.1, 3.5), (0.16, 0.16, 7.0), M["metal_dark"], C_SITE)
box("Road sign | frame", (-16.4, -3.1, 6.5), (1.5, 0.22, 1.65), M["trim"], C_SITE, 0.02)
box("Road sign | purple face", (-16.4, -3.225, 6.5), (1.30, 0.02, 1.45), M["purple_glow"], C_SITE)
text("Road sign | 24", "24", (-16.4, -3.25, 6.58), 0.75, M["sign_letter"], C_SITE, font=FONT_LATIN, extrude=0)
text("Road sign | hours", "HOURS", (-16.4, -3.25, 6.02), 0.13, M["white_sign"], C_SITE, font=FONT_LATIN, extrude=0)
# Truck cabin, mirrors, wheel arches, grille and freight corrugation.
for yy in (-0.94, 0.94):
    box(f"Truck | cab side glass {yy}", (truck_x + 2.27, truck_y + yy, 2.0),
        (0.90, 0.022, 0.64), M["ice_blue"], C_SITE, 0.02)
    box(f"Truck | mirror {yy}", (truck_x + 2.9, truck_y + yy * 1.43, 1.9),
        (0.14, 0.12, 0.25), M["metal_dark"], C_SITE, 0.025)
    curve_tube(f"Truck | mirror arm {yy}", [(truck_x+2.9,truck_y+yy,1.7),
               (truck_x+3.02,truck_y+yy*1.43,1.8)],0.025,M["metal_dark"],C_SITE)
for z in (0.8, 0.9, 1.0):
    box(f"Truck | grille {z}", (truck_x + 3.021, truck_y, z),
        (0.02, 1.6, 0.035), M["black"], C_SITE)
for i in range(24):
    box(f"Truck | corrugation {i}", (truck_x - 3.02 + i * 0.18, truck_y - 1.203, 2.5),
        (0.025, 0.012, 1.55), M["trim_dark"], C_SITE)
for i, ((hx, hy), (sx, sy, sz), rot) in enumerate(houses):
    for row in (0.9, 3.1):
        for wx in (-sx*0.23, sx*0.23):
            box(f"House detail {i} | window frame {wx} {row}", (hx+wx,hy-sy/2-0.05,row),
                (0.95,0.08,0.95),M["trim_dark"],C_SITE)
            box(f"House detail {i} | lit curtain {wx} {row}", (hx+wx,hy-sy/2-0.10,row),
                (0.75,0.025,0.76),M["warm_window"] if (i+int(row))%3 else M["ice_blue"],C_SITE)
            box(f"House detail {i} | mullion {wx} {row}", (hx+wx,hy-sy/2-0.12,row),
                (0.045,0.04,0.8),M["trim_dark"],C_SITE)
            box(f"House detail {i} | sill {wx} {row}", (hx+wx,hy-sy/2-0.16,row-0.5),
                (1.12,0.28,0.11),M["concrete"],C_SITE)

# Rooftop air-conditioning units, visible in the high exterior view.
for i, (x, y, sx, sy, sz) in enumerate(((-4.1, 0.8, 1.55, 1.05, 0.72), (0.3, -0.3, 1.15, 0.85, 0.55),
                                        (4.9, 1.6, 1.35, 1.0, 0.62))):
    box(f"Rooftop AC {i+1}", (x, y, H + 0.72 + sz / 2), (sx, sy, sz), M["trim"], C_ARCH, 0.025)
    cyl(f"Rooftop AC {i+1} | fan", (x, y, H + 0.72 + sz + 0.01), 0.27, 0.035, M["metal_dark"],
        C_ARCH, segments=28)
    for dx in (-0.4, 0.4):
        box(f"Rooftop AC {i+1} | foot {dx}", (x + dx, y, H + 0.66), (0.12, 0.18, 0.12), M["metal_dark"],
            C_ARCH, 0.006)
# Roof vents.
for i, (x, y) in enumerate(((-1.9, 2.9), (6.2, -2.7), (2.8, 3.0))):
    cyl(f"Roof vent {i+1}", (x, y, H + 0.9), 0.13, 0.95, M["metal"], C_ARCH, segments=20)
    cyl(f"Roof vent {i+1} cap", (x, y, H + 1.40), 0.24, 0.05, M["metal_dark"], C_ARCH, segments=20)

# Stars: small emissive spheres far enough away to read as points.
for i in range(110):
    az = math.radians(random.uniform(-110, 100))
    el = math.radians(random.uniform(8, 72))
    r = 38.0
    x = r * math.cos(el) * math.sin(az)
    y = r * math.cos(el) * math.cos(az) - 8
    z = r * math.sin(el) + 1.5
    size = random.uniform(0.022, 0.058)
    sphere(f"Star {i+1:03d}", (x, y, z), size, M["ceiling_light"], C_STARS,
           scale=(1, 1, 1), subdiv=1)

# ----------------------------------------------------------------------------
# Lighting rigs: day and night
# ----------------------------------------------------------------------------
# Align the POS with the end of the customer aisle seen in the references.
for obj in C_INT.objects:
    if obj.name.startswith(("Checkout | register", "Checkout | screen face",
            "Checkout | receipt printer", "Checkout | scanner", "Checkout | card terminal",
            "Checkout | customer display")):
        obj.location.y += 0.05
    elif obj.name == "Checkout | basket":
        obj.location.y += 0.20

# Keep the copier clear of the full left-door sweep.
for obj in C_INT.objects:
    if obj.name.startswith("Printer |"):
        obj.location.y += 0.22

# Day - luminaire group is enabled and a sky/sun rig is added.
sun_data = bpy.data.lights.new("Sun | day", "SUN")
sun_data.energy = 7.0
sun_data.angle = math.radians(0.65)
sun_data.color = (1.0, 0.91, 0.77)
sun = bpy.data.objects.new("Sun | day", sun_data)
C_LIGHT_DAY.objects.link(sun)
sun.location = (7.0, -21.0, 8.5)
aim(sun, (-0.8, 2.0, 0.0))
light_area("Day | window fill", (0.0, -8.8, 2.7), (0.0, 0.0, 1.5), 45.0, 14.0, 3.0,
           (0.78, 0.88, 1.0), C_LIGHT_DAY, 150)
light_area("Day | checkout fill", (-4.8, 1.0, H - 0.5), (-5.2, -1.4, 0.8), 25.0, 3.0, 2.0,
           (1.0, 0.83, 0.64), C_LIGHT_DAY, 170)
light_area("Day | freezer fill", (4.3, -2.0, H - 0.45), (4.3, -3.8, 0.8), 25.0, 3.0, 1.5,
           (0.78, 0.92, 1.0), C_LIGHT_DAY, 170)

# Night - exterior practicals, interior stays lit.
# A soft cool sky key outside, plus warm interior fill.
light_area("Night | sky key", (4.0, -12.0, 13.0), (0.0, -2.0, 2.0), 110.0, 16.0, 8.0,
           (0.40, 0.55, 1.0), C_LIGHT_NIGHT, 180)
light_area("Night | interior ambient", (-1.0, 1.6, H - 0.3), (-1.0, 0.0, 0.0), 70.0, 6.0, 3.0,
           (1.0, 0.78, 0.52), C_LIGHT_NIGHT, 180)
light_area("Night | checkout practical", (-5.3, -1.2, 2.6), (-5.5, -1.6, 0.9), 42.0, 2.0, 1.4,
           (1.0, 0.77, 0.50), C_LIGHT_NIGHT, 160)
# Entrance glow.
light_area("Entrance | canopy wash", (DOOR_CENTER, FY - 0.75, HEAD + 0.16), (DOOR_CENTER, FY - 0.2, 0.0), 70.0, 2.7, 0.8,
           (1.0, 0.78, 0.47), C_LIGHT_NIGHT, 150)
# Exterior practicals at the facade.
for i, x in enumerate((-6.2, -4.6, DOOR_CENTER, -1.2, 1.4, 3.6, 5.8)):
    light_spot(f"Facade | downlight {i+1}", (x, -5.5, H + 0.72), (x, -6.7, 0.0), 65.0, 55, 0.6,
               (1.0, 0.67, 0.36), C_LIGHT_NIGHT, 0.08)
# Additional cool rim from the street side.
light_area("Night | street rim", (12.0, -9.0, 5.5), (6.0, -4.0, 2.0), 110.0, 6.0, 4.0,
           (0.44, 0.58, 1.0), C_LIGHT_NIGHT, 170)

# ----------------------------------------------------------------------------
# Worlds
# ----------------------------------------------------------------------------
def make_world(name, kind):
    w = bpy.data.worlds.new(name)
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (420, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (160, 0)
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    if kind == "day":
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.location = (-160, 40)
        sky.sky_type = "MULTIPLE_SCATTERING"
        sky.sun_elevation = math.radians(25)
        sky.sun_rotation = math.radians(125)
        sky.sun_intensity = 0.25
        sky.altitude = 120
        sky.air_density = 1.1
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.035
    else:
        bg.inputs["Color"].default_value = (0.008, 0.018, 0.052, 1.0)
        bg.inputs["Strength"].default_value = 0.55
    return w

world_day = make_world("World | day", "day")
world_night = make_world("World | night", "night")
world_night.use_fake_user = True
scene.world = world_day

# ----------------------------------------------------------------------------
# Cameras
# ----------------------------------------------------------------------------
def camera(name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36
    data.clip_start = 0.08
    data.clip_end = 160
    obj = bpy.data.objects.new(name, data)
    C_CAM.objects.link(obj)
    obj.location = loc
    aim(obj, target)
    return obj

cam_int = camera("CAM | interior hero", (-0.5, 2.0, 3.05), (-5.2, -1.9, 1.05), 23.0)
cam_ext = camera("CAM | exterior night", (18.0, -48.0, 27.0), (-3.2, -9.2, 0.8), 40.0)
cam_ext.data.type = "ORTHO"
cam_ext.data.ortho_scale = 43
cam_sign = camera("CAM | storefront detail", (10.5, -15.5, 3.0), (-0.3, -4.9, 3.3), 42.0)
cam_checkout = camera("CAM | checkout machines", (-3.20, -3.90, 1.80), (-6.70, -0.40, 1.20), 28.0)
cam_aisle = camera("CAM | aisle reference", (3.1, 0.15, 1.58), (-5.65, 0.15, 1.3), 31.0)
scene.camera = cam_int

# ----------------------------------------------------------------------------
# Render / colour setup
# ----------------------------------------------------------------------------
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.film_transparent = False
scene.render.use_file_extension = True
scene.render.fps = 24
scene.render.filepath = os.path.join(ROOT, "renders", "Popuri_Interior.png")
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scene.view_settings.exposure = -0.2

# Store useful custom props for the render helper.
scene["popuri_day_exposure"] = -0.2
scene["popuri_night_exposure"] = 0.0
scene["popuri_day_world"] = "World | day"
scene["popuri_night_world"] = "World | night"
scene["popuri_built"] = "2026-10-25"
scene["popuri_notes"] = (
    "Reference driven convenience store. Shell walls overlap at corners, "
    "interior linings are continuous, glass panes sit in continuous rebates, "
    "and all glazed openings have overlapping frames."
)

# Save with the day setup active and the hero interior camera selected.
for obj in C_LIGHT_DAY.objects:
    obj.hide_render = False
for obj in C_LIGHT_NIGHT.objects:
    obj.hide_render = True
for obj in C_STARS.objects:
    obj.hide_render = True
# The sliding-door track sits just behind the New Open banner; disabling its
# shadow keeps the lettering clean without changing the door geometry.
track = bpy.data.objects.get("Entrance | track")
if track:
    track.visible_shadow = False
scene.world = world_day
scene.camera = cam_int
scene.render.filepath = os.path.join(ROOT, "renders", "Popuri_Interior.png")
import sys
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from popuri_checkout import apply_checkout_layout
# Manual edits are the authoritative base for subsequent shelving changes.
user_base = os.path.join(ROOT, 'archive', 'user-edits-20261025-224643', 'Popuri_Store.blend')
if os.path.isfile(user_base):
    bpy.ops.wm.open_mainfile(filepath=user_base)
    scene = bpy.context.scene
    apply_checkout_layout()
else:
    apply_checkout_layout()
    from popuri_style import apply_style
    apply_style()
scene.frame_set(25)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print("POPURI_BUILD_OK", BLEND_PATH)
