"""M6 — Find the object (contours).

Goal: isolate the main object from the background ("crop to product").
Learn: contours are lists of boundary points; "largest area" is a cheap "main object" proxy;
       preprocessing quality (M5) determines detection quality (garbage in -> garbage out).
Maps to: crop-to-largest-contour in capture/preprocess.py.

See ../src/notes/roadmap.md (M6).
"""
import cv2
import numpy as np


def largest_bbox(binary: np.ndarray):
    """Return (x, y, w, h) of the largest contour, or None if there are no contours."""
    # TODO:
    #   contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
    #   if not contours: return None
    #   biggest = max(contours, key=cv2.contourArea)
    #   return cv2.boundingRect(biggest)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(biggest)
    raise NotImplementedError


def main() -> None:
    from pathlib import Path

    img = cv2.imread(str(Path(__file__).resolve().parent / "assets" / "sample.jpg"))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    box = largest_bbox(binary)
    print("largest object bbox (x,y,w,h):", box)
    if box:
        x, y, w, h = box
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.imshow("M6 — detected object", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
