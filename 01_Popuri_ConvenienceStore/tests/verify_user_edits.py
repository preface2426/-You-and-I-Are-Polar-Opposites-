"""Confirm every object outside the shelving scope still matches the user's saved scene."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'archive/user-edits-20261025-224643/Popuri_Store.blend'
scope = ('Back bar |', 'Coffee machine |', 'Coffee |', 'Left wall rack |', 'Wall goods ', 'Gondola A |', 'Gondola B |')
current = {o.name: o for o in bpy.context.scene.objects}
with bpy.data.libraries.load(str(BASE), link=False) as (source, loaded):
    names = [n for n in source.objects if not n.startswith(scope) and n != 'CAM | checkout machines']
    loaded.objects = names[:]
for name, expected in zip(names, loaded.objects):
    assert name in current, ('Lost user object', name)
    actual = current[name]
    assert actual.type == expected.type, name
    for field in ('location', 'rotation_euler', 'scale'):
        assert max(abs(a-b) for a,b in zip(getattr(actual,field),getattr(expected,field))) < 1e-6, (name,field)
    assert actual.hide_render == expected.hide_render, name
    if actual.type == 'MESH':
        assert len(actual.data.vertices) == len(expected.data.vertices), name
        assert len(actual.data.polygons) == len(expected.data.polygons), name
        assert all((a.co-b.co).length < 1e-6 for a,b in zip(actual.data.vertices,expected.data.vertices)), name
    elif actual.type == 'FONT':
        assert actual.data.body == expected.data.body, name
assert not any(n in current for n in ('Entrance | interior mat','Parking | front boundary','Parking | stop line','Sign | Chinese name'))
assert 'Entrance | exterior mat.001' in current
print('USER_EDITS_PRESERVED', len(names), 'unchanged objects; manual deletions and extra mat retained')
