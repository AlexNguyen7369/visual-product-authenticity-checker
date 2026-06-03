"""M5 — Preprocessing primitives.

Goal: build the exact ops Phase 1 chains, and feel the fidelity/aggression trade-off.
Learn: resize (note cv2 wants (width, height) — opposite of NumPy's (rows, cols)!),
       denoise reduces high-frequency detail, threshold yields a binary {0,255} image.
Maps to: capture/preprocess.py (Phase 1).

See ../src/notes/roadmap.md (M5). Tests: experiments/tests/test_m05_preprocess.py
"""
import cv2
import numpy as np


def resize_square(img: np.ndarray, size: int = 1024) -> np.ndarray:
    """Resize to exactly (size, size, 3). Watch the (width, height) argument order."""
    # TODO: cv2.resize(img, (size, size))
    raise NotImplementedError


def denoise(img: np.ndarray) -> np.ndarray:
    """TODO: cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)"""
    raise NotImplementedError


def to_binary(gray: np.ndarray, thresh: int = 127) -> np.ndarray:
    """Threshold a grayscale image to {0, 255}. TODO: cv2.threshold(...)[1]"""
    raise NotImplementedError


def main() -> None:
    from pathlib import Path

    img = cv2.imread(str(Path(__file__).resolve().parent / "assets" / "sample.jpg"))
    square = resize_square(img)
    print("resized to:", square.shape)
    print("noise variance  before:", float(img.var()))
    print("noise variance  after :", float(denoise(img).var()), "(should be lower)")


if __name__ == "__main__":
    main()
