"""Generate experiments/assets/sample.jpg — a stand-in "photo" for the still-image modules.

Run once:  python experiments\\assets\\make_sample.py

It draws a single bright object (a filled ellipse) on a darker gradient background, so the
contour module (M6) has one clear largest object to find, and the preprocessing module (M5)
has texture to denoise.
"""
from pathlib import Path

import cv2
import numpy as np


def make_sample(width: int = 1280, height: int = 720) -> np.ndarray:
    # Vertical gradient background (BGR), so it isn't a flat color.
    bg = np.linspace(40, 120, height, dtype=np.uint8)
    img = np.repeat(bg[:, None, None], width, axis=1)
    img = np.repeat(img, 3, axis=2)  # (H, W, 3)

    # One bright "object" roughly centered — the thing M6's contour finder should latch onto.
    center = (width // 2, height // 2)
    axes = (width // 4, height // 3)
    cv2.ellipse(img, center, axes, 0, 0, 360, color=(60, 180, 240), thickness=-1)

    # A little speckle noise so denoising in M5 has something to remove.
    noise = np.random.default_rng(0).integers(-15, 15, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return img


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample.jpg"
    cv2.imwrite(str(out), make_sample())
    print("wrote", out)
