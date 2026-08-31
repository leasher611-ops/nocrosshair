#!/usr/bin/env python3

import math
import pytest
from nocrosshair.features.aa_mobile_proto import (
    MobileAAProtoConfig, FortniteMobileAAProto, MobileAATestbed,
)


def base_cfg(**kw) -> MobileAAProtoConfig:
    kw.setdefault("humanize", False)
    kw.setdefault("easing_tau_ms", 1.0)
    kw.setdefault("seed", 1234)
    return MobileAAProtoConfig(**kw)


class TestSlider:

    def test_slider_zero_passthrough(self):
        tb = MobileAATestbed(base_cfg(strength_slider=0))
        rx, ry = tb.simulate(2000, 1000)
        assert rx == 2000
        assert ry == 1000

    def test_slider_clamped(self):
        tb = MobileAATestbed(base_cfg(strength_slider=150))
        rx, _ = tb.simulate(2000, 0)
        assert math.isfinite(rx)

    def test_slider_one_nearly_passthrough(self):
        tb = MobileAATestbed(base_cfg(strength_slider=1, rotational_enabled=False))
        rx, _ = tb.simulate(2000, 0)
        assert rx > 1500

    def test_slider_hundred_max_slowdown(self):
        tb = MobileAATestbed(base_cfg(strength_slider=100, rotational_enabled=False))
        rx, _ = tb.simulate(1000, 0)
        assert rx < 1000

    def test_not_aiming_passthrough(self):
        tb = MobileAATestbed(base_cfg())
        rx, ry = tb.simulate(3000, 1500, is_aiming=False, is_shooting=False)
        assert rx == 3000
        assert ry == 1500


class TestSlowdown:

    def test_slows_magnitude(self):
        tb = MobileAATestbed(base_cfg(rotational_enabled=False))
        rx, _ = tb.simulate(1000, 0)
        assert 0 < abs(rx) < 1000

    def test_slower_closer_to_center(self):
        tb = MobileAATestbed(base_cfg(rotational_enabled=False))
        near, _ = tb.simulate(1000, 0)
        far, _ = tb.simulate(4000, 0)
        assert (near / 1000.0) < (far / 4000.0)

    def test_no_slowdown_outside_zone(self):
        tb = MobileAATestbed(base_cfg(zone=500, rotational_enabled=False))
        rx, _ = tb.simulate(2000, 0)
        assert math.isclose(rx, 2000.0, rel_tol=1e-6)

    def test_curve_zero_no_slowdown(self):
        tb = MobileAATestbed(base_cfg(slow_curve=0.0, rotational_enabled=False))
        rx, _ = tb.simulate(1000, 0)
        assert math.isclose(rx, 1000.0, rel_tol=1e-6)

    def test_ads_multiplier_scale(self):
        tb = MobileAATestbed(base_cfg(rotational_enabled=False, ads_multiplier=1.5))
        rx, _ = tb.simulate(4000, 0)
        assert rx < 4000


class TestRotational:

    def test_adds_along_input_direction(self):
        on = MobileAATestbed(base_cfg(rotational_enabled=True))
        off = MobileAATestbed(base_cfg(rotational_enabled=False))
        rx_on, _ = on.simulate(3000, 0)
        rx_off, _ = off.simulate(3000, 0)
        assert rx_on > rx_off

    def test_no_rotational_below_gate(self):
        on = MobileAATestbed(base_cfg(rotational_enabled=True))
        off = MobileAATestbed(base_cfg(rotational_enabled=False))
        rx_on, _ = on.simulate(300, 0)
        rx_off, _ = off.simulate(300, 0)
        assert math.isclose(rx_on, rx_off, abs_tol=1e-6)

    def test_zero_input_no_rotational(self):
        tb = MobileAATestbed(base_cfg())
        rx, ry = tb.simulate(0, 0)
        assert math.isclose(rx, 0.0, abs_tol=1e-6)
        assert math.isclose(ry, 0.0, abs_tol=1e-6)

    def test_stops_when_input_drops(self):
        on = MobileAATestbed(base_cfg(rotational_enabled=True))
        off = MobileAATestbed(base_cfg(rotational_enabled=False))
        on.simulate(3000, 0)
        on.simulate(3000, 0)
        for _ in range(30):
            on.simulate(300, 0)
            off.simulate(300, 0)
        rx_on, _ = on.simulate(300, 0)
        rx_off, _ = off.simulate(300, 0)
        assert math.isclose(rx_on, rx_off, abs_tol=1e-3)

    def test_ramps_in_over_frames(self):
        tb = MobileAATestbed(base_cfg())
        outs = []
        for _ in range(20):
            rx, _ = tb.simulate(3000, 0)
            outs.append(rx)
        assert all(b >= a for a, b in zip(outs, outs[1:]))
        assert outs[-1] > outs[0]

    def test_move_boost_increases_pull(self):
        cfg = base_cfg(move_boost=2.0)
        moving = MobileAATestbed(cfg)
        still = MobileAATestbed(cfg)
        for _ in range(20):
            rx_m, _ = moving.simulate(3000, 0, is_moving=True)
            rx_s, _ = still.simulate(3000, 0, is_moving=False)
        assert rx_m > rx_s


