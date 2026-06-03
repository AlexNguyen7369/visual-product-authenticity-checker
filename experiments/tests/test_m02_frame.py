"""Tests for M2. Red until you implement m02_frame_by_hand.py.

Demonstrates happy-path, edge, and the view-aliasing failure case.
"""
import cv2
import numpy as np

from m02_frame_by_hand import make_frame, swap_channels


def test_shape_and_dtype():
    frame = make_frame(4, 6)
    assert frame.shape == (4, 6, 3)
    assert frame.dtype == np.uint8


def test_nbytes_is_h_times_w_times_3():
    frame = make_frame(4, 6)
    assert frame.nbytes == 4 * 6 * 3


def test_manual_swap_matches_cv2():
    frame = make_frame()
    assert np.array_equal(swap_channels(frame), cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def test_slice_is_a_view_unless_copied():
    # Failure case made explicit: a slice aliases the parent; mutate it and the parent changes.
    frame = make_frame()
    view = frame[0:2, 0:2]
    view[0, 0] = [9, 9, 9]
    assert np.array_equal(frame[0, 0], [9, 9, 9]), "slice should be a view (aliasing)"

    safe = frame[0:2, 0:2].copy()
    safe[0, 0] = [1, 1, 1]
    assert not np.array_equal(frame[0, 0], [1, 1, 1]), ".copy() should break aliasing"
