#!/usr/bin/env python3

import math
import pytest
from nocrosshair.features.aimlock_proto import (
    AimLockProtoConfig, AimLockProtoEngine, AimLockTestbed,
)


def base_cfg(**kw) -> AimLockProtoConfig:
    """Config base dos testes legados — mecânicas Super desligadas para
    preservar o contrato do engine clássico (os testes Super ativam
    explicitamente os campos novos)."""
    kw.setdefault("humanize", False)
    kw.setdefault("seed", 1234)
    kw.setdefault("pull_max_rate_deg_s", 0.0)
    kw.setdefault("pull_ramp_up_ms", 0.0)
    kw.setdefault("initial_downsight_mult", 1.0)
    kw.setdefault("initial_downsight_ms", 0.0)
    kw.setdefault("center_strength_mult", 1.0)
    kw.setdefault("glue_drift_mult", 1.0)
    kw.setdefault("glue_drift_window_deg", 0.0)
    kw.setdefault("target_bone", "body")
    kw.setdefault("lock_timeout_ms", 0.0)
    return AimLockProtoConfig(**kw)


class TestDisabled:

    def test_disabled_no_output(self):
        tb = AimLockTestbed(base_cfg(enabled=False))
        tb.aim_at(10, 5, 5000)
        assert tb.compute(0, 0) == (0.0, 0.0)
        assert tb.engine.engaged is False

    def test_disabled_never_engages(self):
        tb = AimLockTestbed(base_cfg(enabled=False))
        tb.aim_at(2, 1, 5000)
        for _ in range(10):
            assert tb.compute(0, 0) == (0.0, 0.0)
        assert tb.engine.engaged is False


class TestAngleMath:

    def test_forward_target_zero_error(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False))
        tb.aim_at(0, 0, 5000)
        yaw, pitch = tb.engine.target_angles()
        assert math.isclose(yaw, 0.0, abs_tol=1e-9)
        assert math.isclose(pitch, 0.0, abs_tol=1e-9)

    def test_offset_angles(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False))
        tb.aim_at(10, 5, 5000)
        yaw, pitch = tb.engine.target_angles()
        assert math.isclose(yaw, 10.0, abs_tol=1e-6)
        assert math.isclose(pitch, 5.0, abs_tol=1e-6)

    def test_negative_yaw(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False))
        tb.aim_at(-10, 0, 5000)
        yaw, pitch = tb.engine.target_angles()
        assert math.isclose(yaw, -10.0, abs_tol=1e-6)
        assert math.isclose(pitch, 0.0, abs_tol=1e-6)

    def test_yaw_wraps_180(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=180, prediction_enabled=False))
        tb.aim_at(190, 0, 5000)
        yaw, _ = tb.engine.target_angles()
        assert math.isclose(yaw, -170.0, abs_tol=1e-6)

    def test_wrap180_helper(self):
        eng = AimLockProtoEngine()
        assert math.isclose(eng.wrap180(190.0), -170.0, abs_tol=1e-9)
        assert math.isclose(eng.wrap180(-190.0), 170.0, abs_tol=1e-9)
        assert math.isclose(eng.wrap180(360.0), 0.0, abs_tol=1e-9)
        assert math.isclose(eng.wrap180(450.0), 90.0, abs_tol=1e-9)


class TestFovGate:

    def test_outside_fov_not_engaged(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30))
        tb.aim_at(40, 0, 5000)
        assert tb.compute(0, 0) == (0.0, 0.0)
        assert tb.engine.engaged is False

    def test_inside_fov_engaged(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30))
        tb.aim_at(10, 0, 5000)
        rx, ry = tb.compute(0, 0)
        assert rx > 0
        assert tb.engine.engaged is True

    def test_hysteresis_holds_lock(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30, fov_hysteresis=1.2,
                                     snappiness=1.0, smoothing_rate=100.0))
        tb.aim_at(25, 0, 5000)
        assert tb.compute(0, 0)[0] > 0
        assert tb.engine.engaged is True
        tb.aim_at(35, 0, 5000)
        assert tb.compute(0, 0)[0] > 0
        assert tb.engine.engaged is True

    def test_hysteresis_drops_beyond_exit(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30, fov_hysteresis=1.2))
        tb.aim_at(25, 0, 5000)
        tb.compute(0, 0)
        tb.aim_at(37, 0, 5000)
        assert tb.compute(0, 0) == (0.0, 0.0)
        assert tb.engine.engaged is False

    def test_reengage_after_drop(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30, fov_hysteresis=1.2))
        tb.aim_at(25, 0, 5000)
        tb.compute(0, 0)
        tb.aim_at(40, 0, 5000)
        assert tb.compute(0, 0) == (0.0, 0.0)
        tb.aim_at(10, 0, 5000)
        assert tb.compute(0, 0)[0] > 0
        assert tb.engine.engaged is True


