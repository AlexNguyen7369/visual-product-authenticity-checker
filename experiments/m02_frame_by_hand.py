"""M2 — Build a frame by hand (no camera).

Goal: internalize that a frame IS an (H, W, 3) uint8 ndarray — a flat byte buffer + shape.
Learn: shape/dtype/nbytes, slicing-as-view (aliasing), BGR vs RGB, uint8 overflow.
Maps to: the data structure every later module passes around; BGR->RGB in Step 0.3.

See ../src/notes/roadmap.md (M2) for the full why, the test cases, and the debugging drill.
"""
import cv2 
import numpy as np


def make_frame(height: int = 4, width: int = 6) -> np.ndarray:
    """Return an (height, width, 3) uint8 zero frame with the top-left pixel set to blue (BGR)."""
    # TODO: np.zeros((height, width, 3), dtype=np.uint8); set frame[0, 0] = [255, 0, 0]
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[0, 0] = [255, 0, 0]
    return frame


def swap_channels(frame: np.ndarray) -> np.ndarray:
    """Convert BGR<->RGB by reversing the channel axis. Return a COPY, not a view."""
    # TODO: frame[..., ::-1].copy()  — and understand why .copy() matters here
    frame_rgb = frame[..., ::-1].copy()
    return frame_rgb
    raise NotImplementedError

def main() -> None:
    frame = make_frame()
    print("shape :", frame.shape)
    print("dtype :", frame.dtype)
    print("nbytes:", frame.nbytes, "(== H*W*3?)")

    rgb_manual = swap_channels(frame)
    rgb_cv2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    print("manual swap == cvtColor? ", np.array_equal(rgb_manual, rgb_cv2))


if __name__ == "__main__":
    main()
