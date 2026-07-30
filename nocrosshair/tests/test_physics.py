import math
import pytest
from nocrosshair.core.config import StickPhysicsConfig, TriggerPhysicsConfig
from nocrosshair.features.physics import (
    StickPhysicsEngine, TriggerPhysicsEngine, apply_recoil_curve_factor
)


class TestStickPhysicsZeroInput:

    def test_zero_returns_zero(self):
        cfg = StickPhysicsConfig()
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(0, 0)
        assert x == 0
        assert y == 0


class TestStickPhysicsDeadzone:

    def test_below_deadzone_blocked(self):
        cfg = StickPhysicsConfig(deflection_min=0.5)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(5000, 0)
        assert x == 0
        assert y == 0

    def test_above_deadzone_passes(self):
        cfg = StickPhysicsConfig(deflection_min=0.5, deflection_max=1.0)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(20000, 0)
        assert x > 0


class TestStickPhysicsFullInput:

    def test_full_input_passes(self):
        cfg = StickPhysicsConfig()
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(32767, 0)
        assert x != 0

    def test_output_clamped(self):
        cfg = StickPhysicsConfig(initial_speed=1.0)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(32767, 32767)
        assert -32768 <= x <= 32767
        assert -32768 <= y <= 32767


class TestTriggerPhysicsHairTrigger:

    def test_zero_returns_zero(self):
        cfg = TriggerPhysicsConfig(hair_trigger=True)
        engine = TriggerPhysicsEngine(cfg)
        assert engine.apply(0) == 0

    def test_nonzero_returns_255(self):
        cfg = TriggerPhysicsConfig(hair_trigger=True)
        engine = TriggerPhysicsEngine(cfg)
        assert engine.apply(1) == 255
        assert engine.apply(128) == 255
        assert engine.apply(255) == 255


class TestTriggerPhysicsDeadzone:

    def test_below_deadzone_blocked(self):
        cfg = TriggerPhysicsConfig(hair_trigger=False, deadzone=0.1, sensitivity=1.0)
        engine = TriggerPhysicsEngine(cfg)
        assert engine.apply(10) == 0

    def test_above_deadzone_passes(self):
        cfg = TriggerPhysicsConfig(hair_trigger=False, deadzone=0.1, sensitivity=1.0)
        engine = TriggerPhysicsEngine(cfg)
        val = engine.apply(128)
        assert val > 0


class TestTriggerPhysicsFullPress:

    def test_full_press_max(self):
        cfg = TriggerPhysicsConfig(hair_trigger=False, deadzone=0.0, sensitivity=1.0)
        engine = TriggerPhysicsEngine(cfg)
        val = engine.apply(255)
        assert val == 255

    def test_output_clamped(self):
        cfg = TriggerPhysicsConfig(hair_trigger=False, deadzone=0.0, sensitivity=0.5)
        engine = TriggerPhysicsEngine(cfg)
        val = engine.apply(255)
        assert 0 <= val <= 255


class TestRecoilCurveFactor:

    def test_ease_out_decreases(self):
        start = apply_recoil_curve_factor(0, 10, "ease_out")
        mid = apply_recoil_curve_factor(5, 10, "ease_out")
        end = apply_recoil_curve_factor(9, 10, "ease_out")
        assert start > mid > end

    def test_ease_in_increases(self):
        start = apply_recoil_curve_factor(0, 10, "ease_in")
        mid = apply_recoil_curve_factor(5, 10, "ease_in")
        end = apply_recoil_curve_factor(9, 10, "ease_in")
        assert start < mid < end

    def test_linear_constant(self):
        a = apply_recoil_curve_factor(0, 10, "linear")
        b = apply_recoil_curve_factor(5, 10, "linear")
        c = apply_recoil_curve_factor(9, 10, "linear")
        assert a == 1.0
        assert b == 1.0
        assert c == 1.0


class TestStickPhysicsAntiDeadzone:

    def test_anti_deadzone_boosts_below_threshold(self):
        cfg = StickPhysicsConfig(deflection_min=0.0, anti_deadzone=20)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(5000, 0)
        mag = math.sqrt(x * x + y * y)
        expected_min = (20 / 100.0) * 32768.0
        assert mag >= expected_min * 0.99

    def test_anti_deadzone_no_effect_above_threshold(self):
        cfg = StickPhysicsConfig(deflection_min=0.0, anti_deadzone=20)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(30000, 0)
        qqq = 30000 / 32768.0
        expected = int(qqq * 32768.0)
        assert abs(x - expected) < 100

    def test_anti_deadzone_zero_disabled(self):
        cfg = StickPhysicsConfig(deflection_min=0.0, anti_deadzone=0)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(1000, 0)
        assert x == 1000


class TestStickPhysicsRawMode:

    def test_raw_mode_skips_squaring(self):
        cfg = StickPhysicsConfig(
            deflection_min=0.0, deflection_max=1.0,
            square_stick=True, squaring_factor=1.0,
            raw_mode=True,
        )
        engine = StickPhysicsEngine(cfg)
        x_sq, y_sq = engine.apply(20000, 15000)
        mag_sq = math.sqrt(x_sq * x_sq + y_sq * y_sq)
        input_mag = math.sqrt(20000 * 20000 + 15000 * 15000)
        assert abs(mag_sq - input_mag) < 100

    def test_raw_mode_off_squaring_applied(self):
        cfg = StickPhysicsConfig(
            deflection_min=0.0, deflection_max=1.0,
            square_stick=True, squaring_factor=1.0,
            raw_mode=False,
        )
        engine = StickPhysicsEngine(cfg)
        x_sq, y_sq = engine.apply(20000, 15000)
        mag_sq = math.sqrt(x_sq * x_sq + y_sq * y_sq)
        input_mag = math.sqrt(20000 * 20000 + 15000 * 15000)
        assert mag_sq > input_mag + 500


class TestStickPhysicsResponseCurve:

    def test_linear_default(self):
        cfg = StickPhysicsConfig(response_curve="linear", acceleration=1.0)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(16384, 0)
        assert x == 16384

    def test_raw_bypasses_accel(self):
        cfg = StickPhysicsConfig(response_curve="raw", acceleration=3.0)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(16384, 0)
        assert x == 16384

    def test_exponential_steeper(self):
        linear = StickPhysicsEngine(StickPhysicsConfig(response_curve="linear", acceleration=1.0))
        exp = StickPhysicsEngine(StickPhysicsConfig(response_curve="exponential", acceleration=1.0))
        x_lin, _ = linear.apply(10000, 0)
        x_exp, _ = exp.apply(10000, 0)
        assert x_exp < x_lin

    def test_aggressive_higher_than_linear(self):
        linear = StickPhysicsEngine(StickPhysicsConfig(response_curve="linear", acceleration=1.0, initial_speed=0.0))
        aggr = StickPhysicsEngine(StickPhysicsConfig(response_curve="aggressive", acceleration=1.0, initial_speed=0.0))
        x_lin, _ = linear.apply(20000, 0)
        x_ag, _ = aggr.apply(20000, 0)
        assert x_ag > x_lin

    def test_precise_low_input(self):
        cfg = StickPhysicsConfig(response_curve="precise", acceleration=1.0)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(5000, 0)
        assert x > 0