class TestSmoothing:

    def test_first_order_monotonic_convergence(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=60, smoothing_rate=8.0))
        tb.aim_at(30, 0, 5000)
        outputs = []
        for _ in range(40):
            rx, _ = tb.compute(0, 0, 16.0)
            outputs.append(rx)
        assert all(b > a for a, b in zip(outputs, outputs[1:]))
        assert math.isclose(outputs[-1], 32767.0 * (30.0 / 30.0), rel_tol=0.02)

    def test_dt_independent(self):
        cfg = base_cfg(fov_degrees=60, smoothing_rate=8.0, snappiness=0.5)
        a = AimLockTestbed(cfg)
        b = AimLockTestbed(cfg)
        a.aim_at(30, 5, 5000)
        b.aim_at(30, 5, 5000)
        for _ in range(8):
            a.compute(0, 0, 16.0)
        for _ in range(4):
            b.compute(0, 0, 32.0)
        assert math.isclose(a.engine._sm_yaw, b.engine._sm_yaw, abs_tol=1e-9)
        assert math.isclose(a.engine._sm_pitch, b.engine._sm_pitch, abs_tol=1e-9)

    def test_snappiness_zero_pure_filter(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=60, snappiness=0.0,
                                     smoothing_rate=8.0))
        tb.aim_at(30, 0, 5000)
        rx, _ = tb.compute(0, 0, 16.0)
        assert math.isclose(rx, 32767.0 * (1 - math.exp(-8.0 * 0.016)) * 30.0 / 30.0,
                            rel_tol=1e-6)


class TestPrediction:

    def test_lead_moves_aim_toward_velocity(self):
        cfg = base_cfg(snappiness=1.0, smoothing_rate=100.0,
                       prediction_enabled=True, bullet_speed=30000.0)
        tb = AimLockTestbed(cfg)
        tb.aim_at(0, 0, 5000, vel=(0, 300, 0))
        rx_pred, _ = tb.compute(0, 0)
        tb_nopred = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0,
                                            prediction_enabled=False))
        tb_nopred.aim_at(0, 0, 5000, vel=(0, 300, 0))
        rx_nopred, _ = tb_nopred.compute(0, 0)
        t = 5000.0 / 30000.0
        expected_deg = math.degrees(math.atan2(300.0 * t, 5000.0))
        assert rx_pred > rx_nopred + 100
        assert math.isclose(rx_pred, 32767.0 * expected_deg / 30.0, rel_tol=0.05)

    def test_gravity_drop_aims_higher(self):
        cfg = base_cfg(snappiness=1.0, smoothing_rate=100.0,
                       prediction_enabled=True, bullet_speed=30000.0,
                       gravity_scale=0.12, world_gravity=980.0)
        tb = AimLockTestbed(cfg)
        tb.aim_at(0, 0, 5000)
        rx_pred, ry_pred = tb.compute(0, 0)
        tb_nopred = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0,
                                            prediction_enabled=False))
        tb_nopred.aim_at(0, 0, 5000)
        rx_nopred, ry_nopred = tb_nopred.compute(0, 0)
        assert ry_pred < ry_nopred
        assert math.isclose(rx_pred, rx_nopred, abs_tol=1e-6)

    def test_no_velocity_no_lead(self):
        tb = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0))
        tb.aim_at(0, 0, 5000)
        rx, _ = tb.compute(0, 0)
        assert abs(rx) < 1e-6


