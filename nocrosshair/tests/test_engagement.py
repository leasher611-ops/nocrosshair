#!/usr/bin/env python3

import math
from nocrosshair.features.engagement import EngagementEstimator


def _est(**kw):
    return EngagementEstimator(**kw)


class TestStages:

    def test_idle_when_no_input(self):
        e = _est()
        e.update(0, 0, is_shooting=False, is_aiming=False, delta_ms=16.0)
        assert e.stage == EngagementEstimator.IDLE
        assert e.confidence == 0.0

    def test_searching_when_large_input(self):
        e = _est()
        e.update(12000, 0, True, True, 16.0)
        assert e.stage == EngagementEstimator.SEARCHING

    def test_locked_when_shooting_small_input(self):
        e = _est()
        e.update(800, 0, is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert e.stage == EngagementEstimator.LOCKED
        assert e.locked is True

    def test_tracking_when_aiming_medium_input(self):
        e = _est()
        e.update(4000, 0, is_shooting=False, is_aiming=True, delta_ms=16.0)
        assert e.stage == EngagementEstimator.TRACKING

    def test_shooting_raises_confidence(self):
        aim = _est()
        shoot = _est()
        for _ in range(30):
            aim.update(800, 0, False, True, 16.0)
            shoot.update(800, 0, True, True, 16.0)
        assert shoot.confidence > aim.confidence


class TestFollowDir:

    def test_follow_dir_tracks_input_direction(self):
        e = _est()
        for _ in range(10):
            e.update(1000, 0, True, True, 16.0)  # empurra +x
        fx, fy = e.follow_dir
        assert fx > 0.5
        assert abs(fy) < 0.3

    def test_follow_dir_smoothed(self):
        e = _est(direction_alpha=0.15)
        e.update(1000, 0, True, True, 16.0)
        fx, _ = e.follow_dir
        # depois de 1 frame, a EMA ainda está bem abaixo de 1.0
        assert 0.0 < fx < 1.0

    def test_reset_clears(self):
        e = _est()
        e.update(1000, 0, True, True, 16.0)
        e.reset()
        assert e.stage == EngagementEstimator.IDLE
        assert e.confidence == 0.0
        assert e.follow_dir == (0.0, 0.0)


class TestDwell:

    def test_dwell_ramps_confidence(self):
        e = _est(dwell_ramp_ms=250.0)
        for _ in range(30):  # ~480ms de dwell
            e.update(500, 0, True, True, 16.0)
        fresh = _est(dwell_ramp_ms=250.0)
        fresh.update(500, 0, True, True, 16.0)
        assert e.confidence > fresh.confidence

    def test_confidence_bounded(self):
        e = _est()
        for _ in range(200):
            e.update(500, 0, True, True, 16.0)
        assert 0.0 <= e.confidence <= 1.0
