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
    img = cv2.imread(str(path)) # this only checks if the file exists and is a valid image format; it doesn't check if the path is a directory or if the file is corrupted, but those cases also cause imread to return None, so we can treat all of those as "bad paths" for our purposes.
    if img is None:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        elif path.is_dir():
            raise IsADirectoryError(f"Expected a file but found a directory: {path}")
        else:
            raise FileNotFoundError(f"File not found: {path}")
    return img
# how would i make it so that it isnt two if statements? i could check if the path is a directory first, and then check if the file exists and is a valid image format, but that would require two separate checks. since imread returns None for both cases, we can just check for None and raise a FileNotFoundError, which is a reasonable way to handle both cases in one check.
# what makes a path bad? non-existent, or a directory, or a non-image file. all of these cause imread to return None, which is a silent failure mode that can cause confusing downstream errors if not checked for explicitly.
# how would i check if a path is a directory or corrupted? os.path.isdir(path)



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
