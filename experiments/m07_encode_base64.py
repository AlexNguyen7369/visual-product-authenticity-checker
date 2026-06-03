"""M7 — Encode, base64, measure.

Goal: watch an in-memory image become bytes that can cross a network, and measure the cost.
Learn: raw->JPEG is ~30x smaller (lossy); JPEG->base64 is +33% (text-safe); WHY each step exists.
Maps to: the ndarray->JPEG->base64->HTTPS flow in Step 0.3; canonical bytes hashed in Phase 1.

See ../src/notes/roadmap.md (M7).
"""
import base64

import cv2
import numpy as np


def to_jpeg_bytes(img: np.ndarray) -> bytes:
    """Encode an ndarray to JPEG bytes. TODO: ok, buf = cv2.imencode('.jpg', img); return buf.tobytes()"""
    raise NotImplementedError


def to_base64(data: bytes) -> str:
    """TODO: base64.b64encode(data).decode('ascii')"""
    raise NotImplementedError


def main() -> None:
    from pathlib import Path

    img = cv2.imread(str(Path(__file__).resolve().parent / "assets" / "sample.jpg"))
    jpeg = to_jpeg_bytes(img)
    b64 = to_base64(jpeg)
    print(f"raw ndarray : {img.nbytes:>9} bytes")
    print(f"jpeg        : {len(jpeg):>9} bytes   ({img.nbytes / len(jpeg):.1f}x smaller)")
    print(f"base64      : {len(b64):>9} chars   (~{len(b64) / len(jpeg):.2f}x the jpeg)")


if __name__ == "__main__":
    main()
