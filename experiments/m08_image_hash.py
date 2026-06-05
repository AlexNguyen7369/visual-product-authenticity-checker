"""M8 — Deterministic image hashing.

Goal: build the cache key. identical bytes -> identical hash; any change -> totally different hash.
Learn: a hash is a content fingerprint; why you hash the *canonical preprocessed* bytes, not raw
       frames (raw frames are never byte-identical twice -> 0% cache hits).
Maps to: capture/hash.py (Phase 1); the cache-key contract for Phase 5.

See ../src/notes/roadmap.md (M8). Tests: experiments/tests/test_m08_hash.py
"""
import hashlib

import cv2
import numpy as np


def image_hash(img: np.ndarray) -> str:
    """Return the sha256 hex digest of the image's canonical (JPEG) bytes."""
    # TODO:
    #   ok, buf = cv2.imencode('.jpg', img)
    #   return hashlib.sha256(buf.tobytes()).hexdigest()
    success, buf = cv2.imencode('.jpg', img)
    return hashlib.sha256(buf.tobytes()).hexdigest() 
    raise NotImplementedError


def main() -> None:
    from pathlib import Path

    img = cv2.imread(str(Path(__file__).resolve().parent / "assets" / "sample.jpg"))
    h1 = image_hash(img)

    changed = img.copy()
    changed[0, 0, 0] = (int(changed[0, 0, 0]) + 1) % 256   # flip one byte
    h2 = image_hash(changed)

    print("hash      :", h1)
    print("len        :", len(h1), "(expect 64 hex chars)")
    print("same twice :", h1 == image_hash(img))
    print("1px change :", h1 != h2, "(avalanche: tiny change -> different hash)")


if __name__ == "__main__":
    main()