class TestOutput:

    def test_clamped_full_deflection(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=120, snappiness=1.0,
                                     smoothing_rate=100.0))
        tb.aim_at(90, 0, 1000)
        rx, _ = tb.compute(0, 0)
        assert rx == 32767.0

    def test_sign_yaw_right(self):
        tb = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0))
        tb.aim_at(10, 0, 5000)
        rx, _ = tb.compute(0, 0)
        assert rx > 0

    def test_sign_yaw_left(self):
        tb = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0))
        tb.aim_at(-10, 0, 5000)
        rx, _ = tb.compute(0, 0)
        assert rx < 0

    def test_sign_pitch_up_ry_negative(self):
        tb = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0))
        tb.aim_at(0, 10, 5000)
        _, ry = tb.compute(0, 0)
        assert ry < 0

    def test_sign_pitch_down_ry_positive(self):
        tb = AimLockTestbed(base_cfg(snappiness=1.0, smoothing_rate=100.0))
        tb.aim_at(0, -10, 5000)
        _, ry = tb.compute(0, 0)
        assert ry > 0

    def test_no_nan_on_odd_deltas(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=60))
        tb.aim_at(20, 10, 5000)
        for dt in (0.0, -5.0, 0.0001, 16.0, 1000.0):
            rx, ry = tb.compute(0, 0, dt)
            assert math.isfinite(rx)
            assert math.isfinite(ry)
            assert abs(rx) <= 32767.0 + 1e-9
            assert abs(ry) <= 32767.0 + 1e-9

    def test_no_nan_target_at_eye(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=60))
        tb.engine.set_target((0, 0, 0), (0, 0, 0))
        rx, ry = tb.compute(0, 0, 16.0)
        assert math.isfinite(rx)
        assert math.isfinite(ry)

    def test_reset_clears_lock(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30))
        tb.aim_at(10, 0, 5000)
        tb.compute(0, 0)
        assert tb.engine.engaged is True
        tb.engine.reset()
        assert tb.engine.engaged is False
        tb.aim_at(90, 0, 5000)
        assert tb.compute(0, 0) == (0.0, 0.0)
        assert tb.engine.engaged is False


class TestHumanize:

    def test_noise_bounded(self):
        clean = base_cfg(snappiness=1.0, smoothing_rate=100.0,
                         fov_degrees=60, humanize=False, seed=1)
        noisy = base_cfg(snappiness=1.0, smoothing_rate=100.0,
                         fov_degrees=60, humanize=True, noise_degrees=0.25, seed=1)
        tb_clean = AimLockTestbed(clean)
        tb_noisy = AimLockTestbed(noisy)
        tb_clean.aim_at(30, 0, 5000)
        tb_noisy.aim_at(30, 0, 5000)
        rx_clean, _ = tb_clean.compute(0, 0)
        rx_noisy, _ = tb_noisy.compute(0, 0)
        max_shift = 32767.0 * 0.25 / 30.0
        assert abs(rx_noisy - rx_clean) <= max_shift + 1e-6

    def test_deterministic_with_seed(self):
        cfg = base_cfg(humanize=True, noise_degrees=0.25, seed=42)
        a = AimLockTestbed(cfg)
        b = AimLockTestbed(cfg)
        a.aim_at(15, 7, 5000)
        b.aim_at(15, 7, 5000)
        out_a = [a.compute(0, 0, 16.0) for _ in range(5)]
        out_b = [b.compute(0, 0, 16.0) for _ in range(5)]
        assert all(math.isclose(x1, x2, abs_tol=1e-9) for (x1, _), (x2, _) in zip(out_a, out_b))

    def test_different_seed_differs(self):
        a = AimLockTestbed(base_cfg(humanize=True, noise_degrees=0.25, seed=1))
        b = AimLockTestbed(base_cfg(humanize=True, noise_degrees=0.25, seed=2))
        a.aim_at(15, 7, 5000)
        b.aim_at(15, 7, 5000)
        ra, _ = a.compute(0, 0)
        rb, _ = b.compute(0, 0)
        assert ra != rb


class TestRateLimit:

    def test_stale_output_below_min_delta(self):
        tb = AimLockTestbed(base_cfg(fov_degrees=30))
        tb.aim_at(10, 0, 5000)
        out1 = tb.compute(0, 0, 16.0)
        assert out1 != (0.0, 0.0)
        out2 = tb.compute(0, 0, 1.0)
        assert out2 == out1


