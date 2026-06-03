"""Shared pytest fixtures for the sandbox.

Placing conftest.py at the experiments/ root also puts this directory on sys.path, so the
test files can `import m02_frame_by_hand` etc.
"""
import numpy as np
import pytest


@pytest.fixture
def sample_bgr() -> np.ndarray:
    """A small, deterministic (H=4, W=6, 3) uint8 BGR frame — no camera or file needed.

    Hand-set pixels make assertions easy: top-left is pure blue in BGR.
    """
    frame = np.zeros((4, 6, 3), dtype=np.uint8)
    frame[0, 0] = [255, 0, 0]   # blue in BGR
    frame[1, 1] = [0, 255, 0]   # green
    frame[2, 2] = [0, 0, 255]   # red in BGR
    return frame


class FakeClock:
    """A controllable stand-in for time.time(), so TTL tests never have to sleep()."""

    def __init__(self, start: float = 1000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