class TestLayers:

    def test_big_input_enters_camera(self):
        tb = MobileAATestbed(base_cfg())
        tb.simulate(20000, 0)
        assert tb.engine.in_camera_layer is True

    def test_hysteresis_holds_camera(self):
        tb = MobileAATestbed(base_cfg())
        tb.simulate(20000, 0)
        tb.simulate(15000, 0)
        assert tb.engine.in_camera_layer is True

    def test_exits_to_aim(self):
        tb = MobileAATestbed(base_cfg())
        tb.simulate(20000, 0)
        tb.simulate(13000, 0)
        assert tb.engine.in_camera_layer is False

    def test_small_input_stays_aim(self):
        tb = MobileAATestbed(base_cfg())
        tb.simulate(3000, 0)
        assert tb.engine.in_camera_layer is False

    def test_camera_layer_weaker_slowdown(self):
        cam = MobileAATestbed(base_cfg(zone=30000, rotational_enabled=False))
        aim = MobileAATestbed(base_cfg(zone=30000, rotational_enabled=False))
        rx_cam, _ = cam.simulate(20000, 0)
        rx_aim, _ = aim.simulate(6000, 0)
        assert (rx_cam / 20000.0) > (rx_aim / 6000.0)


class TestHumanize:

    def test_deterministic_with_seed(self):
        cfg = base_cfg(humanize=True, seed=7)
        a = MobileAATestbed(cfg)
        b = MobileAATestbed(cfg)
        for _ in range(5):
            out_a = a.simulate(3000, 1000)
            out_b = b.simulate(3000, 1000)
            assert all(math.isclose(x, y, abs_tol=1e-9) for x, y in zip(out_a, out_b))

    def test_noise_bounded(self):
        noisy = MobileAATestbed(base_cfg(humanize=True, seed=7))
        clean = MobileAATestbed(base_cfg(humanize=False))
        rx_n, ry_n = noisy.simulate(3000, 1000)
        rx_c, ry_c = clean.simulate(3000, 1000)
        assert abs(rx_n - rx_c) <= 30.0 + 1e-6
        assert abs(ry_n - ry_c) <= 30.0 + 1e-6


class TestUniversalSweep:

    @pytest.mark.parametrize("slider", [0, 1, 50, 100])
    @pytest.mark.parametrize("zone", [1000, 6000, 15000])
    @pytest.mark.parametrize("input_mag", [(0, 0), (500, 500), (3000, 1000), (25000, 25000)])
    def test_sweep_finite_bounded(self, slider, zone, input_mag):
        cfg = base_cfg(strength_slider=slider, zone=zone,
                       humanize=True, seed=3, easing_tau_ms=24.0)
        tb = MobileAATestbed(cfg)
        for dt in (0.0, 16.0, 1000.0):
            rx, ry = tb.simulate(input_mag[0], input_mag[1], delta_ms=dt)
            assert math.isfinite(rx) and math.isfinite(ry)
            assert abs(rx) <= 32767.0 + 1e-9
            assert abs(ry) <= 32767.0 + 1e-9

    def test_sweep_never_amplifies_beyond_cap(self):
        tb = MobileAATestbed(base_cfg(rotation_cap=500))
        max_rx = 0
        for _ in range(40):
            rx, _ = tb.simulate(20000, 0)
            max_rx = max(max_rx, rx)
        assert max_rx <= 32767.0

    def test_reset_clears_state(self):
        tb = MobileAATestbed(base_cfg())
        tb.simulate(3000, 0)
        assert tb.engine.rotation_engaged is True
        tb.engine.reset()
        assert tb.engine.rotation_engaged is False
        assert tb.engine.in_camera_layer is False


