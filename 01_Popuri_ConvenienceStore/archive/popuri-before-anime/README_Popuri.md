# Popuri convenience store

Reference-driven Blender reconstruction of the supplied convenience-store
interior, night forecourt and façade, plus an offline 3D web viewer.

## Open the interactive web viewer

Double-click:

```text
D:\Projects\Blender\Popuri_Gallery.html
```

Keep the `web/` folder next to the HTML file. The viewer is completely local:
Three.js, the scene data and the 3D model are all embedded or stored in `web/`.

Controls:

- drag to orbit, wheel to zoom, right-drag to pan
- preset buttons for overview / interior / checkout / entrance / sign / aerial
- day/night toggle
- exposure, ambient and indoor-light sliders
- hide roof / ceiling for a dollhouse view
- auto-rotate, reset view
- keyboard: `1`–`5` presets, `D` day, `N` night

## Files

- `Popuri_Gallery.html` — offline interactive 3D viewer.
- `web/` — local Three.js, compressed scene data and viewer script.
- `Popuri_Store.blend` — complete model, day/night lighting rigs, four cameras.
- `renders/Popuri_Interior.png` — daytime interior hero.
- `renders/Popuri_Checkout_Detail.png` — checkout machines close-up.
- `renders/Popuri_Exterior_Night.png` — night forecourt view.
- `renders/Popuri_Storefront_Detail.png` — glazing / sign / bins / parking detail.
- `popuri_build.py` — rebuilds the whole scene from an empty file.
- `popuri_render.py` — switches day/night lighting, camera and render settings.
- `popuri_post.py` — optional Pillow grade (bloom, contrast, vignette).
- `export_popuri_web.py` — builds the web-ready GLB (merged, web-safe materials).
- `gzip_glb.py` — compresses the GLB and prepares `web/glb-data.js`.

## Build features

- Continuous exterior wall shell with overlapping corner joints, continuous
  interior linings, baseboards and cornice. No open seams at the ceiling or floor.
- Recessed **left-side horizontal sliding glass entrance** with independent
  portal, silver door leaves, top/bottom track and a clearly open leaf. It no
  longer shares a plane with the adjacent shopfront wall.
- Storefront glazing sits in continuous sill/head rails and overlapping mullions;
  glass uses a physical Principled transmission shader with shadow-ray
  transparency so daylight enters without caustic noise.
- Checkout equipment: hot-dog roller grill with sausages and sneeze guard,
  coffee machine with group head / portafilter / steam wand / screen, hot snack
  warmer, cup dispenser and condiments.
- Three colour-coded recycling bins outside, left of the entrance.
- Five numbered parking bays directly in front of the shop, with painted lines
  and concrete wheel stops.
- Floor-plan layout: L-shaped checkout, left wall rack, two double-sided
  gondolas, ice-cream chest freezer with glazed lids, printer station, back-wall
  drink cooler and entrance.
- Night rig: star field, neighbouring silhouettes, parking lot, utility pole,
  street lamp, warm shop interior, magenta/pink sign wash and canopy spill.

## Re-render the stills

Use Blender 5.4:

```bat
blender -b Popuri_Store.blend --python popuri_render.py -- --mode day
blender -b Popuri_Store.blend --python popuri_render.py -- --mode checkout
blender -b Popuri_Store.blend --python popuri_render.py -- --mode night
blender -b Popuri_Store.blend --python popuri_render.py -- --mode sign
```

Add `--preview` for a quick 800×450 render, or override
`--width/--height/--samples/--exposure`.

The file opens in **day** mode. The render helper hides the night rig in day
mode and hides the day rig at night; both rigs and all cameras are preserved in
the .blend.

## Rebuild the web scene

After changing geometry in `popuri_build.py`:

```bat
blender -b --python popuri_build.py
blender -b Popuri_Store.blend --python export_popuri_web.py
python gzip_glb.py
```

`export_popuri_web.py` merges geometry into four groups (store / glass / roof /
stars), replaces procedural packaging materials with solid export colours, and
simplifies glass for glTF. The viewer upgrades the glass and emissive signs at
runtime.
