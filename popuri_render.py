"""Render Popuri Store day/night views.

Examples:
  blender -b Popuri_Store.blend --python popuri_render.py -- --mode day --preview
  blender -b Popuri_Store.blend --python popuri_render.py -- --mode night
"""
from __future__ import annotations

import argparse
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
scene = bpy.context.scene

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=("day", "night", "sign", "checkout", "aisle"), default="day")
parser.add_argument("--preview", action="store_true")
parser.add_argument("--samples", type=int, default=0)
parser.add_argument("--width", type=int, default=0)
parser.add_argument("--height", type=int, default=0)
parser.add_argument("--exposure", type=float, default=None)
parser.add_argument("--cam", type=float, nargs=7, default=None,
                    metavar=("X", "Y", "Z", "TX", "TY", "TZ", "LENS"))
parser.add_argument("--out", default="")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

DAY = args.mode in ("day", "checkout", "aisle")
W = args.width or (800 if args.preview else 1920)
H = args.height or (450 if args.preview else 1080)
SAMPLES = args.samples or (24 if args.preview else 112)

# Render visibility -----------------------------------------------------------
for obj in bpy.data.collections["LIGHTS - day"].objects:
    obj.hide_render = not DAY
for obj in bpy.data.collections["LIGHTS - night"].objects:
    obj.hide_render = DAY
for obj in bpy.data.collections["SITE - stars"].objects:
    obj.hide_render = DAY
scene.world = bpy.data.worlds["World | day" if DAY else "World | night"]
scene.view_settings.exposure = (args.exposure if args.exposure is not None
                                else 0.0)

# Camera ----------------------------------------------------------------------
cameras = {
    "day": "CAM | interior hero",
    "night": "CAM | exterior night",
    "sign": "CAM | storefront detail",
    "checkout": "CAM | checkout machines",
    "aisle": "CAM | aisle reference",
}
scene.camera = bpy.data.objects[cameras[args.mode]]
if args.cam:
    from mathutils import Vector
    cam = scene.camera
    x, y, z, tx, ty, tz, lens = args.cam
    cam.location = (x, y, z)
    cam.rotation_euler = (Vector((tx, ty, tz)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens

# Render settings -------------------------------------------------------------
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = SAMPLES
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.film_transparent = False

name = args.out or ("Popuri_Aisle.png" if args.mode == "aisle" else ("Popuri_Interior_preview.png" if args.mode == "day" and args.preview
                    else "Popuri_Exterior_Night_preview.png" if args.mode == "night" and args.preview
                    else "Popuri_Sign_preview.png" if args.mode == "sign" and args.preview
                    else "Popuri_Checkout_preview.png" if args.mode == "checkout" and args.preview
                    else "Popuri_Interior.png" if args.mode == "day"
                    else "Popuri_Exterior_Night.png" if args.mode == "night"
                    else "Popuri_Storefront_Detail.png" if args.mode == "sign"
                    else "Popuri_Checkout_Detail.png"))
out_path = os.path.join(ROOT, "renders", name)
os.makedirs(os.path.dirname(out_path), exist_ok=True)
scene.render.filepath = out_path
scene.frame_set(25)
bpy.ops.render.render(write_still=True)
print("POPURI_RENDER_OK", out_path)
