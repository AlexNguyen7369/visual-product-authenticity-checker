"""Tests for M5. Red until you implement m05_preprocess.py."""
import numpy as np
import pytest

from m05_preprocess import resize_square, denoise, to_binary


@pytest.fixture
def noisy_bgr():
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (200, 300, 3), dtype=np.uint8)


def test_resize_is_exactly_square(noisy_bgr):
    assert resize_square(noisy_bgr, 1024).shape == (1024, 1024, 3)


def test_denoise_reduces_variance(noisy_bgr):
    # Denoising removes high-frequency content -> lower pixel variance.
    assert denoise(noisy_bgr).var() < noisy_bgr.var()


def test_threshold_is_binary(noisy_bgr):
    gray = noisy_bgr[:, :, 0]            # any single channel is a valid 2-D "gray"
    out = to_binary(gray, 127)
    assert set(np.unique(out)).issubset({0, 255})
