"""
 nocrosshair — test_aim_optimizer.py
 ═══════════════════════════════════════════════════════════════════════════════
 TESTES PARA O PIPELINE DE AIM ASSIST OTIMIZADO

 Testa os novos módulos:
   - aim_lut.py (lookup tables)
   - aim_engines.py (motores otimizados)
   - aim_optimizer.py (pipeline consolidado)

 ═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import math
from nocrosshair.features.aim_lut import aim_lut, AimLUT
from nocrosshair.features.aim_engines import (
    RotationalAAEngine,
    MagnetEngine,
    PredictEngine,
    MicroCorrectionEngine,
    AdaptiveStrengthEngine,
    EngagementState,
)
from nocrosshair.features.aim_optimizer import (
    AimOptimizerPipeline,
    EngagementDetector,
)


class TestAimLUT:
    """Testes para lookup tables otimizadas."""

    def test_sin_zero(self):
        assert aim_lut.sin(0.0) == pytest.approx(0.0, abs=1e-5)

    def test_sin_pi(self):
        assert aim_lut.sin(math.pi) == pytest.approx(0.0, abs=1e-5)

    def test_sin_pi_half(self):
        assert aim_lut.sin(math.pi / 2) == pytest.approx(1.0, abs=1e-3)

    def test_cos_zero(self):
        assert aim_lut.cos(0.0) == pytest.approx(1.0, abs=1e-5)

    def test_cos_pi(self):
        assert aim_lut.cos(math.pi) == pytest.approx(-1.0, abs=1e-3)

    def test_sqrt_zero(self):
        assert aim_lut.sqrt(0.0) == 0.0

    def test_sqrt_four(self):
        assert aim_lut.sqrt(4.0) == pytest.approx(2.0, abs=1e-3)

    def test_sqrt_large(self):
        assert aim_lut.sqrt(100000.0) == pytest.approx(math.sqrt(100000.0), rel=1e-3)

    def test_atan2_zero(self):
        assert aim_lut.atan2(0.0, 0.0) == 0.0

    def test_atan2_pi_half(self):
        assert aim_lut.atan2(1.0, 0.0) == pytest.approx(math.pi / 2, abs=1e-3)

    def test_normalize_angle(self):
        assert aim_lut.normalize_angle(0.0) == 0.0
        assert aim_lut.normalize_angle(2 * math.pi) == pytest.approx(0.0, abs=1e-5)
        assert aim_lut.normalize_angle(-math.pi) == pytest.approx(math.pi, abs=1e-3)

    def test_mag_xy(self):
        assert aim_lut.mag_xy(3.0, 4.0) == pytest.approx(5.0, abs=1e-3)

    def test_clamp(self):
        assert aim_lut.clamp(5.0, 0.0, 10.0) == 5.0
        assert aim_lut.clamp(-5.0, 0.0, 10.0) == 0.0
        assert aim_lut.clamp(15.0, 0.0, 10.0) == 10.0

    def test_lerp(self):
        assert aim_lut.lerp(0.0, 10.0, 0.5) == 5.0
        assert aim_lut.lerp(0.0, 10.0, 0.0) == 0.0
        assert aim_lut.lerp(0.0, 10.0, 1.0) == 10.0


class TestEngagementState:
    """Testes para estados de engajamento."""

    def test_states_exist(self):
        assert EngagementState.IDLE == 0
        assert EngagementState.SEARCHING == 1
        assert EngagementState.TRACKING == 2
        assert EngagementState.LOCKED == 3


class TestRotationalAAEngine:
    """Testes para engine de rotação adaptativa."""

    def test_disabled_passthrough(self):
        engine = RotationalAAEngine()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            state=EngagementState.TRACKING,
            zone=1000,
            speed=0.3,
            radius_mult=1.0,
            shape="circular",
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_idle_passthrough(self):
        engine = RotationalAAEngine()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.IDLE,
            zone=1000,
            speed=0.3,
            radius_mult=1.0,
            shape="circular",
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_adds_rotation(self):
        engine = RotationalAAEngine()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.TRACKING,
            zone=1000,
            speed=0.3,
            radius_mult=1.0,
            shape="circular",
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_reset(self):
        engine = RotationalAAEngine()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            state=EngagementState.TRACKING,
            zone=1000,
            speed=0.3,
            radius_mult=1.0,
            shape="circular",
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._angle == 0.0


class TestMagnetEngine:
    """Testes para engine de magnetismo unificada."""

    def test_disabled_passthrough(self):
        engine = MagnetEngine()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            strength=0.5,
            magnetic_pull=500,
            lock_fov=1000,
            lock_strength=500,
            lock_smooth=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_engaged_pull(self):
        engine = MagnetEngine()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=0.5,
            magnetic_pull=500,
            lock_fov=1000,
            lock_strength=500,
            lock_smooth=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx > 1000.0 or ry > 1000.0

    def test_persistence(self):
        engine = MagnetEngine()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=0.5,
            magnetic_pull=500,
            lock_fov=1000,
            lock_strength=500,
            lock_smooth=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        rx, ry = engine.apply(
            0.0, 0.0,
            enabled=True,
            strength=0.5,
            magnetic_pull=500,
            lock_fov=1000,
            lock_strength=500,
            lock_smooth=0.5,
            is_shooting=False,
            is_aiming=False,
            delta_ms=16.67,
        )
        assert rx != 0.0 or ry != 0.0

    def test_reset(self):
        engine = MagnetEngine()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=0.5,
            magnetic_pull=500,
            lock_fov=1000,
            lock_strength=500,
            lock_smooth=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._persist_rx == 0.0
        assert engine._persist_ry == 0.0


class TestPredictEngine:
    """Testes para engine de predição."""

    def test_first_call_zero(self):
        engine = PredictEngine()
        lead_x, lead_y = engine.predict(
            1000.0, 1000.0, 16.67,
            vel_alpha=0.15,
            accel_alpha=0.06,
            lead_horizon_ms=40.0,
            min_speed=200.0,
            max_lead=3000.0,
            consistency=3,
            kalman_weight=0.3,
        )
        assert lead_x == 0.0
        assert lead_y == 0.0

    def test_consistency_gate(self):
        engine = PredictEngine()
        for _ in range(2):
            engine.predict(
                1000.0, 1000.0, 16.67,
                vel_alpha=0.15,
                accel_alpha=0.06,
                lead_horizon_ms=40.0,
                min_speed=200.0,
                max_lead=3000.0,
                consistency=3,
                kalman_weight=0.3,
            )
        lead_x, lead_y = engine.predict(
            1000.0, 1000.0, 16.67,
            vel_alpha=0.15,
            accel_alpha=0.06,
            lead_horizon_ms=40.0,
            min_speed=200.0,
            max_lead=3000.0,
            consistency=3,
            kalman_weight=0.3,
        )
        assert lead_x == 0.0
        assert lead_y == 0.0

    def test_reset(self):
        engine = PredictEngine()
        engine.predict(
            1000.0, 1000.0, 16.67,
            vel_alpha=0.15,
            accel_alpha=0.06,
            lead_horizon_ms=40.0,
            min_speed=200.0,
            max_lead=3000.0,
            consistency=3,
            kalman_weight=0.3,
        )
        engine.reset()
        assert engine._prev_x is None


class TestMicroCorrectionEngine:
    """Testes para engine de micro-correções."""

    def test_disabled_passthrough(self):
        engine = MicroCorrectionEngine()
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

    def test_large_input_passthrough(self):
        engine = MicroCorrectionEngine()
        rx, ry = engine.apply(
            5000.0, 5000.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=5000.0,
            prev_ry=5000.0,
            delta_ms=16.67,
        )
        assert rx == 5000.0
        assert ry == 5000.0

    def test_axis_lock(self):
        engine = MicroCorrectionEngine()
        rx, ry = engine.apply(
            100.0, 10.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=100.0,
            prev_ry=10.0,
            delta_ms=16.67,
        )
        assert ry < 10.0

    def test_reset(self):
        engine = MicroCorrectionEngine()
        engine.apply(
            100.0, 10.0,
            enabled=True,
            pull_strength=0.3,
            prev_rx=100.0,
            prev_ry=10.0,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._persist_rx == 0.0


class TestAdaptiveStrengthEngine:
    """Testes para engine de força adaptativa."""

    def test_disabled_passthrough(self):
        engine = AdaptiveStrengthEngine()
        rx, ry = engine.apply(
            1000.0, 1000.0,
            enabled=False,
            is_shooting=True,
            is_hit=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_reset(self):
        engine = AdaptiveStrengthEngine()
        engine.apply(
            1000.0, 1000.0,
            enabled=True,
            is_shooting=True,
            is_hit=True,
            delta_ms=16.67,
        )
        engine.reset()
        assert engine._current_mult == 1.0


class TestEngagementDetector:
    """Testes para detector de engajamento."""

    def test_idle_state(self):
        detector = EngagementDetector()
        state = detector.update(0.0, 0.0, False, False, 16.67)
        assert state == EngagementState.IDLE

    def test_locked_state(self):
        detector = EngagementDetector()
        state = detector.update(50.0, 50.0, True, True, 16.67)
        assert state == EngagementState.LOCKED

    def test_tracking_state(self):
        detector = EngagementDetector()
        for _ in range(5):
            state = detector.update(1000.0, 1000.0, False, False, 16.67)
        assert state == EngagementState.TRACKING

    def test_reset(self):
        detector = EngagementDetector()
        detector.update(1000.0, 1000.0, True, True, 16.67)
        detector.reset()
        assert detector.state == EngagementState.IDLE


class TestAimOptimizerPipeline:
    """Testes para pipeline otimizado."""

    def test_disabled_passthrough(self):
        pipeline = AimOptimizerPipeline()

        class MockConfig:
            enabled = False

        rx, ry = pipeline.process(
            1000.0, 1000.0,
            is_shooting=True,
            is_aiming=True,
            is_moving=False,
            delta_ms=16.67,
            config=MockConfig(),
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_pipeline_runs(self):
        pipeline = AimOptimizerPipeline()

        class MockConfig:
            enabled = True
            rotational = True
            zone = 1000
            sticky_enabled = True
            magnetic_pull = 500
            sticky_strength = 0.5
            lock_fov = 1000
            lock_strength = 500
            lock_smooth = 0.5
            predictive_tracker_enabled = False
            micro_adjust_enabled = False
            adaptive_strength = False

        rx, ry = pipeline.process(
            1000.0, 1000.0,
            is_shooting=True,
            is_aiming=True,
            is_moving=False,
            delta_ms=16.67,
            config=MockConfig(),
        )
        assert -32767 <= rx <= 32767
        assert -32767 <= ry <= 32767

    def test_reset(self):
        pipeline = AimOptimizerPipeline()

        class MockConfig:
            enabled = True
            rotational = True
            zone = 1000
            sticky_enabled = True
            magnetic_pull = 500
            sticky_strength = 0.5
            lock_fov = 1000
            lock_strength = 500
            lock_smooth = 0.5
            predictive_tracker_enabled = False
            micro_adjust_enabled = False
            adaptive_strength = False

        pipeline.process(
            1000.0, 1000.0,
            is_shooting=True,
            is_aiming=True,
            is_moving=False,
            delta_ms=16.67,
            config=MockConfig(),
        )
        pipeline.reset()
        assert pipeline.engagement.state == EngagementState.IDLE