class TestUniversalSweep:

    @pytest.mark.parametrize("fov", [5.0, 15.0, 30.0, 45.0])
    @pytest.mark.parametrize("smoothing_rate", [2.0, 10.0, 30.0])
    @pytest.mark.parametrize("snappiness", [0.0, 0.5, 1.0])
    @pytest.mark.parametrize("prediction_enabled", [True, False])
    def test_sweep_finite_bounded(self, fov, smoothing_rate, snappiness, prediction_enabled):
        cfg = base_cfg(fov_degrees=fov, smoothing_rate=smoothing_rate,
                       snappiness=snappiness, prediction_enabled=prediction_enabled,
                       humanize=True, noise_degrees=0.25)
        tb = AimLockTestbed(cfg)
        tb.aim_at(12, 5, 5000)
        for _ in range(10):
            rx, ry = tb.compute(0, 0, 16.0)
            assert math.isfinite(rx) and math.isfinite(ry)
            assert abs(rx) <= 32767.0 + 1e-9
            assert abs(ry) <= 32767.0 + 1e-9
        dist = math.sqrt(12.0 ** 2 + 5.0 ** 2)
        assert tb.engine.engaged == (dist <= fov)

    @pytest.mark.parametrize("fov", [5.0, 30.0, 45.0])
    def test_sweep_outside_gate_stays_zero(self, fov):
        cfg = base_cfg(fov_degrees=fov, humanize=True, noise_degrees=0.25)
        tb = AimLockTestbed(cfg)
        tb.aim_at(60, 20, 5000)
        for _ in range(10):
            assert tb.compute(0, 0, 16.0) == (0.0, 0.0)
        assert tb.engine.engaged is False


class TestSuperSlow:
    """Adhesion/Slow: fator de aderência perto do centro (estilo FortAimAssist2D)."""

    def _tb(self, **kw) -> AimLockTestbed:
        kw.setdefault("adhesion_cone_deg", 8.0)
        kw.setdefault("slow_strength", 0.85)
        return AimLockTestbed(base_cfg(prediction_enabled=False, **kw))

    def test_zero_when_not_engaged(self):
        tb = self._tb()
        tb.aim_at(60, 0, 5000)
        tb.compute(0, 0)
        assert tb.engine.engaged is False
        assert tb.engine.slow_factor(0, 0) == 0.0

    def test_max_at_center(self):
        tb = self._tb()
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0)
        assert tb.engine.slow_factor(0, 0) == pytest.approx(0.85, abs=1e-6)

    def test_zero_outside_cone(self):
        tb = self._tb(adhesion_cone_deg=8.0)
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0)
        assert tb.engine.slow_factor(10, 0) == 0.0

    def test_linear_falloff(self):
        tb = self._tb(adhesion_cone_deg=10.0, slow_strength=1.0)
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0)
        mid = tb.engine.slow_factor(5, 0)
        assert mid == pytest.approx(0.5, abs=1e-6)

    def test_no_slow_when_strength_zero(self):
        tb = self._tb(slow_strength=0.0)
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0)
        assert tb.engine.slow_factor(0, 0) == 0.0


