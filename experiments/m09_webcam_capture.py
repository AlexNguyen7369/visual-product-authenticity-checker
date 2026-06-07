"""M9 — Webcam preview + keypress capture.

Goal: the live, blocking capture loop with a clean device release.
Learn: cap.read() is blocking (loop runs at camera cadence); waitKey(1) keeps the loop live
       while polling keys; always release the device (try/finally) or the camera stays locked.
Maps to: capture/webcam.py (Phase 1); Phase 0, Step 0.2.

See ../src/notes/roadmap.md (M9). The pure key check is unit-tested in tests/ via is_space().
"""
from pathlib import Path

import cv2

ASSETS = Path(__file__).resolve().parent / "assets"
SPACE = 32


def is_space(key: int) -> bool:
    """Pure, testable: was the SPACE bar pressed? (waitKey returns -1 when no key.)"""
    return key == SPACE 


def capture_on_space():
    """Open camera 0, preview until SPACE, return the held BGR frame. Releases on any exit."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera 0 — is one connected / not in use?")
    try:
        while True:
            ok, frame = cap.read()          # blocking: parks until the next frame arrives
            if not ok:
                raise RuntimeError("Frame grab failed")
            cv2.imshow("M9 — press SPACE to capture, Q to quit", frame)
            key = cv2.waitKey(1) & 0xFF      # 1ms poll, not 0 (which would block)
            if is_space(key):
                return frame
            if key == ord("q"):
                return None
    finally:
        cap.release()                        # <- the bug to avoid: forget this, camera stays locked
        cv2.destroyAllWindows()


def main() -> None:
    frame = capture_on_space()
    if frame is not None:
        out = ASSETS / "capture.jpg"
        cv2.imwrite(str(out), frame)
        print("saved", out, frame.shape)


if __name__ == "__main__":
    main()