class TestPipelineWiring:

    def _pipeline(self, **overrides):
        from nocrosshair.core.config import AimAssistConfig
        from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPipeline
        fn_slow = overrides.pop("fn_slow_strength", 0.0)
        fn_pull = overrides.pop("fn_pull_strength", 0.0)
        fn_magnet = overrides.pop("fn_magnet_force", 0.0)
        cfg = AimAssistConfig(
            enabled=True,
            base_aa_enabled=False,
            rotational=False,
            anti_flinch=False,
            adaptive_strength=False,
            anti_shake_blend=0.0,
            enhanced_enabled=False,
            sticky_enabled=False,
            lock_enabled=False,
            head_assist_enabled=False,
            auto_rotation_enabled=False,
            fn_slow_strength=fn_slow,
            fn_pull_strength=fn_pull,
            fn_magnet_force=fn_magnet,
            **overrides,
        )
        return AimAssistPipeline(AimAssistEngine(cfg))

    def test_slider_zero_passthrough(self):
        p = self._pipeline(fn_strength_slider=0)
        rx, ry = p.apply(2000, 1000, True, True, False, 16.0, p.aa_engine.cfg, 0, 0)
        assert rx == 2000
        assert ry == 1000

    def test_slider_hundred_slows(self):
        p = self._pipeline(fn_strength_slider=100, fn_slow_strength=0.8)
        rx, _ = p.apply(1000, 0, True, True, False, 16.0, p.aa_engine.cfg, 0, 0)
        assert 0 < rx < 1000

    def test_rotational_adds_to_input(self):
        p_on = self._pipeline(fn_magnet_force=0.65)
        p_off = self._pipeline(fn_magnet_force=0.0)
        rx_on = rx_off = 0
        for _ in range(15):
            rx_on, _ = p_on.apply(3000, 0, True, True, False, 16.0, p_on.aa_engine.cfg, 0, 0)
            rx_off, _ = p_off.apply(3000, 0, True, True, False, 16.0, p_off.aa_engine.cfg, 0, 0)
        assert rx_on > rx_off

    def test_zero_input_no_output(self):
        p = self._pipeline(fn_strength_slider=100, fn_magnet_force=0.65)
        rx, ry = p.apply(0, 0, True, True, False, 16.0, p.aa_engine.cfg, 0, 0)
        assert math.isclose(rx, 0.0, abs_tol=1.0)
        assert math.isclose(ry, 0.0, abs_tol=1.0)

    def test_layer_strength_scales_engine(self):
        p = self._pipeline(fn_strength_slider=100, fn_slow_strength=1.0,
                           fn_layer_strength=1.5, fn_magnet_force=0.0)
        rx, _ = p.apply(1000, 0, True, True, False, 16.0, p.aa_engine.cfg, 0, 0)
        assert rx < 1000


class TestStickyLayers:

    def test_higher_camera_keep_slows_more(self):
        weak = MobileAATestbed(base_cfg(zone=30000, rotational_enabled=False,
                                        camera_slow_keep=0.5))
        strong = MobileAATestbed(base_cfg(zone=30000, rotational_enabled=False,
                                          camera_slow_keep=1.0))
        rx_w, _ = weak.simulate(20000, 0)
        rx_s, _ = strong.simulate(20000, 0)
        assert rx_s < rx_w

    def test_camera_floor_pulls_in_camera_layer(self):
        tb = MobileAATestbed(base_cfg(camera_threshold=18000, zone=6000,
                                      camera_pull_floor=0.55,
                                      aim_pull_floor=0.0,
                                      rotation_cap=1000))
        rx, _ = tb.simulate(20000, 0)
        assert rx > 20000

    def test_camera_floor_stronger_than_aim_floor(self):
        cam = MobileAATestbed(base_cfg(camera_threshold=18000, zone=6000,
                                       aim_pull_floor=0.0,
                                       camera_pull_floor=0.9,
                                       rotation_cap=1000))
        rx_cam, _ = cam.simulate(20000, 0)
        assert rx_cam > 20000

    def test_aim_floor_zero_legacy_beyond_zone(self):
        legacy = MobileAATestbed(base_cfg(zone=6000, aim_pull_floor=0.0,
                                          rotation_cap=1000))
        rx, _ = legacy.simulate(15000, 0)
        assert math.isclose(rx, 15000.0, abs_tol=1e-6)
