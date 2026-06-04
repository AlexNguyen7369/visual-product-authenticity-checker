"""M4 — Color spaces and channels.

Goal: see why skipping BGR->RGB makes colors wrong, and how grayscale changes the shape.
Learn: cvtColor, split/merge; grayscale collapses (H,W,3) -> (H,W); round-trip identity.
Maps to: the mandatory BGR->RGB before encoding in Step 0.3; Phase 1 preprocessing.


See ../src/notes/roadmap.md (M4).
"""
from pathlib import Path

import cv2
import numpy as np

ASSETS = Path(__file__).resolve().parent / "assets" 


def to_rgb(bgr: np.ndarray) -> np.ndarray: # input is a numpyarray in BGR format, output should be a numpy array in RGB format
    """TODO: cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)"""
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    raise NotImplementedError


def to_gray(bgr: np.ndarray) -> np.ndarray:
    """TODO: cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) — note the result is 2-D."""
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    raise NotImplementedError


def main() -> None:
    bgr = cv2.imread(str(ASSETS / "sample.jpg"))
    gray = to_gray(bgr)
    print("bgr shape :", bgr.shape, "(3-D)")
    print("gray shape:", gray.shape, "(2-D — code expecting 3 channels will break)")

    # Show the BGR-as-RGB mistake next to the correct conversion.
    cv2.imshow("wrong (BGR shown as RGB)", bgr)
    cv2.imshow("right (converted)", cv2.cvtColor(to_rgb(bgr), cv2.COLOR_RGB2BGR))
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
