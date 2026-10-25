"""Reference-based stock shelving behind and beside the checkout."""
import bpy
from mathutils import Vector


def apply_checkout_layout():
    scene = bpy.context.scene
    if scene.get('checkout_shelves_v3'):
        return
    fixtures = bpy.data.collections['INTERIOR - fixtures']
    goods = bpy.data.collections['INTERIOR - merchandise']
    mats = bpy.data.materials
    pale = mats['Shelving | off white']
    dark = mats['Trim | graphite']
    paper = mats['Paper | display']
    blue = mats['Accent | ice blue']
    palette = sorted((m for m in mats if m.name.startswith('Packaging |')), key=lambda m: m.name)
    assert palette, 'Missing merchandise palette'

    def box(name, location, size, material, collection=fixtures):
        mesh = bpy.data.meshes.new(name)
        vertices = [(x * size[0] / 2, y * size[1] / 2, z * size[2] / 2)
                    for x, y, z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
        mesh.from_pydata(vertices, [], [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)])
        obj = bpy.data.objects.new(name, mesh)
        obj.location = location
        collection.objects.link(obj)
        mesh.materials.append(material)
        return obj

    # A waist-high worktop leaves the stock rack visible above the POS.
    cabinet = bpy.data.objects['Back bar | cabinet']
    cabinet.location.z = .52
    cabinet.dimensions.z = 1.04
    top = bpy.data.objects['Back bar | top']
    top.location.z = 1.08
    for obj in list(scene.objects):
        if obj.name.startswith(('Coffee machine |', 'Coffee |', 'Back bar | cup sleeve')):
            obj.location.z -= .56
        elif obj.name.startswith(('Back bar | header', 'Back bar | shelf', 'Back bar | pack', 'Back bar | light strip')):
            bpy.data.objects.remove(obj, do_unlink=True)

    # Five tightly spaced rows, with a shallow dark frame rather than tall boxes.
    cy, width = .15, 2.30
    box('Checkout back rack | back', (-7.37, cy, 1.60), (.035, width, 1.04), dark)
    for side in (-1, 1):
        box(f'Checkout back rack | side {side}', (-7.17, cy + side * width / 2, 1.60), (.43, .035, 1.04), dark)
    for row in range(6):
        z = 1.14 + row * .18
        box(f'Checkout back rack | shelf {row}', (-7.17, cy, z), (.43, width, .025), dark)
        if row == 5:
            continue
        for col in range(16):
            y = cy - 1.065 + col * .142
            color = palette[(row * 7 + col // 2) % len(palette)]
            box(f'Checkout stock | pack {row}-{col}', (-7.065, y, z + .079), (.15, .119, .13), color, goods)
            box(f'Checkout stock | label {row}-{col}', (-6.987, y, z + .08), (.005, .10, .027), paper, goods)
    for col in range(1, 4):
        box(f'Checkout back rack | divider {col}', (-7.15, cy - width / 2 + col * width / 4, 1.60), (.40, .012, .94), dark)
    box('Checkout back rack | canopy', (-7.12, cy, 2.12), (.62, 2.47, .055), pale)
    for panel in range(2):
        y = cy - .59 + panel * 1.18
        box(f'Checkout back rack | advert frame {panel}', (-7.35, y, 2.40), (.065, 1.14, .45), pale)
        box(f'Checkout back rack | advert face {panel}', (-7.311, y, 2.40), (.009, 1.055, .37), blue if panel else paper)
        for motif in range(3):
            box(f'Checkout back rack | advert graphic {panel}-{motif}', (-7.302, y - .31 + motif * .31, 2.415), (.006, .21, .22), palette[(panel * 4 + motif * 2) % len(palette)], goods)
        box(f'Checkout back rack | advert footer {panel}', (-7.297, y, 2.257), (.006, 1.05, .055), paper if panel else mats['Accent | red'])

    # Shift the adjacent wall rack into the rear corner so it does not crowd the stock display.
    for obj in scene.objects:
        if obj.name.startswith(('Left wall rack |', 'Wall goods ')):
            obj.location.y = 3.45 + (obj.location.y - 3.165) * .70
            obj.scale.y *= .70
            obj.location.z *= .90
            obj.scale.z *= .90

    # Bring both long racks toward the checkout; keep their central aisle open.
    for obj in list(scene.objects):
        if obj.name.startswith(('Gondola A |', 'Gondola B |')):
            obj.location += Vector((-2.80, -.20 if obj.name.startswith('Gondola A') else .20, 0))
            facing = 1 if obj.name.startswith('Gondola A') else -1
            if obj.name.startswith((f'Gondola A | goods {facing} 4-', f'Gondola A | can {facing} 4-', f'Gondola B | goods {facing} 4-', f'Gondola B | can {facing} 4-')) and obj.location.x < -1.55:
                bpy.data.objects.remove(obj, do_unlink=True)
                continue
            # Counter-end displays are open shelving, with visible stock instead of solid blocks.
            if ' | endcap display -1 body' in obj.name or ' | endcap stripe ' in obj.name or obj.name in ('Gondola A | endcap -1', 'Gondola A | endcap 1', 'Gondola B | endcap -1', 'Gondola B | endcap 1'):
                bpy.data.objects.remove(obj, do_unlink=True)
            elif ' | endcap display -1 header' in obj.name:
                obj.data.materials.clear()
                obj.data.materials.append(blue)
    for name, y in [('Gondola A', -1.15), ('Gondola B', 1.45)]:
        for side in (-1, 1):
            box(f'{name} | checkout end upright {side}', (-3.535, y + side * .49, .85), (.43, .035, 1.46), pale)
        box(f'{name} | checkout end backing', (-3.31, y, .85), (.025, .96, 1.46), pale)
        # Narrow upright packs on the aisle-facing top shelf near the register.
        facing = 1 if name == 'Gondola A' else -1
        for col in range(8):
            x = -3.02 + col * .19
            box(f'{name} | checkout upright pack {col}', (x, y + facing * .39, 1.59), (.145, .16, .28), palette[(col + (4 if facing < 0 else 0)) % len(palette)], goods)
            box(f'{name} | checkout upright label {col}', (x, y + facing * .474, 1.59), (.10, .006, .09), paper, goods)

    camera = bpy.data.objects['CAM | checkout machines']
    camera.location = (-3.80, -2.85, 1.75)
    camera.rotation_euler = (Vector((-6.90, -.35, 1.40)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.lens = 24
    scene['checkout_shelves_v3'] = True
    bpy.context.view_layer.update()


if __name__ == '__main__':
    from pathlib import Path
    apply_checkout_layout()
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(__file__).resolve().parent / 'Popuri_Store.blend'))
