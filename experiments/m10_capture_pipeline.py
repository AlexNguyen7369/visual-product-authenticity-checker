"""M10 — Capture -> preprocess -> save (mini Phase 1).

Goal: compose the small pieces into one pipeline where each stage's output feeds the next.
Learn: integration is where mismatched assumptions surface; save intermediate images to debug
       (you can't print an image — you look at it).
Maps to: the whole of Phase 1.

See ../src/notes/roadmap.md (M10). Reuses functions from M4/M5/M6/M8/M9.
"""
from pathlib import Path

import cv2

from m04_color_spaces import to_rgb
from m05_preprocess import resize_square, denoise
from m08_image_hash import image_hash
from m09_webcam_capture import capture_on_space

ASSETS = Path(__file__).resolve().parent / "assets"


def process(frame_bgr):
    """frame (BGR) -> RGB -> denoise -> resize 1024 -> (processed_rgb, hash)."""
    # TODO: chain to_rgb -> denoise -> resize_square, then image_hash() the result.
    raise NotImplementedError


def main() -> None:
    frame = capture_on_space()
    if frame is None:
        return
    processed, h = process(frame)
    # processed is RGB; convert back to BGR just for cv2.imwrite
    cv2.imwrite(str(ASSETS / f"{h}.jpg"), cv2.cvtColor(processed, cv2.COLOR_RGB2BGR))
    print("saved", f"{h}.jpg", "shape", processed.shape)


if __name__ == "__main__":
    main()
