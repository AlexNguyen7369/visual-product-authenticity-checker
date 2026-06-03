"""M3 — Load, show, save.

Goal: the file-I/O round-trip and OpenCV's silent failure modes.
Learn: imread returns None (not an exception) on bad paths; waitKey pumps the GUI loop;
       JPEG save->load is lossy (reloaded array is NOT byte-identical).
Maps to: file I/O in every capture/save step.

See ../src/notes/roadmap.md (M3).
"""
from pathlib import Path

import cv2

ASSETS = Path(__file__).resolve().parent / "assets"


def load_image(path: Path):
    """Load an image, raising a CLEAR error if the path is bad (don't let None propagate)."""
    # TODO: img = cv2.imread(str(path)); if img is None: raise FileNotFoundError(path); return img
    raise NotImplementedError


def main() -> None:
    img = load_image(ASSETS / "sample.jpg")
    cv2.imshow("M3 — press any key to close", img)
    cv2.waitKey(0)            # <- remove this and the window hangs gray
    cv2.destroyAllWindows()

    out = ASSETS / "sample_copy.jpg"
    cv2.imwrite(str(out), img)
    reloaded = load_image(out)
    print("same shape? ", img.shape == reloaded.shape)
    print("byte-identical after JPEG round-trip? (expect False)", (img == reloaded).all())


if __name__ == "__main__":
    main()
