"""
 nocrosshair — test_aim_engines_v3.py
 ═══════════════════════════════════════════════════════════════════════════════
 TESTES PARA MOTORES DE AIM GENERACAO 3.0

 ═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from nocrosshair.features.aim_engines_v3 import (
    RotationalAAEngineV3,
    MagnetEngineV3,
    PredictEngineV3,
    MicroCorrectionEngineV3,
    AdaptiveStrengthEngineV3,
    EngagementDetectorV3,
    EngagementState,
)


class TestRotationalAAEngineV3:
    """Testes para RotationalAAEngineV3."""

    def test_initial_state(self):
        engine = RotationalAAEngineV3()
        assert engine._angle == 0.0

    def test_disabled_passthrough(self):
        engine = RotationalAAEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            state=EngagementState.LOCKED,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="zen",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_idle_passthrough(self):
        engine = RotationalAAEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.IDLE,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="zen",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_circular_orbit(self):
        engine = RotationalAAEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.LOCKED,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="circular",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_helix_orbit(self):
        engine = RotationalAAEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.TRACKING,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="helix",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_fibonacci_orbit(self):
        engine = RotationalAAEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.SEARCHING,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="fibonacci",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_state_scale_affects_amplitude(self):
        engine = RotationalAAEngineV3()
        rx_locked, _ = engine.apply(
            1000.0, 0.0,
            enabled=True,
            state=EngagementState.LOCKED,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="zen",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        engine.reset()
        rx_searching, _ = engine.apply(
            1000.0, 0.0,
            enabled=True,
            state=EngagementState.SEARCHING,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="zen",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert abs(rx_searching - 1000.0) > abs(rx_locked - 1000.0)

    def test_adapt_amplitude(self):
        engine = RotationalAAEngineV3()
        engine._hit_rate = 0.8
        engine._adapt_amplitude()
        after_high = engine._amplitude_adapt
        assert after_high < 1.0
        engine._hit_rate = 0.2
        for _ in range(50):
            engine._adapt_amplitude()
        assert engine._amplitude_adapt > after_high

    def test_reset(self):
        engine = RotationalAAEngineV3()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.LOCKED,
            zone=6000,
            speed=0.3,
            radius_mult=1.0,
            shape="zen",
            is_shooting=False,
            is_aiming=True,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._angle == 0.0
        assert engine._amplitude_adapt == 1.0


class TestMagnetEngineV3:
    """Testes para MagnetEngineV3."""

    def test_initial_state(self):
        engine = MagnetEngineV3()
        assert engine._persist_rx == 0.0

    def test_engaged_pull(self):
        engine = MagnetEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx > 1000.0 or ry > 1000.0

    def test_three_zone_pull(self):
        engine = MagnetEngineV3()
        rx_outer, _ = engine.apply(
            5000.0, 0.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        engine.reset()
        rx_inner, _ = engine.apply(
            500.0, 0.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert abs(rx_inner - 500.0) > abs(rx_outer - 5000.0)

    def test_hysteresis(self):
        engine = MagnetEngineV3()
        engine.apply(
            500.0, 0.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert engine._lock_active is True
        assert engine._hysteresis == 1.0

    def test_persistence(self):
        engine = MagnetEngineV3()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        rx, ry = engine.apply(
            0.0, 0.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=False,
            is_aiming=False,
            delta_ms=16.67,
        )
        assert rx != 0.0 or ry != 0.0

    def test_disabled_passthrough(self):
        engine = MagnetEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_reset(self):
        engine = MagnetEngineV3()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=1.0,
            magnetic_pull=5000,
            lock_fov=8000,
            lock_strength=14000,
            lock_smooth=0.25,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._persist_rx == 0.0
        assert engine._lock_active is False


class TestPredictEngineV3:
    """Testes para PredictEngineV3."""

    def test_initial_state(self):
        engine = PredictEngineV3()
        assert engine._prev_x is None

    def test_first_frame_returns_zero(self):
        engine = PredictEngineV3()
        lead_x, lead_y = engine.predict(100.0, 200.0, 16.67)
        assert lead_x == 0.0
        assert lead_y == 0.0

    def test_consistent_input_builds_lead(self):
        engine = PredictEngineV3()
        for _ in range(10):
            engine.predict(100.0, 200.0, 16.67)
        lead_x, lead_y = engine.predict(100.0, 200.0, 16.67)
        assert isinstance(lead_x, float)
        assert isinstance(lead_y, float)

    def test_moving_input_generates_lead(self):
        engine = PredictEngineV3()
        for i in range(20):
            lead_x, lead_y = engine.predict(float(i * 5000), 200.0, 16.67)
        for i in range(20):
            lead_x, lead_y = engine.predict(float(100000 + i * 5000), 200.0, 16.67)
        assert lead_x != 0.0 or lead_y != 0.0

    def test_confidence_builds(self):
        engine = PredictEngineV3()
        for _ in range(20):
            engine.predict(100.0, 200.0, 16.67)
        for i in range(10):
            engine.predict(float(i * 5000), 200.0, 16.67)
        assert engine._confidence > 0.0

    def test_jerk_estimation(self):
        engine = PredictEngineV3()
        for i in range(10):
            engine.predict(float(i * 10), 200.0, 16.67)
        for i in range(10):
            engine.predict(float(100 - i * 5), 200.0, 16.67)
        assert abs(engine._jx) > 0.0

    def test_reset(self):
        engine = PredictEngineV3()
        for _ in range(10):
            engine.predict(100.0, 200.0, 16.67)
        engine.reset()
        assert engine._prev_x is None
        assert engine._confidence == 0.0


class TestMicroCorrectionEngineV3:
    """Testes para MicroCorrectionEngineV3."""

    def test_initial_state(self):
        engine = MicroCorrectionEngineV3()
        assert engine._overshoot_count == 0

    def test_large_input_passthrough(self):
        engine = MicroCorrectionEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=1000.0,
            prev_ry=1000.0,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_axis_lock(self):
        engine = MicroCorrectionEngineV3()
        rx, ry = engine.apply(
            200.0, 10.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=200.0,
            prev_ry=10.0,
            delta_ms=16.67,
        )
        assert abs(ry) < abs(10.0)

    def test_overshoot_detection(self):
        engine = MicroCorrectionEngineV3()
        engine.apply(
            1000.0, 0.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=0.0,
            prev_ry=0.0,
            delta_ms=16.67,
        )
        engine.apply(
            600.0, 0.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=1000.0,
            prev_ry=0.0,
            delta_ms=16.67,
        )
        assert engine._overshoot_count > 0

    def test_disabled_passthrough(self):
        engine = MicroCorrectionEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            pull_strength=0.3,
            prev_rx=1000.0,
            prev_ry=1000.0,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_reset(self):
        engine = MicroCorrectionEngineV3()
        engine.apply(
            1000.0, 0.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=0.0,
            prev_ry=0.0,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._overshoot_count == 0
        assert engine._prev_magnitude == 0.0


class TestAdaptiveStrengthEngineV3:
    """Testes para AdaptiveStrengthEngineV3."""

    def test_initial_state(self):
        engine = AdaptiveStrengthEngineV3()
        assert engine._current_mult == 1.0

    def test_disabled_passthrough(self):
        engine = AdaptiveStrengthEngineV3()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            is_shooting=True,
            is_hit=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_high_hit_rate_reduces_mult(self):
        engine = AdaptiveStrengthEngineV3()
        for _ in range(20):
            engine.apply(
                1000.0, 1000.0,
                enabled=True,
                is_shooting=True,
                is_hit=True,
                delta_ms=16.67,
            )
        engine._update_short_window(0.7, 1.3)
        assert engine._target_mult <= 1.0

    def test_low_hit_rate_increases_mult(self):
        engine = AdaptiveStrengthEngineV3()
        for _ in range(20):
            engine.apply(
                1000.0, 1000.0,
                enabled=True,
                is_shooting=True,
                is_hit=False,
                delta_ms=16.67,
            )
        engine._update_short_window(0.7, 1.3)
        assert engine._target_mult >= 1.0

    def test_trend_detection(self):
        engine = AdaptiveStrengthEngineV3()
        engine._prev_hit_rate = 0.5
        engine._hits_short = 8
        engine._shots_short = 10
        engine._update_short_window(0.7, 1.3)
        assert engine._trend != 0.0

    def test_reset(self):
        engine = AdaptiveStrengthEngineV3()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            is_shooting=True,
            is_hit=True,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._current_mult == 1.0
        assert engine._shots_short == 0


class TestEngagementDetectorV3:
    """Testes para EngagementDetectorV3."""

    def test_initial_state(self):
        detector = EngagementDetectorV3()
        assert detector.state == EngagementState.IDLE

    def test_idle_detection(self):
        detector = EngagementDetectorV3()
        state = detector.update(0.0, 0.0, False, False, 16.67)
        assert state == EngagementState.IDLE

    def test_tracking_detection(self):
        detector = EngagementDetectorV3()
        state = detector.update(1000.0, 1000.0, False, False, 16.67)
        assert state in (EngagementState.TRACKING, EngagementState.SEARCHING)

    def test_locked_detection(self):
        detector = EngagementDetectorV3()
        state = detector.update(100.0, 100.0, False, True, 16.67)
        assert state == EngagementState.LOCKED

    def test_spray_detection(self):
        detector = EngagementDetectorV3()
        for _ in range(6):
            detector.update(500.0, 500.0, True, False, 16.67)
        assert detector.is_spraying is True

    def test_confidence_building(self):
        detector = EngagementDetectorV3()
        for _ in range(10):
            detector.update(100.0, 100.0, True, True, 16.67)
        assert detector.confidence > 0.0

    def test_hysteresis(self):
        detector = EngagementDetectorV3()
        detector.update(5000.0, 5000.0, False, False, 16.67)
        state1 = detector.state
        detector.update(100.0, 100.0, True, False, 16.67)
        state2 = detector.state
        assert state2.value >= state1.value

    def test_reset(self):
        detector = EngagementDetectorV3()
        detector.update(1000.0, 1000.0, True, False, 16.67)
        detector.reset()
        assert detector.state == EngagementState.IDLE
        assert detector.confidence == 0.0
