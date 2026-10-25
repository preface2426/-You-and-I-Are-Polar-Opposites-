"""Shared EEVEE anime shading, used by both the saved scene and still renders."""
import bpy
import math


def apply_style():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.name.startswith('Glass |'):
            continue
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not bsdf:
            continue
        strength = bsdf.inputs.get('Emission Strength')
        if strength and strength.default_value > 0:
            continue
        base = bsdf.inputs['Base Color']
        source = base.links[0].from_socket if base.is_linked else None
        color = tuple(base.default_value)
        diffuse = nt.nodes.new('ShaderNodeBsdfDiffuse')
        diffuse.inputs['Color'].default_value = (1, 1, 1, 1)
        rgb = nt.nodes.new('ShaderNodeShaderToRGB')
        nt.links.new(diffuse.outputs[0], rgb.inputs[0])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.interpolation = 'LINEAR' if mat.name.startswith(('Site |', 'Concrete |')) else 'CONSTANT'
        stops = [(0, (0.025, 0.045, 0.09, 1)),
                 (0.035, (0.28, 0.36, 0.48, 1)),
                 (0.18, (0.68, 0.76, 0.81, 1)),
                 (0.55, (1.0, 1.0, 0.95, 1))]
        ramp.color_ramp.elements.remove(ramp.color_ramp.elements[-1])
        for i, (position, shade) in enumerate(stops):
            el = ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(position)
            el.position = position
            el.color = shade
        nt.links.new(rgb.outputs[0], ramp.inputs[0])
        multiply = nt.nodes.new('ShaderNodeMixRGB')
        multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1
        multiply.inputs[1].default_value = color
        if source:
            nt.links.new(source, multiply.inputs[1])
        nt.links.new(ramp.outputs[0], multiply.inputs[2])
        emission = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(multiply.outputs[0], emission.inputs[0])
        output = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        nt.links.new(emission.outputs[0], output.inputs['Surface'])
        mat['anime_surface'] = True

    # Flat transparent glass avoids screen-space refraction artifacts and keeps
    # shelf silhouettes visible from either side of the storefront.
    for mat in bpy.data.materials:
        if not mat.name.startswith('Glass |'):
            continue
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
        transparent.inputs[0].default_value = (0.83, 0.93, 0.91, 1)
        nt.links.new(transparent.outputs[0], out.inputs['Surface'])
        mat.surface_render_method = 'BLENDED'
        mat.use_transparent_shadow = True

    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.eevee.taa_render_samples = 64
    scene.eevee.taa_samples = 24
    scene.eevee.use_raytracing = False
    scene.world.color = (0.05, 0.08, 0.14)

    for obj in bpy.data.objects:
        if obj.name.startswith(('Rooftop AC', 'Roof vent', 'Star', 'Horizon tree', 'Across road tree')):
            obj.hide_render = True
            obj.hide_set(True)
        if obj.type == 'LIGHT':
            obj.data.use_shadow = obj.name in {'Sun | day','Night | sky key','Canopy | apron pool','Interior ceiling light 0-0','Interior ceiling light 1-1','Interior ceiling light 2-2'}
            if obj.name.startswith('Interior ceiling light'):
                obj.data.energy = 160
                obj.data.color = (0.90, 1.0, 0.86)
            elif obj.name == 'Sun | day':
                obj.data.energy = 2.2
                obj.data.angle = math.radians(1.5)
            elif obj.name == 'Night | sky key':
                obj.data.energy = 1100
                obj.data.color = (0.37, 0.53, 0.84)
            elif obj.name == 'Night | lot fill':
                obj.data.energy = 1100
            elif obj.name in ('Canopy | apron pool', 'Facade | white wash'):
                obj.data.energy *= 3
            elif obj.name == 'Night | interior ambient':
                obj.data.energy = 700
            elif obj.name.startswith('Street lamp |'):
                obj.data.color = (0.67, 0.85, 0.78)
    scene['popuri_style'] = 'EEVEE stepped anime shading / no people'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.type = 'RENDERED'
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