class TestSuperBurst:
    """InitialDownsight + RampUp: força extra nos primeiros ms após adquirir."""

    def test_burst_stronger_than_sustained(self):
        def first_out(mult: float) -> float:
            cfg = base_cfg(
                prediction_enabled=False,
                smoothing_rate=30.0, snappiness=0.0,
                pull_ramp_up_ms=0.0,
                initial_downsight_mult=mult, initial_downsight_ms=500.0,
            )
            tb = AimLockTestbed(cfg)
            tb.aim_at(10, 0, 5000)
            return tb.compute(0, 0, 16.0)[0]

        burst = first_out(3.0)
        sustained = first_out(1.0)
        assert burst > sustained, f"burst={burst} sustained={sustained}"

    def test_ramp_up_starts_soft(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=0.0,
            pull_ramp_up_ms=400.0,
            initial_downsight_mult=1.0, initial_downsight_ms=0.0,
            humanize=False,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(10, 0, 5000)
        early = tb.compute(0, 0, 16.0)
        for _ in range(20):
            tb.compute(0, 0, 16.0)
        late = tb.compute(0, 0, 16.0)
        assert abs(early[0]) < abs(late[0])

    def test_lock_age_resets_on_reacquire(self):
        cfg = base_cfg(prediction_enabled=False, humanize=False)
        tb = AimLockTestbed(cfg)
        tb.aim_at(15, 0, 5000)
        tb.compute(0, 0, 16.0)
        for _ in range(10):
            tb.compute(0, 0, 16.0)
        assert tb.engine.lock_age_ms is not None and tb.engine.lock_age_ms > 0
        tb.aim_at(60, 0, 5000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.lock_age_ms is None


class TestSuperPullMaxRate:
    """PullMaxRate: cap de rotação de correção por tick."""

    def test_output_delta_capped(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=1.0, humanize=False,
            pull_max_rate_deg_s=100.0,
            pull_ramp_up_ms=0.0,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(20, 0, 5000)
        dt_s = 0.016
        prev = 0.0
        for _ in range(20):
            rx, _ = tb.compute(0, 0, 16.0)
            deg = rx * cfg.degrees_full_stick / 32767.0
            delta = abs(deg - prev)
            assert delta <= 100.0 * dt_s + 1e-6
            prev = deg
        assert tb.engine.engaged

    def test_very_slow_rate_crawls(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=1.0, humanize=False,
            pull_max_rate_deg_s=1.0,
            pull_ramp_up_ms=0.0,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(20, 0, 5000)
        for _ in range(20):
            tb.compute(0, 0, 16.0)
        rx, _ = tb.compute(0, 0, 16.0)
        deg = abs(rx) * cfg.degrees_full_stick / 32767.0
        assert deg <= 1.0 * 0.336 + 1e-6, f"crawled {deg} deg em 336ms com rate 1 deg/s"
        assert deg > 0


class TestSuperMagnet:
    """SoftAimMagnet: clamp de correção por eixo."""

    def test_yaw_clamped(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=1.0, humanize=False,
            max_yaw_correction_deg=5.0, max_pitch_correction_deg=90.0,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(20, 0, 5000)
        rx, _ = tb.compute(0, 0, 16.0)
        deg = rx * cfg.degrees_full_stick / 32767.0
        assert deg <= 5.0 + 1e-6

    def test_pitch_clamped(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=1.0, humanize=False,
            max_yaw_correction_deg=90.0, max_pitch_correction_deg=3.0,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(0, 8, 5000)
        _, ry = tb.compute(0, 0, 16.0)
        deg = ry * cfg.degrees_full_stick / -32767.0
        assert deg <= 3.0 + 1e-6


class TestSuperCenterMult:
    """AngularStrengthMultiplier INVERTIDO: mais forte perto do centro."""

    def test_center_pulls_harder_than_edge(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=0.0, humanize=False,
            center_strength_mult=2.5, adhesion_cone_deg=20.0,
            smoothing_rate=30.0,
        )
        near = AimLockTestbed(cfg)
        near.aim_at(3, 0, 5000)
        rx_near, _ = near.compute(0, 0, 16.0)
        far = AimLockTestbed(cfg)
        far.aim_at(15, 0, 5000)
        rx_far, _ = far.compute(0, 0, 16.0)
        eff_near = rx_near / 3.0
        eff_far = rx_far / 15.0
        assert eff_near > eff_far, f"eff_near={eff_near} eff_far={eff_far}"

    def test_mult_one_is_neutral(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=0.0, humanize=False,
            center_strength_mult=1.0, adhesion_cone_deg=20.0,
            smoothing_rate=30.0,
        )
        near = AimLockTestbed(cfg)
        near.aim_at(3, 0, 5000)
        rx_near, _ = near.compute(0, 0, 16.0)
        far = AimLockTestbed(cfg)
        far.aim_at(15, 0, 5000)
        rx_far, _ = far.compute(0, 0, 16.0)
        eff_near = rx_near / 3.0
        eff_far = rx_far / 15.0
        assert math.isclose(eff_near, eff_far, rel_tol=0.05), \
            f"eff_near={eff_near} eff_far={eff_far}"


class TestSuperGlueDrift:
    """DistanceAheadToRampUp: agarra MAIS quando o alvo foge do cone."""

    def _eff(self, dist_deg: float, drift_mult: float) -> float:
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=0.0, humanize=False,
            center_strength_mult=1.0, adhesion_cone_deg=8.0,
            glue_drift_mult=drift_mult, glue_drift_window_deg=20.0,
            smoothing_rate=30.0,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(dist_deg, 0, 5000)
        rx, _ = tb.compute(0, 0, 16.0)
        return rx / dist_deg

    def test_drift_ramps_up_outside_cone(self):
        assert self._eff(16.0, 2.0) > self._eff(16.0, 1.0)

    def test_drift_saturates_at_window(self):
        assert self._eff(30.0, 2.0) > self._eff(16.0, 2.0)

    def test_inside_cone_center_mult_rules(self):
        cfg = base_cfg(
            prediction_enabled=False,
            snappiness=0.0, humanize=False,
            center_strength_mult=2.0, adhesion_cone_deg=8.0,
            glue_drift_mult=1.0, glue_drift_window_deg=20.0,
            smoothing_rate=30.0,
        )
        tb = AimLockTestbed(cfg)
        tb.aim_at(4.0, 0, 5000)
        rx, _ = tb.compute(0, 0, 16.0)
        eff = rx / 4.0
        flat = base_cfg(
            prediction_enabled=False,
            snappiness=0.0, humanize=False,
            center_strength_mult=1.0, adhesion_cone_deg=8.0,
            smoothing_rate=30.0,
        )
        tb2 = AimLockTestbed(flat)
        tb2.aim_at(4.0, 0, 5000)
        rx2, _ = tb2.compute(0, 0, 16.0)
        assert eff > rx2 / 4.0


class TestTargetBone:

    def test_head_bone_aims_up(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False,
                                     target_bone="head",
                                     head_height_cm=30.0))
        tb.aim_at(0, 0, 5000)
        _, pitch = tb.engine.target_angles()
        assert pitch > 0.3

    def test_body_bone_no_offset(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False,
                                     target_bone="body"))
        tb.aim_at(0, 0, 5000)
        _, pitch = tb.engine.target_angles()
        assert math.isclose(pitch, 0.0, abs_tol=1e-9)

    def test_auto_uses_head_when_locked(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False,
                                     target_bone="auto",
                                     head_height_cm=30.0))
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.engaged is True
        _, pitch = tb.engine.target_angles()
        assert pitch > 0.3

    def test_auto_uses_body_before_lock(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=False,
                                     target_bone="auto",
                                     head_height_cm=30.0,
                                     fov_degrees=2.0))
        tb.aim_at(0, 0, 5000)
        _, pitch = tb.engine.target_angles()
        assert math.isclose(pitch, 0.0, abs_tol=1e-9)

    def test_head_lock_corrects_pitch_upward(self):
        tb = AimLockTestbed(base_cfg(target_bone="head",
                                     head_height_cm=30.0))
        tb.aim_at(0, 0, 5000)
        rx, ry = tb.compute(0, 0, 16.0)
        assert ry < 0


class TestTrackingRange:

    def test_out_of_range_never_engages(self):
        tb = AimLockTestbed(base_cfg(max_tracking_distance_cm=50000.0))
        tb.aim_at(0, 0, 60000)
        rx, ry = tb.compute(0, 0, 16.0)
        assert rx == 0.0 and ry == 0.0
        assert tb.engine.engaged is False

    def test_within_range_engages(self):
        tb = AimLockTestbed(base_cfg(max_tracking_distance_cm=50000.0))
        tb.aim_at(0, 0, 40000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.engaged is True

    def test_locked_holds_with_hysteresis(self):
        tb = AimLockTestbed(base_cfg(max_tracking_distance_cm=50000.0))
        tb.aim_at(0, 0, 40000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.engaged is True
        tb.aim_at(0, 0, 55000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.engaged is True

    def test_releases_beyond_hysteresis(self):
        tb = AimLockTestbed(base_cfg(max_tracking_distance_cm=50000.0))
        tb.aim_at(0, 0, 40000)
        tb.compute(0, 0, 16.0)
        tb.aim_at(0, 0, 58000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.engaged is False


class TestLockTimeout:

    def test_releases_on_stale_target(self):
        tb = AimLockTestbed(base_cfg(lock_timeout_ms=500.0))
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0, 16.0)
        assert tb.engine.engaged is True
        tb.compute(0, 0, 600.0)
        assert tb.engine.engaged is False

    def test_holds_before_timeout(self):
        tb = AimLockTestbed(base_cfg(lock_timeout_ms=500.0))
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0, 16.0)
        tb.compute(0, 0, 400.0)
        assert tb.engine.engaged is True

    def test_target_update_resets_timer(self):
        tb = AimLockTestbed(base_cfg(lock_timeout_ms=500.0))
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0, 16.0)
        tb.compute(0, 0, 400.0)
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0, 400.0)
        assert tb.engine.engaged is True

    def test_timeout_zero_disables(self):
        tb = AimLockTestbed(base_cfg(lock_timeout_ms=0.0))
        tb.aim_at(0, 0, 5000)
        tb.compute(0, 0, 16.0)
        tb.compute(0, 0, 600.0)
        assert tb.engine.engaged is True


class TestKalmanVelocity:

    def test_kalman_converges_to_measurement(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=True,
                                     kalman_smoothing=0.3))
        tb.aim_at(10, 5, 5000, vel=(800.0, 0.0, 0.0))
        p0 = tb.engine.aim_point()
        for _ in range(40):
            tb.aim_at(10, 5, 5000, vel=(800.0, 0.0, 0.0))
        p1 = tb.engine.aim_point()
        raw = AimLockTestbed(base_cfg(prediction_enabled=True,
                                      kalman_smoothing=0.0))
        raw.aim_at(10, 5, 5000, vel=(800.0, 0.0, 0.0))
        pr = raw.engine.aim_point()
        assert math.isclose(p1[0], pr[0], rel_tol=1e-6)
        assert abs(p1[0] - pr[0]) < abs(p0[0] - pr[0])

    def test_kalman_zero_uses_raw(self):
        tb = AimLockTestbed(base_cfg(prediction_enabled=True,
                                     kalman_smoothing=0.0))
        tb.aim_at(10, 5, 5000, vel=(800.0, 0.0, 0.0))
        p0 = tb.engine.aim_point()
        tb.aim_at(10, 5, 5000, vel=(800.0, 0.0, 0.0))
        p1 = tb.engine.aim_point()
        assert math.isclose(p0[0], p1[0], abs_tol=1e-9)


class TestAdaptiveSmoothing:

    def test_fast_target_responds_faster(self):
        boost = AimLockTestbed(base_cfg(prediction_enabled=False,
                                        snappiness=0.0, humanize=False,
                                        smoothing_rate=10.0,
                                        velocity_adaptive_boost=2.0,
                                        velocity_adaptive_saturate=5000.0))
        flat = AimLockTestbed(base_cfg(prediction_enabled=False,
                                       snappiness=0.0, humanize=False,
                                       smoothing_rate=10.0,
                                       velocity_adaptive_boost=0.0))
        boost.aim_at(10, 0, 5000, vel=(5000.0, 0.0, 0.0))
        flat.aim_at(10, 0, 5000, vel=(5000.0, 0.0, 0.0))
        for _ in range(8):
            boost.compute(0, 0, 16.0)
            flat.compute(0, 0, 16.0)
        assert boost.engine._sm_yaw > flat.engine._sm_yaw

    def test_zero_boost_legacy_identical(self):
        a = AimLockTestbed(base_cfg(prediction_enabled=False,
                                    snappiness=0.0, humanize=False,
                                    smoothing_rate=10.0,
                                    velocity_adaptive_boost=0.0))
        b = AimLockTestbed(base_cfg(prediction_enabled=False,
                                    snappiness=0.0, humanize=False,
                                    smoothing_rate=10.0,
                                    velocity_adaptive_boost=0.0))
        a.aim_at(10, 0, 5000, vel=(5000.0, 0.0, 0.0))
        b.aim_at(10, 0, 5000, vel=(5000.0, 0.0, 0.0))
        for _ in range(8):
            a.compute(0, 0, 16.0)
            b.compute(0, 0, 16.0)
        assert math.isclose(a.engine._sm_yaw, b.engine._sm_yaw, abs_tol=1e-9)
