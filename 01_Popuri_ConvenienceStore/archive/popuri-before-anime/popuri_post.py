"""Tasteful post grade for the Popuri store renders.

Pillow only. Adds a restrained photographic curve, highlight bloom and a soft
vignette without changing the geometry or inventing detail.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))


def bloom_layer(rgb: np.ndarray, threshold: float, radius: float, tint):
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    mask = np.clip((lum - threshold) / max(1e-5, 1.0 - threshold), 0, 1) ** 1.6
    im = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    im = im.filter(ImageFilter.GaussianBlur(radius))
    b = np.asarray(im).astype(np.float32) / 255.0
    glow = np.stack([b * tint[0], b * tint[1], b * tint[2]], axis=-1)
    return glow


def grade(src: str, dst: str, mode: str):
    img = Image.open(src).convert("RGB")
    rgb = np.asarray(img).astype(np.float32) / 255.0

    if mode == "night":
        # Deepen the night while lifting the deepest blacks just enough to keep
        # the asphalt readable.
        rgb = np.clip((rgb - 0.5) * 1.08 + 0.5, 0, 1)
        rgb = np.clip(rgb * 0.985 + 0.008, 0, 1)
        rgb = np.clip(rgb ** 0.97, 0, 1)
        glow = bloom_layer(rgb, 0.56, 22.0, (1.0, 0.58, 0.92))
        rgb = 1 - (1 - rgb) * (1 - glow * 0.36)
        rgb = np.clip(rgb, 0, 1)
        sat = 1.14
        vignette = 0.20
        sharpen = 1.1
    elif mode == "sign":
        rgb = np.clip((rgb - 0.5) * 1.05 + 0.5, 0, 1)
        glow = bloom_layer(rgb, 0.64, 16.0, (1.0, 0.62, 0.92))
        rgb = 1 - (1 - rgb) * (1 - glow * 0.28)
        rgb = np.clip(rgb, 0, 1)
        sat = 1.08
        vignette = 0.14
        sharpen = 1.05
    else:
        # Day interior: add presence and a little warmth, no neon bloom.
        rgb = np.clip((rgb - 0.5) * 1.075 + 0.5, 0, 1)
        rgb[..., 0] *= 1.018
        rgb[..., 2] *= 0.992
        glow = bloom_layer(rgb, 0.82, 14.0, (1.0, 0.86, 0.72))
        rgb = 1 - (1 - rgb) * (1 - glow * 0.12)
        rgb = np.clip(rgb, 0, 1)
        sat = 1.05
        vignette = 0.09
        sharpen = 1.03

    # Saturation and a gentle filmic S-curve.
    im = Image.fromarray((rgb * 255).astype(np.uint8))
    im = ImageEnhance.Color(im).enhance(sat)
    im = ImageEnhance.Contrast(im).enhance(1.035)
    im = ImageEnhance.Sharpness(im).enhance(sharpen)

    # Radial vignette.
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx - w / 2) / (w / 2)
    ny = (yy - h / 2) / (h / 2)
    r = np.sqrt(nx * nx + ny * ny) / 1.414
    vig = np.clip(1.0 - vignette * (r ** 2.2), 0, 1)[..., None]
    arr = np.asarray(im).astype(np.float32) * vig
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(dst)
    print("POST_OK", dst)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--mode", choices=("day", "night", "sign"), required=True)
    args = parser.parse_args()
    grade(args.src, args.dst, args.mode)
