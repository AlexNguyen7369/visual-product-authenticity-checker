"""Tests for M8. Red until you implement m08_image_hash.py."""
import numpy as np

from m08_image_hash import image_hash


def _img():
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)


def test_deterministic():
    img = _img()
    assert image_hash(img) == image_hash(img)


def test_digest_length():
    assert len(image_hash(_img())) == 64       # sha256 -> 64 hex chars


def test_avalanche_on_one_pixel():
    img = _img()
    changed = img.copy()
    changed[0, 0, 0] = (int(changed[0, 0, 0]) + 1) % 256
    assert image_hash(img) != image_hash(changed)
